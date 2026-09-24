#!/usr/bin/env python3
# MIT License
# 
# Copyright 2026 Broad Institute
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
"""
Launch the single-nucleus RNA-seq (snRNA) workflow on an existing library, starting at the stage specified by the user.
This is useful for re-running a workflow from a particular stage, for running a workflow on a library that has already
been processed up to a certain point, or running a stage with different parameters.

Note that downstream stages will also be run if enabled in the manifest.
"""
import sys
from typing import Any, Dict, List, Optional
import argparse

from clp.launch_sn_rna import LaunchSnRna
from manifest.util.documenter import TextYamlManifestDocumenter
from manifest.enums import StartAt, enum_names
from manifest.manifest_keys import dctStageSchemaElements, dctStartAtManifestKeys
from util import gcs_util
from util.argparse_util import gcs_path_type, LaunchSnRnaError

_MODULE_DOC = __doc__

def getNextStage(stage: str) -> Optional[str]:
    """Return the next stage after the given stage, or None if there is no next stage."""
    stages = list(enum_names(StartAt))
    if stage == 'beginning':
        return stages[0]
    try:
        index = stages.index(stage)
    except ValueError:
        raise ValueError(f"Invalid stage: {stage}")
    if index + 1 < len(stages):
        return stages[index + 1]
    raise LaunchSnRnaError(f"Stage has no downstream stage: {stage}")

# number of directory levels to go up from the properties.yaml file to find the upstream properties.yaml file for each stage
dctUpstreamStageLevels = {
    StartAt.mmc.name: 2,
    StartAt.dropulation.name: 2,
    StartAt.standard_analysis.name: 1,
    StartAt.cell_selection.name: 2,
    StartAt.cbrb.name: 2,
    StartAt.alignment.name: 1,
}

# number of directory levels to go up from the properties.yaml file to find the library directory
dctLevelsToRoot = {
    StartAt.mmc.name: 8,
    StartAt.dropulation.name: 8,
    StartAt.standard_analysis.name: 6,
    StartAt.cell_selection.name: 5,
    StartAt.cbrb.name: 3,
    StartAt.alignment.name: 1,
}

def getUpstreamPropertiesPath(properties_path: str, levels: int) -> Optional[str]:
    upstream_properties_dir = gcs_util.gcs_parent_dir(properties_path)
    for _ in range(levels):
        upstream_properties_dir = gcs_util.gcs_parent_dir(upstream_properties_dir)
    upstream_properties_path = gcs_util.gcs_join(upstream_properties_dir, "properties.yaml")
    if not gcs_util.gcs_path_exists(upstream_properties_path):
        raise LaunchSnRnaError(f"Upstream properties file not found: {upstream_properties_path}")
    return upstream_properties_path

def getLibraryDirectoryFromPropertiesPath(properties_path: str, stage: str) -> str:
    """Return the library directory for the given properties.yaml file and upstream stage."""
    levels_to_root = dctLevelsToRoot.get(stage)
    if levels_to_root is None:
        raise LaunchSnRnaError(f"Upstream stage '{stage}' is not recognized.")
    library_dir = gcs_util.gcs_parent_dir(properties_path)
    for _ in range(levels_to_root):
        library_dir = gcs_util.gcs_parent_dir(library_dir)
    return library_dir

def loadAllUpstreamProperties(properties_path: str) -> Dict[str, Any]:
    """Load all properties from the given properties.yaml file and all upstream properties.yaml files."""
    dctProperties = gcs_util.load_gcs_yaml(properties_path)
    upstream_stage = dctProperties.get('stage')
    if upstream_stage is None:
        raise LaunchSnRnaError(f"Properties file '{properties_path}' does not contain a 'stage' key.")
    while upstream_stage in dctUpstreamStageLevels.keys():
        properties_path = getUpstreamPropertiesPath(properties_path, dctUpstreamStageLevels[upstream_stage])
        upstream_properties = gcs_util.load_gcs_yaml(properties_path)
        upstream_stage = upstream_properties.get('stage')
        # There shouldn't be key collisions between upstream and downstream properties, but if there are, the downstream properties should take precedence.
        upstream_properties.update(dctProperties)
        dctProperties = upstream_properties
    return dctProperties

class LaunchSnRnaStage(LaunchSnRna):
    prog_description = _MODULE_DOC

    def print_manifest_keys(self, out) -> None:
        print("\nManifest keys by stage.  Note that downstream manifest keys are allowed:", file=out)
        documenter = TextYamlManifestDocumenter(out=out)
        for stage in enum_names(StartAt):
            print(f"\nStage: {stage}", file=out)
            for element in dctStageSchemaElements.get(stage, []):
                documenter.document_element_recursive(element, 1)

    def build_parser(self) -> argparse.ArgumentParser:
        parser = super().build_parser()
        project_action = parser._option_string_actions["--project"]
        project_action.required = False
        project_action.help += " Default: Inferred from the location of the properties file."
        parser.add_argument(
            "--properties", type=gcs_path_type, metavar="GCS_PATH", required=True,
            help="gs:// path to properties.yaml that is upstream of the stage to be started.")
        return parser

    def load_launch_state(self, args: argparse.Namespace) -> int:
        self.load_metadata(args)
        if args.project is None:
            bucket = gcs_util.split_gcs_path(args.properties)[0]
            # scan through project dictionaries in self.project_metadata and return the project name for the one that has a bucket matching the properties file's bucket
            for project_dict in self.project_metadata.values():
                if project_dict.get('standard_bucket') == bucket:
                    args.project = project_dict['name']
                    break
            if args.project is None:
                raise LaunchSnRnaError(f"Could not infer project name from properties file '{args.properties}'.  "
                                       f"use --project to specify the project name explicitly.")
        super().load_launch_state(args)
        dctProperties = gcs_util.load_gcs_yaml(args.properties)
        upstreamStage = dctProperties['stage']
        if args.output_dir is None:
            args.output_dir = getLibraryDirectoryFromPropertiesPath(args.properties, upstreamStage)
        self.start_stage = getNextStage(upstreamStage)
        errors = dctStartAtManifestKeys[self.start_stage].validate_manifest(self.manifest)
        if errors:
            print("Errors parsing manifest:\n" + "\n".join(errors), file=sys.stderr)
            return 1
        manifest = loadAllUpstreamProperties(args.properties)
        lstKeysToRemove = ['stage', 'submitter', 'dropulation_label', 'mmcModel']
        for key in lstKeysToRemove:
            manifest.pop(key, None)
        # There shouldn't be key collisions between upstream properties and current manifest, but if there are, the manifest should take precedence.
        manifest.update(self.manifest)
        manifest['start_at'] = self.start_stage
        self.manifest = manifest
        self.manifests = [self.manifest]
        return 0

    def getRunName(self, manifest: Dict[str, Any]) -> str:
        run_name = super().getRunName(manifest)
        return f"{self.start_stage}_{run_name}"

    def main(self, argv: Optional[List[str]] = None) -> int:
        args = self.parse_args(argv)
        if self.load_launch_state(args) != 0:
            return 1
        for manifest in self.get_manifests():
            self.launch_manifest(manifest, args)
        return 0

def main(argv: Optional[List[str]] = None) -> int:
    launcher = LaunchSnRnaStage()
    return launcher.main(argv)

if __name__ == "__main__":
    sys.exit(main())
