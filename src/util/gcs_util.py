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

import re
from typing import Any, Dict

import yaml
from google.cloud import storage

GCS_PATH_RE = re.compile(r"^gs://(?P<bucket>[^/]+)/(?P<blob>.+)$")

storage_client = storage.Client()


def _split_gcs_path(gcs_path: str) -> (str, str):
    match = GCS_PATH_RE.match(gcs_path)
    if not match:
        raise Exception(f"not a gs:// path: '{gcs_path}'")
    return match.group("bucket"), match.group("blob")


def gcs_path_is_file(gcs_path: str) -> bool:
    """Return True if gcs_path exists as a file (blob)."""
    bucket_name, blob_name = _split_gcs_path(gcs_path)
    return storage_client.bucket(bucket_name).blob(blob_name).exists()


def gcs_path_is_dir(gcs_path: str) -> bool:
    """Return True if gcs_path exists as a directory prefix."""
    bucket_name, blob_name = _split_gcs_path(gcs_path)
    prefix = blob_name.rstrip("/") + "/"
    return any(True for _ in storage_client.bucket(bucket_name).list_blobs(prefix=prefix, max_results=1))


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


def load_gcs_yaml(gcs_path: str) -> Dict[str, Any]:
    """Download a yaml file from Google Cloud Storage and parse it into a dict."""
    bucket_name, blob_name = _split_gcs_path(gcs_path)
    blob = storage_client.bucket(bucket_name).blob(blob_name)
    if not blob.exists():
        raise Exception(f"gs:// object not found: '{gcs_path}'")
    loaded = yaml.safe_load(blob.download_as_text())
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise Exception(
            f"expected a yaml mapping at '{gcs_path}', found {type(loaded).__name__}")
    return loaded


