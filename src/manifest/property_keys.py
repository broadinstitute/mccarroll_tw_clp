"""Strings for element names in properties.yaml files."""
from manifest.enums import (
    FunctionalDataProcessorStrategy,
    StrandStrategy,
    YamlSchemaElementType,
    enum_names,
)
from manifest.util.schema_element import YamlSchemaElement


class YamlPropertyKey:
    analysis_identifier = YamlSchemaElement(
        "analysisIdentifier",
        doc="Zamboni multiome workflow that created fastqs in this directory.",
        tyype=YamlSchemaElementType.STRING)
    analysis_directory = YamlSchemaElement(
        "analysisDirectory",
        doc="Directory for Zamboni multiome workflow that created these fastqs.",
        tyype=YamlSchemaElementType.PATH)
    project = YamlSchemaElement(
        "project",
        doc="Key into project_metadata.yaml to find project resources.",
        tyype=YamlSchemaElementType.STRING)
    project_metadata_file = YamlSchemaElement(
        "projectMetadataFile",
        doc="File containing project resources.",
        tyype=YamlSchemaElementType.PATH)
    command_line = YamlSchemaElement(
        "commandLine",
        doc="Command line that launched this workflow.",
        tyype=YamlSchemaElementType.STRING)
    workflow_submission_date = YamlSchemaElement(
        "workflowSubmissionDate",
        doc="'nuff said'",
        tyype=YamlSchemaElementType.DATE)
    workflow_version = YamlSchemaElement(
        "workflowVersion",
        doc="Integer workflow timestamp",
        tyype=YamlSchemaElementType.INT)
    workflow_kind = YamlSchemaElement(
        "workflowKind",
        doc="Kind of workflow (e.g. alignment, locus function, etc)",
        tyype=YamlSchemaElementType.ENUM,
        enum_values=enum_names(WorkflowKind))
    tools_directory = YamlSchemaElement(
        "toolsDirectory",
        doc="Location of tools used to run this workflow.",
        tyype=YamlSchemaElementType.PATH)
    creating_user = YamlSchemaElement(
        "creatingUser",
        doc="User who launched this this workflow (or its predecessor).",
        tyype=YamlSchemaElementType.STRING)
    library_directory = YamlSchemaElement(
        "libraryDirectory",
        doc="Root directory for library.  Should always be absolute, so needs to be fixed if library is moved.",
        tyype=YamlSchemaElementType.PATH)
    upstream_properties = YamlSchemaElement(
        "upstreamProperties",
        doc="Properties for the analysis that was input to the current analysis.",
        tyype=YamlSchemaElementType.PATH)
    legacy_properties = YamlSchemaElement(
        "legacyProperties",
        doc="Marks a properities.yaml created for a pre-yaml analysis directory,",
        tyype=YamlSchemaElementType.BOOLEAN)


class ScRnaBasecallingPropertyKey:
    library = YamlSchemaElement(
        "library",
        doc="Library name (without experiment date prefix).",
        tyype=YamlSchemaElementType.STRING)
    bam = YamlSchemaElement(
        "bam",
        doc="BAM(s) or bam_list(s) corresponding to this properties file.",
        tyype=YamlSchemaElementType.PATH,
        list_allowed=True)
    flowcell_date = YamlSchemaElement(
        "flowcellDate",
        doc="Date from run folder.",
        tyype=YamlSchemaElementType.DATE)
    instrument_model = YamlSchemaElement(
        "instrumentModel",
        doc="Either inferred from run folder, or specified in workflow submission.",
        tyype=YamlSchemaElementType.STRING)
    experiment_date = YamlSchemaElement(
        "experimentDate",
        tyype=YamlSchemaElementType.DATE)
    version10_x = YamlSchemaElement(
        "version10X",
        doc="Version of 10X chemistry",
        tyype=YamlSchemaElementType.STRING)
    read_structure = YamlSchemaElement(
        "readStructure",
        doc="The read structure passed to BasecallsToSam, not necessarily the native read structure.",
        tyype=YamlSchemaElementType.STRING)
    sample_type = YamlSchemaElement(
        "sampleType",
        doc=f"One of {', '.join(enum_names(SampleType))}",
        tyype=YamlSchemaElementType.ENUM,
        enum_values=enum_names(SampleType))
    estimated_num_cells = YamlSchemaElement(
        "estimated_num_cells",
        doc="Estimated number of cells in the reaction.",
        tyype=YamlSchemaElementType.INT)
    bams = YamlSchemaElement(
        "bams",
        doc="For unmapped BAM input (instead of run folder).",
        tyype=YamlSchemaElementType.PATH,
        list_allowed=True)
    read1_fastqs = YamlSchemaElement(
        "read1Fastqs",
        doc="For FASTQ input (instead of run folder).",
        tyype=YamlSchemaElementType.PATH,
        list_allowed=True)
    read2_fastqs = YamlSchemaElement(
        "read2Fastqs",
        doc="For FASTQ input (instead of run folder).",
        tyype=YamlSchemaElementType.PATH,
        list_allowed=True)
    run_folder = YamlSchemaElement(
        "runFolder",
        doc="Sequencer run folder",
        tyype=YamlSchemaElementType.PATH,
        list_allowed=True)
    strand_strategy = YamlSchemaElement(
        "strandStrategy",
        doc="One of " + ", ".join(f"'{n}'" for n in enum_names(StrandStrategy)) + ".",
        tyype=YamlSchemaElementType.ENUM,
        enum_values=enum_names(StrandStrategy))
    sample_indices = YamlSchemaElement(
        "sampleIndices",
        doc="Container for one or more lane, sample index",
        tyype=YamlSchemaElementType.DICT,
        opaque_dict=True)
    lane = YamlSchemaElement(
        "lane",
        doc="lane number",
        tyype=YamlSchemaElementType.INT)
    sample_index = YamlSchemaElement(
        "sampleIndex",
        doc="index sequence, with comma(s) if multi-indexed",
        tyype=YamlSchemaElementType.STRING)
    cbcs_corrected = YamlSchemaElement(
        "cbcsCorrected",
        doc="CBC correction has been run on the unmapped BAMs.",
        tyype=YamlSchemaElementType.BOOLEAN)
    cbcs_tagged = YamlSchemaElement(
        "cbcsTagged",
        doc="The unmapped BAMs already have CBC tags.",
        tyype=YamlSchemaElementType.BOOLEAN)


