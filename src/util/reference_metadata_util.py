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
from util import gcs_util

ReferenceMap = {
    'GRCh38-2020-A': 'gs://mccarroll_scrnaseq_standard/metadata/reference/GRCh38-2020-A/GRCh38-2020-A.fasta.gz',
    'GRCh38_ensembl_v43': 'gs://mccarroll_scrnaseq_standard/metadata/reference/GRCh38_ensembl_v43/GRCh38_ensembl_v43.fasta.gz',
    'GRCh38_maskedAlt': 'gs://mccarroll_scrnaseq_standard/metadata/reference/GRCh38_maskedAlt/GRCh38_maskedAlt.fasta.gz',
    'm38': 'gs://mccarroll_scrnaseq_standard/metadata/reference/m38/m38.fasta.gz'
}

def validateReference(reference: str) -> None:
    """
    Resolve a reference name to a GCS path, and validate that the GCS path exists.

    :param reference: The reference name or GCS path.
    :return: The resolved GCS path.
    :raises ValueError: If the reference name is not recognized or the GCS path does not exist.
    """
    if '/' in reference:
        gcs_path = reference
    elif reference in ReferenceMap:
        gcs_path = ReferenceMap[reference]
    else:
        raise ValueError(f"Reference name '{reference}' not recognized.")
    if not gcs_util.gcs_path_is_file(gcs_path):
        raise ValueError(
            f"Reference '{gcs_path}' does not exist as a file in GCS.")
