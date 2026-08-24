#!/usr/bin/env python3
"""Helpers for reading files that may live on the local filesystem or in a gs:// bucket."""
import csv
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import util.gcs_util as gcs_util


def is_gcs_path(path: str) -> bool:
    return bool(gcs_util.GCS_PATH_RE.match(path))


def join(path: str, *parts: str) -> str:
    """Join path segments onto a base path, whether the base is a local path or a gs:// path."""
    if is_gcs_path(path):
        return "/".join([path.rstrip("/"), *parts])
    return str(Path(path, *parts))


def read_text(path: str) -> str:
    """Read the full contents of a local or gs:// file as text."""
    if is_gcs_path(path):
        return gcs_util.load_gcs_text(path)
    return Path(path).read_text()


def load_csv_rows(path: str, required_columns: Optional[Iterable[str]] = None) -> List[Dict[str, str]]:
    """Load a local or gs:// csv file into a list of dicts, one per row, keyed by column header.

    :param required_columns: if given, raise an exception if any of these columns is missing from the header.
    """
    if is_gcs_path(path):
        return gcs_util.load_gcs_csv(path, required_columns=required_columns)
    with open(path, newline="") as fh:
        reader = csv.DictReader(fh)
        if required_columns is not None:
            missing = [column for column in required_columns if column not in (reader.fieldnames or [])]
            if missing:
                raise Exception(f"csv file '{path}' is missing required column(s): {', '.join(missing)}")
        return list(reader)
