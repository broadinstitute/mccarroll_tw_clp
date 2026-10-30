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
import sys
import tempfile
from typing import Any, Dict, List, Optional

import yaml

import util.gcs_util as gcs_util
from clp.launch_sn_rna import LaunchSnRna
from util.argparse_util import HiddenArguments, LaunchSnRnaError, gcs_path_type
from util.tw_launch_util import add_tw_launch_arguments, build_tw_launch_command, run_tw_launch

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

    default_pipeline = "https://github.com/broadinstitute/mccarroll-scrna-aggregation"
    default_revision = "prod"
    prog_description = _MODULE_DOC

    def build_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(description=self.prog_description)
        hidden = HiddenArguments()
        hidden.add_help_full_argument(parser)
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
            "--run-qc", action="store_true", default=False,
            help="Run the optional aggregation QC step, which writes PDFs of library, donor and cell type QC and "
                 "donor_qc.txt to qc_plots/ under the output directory.  The other --qc-* options require this.")
        parser.add_argument(
            "--qc-conditions-file", type=gcs_path_type, metavar="GCS_PATH",
            help="Optional. gs:// path to a TSV with a header and two columns (library, condition).  Every library "
                 "must be in it.  Adds plots that compare library metrics, donor nuclei counts and cell type "
                 "counts, median UMIs and proportions across conditions.  Not with --qc-condition-column.")
        parser.add_argument(
            "--qc-condition-column", metavar="COLUMN",
            help="Optional. Name of a cell metadata column (for example one added by a manifest join) with one value "
                 "per library, used as the condition as --qc-conditions-file would be.  Not with "
                 "--qc-conditions-file.")
        parser.add_argument(
            "--qc-core-cell-types", type=gcs_path_type, metavar="GCS_PATH",
            help="Optional. gs:// path to a file with one core cell type per line (no header).  Labels must belong "
                 "to the chosen MapMyCells model and level.")
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
                 "Default: gs://<project standard bucket>/<project>/aggregation/<analysis-id>")
        add_tw_launch_arguments(parser, hidden, self.default_pipeline, self.default_revision)
        parser.add_argument("--verbose", "-v", action="store_true", default=False)
        parser.add_argument("--dry-run", action="store_true", default=False, help="Don't actually run the workflow")
        return parser

    def parse_args(self, argv: Optional[List[str]] = None) -> argparse.Namespace:
        parser = self.build_parser()
        args = parser.parse_args(argv)
        if args.qc_conditions_file and args.qc_condition_column:
            parser.error("--qc-conditions-file and --qc-condition-column are mutually exclusive")
        if not args.run_qc and (args.qc_conditions_file or args.qc_condition_column or args.qc_core_cell_types):
            parser.error("--qc-conditions-file, --qc-condition-column and --qc-core-cell-types require --run-qc")
        return args

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
            outdir = (f"gs://{project_resources['standard_bucket']}/{project_resources['name']}"
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
        if args.run_qc:
            params['run_qc'] = True
        if args.qc_conditions_file:
            params['qc_conditions_file'] = args.qc_conditions_file
        if args.qc_condition_column:
            params['qc_condition_column'] = args.qc_condition_column
        if args.qc_core_cell_types:
            params['qc_core_cell_types'] = args.qc_core_cell_types

        params_yaml = tempfile.mkstemp(suffix=".yaml", prefix=args.analysis_id + '.', text=True)
        with os.fdopen(params_yaml[0], "w") as f:
            yaml.safe_dump(params, f, default_flow_style=False, sort_keys=False)
        if args.verbose:
            print("Wrote params to " + params_yaml[1])

        runName = args.analysis_id
        if runName[0].isdigit():
            runName = 'x' + runName
        lstCommandLine = build_tw_launch_command(
            args, project_resources['tower_workspace'], params_yaml[1], runName, outdir)
        run_tw_launch(lstCommandLine, args)
        return 0


def main(argv: Optional[List[str]] = None) -> int:
    return LaunchScrnaAggregation().main(argv)


if __name__ == "__main__":
    sys.exit(main())