class ScRnaAlignmentPropertyKey:
    library = ScRnaBasecallingPropertyKey.library
    version10_x = ScRnaBasecallingPropertyKey.version10_x
    strand_strategy = ScRnaBasecallingPropertyKey.strand_strategy
    reference = YamlSchemaElement(
        "reference",
        doc="Reference fasta(.gz).",
        tyype=YamlSchemaElementType.PATH,
        required=True)
    include_secondary_alignments = YamlSchemaElement(
        "includeSecondaryAlignments",
        doc="Were multiple alignments for a read enabled, which ensables metagene discovery.",
        tyype=YamlSchemaElementType.BOOLEAN,
        required=True)
    locus_function_label = YamlSchemaElement(
        "locusFunctionLabel",
        doc="Just the locus function label, e.g. 'exonic+intronic'.",
        tyype=YamlSchemaElementType.STRING,
        required=True)
    upstream_properties = YamlPropertyKey.upstream_properties
    unmapped_bam = YamlSchemaElement(
        "unmappedBam",
        doc="Path(s) of unmapped bam input to this workflow",
        tyype=YamlSchemaElementType.PATH,
        required=True,
        list_allowed=True)
    estimated_num_cells = YamlSchemaElement(
        "estimatedNumCells",
        doc="Estimated number of cells in the reaction.",
        tyype=YamlSchemaElementType.INT)
    experiment_date = YamlSchemaElement(
        "experimentDate",
        doc="",
        tyype=YamlSchemaElementType.DATE)
    mark_chimeric_reads = YamlSchemaElement(
        "markChimericReads",
        doc="",
        tyype=YamlSchemaElementType.BOOLEAN)
    dge_min_read_mq = YamlSchemaElement(
        "dgeMinReadMq",
        doc="Minimum mapping quality for reads to be included in DGE counting.",
        tyype=YamlSchemaElementType.INT,
        required=True)
    dge_functional_strategy = YamlSchemaElement(
        "dgeFunctionalStrategy",
        doc="Passed to DigitalExpression FUNCTIONAL_STRATEGY.",
        tyype=YamlSchemaElementType.ENUM,
        enum_values=enum_names(FunctionalDataProcessorStrategy),
        required=True)


class ScRnaCbrbPropertyKey:
    upstream_properties = YamlPropertyKey.upstream_properties
    other_cbrb_arg = YamlSchemaElement(
        "otherCbrbArg",
        doc="User-specified arguments passed to CBRB",
        tyype=YamlSchemaElementType.STRING,
        required=False,
        list_allowed=True)


