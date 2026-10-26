#!/usr/bin/env python3
"""Write a tab-separated table of ELAB metrics to stdout, one row per cell_selection directory, for one or
more library directories in Google Cloud Storage.

Cell selection directories are <libraryDir>/*/cbrb/*/cell_selection/*.
"""
import argparse
import csv
import re
import sys
from typing import Dict, List

import yaml

from util import gcs_util
from util.argparse_util import gcs_path_type

COLUMNS = ["library", "nuclei", "reads_per_umi", "median_umis", "ambient_peak", "cell_selection"]
METRICS_SUFFIX = ".cell_selection_assignments_summary.txt"
METRICS_COLUMNS = {
    "nuclei": "n_STAMPs",
    "reads_per_umi": "medianReadsPerUMI",
    "median_umis": "UMIs_STAMPs_median",
    "ambient_peak": "UMIs_ambient",
}


def library_name(library_dir: str) -> str:
    properties = gcs_util.load_gcs_yaml(gcs_util.gcs_join(library_dir, "properties.yaml"))
    for key in ("experimentDate", "library"):
        if key not in properties:
            raise Exception(f"'{key}' not found in properties.yaml of '{library_dir}'")
    return f"{properties['experimentDate']}_{properties['library']}"


def find_cell_selection_dirs(library_dir: str) -> List[str]:
    """Return the sorted <libraryDir>/*/cbrb/*/cell_selection/* directories that contain a properties.yaml."""
    prefix = library_dir.rstrip("/") + "/"
    regex = re.compile("^" + re.escape(prefix) + r"[^/]+/cbrb/[^/]+/cell_selection/[^/]+(?=/properties\.yaml$)")
    dirs = set()
    for path in gcs_util.list_gcs_paths(library_dir):
        match = regex.match(path)
        if match:
            dirs.add(match.group(0))
    return sorted(dirs)


def read_metrics(cell_selection_dir: str) -> Dict[str, str]:
    """Load the single data row of <library>.readQualityMetrics.txt in the cell selection directory."""
    prefix = cell_selection_dir.rstrip("/") + "/"
    metrics_paths = [path for path in gcs_util.list_gcs_paths(cell_selection_dir)
                     if path.startswith(prefix) and "/" not in path[len(prefix):]
                     and path.endswith(METRICS_SUFFIX)]
    if len(metrics_paths) != 1:
        raise Exception(f"expected exactly one *{METRICS_SUFFIX} in '{cell_selection_dir}', "
                        f"found {len(metrics_paths)}")
    reader = csv.DictReader(gcs_util.load_gcs_text(metrics_paths[0]).splitlines(), delimiter="\t")
    missing = [col for col in METRICS_COLUMNS.values() if col not in (reader.fieldnames or [])]
    if missing:
        raise Exception(f"'{metrics_paths[0]}' is missing column(s): {', '.join(missing)}")
    rows = list(reader)
    if len(rows) != 1:
        raise Exception(f"expected exactly one data row in '{metrics_paths[0]}', found {len(rows)}")
    return rows[0]


def make_rows(library_dir: str) -> List[Dict[str, str]]:
    library = library_name(library_dir)
    rows = []
    for cell_selection_dir in find_cell_selection_dirs(library_dir):
        properties = gcs_util.load_gcs_yaml(gcs_util.gcs_join(cell_selection_dir, "properties.yaml"))
        if "cell_selection_label" not in properties:
            raise Exception(f"'cell_selection_label' not found in properties.yaml of '{cell_selection_dir}'")
        metrics = read_metrics(cell_selection_dir)
        row = {"library": library, "cell_selection": properties["cell_selection_label"]}
        row.update({column: metrics[source] for column, source in METRICS_COLUMNS.items()})
        rows.append(row)
    return rows


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("library_dirs", nargs="+", type=gcs_path_type, metavar="LIBRARY_DIR",
                        help="gs:// library directory")
    args = parser.parse_args(argv)

    writer = csv.DictWriter(sys.stdout, fieldnames=COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    for library_dir in args.library_dirs:
        writer.writerows(make_rows(library_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
