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
"""Compute the labels that the snRNA Nextflow workflow uses to name its output subdirectories.

The labels are passed to the workflow as params (cbrb_label, cell_selection_label, dropulation_label, mmc_label),
and the workflow builds output directories from them, e.g.
<outdir>/<referenceName>/cbrb/<cbrb_label>/cell_selection/<cell_selection_label>/standard_analysis/village/<dropulation_label>/
"""
import struct
import zlib
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional

from util.argparse_util import LaunchSnRnaError

# The cbrb arguments that we make decisions based on.
CBRB_EXPECTED_CELLS = "--expected-cells"
CBRB_TOTAL_DROPLETS_INCLUDED = "--total-droplets-included"
CBRB_NUM_TRAINING_TRIES = "--num-training-tries"
CBRB_FINAL_ELBO_FAIL_FRACTION = "--final-elbo-fail-fraction"
CBRB_LEARNING_RATE = "--learning-rate"

# The defaults for these arguments, while --expected-cells and --total-droplets-included are determined using DropSift.
# Must match CBRB_DEFAULTS() in the Nextflow workflow.  Note that types matter: a user-supplied value is a string,
# so the defaults below are also strings.
CBRB_DEFAULTS: Dict[str, Any] = {
    CBRB_NUM_TRAINING_TRIES: "3",
    CBRB_FINAL_ELBO_FAIL_FRACTION: "0.1",
    CBRB_LEARNING_RATE: "0.00000625",
}

QUERY_MARKERS_EXTENSION = "query_markers.json"


def _stable_hash(s: str) -> int:
    """Return a hash of s that is the same across Python processes (unlike the built-in hash())."""
    return zlib.crc32(s.encode("utf-8"))


def _parse_cbrb_arg_string(arg_string: Optional[str]) -> Dict[str, Any]:
    """Create a dictionary of arguments from the argument string, on top of CBRB_DEFAULTS.
    Arguments with values are expected to be passed as --key=value, and flags as --flag.  A flag's value is ''.
    Whitespace in values is not supported."""
    arg_dict = dict(CBRB_DEFAULTS)
    if arg_string:
        for token in arg_string.split():
            if "=" in token:
                k, v = token.split("=", 1)
                arg_dict[k] = v
            else:
                arg_dict[token] = ""
    return arg_dict


def _to_groovy_string(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def make_cbrb_label(manifest: Dict[str, Any]) -> str:
    if manifest.get("skipCbrb", False):
        return "skip"
    arg_dict = _parse_cbrb_arg_string(manifest.get("cbrbArgs"))
    label = ""
    if arg_dict.get(CBRB_EXPECTED_CELLS) is not None:
        label += f"ec-{arg_dict[CBRB_EXPECTED_CELLS]}_"
    if arg_dict.get(CBRB_TOTAL_DROPLETS_INCLUDED) is not None:
        label += f"tdi-{arg_dict[CBRB_TOTAL_DROPLETS_INCLUDED]}_"
    if not label.endswith("_"):
        label += "auto_"
    label += f"lr-{arg_dict.get(CBRB_LEARNING_RATE)}"

    # figure out if there are any other parameters that should be included in the label
    for key in (CBRB_EXPECTED_CELLS, CBRB_TOTAL_DROPLETS_INCLUDED, CBRB_LEARNING_RATE):
        arg_dict.pop(key, None)
    for k, v in CBRB_DEFAULTS.items():
        if k in arg_dict and arg_dict[k] == v:
            del arg_dict[k]
    if not manifest.get("useSvmParameterEstimation", True):
        arg_dict["disableSvmParameterEstimation"] = True
    # if any arguments remain, make a hash of them.
    if arg_dict:
        remaining_args_string = "&".join(f"{k}={_to_groovy_string(v)}" for k, v in arg_dict.items())
        label += f"_{_stable_hash(remaining_args_string):08x}"
    return label


def has_manual_cell_selection_thresholds(manifest: Dict[str, Any]) -> bool:
    return any(manifest.get(key) is not None
               for key in ("minUmisPerCell", "maxUmisPerCell", "minIntronicPerCell", "maxIntronicPerCell"))


def _format_float_3(value: Any) -> str:
    """Mimic Groovy String.format('%.3f', value as Float)."""
    as_float32 = struct.unpack("f", struct.pack("f", float(value)))[0]
    return str(Decimal(repr(as_float32)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP))


def make_cell_selection_label(manifest: Dict[str, Any]) -> str:
    if not has_manual_cell_selection_thresholds(manifest):
        return "auto"
    label_components: List[str] = []
    min_umis = manifest.get("minUmisPerCell")
    max_umis = manifest.get("maxUmisPerCell")
    if min_umis is not None or max_umis is not None:
        # Note that 0 is treated the same as unspecified, to match the Nextflow workflow.
        min_umi = min_umis or 1
        max_umi = str(max_umis) if max_umis is not None else "Inf"
        label_components.append(f"umi_{min_umi}-{max_umi}")
    min_intronic = manifest.get("minIntronicPerCell")
    max_intronic = manifest.get("maxIntronicPerCell")
    if min_intronic is not None or max_intronic is not None:
        label_components.append(
            f"intronic_{_format_float_3(min_intronic or 0.0)}-{_format_float_3(max_intronic or 1.0)}")
    return "_".join(label_components)


def _basename(path: str) -> str:
    return path.rstrip("/").rsplit("/", 1)[-1]


def _strip_extension(name: str, ext: str) -> str:
    suffix = "." + ext
    return name[:-len(suffix)] if name.endswith(suffix) else name


def make_dropulation_label(vcf: str, donor_file: str) -> str:
    vcf_name = _basename(vcf)
    for ext in ("gz", "vcf", "bcf"):
        vcf_name = _strip_extension(vcf_name, ext)
    donor_name = _basename(donor_file)
    for ext in ("txt", "donors"):
        donor_name = _strip_extension(donor_name, ext)
    return f"{vcf_name}.{donor_name}"


def make_mmc_label(mmc_query_markers: str) -> str:
    name = _basename(mmc_query_markers)
    if not name.endswith("." + QUERY_MARKERS_EXTENSION):
        raise LaunchSnRnaError(f"mmcQueryMarkers '{mmc_query_markers}' does not have expected extension "
                               f"{QUERY_MARKERS_EXTENSION}")
    return _strip_extension(name, QUERY_MARKERS_EXTENSION)


def add_output_labels(manifest: Dict[str, Any]) -> None:
    """Compute the output directory labels from the manifest and store them in the manifest, replacing any
    existing values (e.g. carried over from upstream properties.yaml files)."""
    if "cbrb_label" not in manifest:
        manifest["cbrb_label"] = make_cbrb_label(manifest)
    if "cell_selection_label" not in manifest:
        manifest["cell_selection_label"] = make_cell_selection_label(manifest)
    if manifest.get("vcf") and manifest.get("donorFile") and "dropulation_label" not in manifest:
        manifest["dropulation_label"] = make_dropulation_label(manifest["vcf"], manifest["donorFile"])
    if manifest.get("mmcQueryMarkers") and "mmc_label" not in manifest:
        manifest["mmc_label"] = make_mmc_label(manifest["mmcQueryMarkers"])