class ScRnaCellSelectionPropertyKey:
    locus_function_properties = YamlSchemaElement(
        "locusFunctionProperties",
        doc="Properties for the locusFunction analysis used in the current analysis.",
        tyype=YamlSchemaElementType.PATH)
    cbrb_properties = YamlSchemaElement(
        "cbrbProperties",
        doc="Properties for the CBRB analysis used in the current analysis, if cell selection is done on "
            "CBRB-ed data.",
        tyype=YamlSchemaElementType.PATH)
    min_umis_per_cell = YamlSchemaElement(
        "minUmisPerCell",
        doc="Optional integer UMIs per cell threshold.",
        tyype=YamlSchemaElementType.INT)
    max_umis_per_cell = YamlSchemaElement(
        "maxUmisPerCell",
        doc="Optional integer UMIs per cell threshold.",
        tyype=YamlSchemaElementType.INT)
    max_rbmt_per_cell = YamlSchemaElement(
        "maxRbmtPerCell",
        doc="Optional floating-point RBMT fraction per cell threshold (between 0 and 1).",
        tyype=YamlSchemaElementType.FLOAT)
    min_intronic_per_cell = YamlSchemaElement(
        "minIntronicPerCell",
        doc="Optional floating-point fraction intronic per cell threshold (between 0 and 1).",
        tyype=YamlSchemaElementType.FLOAT)
    max_intronic_per_cell = YamlSchemaElement(
        "maxIntronicPerCell",
        doc="Optional floating-point fraction intronic per cell threshold (between 0 and 1).",
        tyype=YamlSchemaElementType.FLOAT)
    efficiency_threshold_log10 = YamlSchemaElement(
        "efficiencyThresholdLog10",
        doc="Threshold for filtering cells that are too efficient, i.e. have too many UMIs/read.",
        tyype=YamlSchemaElementType.FLOAT)
    call_stamps_method = YamlSchemaElement(
        "callSTAMPsMethod",
        doc=f"CallSTAMPs method to use, if automatic selection picks a bad one.  One of "
            + ", ".join(f"'{n}'" for n in enum_names(CallSTAMPsMethod)),
        tyype=YamlSchemaElementType.ENUM,
        enum_values=enum_names(CallSTAMPsMethod))
    is10_x = YamlSchemaElement(
        "is10X",
        doc="CallSTAMPs handles 10X libraries differently from Drop-seq",
        tyype=YamlSchemaElementType.BOOLEAN,
        required=True)
    selection_criteria_label = YamlSchemaElement(
        "selectionCriteriaLabel",
        doc="Compact string representation of cell selection criteria, for naming directories and workflows.",
        tyype=YamlSchemaElementType.STRING,
        required=True)
    selected_cells_file = YamlSchemaElement(
        "selectedCellsFile",
        doc="List of cell barcodes selected by this workflow.",
        tyype=YamlSchemaElementType.PATH,
        required=True)
    upstream_properties = YamlPropertyKey.upstream_properties


class ScRnaStdAnalysisPropertyKey:
    upstream_properties = YamlPropertyKey.upstream_properties
    vcf = YamlSchemaElement(
        "vcf",
        doc="VCF or BCF used by dropulation.",
        tyype=YamlSchemaElementType.PATH)
    donor_file = YamlSchemaElement(
        "donorFile",
        doc="Donors used by dropulation.",
        tyype=YamlSchemaElementType.PATH)
    donor = YamlSchemaElement(
        "donor",
        doc="Optional single donor name for non-dropulation library.",
        tyype=YamlSchemaElementType.STRING)
    census_file = YamlSchemaElement(
        "censusFile",
        doc="Optional Dropulation-census result used by dropulation.",
        tyype=YamlSchemaElementType.PATH)
    discover_meta_genes = YamlSchemaElement(
        "discoverMetaGenes",
        doc="True is secondary alignments were included, and metagene discovery not disabled.",
        tyype=YamlSchemaElementType.BOOLEAN)
    meta_gene_dge_functional_strategy = YamlSchemaElement(
        "metaGeneDgeFunctionalStrategy",
        doc="Passed to metagene DigitalExpression FUNCTIONAL_STRATEGY.",
        tyype=YamlSchemaElementType.ENUM,
        enum_values=enum_names(FunctionalDataProcessorStrategy),
        required=True)


class XipherFilterBamPropertyKey:
    upstream_properties = YamlPropertyKey.upstream_properties
    donor = YamlSchemaElement(
        "donor",
        doc="donor name.",
        tyype=YamlSchemaElementType.STRING,
        required=True)
    is_dropulation = YamlSchemaElement(
        "isDropulation",
        doc="True if the data came from a dropulation library.",
        tyype=YamlSchemaElementType.BOOLEAN,
        required=True)


class XipherGenotypePropertyKey:
    upstream_properties = YamlPropertyKey.upstream_properties.copy(list_allowed=True)
    bams = YamlSchemaElement(
        "bams",
        doc="List of BAM files to genotype.",
        tyype=YamlSchemaElementType.PATH,
        required=True,
        list_allowed=True)
    donor = YamlSchemaElement(
        "donor",
        doc="donor name.",
        tyype=YamlSchemaElementType.STRING)
    gnomad_variants = YamlSchemaElement(
        "gnomADVariants",
        doc="gnomAD variants to use for genotyping.",
        tyype=YamlSchemaElementType.PATH)
    reference = YamlSchemaElement(
        "reference",
        doc="Reference fasta(.gz).",
        tyype=YamlSchemaElementType.PATH,
        required=True)


