#!/usr/bin/env python3
"""Launch a single-nucleus RNA-seq (snRNA) workflow cascade for each library in Seqera cloud.
"""
import argparse
import copy
import sys
from typing import Any, Dict, List, Optional, Tuple

from clp.launch_sn_rna import LaunchSnRna, LaunchSnRnaError, _gcs_path_type
from manifest.constants import FASTQ_READ1, FASTQ_READ2
from manifest.manifest_keys import libraries, libraryDefaults, snRnaDragenManifestKey, library, experimentDate, rgsm
from manifest.util.manifest_util import YamlManifestUtil
import util.gcs_util as gcs_util
from util import misc_util

_FASTQ_LIST_COLUMNS = ["RGSM", "Read1File", "Read2File"] # We don't care about columns "RGID", "RGLB", "Lane"


class LaunchSnRnaDragen(LaunchSnRna):
    manifest_key_class = snRnaDragenManifestKey
    prog_description = __doc__

    def __init__(self) -> None:
        super().__init__()
        self.manifests: List[Dict[str, Any]] = []
        self.run_folder: str = ""

    def build_parser(self) -> argparse.ArgumentParser:
        parser = super().build_parser()
        parser.add_argument(
            "--run-folder", type=_gcs_path_type, metavar="GCS_PATH", required=True,
            help="gs:// path to the Dragen run folder.")
        return parser

    def load_launch_state(self, args: argparse.Namespace) -> None:
        super().load_launch_state(args)
        self.run_folder = args.run_folder.rstrip("/")
        self.fastq_list_path = f"{self.run_folder}/Reports/fastq_list.csv"

        self.manifests = YamlManifestUtil.apply_defaults(self.manifest, libraryDefaults, libraries)
        # These statements just needed to satisfy manifest validation.
        self.manifest[libraries.name] = copy.deepcopy(self.manifests)
        self.manifest.pop(libraryDefaults.name, None)

        # Get each library's manifest ready for converting into nextflow manifest
        fastqDict = self.load_fastq_list()
        for manifest in self.manifests:
            if rgsm.name not in manifest:
                lstRgsm = [manifest[experimentDate.name] + '_' + manifest[library.name]]
            else:
                lstRgsm = misc_util.force_list(manifest[rgsm.name])
                del manifest[rgsm.name]
            fastq_entries = []
            for manifest_rgsm in lstRgsm:
                if manifest_rgsm not in fastqDict:
                    raise LaunchSnRnaError(
                        f"rgsm '{manifest_rgsm}' not found in {self.fastq_list_path}v")
                fastq_entries.extend(fastqDict[manifest_rgsm])
            manifest[FASTQ_READ1] = [f"{self.run_folder}/{read1}" for read1, _read2 in fastq_entries]
            manifest[FASTQ_READ2] = [f"{self.run_folder}/{read2}" for _read1, read2 in fastq_entries]

    def get_manifests(self) -> List[Dict[str, Any]]:
        return self.manifests

    def load_fastq_list(self) -> Dict[str, List[Tuple[str, str]]]:
        """Load Reports/fastq_list.csv from the run folder, grouped by RGSM,
        with Read1File/Read2File reduced to just the filename."""
        rows = gcs_util.load_gcs_csv(self.fastq_list_path, required_columns=_FASTQ_LIST_COLUMNS)
        result: Dict[str, List[Tuple[str, str]]] = {}
        for row in rows:
            read1 = row["Read1File"].rsplit("/", 1)[-1]
            read2 = row["Read2File"].rsplit("/", 1)[-1]
            result.setdefault(row["RGSM"], []).append((read1, read2))
        return result


def main(argv: Optional[List[str]] = None) -> int:
    return LaunchSnRnaDragen().main(argv)


if __name__ == "__main__":
    sys.exit(main())
