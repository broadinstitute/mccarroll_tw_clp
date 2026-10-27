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
"""Shared command-line options and command construction for `tw launch`."""
import argparse
import subprocess
from typing import List

from util.argparse_util import HiddenArguments

DEFAULT_WORKSPACE_SECRETS = "SENDGRID_API_KEY"


def add_tw_launch_arguments(parser: argparse.ArgumentParser, hidden: HiddenArguments, default_pipeline: str,
                            default_revision: str) -> None:
    """Add the options that control how the workflow is launched with `tw launch`.

    Most users never need these, so they are hidden from --help and only shown by --help-full."""
    group = parser.add_argument_group("tw launch options")
    hidden.add_argument(
        group, "--pipeline", default=default_pipeline,
        help="Nextflow pipeline to invoke: a GitHub URL, or the name of a pipeline in the workspace Launchpad.  "
             "Default: %(default)s)")
    hidden.add_argument(
        group, "--revision", "-r", default=default_revision, metavar="REVISION",
        help="Git branch or tag of the pipeline to run.  Default: %(default)s)")
    hidden.add_argument(
        group, "--commit-id", metavar="COMMIT",
        help="Optional. Pin the pipeline to this git commit hash, e.g. to reproduce an earlier run.")
    hidden.add_argument(
        group, "--profile", metavar="PROFILE[,PROFILE...]",
        help="Optional. Comma-separated Nextflow config profile names to apply.")
    hidden.add_argument(
        group, "--compute-env", metavar="NAME_OR_ID",
        help="Optional. Compute environment to run in.  Default: the workspace's primary compute environment.")
    hidden.add_argument(
        group, "--work-dir", metavar="GCS_PATH",
        help="Optional. Nextflow work directory.  Default: the compute environment's work directory.")
    hidden.add_argument(
        group, "--workspace-secrets", default=DEFAULT_WORKSPACE_SECRETS, metavar="NAME[,NAME...]",
        help="Comma-separated workspace secrets to make available to the pipeline.  "
             "Use an empty string for none.  Default: %(default)s)")
    hidden.add_argument(
        group, "--nextflow-version", metavar="VERSION",
        help="Optional. Nextflow version to run.  Default: determined by Seqera.")
    hidden.add_argument(
        group, "--syntax-parser", choices=["v1", "v2"],
        help="Optional. Nextflow syntax parser version.  Default: determined by Seqera.")
    hidden.add_argument(
        group, "--labels", metavar="LABEL[,LABEL...]",
        help="Optional. Comma-separated labels to assign to the run.")
    hidden.add_argument(
        group, "--tw", default="tw",
        help="Path to the TW executable. Use this if (annoyingly) PyCharm uv doesn't respect PATH changes.  "
             "Default: %(default)s)")


def build_tw_launch_command(args: argparse.Namespace, workspace: str, params_file: str, run_name: str,
                            output_dir: str) -> List[str]:
    """Build the `tw launch` command line from the options added by add_tw_launch_arguments.

    Note that --config is deliberately never passed: it would take priority over the Global Nextflow config of
    the compute environment, which is where lineage, mail and retry settings are kept."""
    command = [
        args.tw, "launch",
        "--workspace=" + workspace,
        "--params-file=" + params_file,
        "--name=" + run_name,
        # Seqera lists a run's outputs from the launch configuration's outputDir, not from params.outdir
        "--output-dir=" + output_dir,
    ]
    optional_flags = [
        ("--revision", args.revision),
        ("--commit-id", args.commit_id),
        ("--profile", args.profile),
        ("--compute-env", args.compute_env),
        ("--work-dir", args.work_dir),
        ("--workspace-secrets", args.workspace_secrets),
        ("--nextflow-version", args.nextflow_version),
        ("--syntax-parser", args.syntax_parser),
        ("--labels", args.labels),
    ]
    command.extend(f"{flag}={value}" for flag, value in optional_flags if value)
    command.append(args.pipeline)
    return command


def run_tw_launch(command: List[str], args: argparse.Namespace) -> None:
    """Print the command if requested, and run it unless this is a dry run."""
    if args.verbose or args.dry_run:
        print(" ".join(command))
    if not args.dry_run:
        subprocess.run(command, check=True)
