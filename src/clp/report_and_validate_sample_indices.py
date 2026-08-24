#!/usr/bin/env python3
"""Summarize and validate the sample index situation for a sequencing run, from bcl-convert's
demultiplexing reports.  Reports directory can be either in local file system or google bucket.

Report output (csv/tsv/log/pdf) is always written locally.
"""
import argparse
import csv
import os
import re
import sys
from typing import Dict, List, Optional, Tuple
from xml.etree import ElementTree

from util import path_util

DEMULTIPLEX_STATS_FILE = "Demultiplex_Stats.csv"
UNKNOWN_BARCODES_FILE = "Top_Unknown_Barcodes.csv"
INDEX_HOPPING_FILE = "Index_Hopping_Counts.csv"
UNDETERMINED = "Undetermined"
EXCEEDS_THRESHOLD = " EXCEEDS THRESHOLD"

MAX_FRAC_UNDETERMINED_READS = 0.07
MAX_FRAC_ALL_G = 0.15
ALL_G_REGEX = re.compile(r"^G+$")


class SampleIndexValidationError(Exception):
    """Raised when the sample index metrics for a run exceed an acceptable threshold, or the run's
    reports can't be parsed."""


def _num_reads(row: Dict[str, str]) -> float:
    return float(row["# Reads"])


def summarize_top_unknown_barcodes(out_file: str, reports_dir: str, num_to_report: int = 1000) -> None:
    """Create a csv of the top unmatched sample indices for a run, sorted by descending read count.

    Reads Demultiplex_Stats.csv in addition to Top_Unknown_Barcodes.csv in order to compute each
    unmatched index pair's percentage of all reads (not just of unmatched reads).
    """
    demultiplex_rows = path_util.load_csv_rows(
        path_util.join(reports_dir, DEMULTIPLEX_STATS_FILE), required_columns=["# Reads"])
    num_reads = sum(_num_reads(row) for row in demultiplex_rows)

    unknown_rows = path_util.load_csv_rows(
        path_util.join(reports_dir, UNKNOWN_BARCODES_FILE), required_columns=["index", "index2", "# Reads"])
    aggregated: Dict[Tuple[str, str], float] = {}
    for row in unknown_rows:
        key = (row["index"], row["index2"])
        aggregated[key] = aggregated.get(key, 0.0) + _num_reads(row)
    num_unknown_reads = sum(aggregated.values())
    top_entries = sorted(aggregated.items(), key=lambda item: -item[1])[:num_to_report]

    with open(out_file, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["index", "index2", "num_reads", "frac_of_unknown_reads", "frac_of_all_reads"])
        for (index, index2), num in top_entries:
            writer.writerow([
                index, index2, int(num),
                round(num / num_unknown_reads, 4),
                round(num / num_reads, 4),
            ])


def summarize_demultiplex_stats(out_file: str, reports_dir: str) -> None:
    """Create a tab-separated file summarizing PF read counts per library for a run."""
    rows = path_util.load_csv_rows(
        path_util.join(reports_dir, DEMULTIPLEX_STATS_FILE), required_columns=["SampleID", "# Reads"])
    library_sizes: Dict[str, float] = {}
    undetermined_size = 0.0
    for row in rows:
        reads = _num_reads(row)
        if row["SampleID"] == UNDETERMINED:
            undetermined_size += reads
        else:
            library_sizes[row["SampleID"]] = library_sizes.get(row["SampleID"], 0.0) + reads
    total_reads = sum(library_sizes.values()) + undetermined_size

    with open(out_file, "w", newline="") as fh:
        writer = csv.writer(fh, delimiter="\t")
        writer.writerow(["Library", "PF_reads"])
        for library_name, size in library_sizes.items():
            writer.writerow([library_name, int(size)])
        writer.writerow([UNDETERMINED, int(undetermined_size)])
        writer.writerow(["total", int(total_reads)])


