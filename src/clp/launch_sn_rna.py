#!/usr/bin/env python3
"""Launch the single-nucleus RNA-seq (snRNA) workflow cascade for a library in Seqera cloud.
"""
import argparse
import os
import re
import sys
import getpass
from pathlib import Path
from typing import Any, Dict, List, Optional
import tempfile

import yaml
import subprocess

from manifest.util.documenter import TextYamlManifestDocumenter
from manifest.util.manifest_util import YamlManifestUtil
from manifest.manifest_keys import SnRnaManifestKey
import util.gcs_util as gcs_util
from manifest.constants import FASTQ_READ1, FASTQ_READ2

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_MODULE_DOC = __doc__


class LaunchSnRnaError(Exception):
    """A user-facing problem with the launch arguments, manifest, or cloud metadata."""


def _gcs_path_type(value: str) -> str:
    if not gcs_util.GCS_PATH_RE.match(value):
        raise argparse.ArgumentTypeError(f"not a gs:// path: '{value}'")
    return value


def _email_type(value: str) -> str:
    if not EMAIL_RE.match(value):
        raise argparse.ArgumentTypeError(f"not a valid email address: '{value}'")
    return value


def _manifest_path_type(value: str) -> Path:
    path = Path(value)
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"manifest file not found: '{path}'")
    return path


