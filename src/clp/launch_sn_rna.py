#!/usr/bin/env python3
"""Launch the single-nucleus RNA-seq (snRNA) workflow cascade for a library in Seqera cloud.
"""
import argparse
import os
import sys
import getpass
from pathlib import Path
from typing import Any, Dict, List, Optional
import tempfile

import yaml
import subprocess

from manifest.util.documenter import TextYamlManifestDocumenter
from manifest.util.manifest_util import YamlManifestUtil
from manifest.enums import Stage, enum_names
from manifest.manifest_keys import SnRnaManifestKey
import util.gcs_util as gcs_util
from manifest.constants import FASTQ_READ1, FASTQ_READ2
from util import misc_util, output_label_util
from util.argparse_util import LaunchSnRnaError, gcs_path_type, email_type, manifest_path_type
from util.reference_metadata_util import validateReference, getReferenceName

_MODULE_DOC = __doc__


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
        self.stages: List[str] = enum_names(Stage)

    def stage_index(self, stage: str) -> int:
        """Return the index of the given stage in the stages list."""
        if stage not in self.stages:
            raise LaunchSnRnaError(f"Invalid stage: {stage}")
        return self.stages.index(stage)

    def print_manifest_keys(self, out) -> None:
        print("\nManifest keys:", file=out)
        documenter = TextYamlManifestDocumenter(out=out)
        for element in self.manifest_key_class.get_documentation_recursive_roots():
            documenter.document_element_recursive(element, 0)
        for element in self.manifest_key_class.get_documentation_non_recursive_roots():
            documenter.document_element_non_recursive(element, 0)

    class _ArgumentParser(argparse.ArgumentParser):
        def __init__(self, launcher, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._launcher = launcher

        def print_help(self, file=None) -> None:
            super().print_help(file)
            out = file if file is not None else sys.stdout
            self._launcher.print_manifest_keys(out)

    def build_parser(self) -> argparse.ArgumentParser:
        parser = self._ArgumentParser(self, description=self.prog_description)
        parser.add_argument(
            "manifest", type=manifest_path_type, nargs="*",
            help="Local yaml manifest file describing the libraries to process.  If more than one manifest file "
                 "is provided, they will be combined with earlier manifest files taking precedence if key collisions.")
        parser.add_argument(
            "--yaml", "-y", action="append", default=[], metavar="YAML",
            help="Yaml string (e.g. --yaml 'cbrbArgs: foo') applied on top of the manifest(s).  May be specified "
                 "more than once.  Yaml strings take precedence over the manifest(s), and later --yaml strings "
                 "take precedence over earlier ones.")
        parser.add_argument(
            "--project", required=True,
            help="Project name, used to look up project resources in the project metadata file.")
        parser.add_argument(
            "--project-metadata", type=gcs_path_type, metavar="GCS_PATH",
            default="gs://mccarroll_scrnaseq_standard/metadata/project/project_metadata.yaml",
            help="gs:// path to a yaml file containing project resources, keyed by project name. Default: %(default)s)")
        parser.add_argument(
            "--tenx-metadata", type=gcs_path_type, metavar="GCS_PATH",
            default='gs://mccarroll_scrnaseq_standard/metadata/10X/10X_version_metadata.yaml',
            help="gs:// path to a yaml file containing 10X chemistry version metadata. Default: %(default)s)")
        parser.add_argument(
            "--email", type=email_type, metavar="EMAIL",
            default=f"{getpass.getuser()}@broadinstitute.org",
            help="Email address of the user launching this workflow. Default: %(default)s)")
        parser.add_argument(
            "--output-dir", type=gcs_path_type, metavar="GCS_PATH",
            help="gs:// path under which workflow outputs will be written. Default: determined based on project and library")
        parser.add_argument(
            "--stop-at", choices=enum_names(Stage), metavar="STAGE",
            help="Optional. Stop the pipeline(s) after this stage. Must be one of: %(choices)s.")
        parser.add_argument("--pipeline", help="Nextflow pipeline to invoke.  Default: %(default)s)",
                            default=self.default_pipeline)
        parser.add_argument("--allow-overwrite", "-f", action="store_true", default=False,
                            help="Allow overwriting existing output directories. Default: %(default)s")
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

    @staticmethod
    def parse_yaml_string(yaml_string: str) -> Dict[str, Any]:
        try:
            loaded = yaml.safe_load(yaml_string)
        except yaml.YAMLError as e:
            raise LaunchSnRnaError(f"could not parse --yaml string '{yaml_string}': {e}")
        if loaded is None:
            return {}
        if not isinstance(loaded, dict):
            raise LaunchSnRnaError(
                f"expected a yaml mapping in --yaml string '{yaml_string}', found {type(loaded).__name__}")
        return loaded

    def load_and_combine_manifests(self, manifest_paths: List[Path], yaml_strings: Optional[List[str]] = None
                                   ) -> Dict[str, Any]:
        """Load each yaml manifest in order and merge them into one, with the earlier manifest taking precedence
        in the event of collisions.  Then apply each yaml string in order, with each taking precedence over the
        manifests and over any earlier yaml strings."""
        combined: Dict[str, Any] = {}
        for manifest_path in manifest_paths:
            manifest = self.load_manifest(manifest_path)
            combined = YamlManifestUtil.project_defaults(combined, manifest)
        for yaml_string in yaml_strings or []:
            combined = YamlManifestUtil.project_defaults(self.parse_yaml_string(yaml_string), combined)
        # note that it might be the case that the manifest is empty, e.g. if starting at standard_analysis stage,
        # which often has no parameters.
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

    def load_metadata(self, args: argparse.Namespace) -> None:
        self.project_metadata = self.load_project_metadata(args.project_metadata)
        self.tenx_metadata = self.load_tenx_metadata(args.tenx_metadata)

    def load_launch_state(self, args: argparse.Namespace) -> None:
        self.manifest = self.load_and_combine_manifests(args.manifest, args.yaml)
        self.manifests = [self.manifest]
        self.project_resources = self.resolve_project_resources(self.project_metadata, args.project)

    def get_manifests(self) -> List[Dict[str, Any]]:
        return self.manifests

    def getRunName(self, manifest: Dict[str, Any]) -> str:
        """Return a run name based on the experiment date and library name."""
        runName = manifest['experimentDate'] + '_' + manifest['library']
        return runName

    def force_lists(self, manifest: Dict[str, Any]) -> None:
        """Force list_allowed manifest keys to be lists, even if the manifest has a single value.
        Note that this is done using SnRnaManifestKey rather than the manifest_key_class,
        because the dragen manifest has been converted into multiple SnRnaManifestKey manifests at this point,
        so SnRnaManifestKey defines the requirements."""
        for key in SnRnaManifestKey.root_elements_no_downstream():
            elementName = key.name
            if key.list_allowed and elementName in manifest:
                manifest[elementName] = misc_util.force_list(manifest[elementName])

    def get_output_subdirectory(self, manifest: Dict[str, Any]) -> str:
        """Return the output subdirectory for the given manifest, based on the start_at stage and any labels."""
        outputSubDir = manifest['outdir']
        start_at = manifest.get('start_at', Stage.beginning.name)
        startAtIndex = self.stage_index(start_at)
        if startAtIndex >= self.stage_index(Stage.alignment.name):
            outputSubDir = outputSubDir + "/" + getReferenceName(manifest['reference'])
        if startAtIndex >= self.stage_index(Stage.cbrb.name):
            outputSubDir = outputSubDir + "/cbrb/" + manifest['cbrb_label']
        if startAtIndex >= self.stage_index(Stage.cell_selection.name):
            outputSubDir = outputSubDir + "/cell_selection/" + manifest['cell_selection_label']
        if startAtIndex >= self.stage_index(Stage.standard_analysis.name):
            outputSubDir = outputSubDir + "/standard_analysis"
        if startAtIndex == self.stage_index(Stage.dropulation.name):
            if 'dropulation_label' in manifest:
                outputSubDir = outputSubDir + "/village/" + manifest['dropulation_label']
            elif 'mmc_label' in manifest:
                outputSubDir = outputSubDir + "/mmc/" + manifest['mmc_label']
        elif startAtIndex == self.stage_index(Stage.mmc.name):
            if  'mmc_label' not in manifest:
                raise LaunchSnRnaError("Unpossible! mmc_label not in manifest when starting at mmc stage")
            outputSubDir = outputSubDir + "/mmc/" + manifest['mmc_label']
        return outputSubDir

    def check_preexisting(self, manifest: Dict[str, Any], allow_overwrite: bool, outputSubDir: str) -> None:
        """Check if the output directory already exists. If it does and --allow-overwrite is not set, raise an error."""
        self.check_preexisting_directory(allow_overwrite, outputSubDir)
        start_at = manifest.get('start_at', Stage.beginning.name)
        startAtIndex = self.stage_index(start_at)
        if startAtIndex == self.stage_index(Stage.dropulation.name) and 'mmc_label' in manifest:
            # mmc and dropulation are unusual in that one is not nested in the other, so go up 2 levels from outputSubDir to check for the mmc directory
            dirToCheck = gcs_util.gcs_parent_dir(gcs_util.gcs_parent_dir(outputSubDir))
            self.check_preexisting_directory(allow_overwrite, dirToCheck + "/mmc/" + manifest['mmc_label'])

    def check_preexisting_directory(self, allow_overwrite: bool, dirToCheck):
        if gcs_util.gcs_path_exists(dirToCheck):
            if not allow_overwrite:
                raise LaunchSnRnaError(
                    f"Output directory '{dirToCheck}' already exists. Use --allow-overwrite to overwrite.")
            else:
                print(f"Warning: Output directory '{dirToCheck}' already exists and will be overwritten.",
                      file=sys.stderr)

    def launch_manifest(self, manifest: Dict[str, Any], args: argparse.Namespace) -> None:
        self.force_lists(manifest)
        manifest.update(self.get_tenx_metadata(manifest['version10X'], self.tenx_metadata))
        output_label_util.add_output_labels(manifest)
        runName = self.getRunName(manifest)
        if args.output_dir:
            outdir = args.output_dir
        else:
            outdir = f"gs://{self.project_resources['standard_bucket']}/projects/{self.project_resources['name']}/{runName}"
        manifest['outdir'] = outdir
        manifest['email'] = args.email
        start_at = manifest.get('start_at', Stage.beginning.name)
        if start_at == Stage.dropulation.name and 'dropulation_label' not in manifest:
            # If starting at dropulation stage and dropulation is not present, we need to start at the mmc stage instead.
            manifest['start_at'] = Stage.mmc.name
            start_at = Stage.mmc.name
        if start_at == Stage.mmc.name and 'mmc_label' not in manifest:
            raise LaunchSnRnaError("Cannot start at mmc stage without specifying mmcQueryMarkers in the manifest")
        if args.stop_at:
            if self.stage_index(args.stop_at) < self.stage_index(start_at):
                raise LaunchSnRnaError(
                    f"Cannot stop at stage '{args.stop_at}' which is before the start_at stage '{start_at}'")
            manifest['stop_at'] = args.stop_at
        for fastq in manifest[FASTQ_READ1] + manifest[FASTQ_READ2]:
            gcs_util.require_gcs_file(fastq)
        if 'reference' in manifest:
            validateReference(manifest['reference'])
        outputSubDir = self.get_output_subdirectory(manifest)
        self.check_preexisting(manifest, args.allow_overwrite, outputSubDir)
        params_yaml = tempfile.mkstemp(suffix=".yaml", prefix=manifest['library'] + '.', text=True)
        with os.fdopen(params_yaml[0], "w") as f:
            yaml.safe_dump(manifest, f, default_flow_style=False, sort_keys=False)
        if args.verbose:
            print("Wrote manifest to " + params_yaml[1])
        if runName[0].isdigit():
            runName = 'x' + runName
        lstCommandLine = [
            args.tw, "launch",
            "--workspace=" + self.project_resources['tower_workspace'],
            args.pipeline,
            "--params-file=" + params_yaml[1],
            "--name=" + runName,
            "--output-dir=" + outdir
        ]
        if args.verbose or args.dry_run:
            print(" ".join(lstCommandLine))
        if not args.dry_run:
            subprocess.run(lstCommandLine, check=True)

    def main(self, argv: Optional[List[str]] = None) -> int:
        args = self.parse_args(argv)
        self.load_metadata(args)
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