class MmcFromSpecifiedMarkersPropertyKey:
    query_markers = YamlSchemaElement(
        "queryMarkers",
        doc="Path to the query_markers.json used by MapMyCells",
        tyype=YamlSchemaElementType.PATH)
    input = YamlSchemaElement(
        "input",
        doc="Path to the input file begin classified",
        tyype=YamlSchemaElementType.PATH)
    mmc_args = YamlSchemaElement(
        "mmcArgs",
        doc="Additional arguments passed to MapMyCells.",
        tyype=YamlSchemaElementType.STRING,
        list_allowed=True)
    reference = YamlSchemaElement(
        "reference",
        doc="Reference fasta(.gz).  Used to locate reduced GTF in order to get gene IDs if input is DGE.",
        tyype=YamlSchemaElementType.PATH)
    map_to_ensembl = YamlSchemaElement(
        "mapToEnsembl",
        doc="If true, MapMyCells will map to Ensembl gene IDs.  Obsolete",
        tyype=YamlSchemaElementType.BOOLEAN)


class ScRnaDownstreamPropertyKey:
    """Definitions for properties.yaml elements that represent dictionaries passed to downstream workflows."""
    downstream = YamlSchemaElement(
        "downstream",
        doc="Settings passed through to downtream workflows",
        tyype=YamlSchemaElementType.DICT,
        opaque_dict=True)
    alignment = YamlSchemaElement(
        "alignment",
        doc="Settings passed through to alignment workflow",
        tyype=YamlSchemaElementType.DICT,
        opaque_dict=True)
    locus_function = YamlSchemaElement(
        "locusFunction",
        doc="Settings passed through to locus function workflow",
        tyype=YamlSchemaElementType.DICT,
        opaque_dict=True)
    cbrb = YamlSchemaElement(
        "cbrb",
        doc="Settings passed through to CBRB workflow",
        tyype=YamlSchemaElementType.DICT,
        opaque_dict=True)
    cell_selection = YamlSchemaElement(
        "cellSelection",
        doc="Settings passed through to cell selection workflow",
        tyype=YamlSchemaElementType.DICT,
        opaque_dict=True)
    std_analysis = YamlSchemaElement(
        "stdAnalysis",
        doc="Settings passed through to standard analysis workflow",
        tyype=YamlSchemaElementType.DICT,
        opaque_dict=True)
    cell_classification = YamlSchemaElement(
        "cellClassification",
        doc="Settings passed through to cell classification workflow",
        tyype=YamlSchemaElementType.DICT,
        opaque_dict=True)
    mmc_from_specified_markers = YamlSchemaElement(
        "mmcFromSpecifiedMarkers",
        doc="Settings passed through to mmcFromSpecifiedMarkers workflow",
        tyype=YamlSchemaElementType.DICT,
        opaque_dict=True)
    # This isn't really like the other elements above, but it's in the cellClassification downstream dictionary
    # and it needs to go somewhere.
    model = YamlSchemaElement(
        "model",
        doc="Passed to SendCellClassificationMessage",
        tyype=YamlSchemaElementType.STRING)
    # This isn't really like the other elements above, but it's written into the MmcFromSpecifiedMarkers
    # manifest, and it needs to go somewhere.
    reference = YamlSchemaElement(
        "reference",
        doc="Written into MmcFromSpecifiedMarkers manifest",
        tyype=YamlSchemaElementType.STRING)
    # This is here just to define the constant so standard analysis can check if it is defined in downstream.
    query_markers = YamlSchemaElement(
        "queryMarkers",
        doc="Path to the query_markers.json to be used by MapMyCells.  It is assumed that there is a "
            "corresponding recomputed_stats.h5",
        tyype=YamlSchemaElementType.STRING)
    launch = YamlSchemaElement(
        "launch",
        doc="Set to false to disable launch of this downstream workflow",
        tyype=YamlSchemaElementType.BOOLEAN)


class ScRnaLocusFunctionPropertyKey:
    upstream_properties = YamlPropertyKey.upstream_properties
    locus_function_label = YamlSchemaElement(
        "locusFunctionLabel",
        doc="Just the locus function label, e.g. 'exonic+intronic'.",
        tyype=YamlSchemaElementType.STRING,
        required=True)
    in_place = YamlSchemaElement(
        "inPlace",
        doc="True if locus function result and alignment result share the same directory.",
        tyype=YamlSchemaElementType.BOOLEAN,
        required=True)
    is10_x = YamlSchemaElement(
        "is10X",
        doc="CallSTAMPs handles 10X libraries differently from Drop-seq",
        tyype=YamlSchemaElementType.BOOLEAN,
        required=True)
