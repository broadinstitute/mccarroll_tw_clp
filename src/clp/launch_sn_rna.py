#!/usr/bin/env python3
"""Launch the single-nucleus RNA-seq (snRNA) workflow cascade for a library in Seqera cloud.
"""
import argparse
import os
import re
import sys
import getpass
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
import tempfile
import shutil

import yaml
import subprocess

from manifest.util.documenter import TextYamlManifestDocumenter
from manifest.util.manifest_util import YamlManifestUtil
from manifest.manifest_keys import SnRnaManifestKey
import util.gcs_util as gcs_util

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class LaunchSnRnaError(Exception):
    """A user-facing problem with the launch arguments, manifest, or cloud metadata."""


@dataclass
class SnRnaLaunchContext:
    manifest_path: List[Path]
    manifest: Dict[str, Any]
    project: str
    project_resources: Optional[Dict[str, Any]]
    tenx_metadata: Optional[Dict[str, Any]]
    email: Optional[str]
    output_dir: Optional[str]

    def describe(self) -> str:
        lines = [
            "Launching snRNA workflow",
            f"  manifest: {self.manifest_path}",
            f"  project: {self.project}",
        ]
        if self.project_resources is not None:
            resource_keys = ", ".join(sorted(self.project_resources)) or "(empty)"
            lines.append(f"  project resources: {resource_keys}")
        else:
            lines.append("  project resources: not resolved (--project-metadata not given)")
        if self.tenx_metadata is not None:
            lines.append(f"  10X metadata: {len(self.tenx_metadata)} chemistry version(s) loaded")
        else:
            lines.append("  10X metadata: not loaded (--tenx-metadata not given)")
        lines.append(f"  user: {self.email or 'not specified'}")
        lines.append(f"  output directory: {self.output_dir or 'not specified'}")
        return "\n".join(lines)


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


class _SnRnaArgumentParser(argparse.ArgumentParser):
    def print_help(self, file=None) -> None:
        super().print_help(file)
        out = file if file is not None else sys.stdout
        print("\nManifest keys:", file=out)
        documenter = TextYamlManifestDocumenter(out=out)
        for element in SnRnaManifestKey.get_documentation_recursive_roots():
            documenter.document_element_recursive(element, 0)


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = _SnRnaArgumentParser(
        description=__doc__)
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
                        default="snRnaSeq_prod")
    parser.add_argument("--verbose", "-v", action="store_true", default=False)
    parser.add_argument("--dry-run", action="store_true",default=False,help="Don't actually run the workflow")
    parser.add_argument("--tw", default="tw",
                        help="Path to the TW executable. Use this if (annoyingly) PyCharm uv doesn't respect PATH changes.  Default: %(default)s)")
    return parser.parse_args(argv)


def load_manifest(manifest_path: Path) -> Dict[str, Any]:
    with open(manifest_path) as fh:
        loaded = yaml.safe_load(fh)
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise LaunchSnRnaError(
            f"expected a yaml mapping in manifest '{manifest_path}', found {type(loaded).__name__}")
    return loaded


_COMBINE_DEFAULTS_KEY = argparse.Namespace(name="defaults")
_COMBINE_TARGET_KEY = argparse.Namespace(name="target")


def load_and_combine_manifests(manifest_paths: List[Path]) -> Dict[str, Any]:
    """Load each yaml manifest in order and merge them into one, with the earlier manifest taking precedence
    in the event of collisions."""
    combined: Dict[str, Any] = load_manifest(manifest_paths[0])
    for manifest_path in manifest_paths[1:]:
        manifest = load_manifest(manifest_path)
        combined = YamlManifestUtil.project_defaults(combined, manifest)
    return combined


def resolve_project_resources(project_metadata: Dict[str, Any], project: str) -> Dict[str, Any]:
    if project not in project_metadata:
        raise LaunchSnRnaError(f"project '{project}' not found in project metadata")
    resources = project_metadata[project]
    if not isinstance(resources, dict):
        raise LaunchSnRnaError(
            f"expected a yaml mapping for project '{project}', found {type(resources).__name__}")
    return resources


def get_tenx_metadata(tenx_version: str, tenx_metadata: Dict[str, Any]) -> Dict[str, Any]:
    """find 10X version in tenx_metadata dictionary, and return that sub-dictionary."""
    if tenx_version not in tenx_metadata:
        raise LaunchSnRnaError(
            f"10X chemistry version(s) not found in 10X metadata: {tenx_version}")
    return tenx_metadata[tenx_version]

def load_project_metadata(gcs_path: str) -> Dict[str, Any]:
    project_metadata = gcs_util.load_gcs_yaml(gcs_path)
    lstProjects = project_metadata['projects']
    # Convert the list of projects into a dictionary in which the key is the value of the 'name' element of each sub-dictionary
    dctProjects = {dctProject['name']: dctProject for dctProject in lstProjects}

    return dctProjects

def load_tenx_metadata(gcs_path: str) -> Dict[str, Any]:
    tenx_metadata = gcs_util.load_gcs_yaml(gcs_path)
    # Convert the list of tenx metadata into a dictionary in which the key is the value of the 'version10X' element of each sub-dictionary
    dctTenxMetadata = {dctTenx['version10X']: dctTenx for dctTenx in tenx_metadata['versions']}
    return dctTenxMetadata

def build_launch_context(args: argparse.Namespace) -> SnRnaLaunchContext:
    manifest = load_and_combine_manifests(args.manifest)

    project_metadata = load_project_metadata(args.project_metadata)
    project_resources = resolve_project_resources(project_metadata, args.project)
    tenx_metadata = load_tenx_metadata(args.tenx_metadata)

    return SnRnaLaunchContext(
        manifest_path=args.manifest,
        manifest=manifest,
        project=args.project,
        project_resources=project_resources,
        tenx_metadata=tenx_metadata,
        email=args.email,
        output_dir=args.output_dir)

def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    context = build_launch_context(args)
    errors = SnRnaManifestKey.validate_manifest(context.manifest)
    if errors:
        print("Errors parsing manifest:\n" + "\n".join(errors), file=sys.stderr)
        return 1
    manifest = context.manifest
    manifest.update(get_tenx_metadata(manifest['version10X'], context.tenx_metadata))
    if args.output_dir:
        outdir = args.output_dir
    else:
        outdir = f"gs://{context.project_resources['standard_bucket']}/projects/{context.project_resources['name']}/{manifest['library']}"
    manifest['outdir'] = outdir
    manifest['email'] = args.email
    params_yaml = tempfile.mkstemp(suffix=".yaml", prefix=manifest['library'] + '.', text=True)
    with os.fdopen(params_yaml[0], "w") as f:
        yaml.safe_dump(manifest, f, default_flow_style=False, sort_keys=False)
    if args.verbose:
        print("Wrote manifest to " + params_yaml[1])
    lstCommandLine = [
        args.tw, "launch",
        "--workspace=" + context.project_resources['tower_workspace'],
        args.pipeline,
        "--params-file=" + params_yaml[1],
        "--name=x" + manifest['experimentDate'] + '_' + manifest['library'],
    ]
    if args.verbose or args.dry_run:
        print(" ".join(lstCommandLine))
    if not args.dry_run:
        subprocess.run(lstCommandLine, check=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