def _sample_index_bar_plot(out_pdf: str, all_sizes: Dict[str, float], analysis_identifier: Optional[str],
                            lanes: List[str], exceeds_threshold: bool) -> None:
    """Bar chart of PF reads per library, written to out_pdf. Approximates sampleIndexBarPlot()."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    names = list(all_sizes.keys())
    values_millions = [v / 1e6 for v in all_sizes.values()]
    total = sum(all_sizes.values())

    fig, ax = plt.subplots(figsize=(max(6.0, 0.5 * len(names)), 6.0))
    bars = ax.bar(range(len(names)), values_millions, color="lightblue")
    ax.set_ylabel("Reads per Library [millions]")
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, rotation=60, ha="right", fontsize=8)

    max_value = max(values_millions) if values_millions else 0.0
    for bar, size in zip(bars, all_sizes.values()):
        pct = f"{100 * size / total:.1f}%"
        ax.text(bar.get_x() + bar.get_width() / 2, max_value / 1.5, pct, rotation=60,
                ha="center", va="bottom", fontsize=9)

    lanes_str = f"lane {lanes[0]}" if len(lanes) == 1 else f"lanes {', '.join(lanes)}"
    title = f"{analysis_identifier} PF reads per library {lanes_str}" if analysis_identifier \
        else f"PF reads per library {lanes_str}"
    ax.set_title(title)
    if exceeds_threshold:
        fig.text(0.5, 0.97, "Sample index problem exceeds threshold!", color="red", ha="center", fontsize=11)

    fig.tight_layout()
    fig.savefig(out_pdf)
    plt.close(fig)


def plot_and_validate_sample_index_reports(
        demultiplex_stats_file: str,
        unknown_barcodes_file: str,
        index_hopping_file: Optional[str] = None,
        analysis_identifier: Optional[str] = None,
        out_pdf: Optional[str] = None,
        out_log: Optional[str] = None,
) -> List[str]:
    """Determine whether the sample index situation looks reasonable, logging the result. If there is a
    problem, the returned messages (and out_pdf, if given) will call it out.

    :param demultiplex_stats_file: bcl-convert Demultiplex_Stats.csv
    :param unknown_barcodes_file: csv in the format written by summarize_top_unknown_barcodes()
    :param index_hopping_file: bcl-convert Index_Hopping_Counts.csv; only needed if out_pdf is given
    :param analysis_identifier: used in the PDF title
    :param out_pdf: if given, a PDF bar chart of reads per library is written here
    :param out_log: if given, the returned messages are also written to this file
    :return: messages describing the sample index situation
    """
    demultiplex_rows = path_util.load_csv_rows(
        demultiplex_stats_file, required_columns=["SampleID", "Lane", "# Reads"])
    unknown_rows = path_util.load_csv_rows(
        unknown_barcodes_file, required_columns=["index", "index2", "frac_of_all_reads"])
    for row in unknown_rows:
        row["has_all_G"] = bool(ALL_G_REGEX.match(row["index"])) or bool(ALL_G_REGEX.match(row["index2"]))

    num_undetermined_reads = sum(
        _num_reads(row) for row in demultiplex_rows if row["SampleID"] == UNDETERMINED)
    num_all_reads = sum(_num_reads(row) for row in demultiplex_rows)

    library_sizes: Dict[str, float] = {}
    for row in demultiplex_rows:
        if row["SampleID"] != UNDETERMINED:
            library_sizes[row["SampleID"]] = library_sizes.get(row["SampleID"], 0.0) + _num_reads(row)
    smallest_library, num_smallest_library = min(library_sizes.items(), key=lambda item: item[1])
    num_largest_library = max(library_sizes.values())

    frac_undetermined = num_undetermined_reads / num_all_reads
    frac_undetermined_exceeds_threshold = frac_undetermined > MAX_FRAC_UNDETERMINED_READS
    messages = [
        f"{num_undetermined_reads:.0f} undetermined reads ({100 * frac_undetermined:.1f}%)"
        f"{EXCEEDS_THRESHOLD if frac_undetermined_exceeds_threshold else ''}"
    ]
    messages.append(
        f"Smallest library ({smallest_library}): {num_smallest_library:.0f} "
        f"({100 * num_smallest_library / num_all_reads:.1f}%), "
        f"{100 * num_smallest_library / num_largest_library:.1f}% of largest library."
    )

    # frac_of_all_reads is precomputed by summarize_top_unknown_barcodes() relative to *all* reads,
    # not just unmatched ones.
    frac_all_g = sum(float(row["frac_of_all_reads"]) for row in unknown_rows if row["has_all_G"])
    frac_all_g_exceeds_threshold = frac_all_g > MAX_FRAC_ALL_G
    messages.append(
        "Percentage of reads that have an all-G sample index (possibly one of dual indices) : "
        f"{100 * frac_all_g:.1f}%{EXCEEDS_THRESHOLD if frac_all_g_exceeds_threshold else ''}"
    )
    messages.append("For details on unmatched sample indices, see:")
    messages.append(unknown_barcodes_file)

    for message in messages:
        print(message, file=sys.stderr)
    if out_log:
        with open(out_log, "w") as fh:
            fh.write("\n".join(messages) + "\n")

    if out_pdf:
        if index_hopping_file is None:
            raise SampleIndexValidationError("index_hopping_file is required when out_pdf is given")
        lanes = sorted({row["Lane"] for row in demultiplex_rows},
                        key=lambda lane: (int(lane), lane) if lane.isdigit() else (-1, lane))
        index_hopping_rows = path_util.load_csv_rows(
            index_hopping_file, required_columns=["SampleID", "# Reads"])
        num_index_hop_reads = sum(
            _num_reads(row) for row in index_hopping_rows if row["SampleID"] == "")
        all_sizes = dict(library_sizes)
        if num_index_hop_reads > 0:
            all_sizes["Index hopping"] = num_index_hop_reads
            all_sizes["Other undetermined"] = num_undetermined_reads - num_index_hop_reads
        else:
            all_sizes["Undetermined"] = num_undetermined_reads
        exceeds_threshold = frac_undetermined_exceeds_threshold or frac_all_g_exceeds_threshold
        _sample_index_bar_plot(out_pdf, all_sizes, analysis_identifier, lanes, exceeds_threshold)

    return messages


def _extract_flowcell(run_info_xml_text: str) -> str:
    root = ElementTree.fromstring(run_info_xml_text)
    flowcell_elem = root.find(".//Flowcell")
    if flowcell_elem is None or not flowcell_elem.text:
        raise SampleIndexValidationError("could not find a Flowcell element in RunInfo.xml")
    return flowcell_elem.text.strip()


def report_and_validate_sample_indices(reports_dir: str, output_dir: str = ".", make_plot: bool = False) -> None:
    """Summarize and validate the sample index situation for a sequencing run.

    :param run_folder: run folder, either a local path or a gs:// path. Must contain RunInfo.xml and a
        fastq/Reports subdirectory containing bcl-convert's demultiplexing reports.
    :param output_dir: local directory to which reports are written.
    :param make_plot: if True, also write a PDF bar chart of reads per library.
    :raise SampleIndexValidationError: if the sample index metrics exceed an acceptable threshold.
    """
    reports_dir = reports_dir.rstrip("/")
    flowcell = _extract_flowcell(path_util.read_text(path_util.join(reports_dir, "RunInfo.xml")))

    top_unknown_barcodes_file = os.path.join(output_dir, f"{flowcell}.Top_Unknown_Barcodes.csv")
    summarize_top_unknown_barcodes(out_file=top_unknown_barcodes_file, reports_dir=reports_dir)
    summarize_demultiplex_stats(
        out_file=os.path.join(output_dir, f"{flowcell}.Demultiplex_Stats.tsv"), reports_dir=reports_dir)

    messages = plot_and_validate_sample_index_reports(
        demultiplex_stats_file=path_util.join(reports_dir, DEMULTIPLEX_STATS_FILE),
        unknown_barcodes_file=top_unknown_barcodes_file,
        index_hopping_file=path_util.join(reports_dir, INDEX_HOPPING_FILE) if make_plot else None,
        analysis_identifier=flowcell,
        out_pdf=os.path.join(output_dir, f"{flowcell}.barcode_metrics.pdf") if make_plot else None,
        out_log=os.path.join(output_dir, f"{flowcell}.sample_index_report.log"),
    )

    concatenated_messages = "\n".join(messages)
    if any(EXCEEDS_THRESHOLD in message for message in messages):
        raise SampleIndexValidationError(concatenated_messages)
    print("Sample index metrics look good.\n" + concatenated_messages, file=sys.stderr)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "reports_dir", help="DRAGEN Reports directory, either a local path or a gs:// path.")
    parser.add_argument(
        "--output-dir", "-o", default=".",
        help="Local directory to which reports are written. Default: %(default)s")
    parser.add_argument(
        "--plot", action="store_true", default=False,
        help="Also write a PDF bar chart of reads per library (requires matplotlib).")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report_and_validate_sample_indices(args.reports_dir, args.output_dir, make_plot=args.plot)
    except SampleIndexValidationError as e:
        print(str(e), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
