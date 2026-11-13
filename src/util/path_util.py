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
"""Helpers for files that may live on the local filesystem or in a gs:// bucket.

Paths are passed in and returned as strings.  Error messages always quote the caller's original path
string, so a gs:// path is reported with its gs:// prefix.
"""
import csv
import io
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

# Quiet gRPC fork() messages:
# - https://github.com/grpc/grpc/issues/37642#issuecomment-2401167865
os.environ.setdefault("GRPC_VERBOSITY", "NONE")

import yaml
from upath import UPath

GCS_PATH_RE = re.compile(r"^gs://(?P<bucket>[^/]+)/(?P<blob>.+)$")


def is_gcs_path(path: str) -> bool:
    return bool(GCS_PATH_RE.match(path))


def require_gcs_path(path: str) -> None:
    """Raise an exception if path is not a gs:// path, e.g. because it will be read by a cloud workflow."""
    if not is_gcs_path(path):
        raise ValueError(f"not a gs:// path: '{path}'")


def gcs_bucket(path: str) -> str:
    """Return the bucket name of a gs:// path."""
    require_gcs_path(path)
    return GCS_PATH_RE.match(path).group("bucket")


def is_file(path: str) -> bool:
    """Return True if path exists as a file."""
    return UPath(path).is_file()


def is_dir(path: str) -> bool:
    """Return True if path exists as a directory (for gs://, a prefix with at least one object under it)."""
    return UPath(path).is_dir()


def exists(path: str) -> bool:
    """Return True if path exists as a file or as a directory."""
    return UPath(path).exists()


def require_file(path: str) -> None:
    """Raise an exception if path does not exist as a file."""
    if not is_file(path):
        raise Exception(f"file not found: '{path}'")


def require_dir(path: str) -> None:
    """Raise an exception if path does not exist as a directory."""
    if not is_dir(path):
        raise Exception(f"directory not found: '{path}'")


def read_text(path: str) -> str:
    """Read the full contents of a file as text."""
    try:
        return UPath(path).read_text()
    except FileNotFoundError:
        # The underlying exception's message omits the gs:// prefix, so report the caller's path instead.
        raise Exception(f"file not found: '{path}'") from None


def load_yaml(path: str) -> Dict[str, Any]:
    """Read a yaml file and parse it into a dict."""
    loaded = yaml.safe_load(read_text(path))
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise Exception(
            f"expected a yaml mapping at '{path}', found {type(loaded).__name__}")
    return loaded


def load_csv_rows(path: str, required_columns: Optional[Iterable[str]] = None) -> List[Dict[str, str]]:
    """Load a local or gs:// csv file into a list of dicts, one per row, keyed by column header.

    :param required_columns: if given, raise an exception if any of these columns is missing from the header.
    """
    reader = csv.DictReader(io.StringIO(read_text(path), newline=""))
    if required_columns is not None:
        missing = [column for column in required_columns if column not in (reader.fieldnames or [])]
        if missing:
            raise Exception(f"csv file '{path}' is missing required column(s): {', '.join(missing)}")
    return list(reader)


def parent_dir(path: str) -> str:
    """Return the parent directory of path.  The parent of gs://bucket/x is gs://bucket."""
    parent = str(UPath(path).parent)
    if is_gcs_path(path) and parent.endswith("/"):
        parent = parent.rstrip("/")
    return parent


def join(base_path: str, *parts: str) -> str:
    """Join relative path segments onto a base path.  A leading '/' on a segment is ignored rather than
    treated as an absolute path."""
    return str(UPath(base_path).joinpath(*(part.lstrip("/") for part in parts)))


def copy_file(local_path: str, dest_path: str) -> None:
    """Copy a local file to dest_path, which may be local or gs://."""
    UPath(dest_path).write_bytes(Path(local_path).read_bytes())


def list_files(dir_path: str) -> List[str]:
    """List the paths of all files under a directory, recursively."""
    directory = UPath(dir_path)
    # fs.find lists everything in one request on gs://, but returns paths without the protocol;
    # with_segments restores it.
    return [str(directory.with_segments(found)) for found in directory.fs.find(directory.path)]
