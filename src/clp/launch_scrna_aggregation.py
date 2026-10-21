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
Launch the scRNA aggregation workflow in Seqera cloud.  The workflow merges the DGEs of several
single-library scRNA-seq runs into one merged sparse matrix, merged cell metadata, library metrics,
and donor / cell type reports and metacells.  What to aggregate comes from a YAML manifest with a
'dges' list (one entry per library) and an optional 'dgeDefaults'.
"""
import argparse
import os
import subprocess
import sys
import tempfile
from typing import Any, Dict, List, Optional

import yaml

import util.gcs_util as gcs_util
from clp.launch_sn_rna import LaunchSnRna
from util.argparse_util import LaunchSnRnaError, gcs_path_type

_MODULE_DOC = __doc__


def manifest_path_or_gcs_type(value: str) -> str:
    """argparse type: a gs:// path, or a local file that exists."""
    if gcs_util.GCS_PATH_RE.match(value):
        return value
    if not os.path.isfile(value):
        raise argparse.ArgumentTypeError(f"manifest file not found: '{value}'")
    return value


class LaunchScrnaAggregation:
    """Launches the scRNA aggregation workflow in Seqera cloud."""

    default_pipeline = "scrnaAggregation_prod"
    prog_description = _MODULE_DOC

    def build_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(description=self.prog_description)
        parser.add_argument(
            "manifest", type=manifest_path_or_gcs_type,
            help="YAML aggregation manifest, either a local file or a gs:// path.  A local file is uploaded to "
                 "<output-dir>/<analysis-id>.manifest.yaml, because the workflow reads the manifest from cloud storage.")
        parser.add_argument(
            "--analysis-id", required=True,
            help="Label of this aggregation: prefix of the merged output files.  Also used as the run name.  "
                 "Must differ from every library id.")
        parser.add_argument(
            "--mmc-model", metavar="MODEL",
            help="Optional. MapMyCells model to use instead of the first model of each library.")
        parser.add_argument(
            "--mmc-level", metavar="LEVEL",
            help="Optional. MapMyCells taxonomy level for the cell type column.  Default: the top level of the taxonomy.")
        parser.add_argument(
            "--project", required=True,
            help="Project name, used to look up project resources in the project metadata file.")
        parser.add_argument(
            "--project-metadata", type=gcs_path_type, metavar="GCS_PATH",
            default="gs://mccarroll_scrnaseq_standard/metadata/project/project_metadata.yaml",
            help="gs:// path to a yaml file containing project resources, keyed by project name. Default: %(default)s)")
        parser.add_argument(
            "--output-dir", type=gcs_path_type, metavar="GCS_PATH",
            help="gs:// path under which workflow outputs will be written. "
                 "Default: gs://<project standard bucket>/projects/<project>/aggregation/<analysis-id>")
        parser.add_argument("--pipeline", help="Nextflow pipeline to invoke.  Default: %(default)s)",
                            default=self.default_pipeline)
        parser.add_argument("--verbose", "-v", action="store_true", default=False)
        parser.add_argument("--dry-run", action="store_true", default=False, help="Don't actually run the workflow")
        parser.add_argument("--tw", default="tw",
                            help="Path to the TW executable. Use this if (annoyingly) PyCharm uv doesn't respect PATH changes.  Default: %(default)s)")
        return parser

    def parse_args(self, argv: Optional[List[str]] = None) -> argparse.Namespace:
        return self.build_parser().parse_args(argv)

    @staticmethod
    def check_local_manifest(manifest_path: str) -> None:
        """Cheap sanity check that a local manifest is a yaml mapping.  The workflow validates the contents."""
        with open(manifest_path) as fh:
            loaded = yaml.safe_load(fh)
        if not isinstance(loaded, dict):
            raise LaunchSnRnaError(
                f"expected a yaml mapping in manifest '{manifest_path}', found {type(loaded).__name__}")

    def main(self, argv: Optional[List[str]] = None) -> int:
        args = self.parse_args(argv)
        project_metadata = LaunchSnRna.load_project_metadata(args.project_metadata)
        project_resources = LaunchSnRna.resolve_project_resources(project_metadata, args.project)

        if args.output_dir:
            outdir = args.output_dir
        else:
            outdir = (f"gs://{project_resources['standard_bucket']}/projects/{project_resources['name']}"
                      f"/aggregation/{args.analysis_id}")

        manifest = args.manifest
        if not gcs_util.GCS_PATH_RE.match(manifest):
            self.check_local_manifest(manifest)
            gcs_manifest = gcs_util.gcs_join(outdir, f"{args.analysis_id}.manifest.yaml")
            if args.verbose or args.dry_run:
                print(f"Upload {manifest} to {gcs_manifest}")
            if not args.dry_run:
                gcs_util.upload_gcs_file(gcs_manifest, manifest)
            manifest = gcs_manifest

        params: Dict[str, Any] = {
            'manifest': manifest,
            'analysis_id': args.analysis_id,
            'outdir': outdir,
        }
        if args.mmc_model:
            params['mmc_model'] = args.mmc_model
        if args.mmc_level:
            params['mmc_level'] = args.mmc_level

        params_yaml = tempfile.mkstemp(suffix=".yaml", prefix=args.analysis_id + '.', text=True)
        with os.fdopen(params_yaml[0], "w") as f:
            yaml.safe_dump(params, f, default_flow_style=False, sort_keys=False)
        if args.verbose:
            print("Wrote params to " + params_yaml[1])

        runName = args.analysis_id
        if runName[0].isdigit():
            runName = 'x' + runName
        lstCommandLine = [
            args.tw, "launch",
            "--workspace=" + project_resources['tower_workspace'],
            args.pipeline,
            "--params-file=" + params_yaml[1],
            "--name=" + runName,
        ]
        if args.verbose or args.dry_run:
            print(" ".join(lstCommandLine))
        if not args.dry_run:
            subprocess.run(lstCommandLine, check=True)
        return 0


def main(argv: Optional[List[str]] = None) -> int:
    return LaunchScrnaAggregation().main(argv)


if __name__ == "__main__":
    sys.exit(main())
