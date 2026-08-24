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

import csv
import io
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

import yaml
from google.cloud import storage

GCS_PATH_RE = re.compile(r"^gs://(?P<bucket>[^/]+)/(?P<blob>.+)$")

_storage_client: storage.Client | None = None


def _get_storage_client() -> storage.Client:
    global _storage_client
    if _storage_client is None:
        _storage_client = storage.Client()
    return _storage_client


def _split_gcs_path(gcs_path: str) -> Tuple[str, str]:
    match = GCS_PATH_RE.match(gcs_path)
    if not match:
        raise ValueError(f"not a gs:// path: '{gcs_path}'")
    return match.group("bucket"), match.group("blob")


def gcs_path_is_file(gcs_path: str) -> bool:
    """Return True if gcs_path exists as a file (blob)."""
    bucket_name, blob_name = _split_gcs_path(gcs_path)
    return _get_storage_client().bucket(bucket_name).blob(blob_name).exists()


def gcs_path_is_dir(gcs_path: str) -> bool:
    """Return True if gcs_path exists as a directory prefix."""
    bucket_name, blob_name = _split_gcs_path(gcs_path)
    prefix = blob_name.rstrip("/") + "/"
    return any(True for _ in _get_storage_client().bucket(bucket_name).list_blobs(prefix=prefix, max_results=1))


def gcs_path_exists(gcs_path: str) -> bool:
    """Return True if gcs_path exists as a file (blob) or as a directory prefix."""
    return gcs_path_is_file(gcs_path) or gcs_path_is_dir(gcs_path)


def require_gcs_file(gcs_path: str) -> None:
    """Raise an exception if gcs_path does not exist as a file (blob)."""
    if not gcs_path_is_file(gcs_path):
        raise Exception(f"gs:// object not found: '{gcs_path}'")


def require_gcs_dir(gcs_path: str) -> None:
    """Raise an exception if gcs_path does not exist as a directory prefix."""
    if not gcs_path_is_dir(gcs_path):
        raise Exception(f"gs:// directory not found: '{gcs_path}'")


def load_gcs_text(gcs_path: str) -> str:
    """Download a file from Google Cloud Storage and return its contents as text."""
    bucket_name, blob_name = _split_gcs_path(gcs_path)
    blob = _get_storage_client().bucket(bucket_name).blob(blob_name)
    if not blob.exists():
        raise Exception(f"gs:// object not found: '{gcs_path}'")
    return blob.download_as_text()


def load_gcs_yaml(gcs_path: str) -> Dict[str, Any]:
    """Download a yaml file from Google Cloud Storage and parse it into a dict."""
    loaded = yaml.safe_load(load_gcs_text(gcs_path))
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise Exception(
            f"expected a yaml mapping at '{gcs_path}', found {type(loaded).__name__}")
    return loaded


def load_gcs_csv(gcs_path: str, required_columns: Optional[Iterable[str]] = None) -> List[Dict[str, str]]:
    """Download a csv file from Google Cloud Storage and parse it into a list of dicts, one per row, keyed
    by column header.

    :param required_columns: if given, raise an exception if any of these columns is missing from the header.
    """
    reader = csv.DictReader(io.StringIO(load_gcs_text(gcs_path)))
    if required_columns is not None:
        missing = [column for column in required_columns if column not in (reader.fieldnames or [])]
        if missing:
            raise Exception(f"csv file '{gcs_path}' is missing required column(s): {', '.join(missing)}")
    return list(reader)