class LaunchSnRna:
    """Launches the snRNA workflow cascade for a library in Seqera cloud.

    Base class holding all the shared launch logic. Subclasses customize behavior by overriding
    `manifest_key_class` (used to validate the manifest and document its keys) and, if needed,
    `default_pipeline` or `prog_description`.
    """

    manifest_key_class = SnRnaManifestKey
    default_pipeline = "snRnaSeq_prod"
    prog_description = _MODULE_DOC

    def __init__(self) -> None:
        self.manifest: Dict[str, Any] = {}
        self.project_resources: Dict[str, Any] = {}
        self.tenx_metadata: Dict[str, Any] = {}

    class _ArgumentParser(argparse.ArgumentParser):
        def __init__(self, manifest_key_class, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._manifest_key_class = manifest_key_class

        def print_help(self, file=None) -> None:
            super().print_help(file)
            out = file if file is not None else sys.stdout
            print("\nManifest keys:", file=out)
            documenter = TextYamlManifestDocumenter(out=out)
            for element in self._manifest_key_class.get_documentation_recursive_roots():
                documenter.document_element_recursive(element, 0)
            for element in self._manifest_key_class.get_documentation_non_recursive_roots():
                documenter.document_element_non_recursive(element, 0)

    def build_parser(self) -> argparse.ArgumentParser:
        parser = self._ArgumentParser(self.manifest_key_class, description=self.prog_description)
        parser.add_argument(
            "manifest", type=_manifest_path_type, nargs="+",
            help="Local yaml manifest file describing the libraries to process.  If more than one manifest file "
                 "is provided, they will be combined with earlier manifest files taking precedence if key collisions.")
        parser.add_argument(
            "--project",
            help="Project name, used to look up project resources in the project metadata file.")
        parser.add_argument(
            "--project-metadata", type=_gcs_path_type, metavar="GCS_PATH",
            default="gs://mccarroll_scrnaseq_standard/metadata/project/project_metadata.yaml",
            help="gs:// path to a yaml file containing project resources, keyed by project name. Default: %(default)s)")
        parser.add_argument(
            "--tenx-metadata", type=_gcs_path_type, metavar="GCS_PATH",
            default='gs://mccarroll_scrnaseq_standard/metadata/10X/10X_version_metadata.yaml',
            help="gs:// path to a yaml file containing 10X chemistry version metadata. Default: %(default)s)")
        parser.add_argument(
            "--email", type=_email_type, metavar="EMAIL",
            default=f"{getpass.getuser()}@broadinstitute.org",
            help="Email address of the user launching this workflow. Default: %(default)s)")
        parser.add_argument(
            "--output-dir", type=_gcs_path_type, metavar="GCS_PATH",
            help="gs:// path under which workflow outputs will be written. Default: determined based on project and library")
        parser.add_argument("--pipeline", help="Nextflow pipeline to invoke.  Default: %(default)s)",
                            default=self.default_pipeline)
        parser.add_argument("--verbose", "-v", action="store_true", default=False)
        parser.add_argument("--dry-run", action="store_true",default=False,help="Don't actually run the workflow")
        parser.add_argument("--tw", default="tw",
                            help="Path to the TW executable. Use this if (annoyingly) PyCharm uv doesn't respect PATH changes.  Default: %(default)s)")
        return parser

    def parse_args(self, argv: Optional[List[str]] = None) -> argparse.Namespace:
        return self.build_parser().parse_args(argv)

    @staticmethod
    def load_manifest(manifest_path: Path) -> Dict[str, Any]:
        with open(manifest_path) as fh:
            loaded = yaml.safe_load(fh)
        if loaded is None:
            return {}
        if not isinstance(loaded, dict):
            raise LaunchSnRnaError(
                f"expected a yaml mapping in manifest '{manifest_path}', found {type(loaded).__name__}")
        return loaded

    def load_and_combine_manifests(self, manifest_paths: List[Path]) -> Dict[str, Any]:
        """Load each yaml manifest in order and merge them into one, with the earlier manifest taking precedence
        in the event of collisions."""
        combined: Dict[str, Any] = self.load_manifest(manifest_paths[0])
        for manifest_path in manifest_paths[1:]:
            manifest = self.load_manifest(manifest_path)
            combined = YamlManifestUtil.project_defaults(combined, manifest)
        return combined

    @staticmethod
    def resolve_project_resources(project_metadata: Dict[str, Any], project: str) -> Dict[str, Any]:
        if project not in project_metadata:
            raise LaunchSnRnaError(f"project '{project}' not found in project metadata")
        resources = project_metadata[project]
        if not isinstance(resources, dict):
            raise LaunchSnRnaError(
                f"expected a yaml mapping for project '{project}', found {type(resources).__name__}")
        return resources

    @staticmethod
    def get_tenx_metadata(tenx_version: str, tenx_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """find 10X version in tenx_metadata dictionary, and return that sub-dictionary."""
        if tenx_version not in tenx_metadata:
            raise LaunchSnRnaError(
                f"10X chemistry version(s) not found in 10X metadata: {tenx_version}")
        return tenx_metadata[tenx_version]

    @staticmethod
    def load_project_metadata(gcs_path: str) -> Dict[str, Any]:
        project_metadata = gcs_util.load_gcs_yaml(gcs_path)
        lstProjects = project_metadata['projects']
        # Convert the list of projects into a dictionary in which the key is the value of the 'name' element of each sub-dictionary
        dctProjects = {dctProject['name']: dctProject for dctProject in lstProjects}

        return dctProjects

    @staticmethod
    def load_tenx_metadata(gcs_path: str) -> Dict[str, Any]:
        tenx_metadata = gcs_util.load_gcs_yaml(gcs_path)
        # Convert the list of tenx metadata into a dictionary in which the key is the value of the 'version10X' element of each sub-dictionary
        dctTenxMetadata = {dctTenx['version10X']: dctTenx for dctTenx in tenx_metadata['versions']}
        return dctTenxMetadata

    def load_launch_state(self, args: argparse.Namespace) -> None:
        self.manifest = self.load_and_combine_manifests(args.manifest)
        self.manifests = [self.manifest]
        project_metadata = self.load_project_metadata(args.project_metadata)
        self.project_resources = self.resolve_project_resources(project_metadata, args.project)
        self.tenx_metadata = self.load_tenx_metadata(args.tenx_metadata)

    def get_manifests(self) -> List[Dict[str, Any]]:
        return self.manifests

    def launch_manifest(self, manifest: Dict[str, Any], args: argparse.Namespace) -> None:
        manifest.update(self.get_tenx_metadata(manifest['version10X'], self.tenx_metadata))
        if args.output_dir:
            outdir = args.output_dir
        else:
            outdir = f"gs://{self.project_resources['standard_bucket']}/projects/{self.project_resources['name']}/{manifest['library']}"
        manifest['outdir'] = outdir
        manifest['email'] = args.email
        for fastq in manifest[FASTQ_READ1] + manifest[FASTQ_READ2]:
            gcs_util.require_gcs_file(fastq)
        params_yaml = tempfile.mkstemp(suffix=".yaml", prefix=manifest['library'] + '.', text=True)
        with os.fdopen(params_yaml[0], "w") as f:
            yaml.safe_dump(manifest, f, default_flow_style=False, sort_keys=False)
        if args.verbose:
            print("Wrote manifest to " + params_yaml[1])
        lstCommandLine = [
            args.tw, "launch",
            "--workspace=" + self.project_resources['tower_workspace'],
            args.pipeline,
            "--params-file=" + params_yaml[1],
            "--name=x" + manifest['experimentDate'] + '_' + manifest['library'],
        ]
        if args.verbose or args.dry_run:
            print(" ".join(lstCommandLine))
        if not args.dry_run:
            subprocess.run(lstCommandLine, check=True)

    def main(self, argv: Optional[List[str]] = None) -> int:
        args = self.parse_args(argv)
        self.load_launch_state(args)
        errors = self.manifest_key_class.validate_manifest(self.manifest)
        if errors:
            print("Errors parsing manifest:\n" + "\n".join(errors), file=sys.stderr)
            return 1
        for manifest in self.get_manifests():
            self.launch_manifest(manifest, args)
        return 0


def main(argv: Optional[List[str]] = None) -> int:
    return LaunchSnRna().main(argv)


if __name__ == "__main__":
    sys.exit(main())
