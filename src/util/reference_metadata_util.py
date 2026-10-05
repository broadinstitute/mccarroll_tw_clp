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
from typing import Dict, Optional

from util import gcs_util

ReferenceParents = [
'gs://mccarroll_scrnaseq_standard/metadata/reference'
]

_reference_map: Optional[Dict[str, str]] = None


def _build_reference_map() -> Dict[str, str]:
    """Scan ReferenceParents for files of the form <referenceParent>/<referenceName>/*.fasta.gz,
    and build a map from referenceName to its gs:// path."""
    reference_map: Dict[str, str] = {}
    for parent in ReferenceParents:
        parent_prefix = parent.rstrip('/') + '/'
        for gcs_path in gcs_util.list_gcs_paths(parent):
            relative = gcs_path[len(parent_prefix):]
            parts = relative.split('/')
            if len(parts) == 2 and parts[1].endswith('.fasta.gz'):
                reference_map.setdefault(parts[0], gcs_path)
    return reference_map


def _get_reference_map() -> Dict[str, str]:
    global _reference_map
    if _reference_map is None:
        _reference_map = _build_reference_map()
    return _reference_map


def validateReference(reference: str) -> None:
    """
    Resolve a reference name to a GCS path, and validate that the GCS path exists.

    :param reference: The reference name or GCS path.
    :return: The resolved GCS path.
    :raises ValueError: If the reference name is not recognized or the GCS path does not exist.
    """
    if '/' in reference:
        gcs_path = reference
    else:
        reference_map = _get_reference_map()
        if reference not in reference_map:
            raise ValueError(f"Reference name '{reference}' not recognized.")
        gcs_path = reference_map[reference]
    if not gcs_util.gcs_path_is_file(gcs_path):
        raise ValueError(
            f"Reference '{gcs_path}' does not exist as a file in GCS.")
