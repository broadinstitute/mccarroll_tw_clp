from manifest.enums import (
    FunctionalDataProcessorStrategy,
    LocusFunction,
    StrandStrategy,
    enum_names,
)
from manifest.property_keys import ScRnaDownstreamPropertyKey
from manifest.util.schema_element import YamlSchemaElement
from manifest.util.validators import YamlPathValidator, YamlPermissiveValidator
from manifest.enums import YamlSchemaElementType
from manifest.util.abstract_manifest_key import AbstractManifestKey


class CellClassificationManifestKey(AbstractManifestKey):
    """Note that cell classification workflow doesn't use a manifest.  However, there are definitions that
    can be specified in the 'downstream' section of upstream workflows, so this is here for validation."""
    model = YamlSchemaElement("model", doc="Passed to MODEL_NAME argument of SendCellClassificationMessage.",
                              tyype=YamlSchemaElementType.STRING, required=True)

    @classmethod
    def _root_elements_no_downstream(cls):
        return [cls.model]

    @classmethod
    def get_documentation_recursive_roots(cls):
        return cls.root_elements()


class XipherGenotypeManifestKey(AbstractManifestKey):
    gnomad_variants = YamlSchemaElement(
        "gnomAdVariants",
        doc="gnomAD variants to use for genotyping.  Default: use gnomAD in reference bundle, if present.  "
            "Set to null to disable use of the one in reference bundle.",
        tyype=YamlSchemaElementType.PATH)
    reference = YamlSchemaElement(
        "reference",
        doc="Reference fasta(.gz).  Default: Reference associated with BAMs, which must agree across all "
            "the BAMs.",
        tyype=YamlSchemaElementType.PATH)
    donor = YamlSchemaElement(
        "donor",
        doc="Donor name.  Default: Directory name from DONOR_REFERENCE_DIR command-line argument.",
        tyype=YamlSchemaElementType.STRING)

    @classmethod
    def _root_elements_no_downstream(cls):
        return [cls.gnomad_variants, cls.reference, cls.donor]

    @classmethod
    def get_documentation_recursive_roots(cls):
        return cls.root_elements()


class MmcFromSpecifiedMarkersManifestKey(AbstractManifestKey):
    query_markers = YamlSchemaElement(
        "queryMarkers",
        doc="Path to the query_markers.json to be used by MapMyCells.  It is assumed that there is a "
            "corresponding recomputed_stats.h5",
        tyype=YamlSchemaElementType.PATH,
        required=True)
    mmc_args = YamlSchemaElement(
        "mmcArgs",
        doc="Additional arguments to pass to MapMyCells.",
        tyype=YamlSchemaElementType.STRING,
        list_allowed=True)
    reference = YamlSchemaElement(
        "reference",
        doc="Reference fasta(.gz).  Used to locate reduced GTF in order to get gene IDs if input is DGE.",
        tyype=YamlSchemaElementType.PATH)
    library = YamlSchemaElement(
        "library",
        doc="Library name used to create the analysisIdentifier.  If not specified, it is derived from the "
            "INPUT file.",
        tyype=YamlSchemaElementType.STRING)

    @classmethod
    def _root_elements_no_downstream(cls):
        return [cls.query_markers, cls.mmc_args, cls.reference, cls.library]

    @classmethod
    def get_documentation_recursive_roots(cls):
        return cls.root_elements()


class ScRnaAlignmentManifestKey(AbstractManifestKey):
    reference = YamlSchemaElement(
        "reference", required=True, doc="Reference fasta(.gz).", tyype=YamlSchemaElementType.PATH)
    star_aligner_flag = YamlSchemaElement(
        "starAlignerFlag", doc="Passed to STAR.", tyype=YamlSchemaElementType.STRING, list_allowed=True)
    star_aligner = YamlSchemaElement(
        "starAligner",
        doc="Path of STAR binary to use. Default: the STAR aligner found via DROPSEQ_TOOLS_DIRECTORY "
            "command-line option.",
        tyype=YamlSchemaElementType.PATH)
    include_secondary_alignments = YamlSchemaElement(
        "includeSecondaryAlignments",
        doc="Set to false to disable multiple alignments for a read, which disables metagene discovery.",
        tyype=YamlSchemaElementType.BOOLEAN)
    tech_prep = YamlSchemaElement(
        "techPrep", doc="Set to false to disable pre-alignment tag and trim, and BQSR.",
        tyype=YamlSchemaElementType.BOOLEAN)
    adapter_aware_poly_a_trimmer = YamlSchemaElement(
        "adapterAwarePolyATrimmer", doc="Set to false to enable old polyA trimmer",
        tyype=YamlSchemaElementType.BOOLEAN)
    separate_secondary_species = YamlSchemaElement(
        "separateSecondarySpecies",
        doc="Set to false to disable separation of secondary species reads into separate BAMs.",
        tyype=YamlSchemaElementType.BOOLEAN)
    mark_chimeric_reads = YamlSchemaElement(
        "markChimericReads",
        doc="Set to false to disable MarkChimericReads (to simulate old Drop-seq flowcell workflow).",
        tyype=YamlSchemaElementType.BOOLEAN)
    tag_cbcs = YamlSchemaElement(
        "tagCbcs",
        doc="Set to true to extract tags from technical read even if input is already tagged.  "
            "Default: !libary_properties.cbcsTagged",
        tyype=YamlSchemaElementType.BOOLEAN)
    splice_read1 = YamlSchemaElement(
        "spliceRead1",
        doc="Set to true to PE align read 1, then splice alignment onto read 2 alignment if possible. "
            "Not allowed unless library strand strategy is ANTISENSE, unless IGNORE_WARNINGS=true. "
            "Default: false",
        tyype=YamlSchemaElementType.BOOLEAN)
    dge_min_read_mq = YamlSchemaElement(
        "dgeMinReadMq",
        doc="Minimum mapping quality for reads to be included in DGE counting. Default: 10",
        tyype=YamlSchemaElementType.INT)
    dge_functional_strategy = YamlSchemaElement(
        "dgeFunctionalStrategy",
        doc="Passed to DigitalExpression FUNCTIONAL_STRATEGY.  Default: DROPSEQ",
        tyype=YamlSchemaElementType.ENUM,
        enum_values=enum_names(FunctionalDataProcessorStrategy))

    @classmethod
    def downstream(cls):
        return YamlSchemaElement(
            "downstream",
            doc="Settings passed to downstream workflows. To suppress invocation of a downstream workflow, "
                "set it to null, e.g. 'stdAnalysis: null' will suppress automatic invocation of standard "
                "analysis.",
            tyype=YamlSchemaElementType.DICT,
            children=[
                DownstreamManifestKey.locus_function(),
                DownstreamManifestKey.cbrb(),
                DownstreamManifestKey.cell_selection(),
                DownstreamManifestKey.std_analysis(),
                DownstreamManifestKey.cell_classification(),
                DownstreamManifestKey.mmc_from_specified_markers(),
            ])

    @classmethod
    def _root_elements_no_downstream(cls):
        return [cls.reference, cls.star_aligner_flag, cls.star_aligner, cls.include_secondary_alignments,
                cls.tech_prep, cls.adapter_aware_poly_a_trimmer, cls.separate_secondary_species,
                cls.mark_chimeric_reads, cls.tag_cbcs, cls.splice_read1, cls.dge_min_read_mq,
                cls.dge_functional_strategy]

    @classmethod
    def _downstream_element_opt(cls):
        return cls.downstream()

    @classmethod
    def get_documentation_recursive_roots(cls):
        return cls.root_elements()


class ScRnaLocusFunctionManifestKey(AbstractManifestKey):
    locus_function = YamlSchemaElement(
        "locusFunction",
        doc=f"Default: {LocusFunction.EXONIC_INTRONIC.label}",
        tyype=YamlSchemaElementType.ENUM,
        enum_values={lf.label for lf in LocusFunction})

    @classmethod
    def downstream(cls):
        return YamlSchemaElement(
            "downstream",
            doc="Settings passed to downstream workflows. To suppress invocation of a downstream workflow, "
                "set it to null, e.g. 'stdAnalysis: null' will suppress automatic invocation of standard "
                "analysis.",
            tyype=YamlSchemaElementType.DICT,
            children=[
                DownstreamManifestKey.cbrb(),
                DownstreamManifestKey.cell_selection(),
                DownstreamManifestKey.std_analysis(),
                DownstreamManifestKey.cell_classification(),
                DownstreamManifestKey.mmc_from_specified_markers(),
            ])

    @classmethod
    def _root_elements_no_downstream(cls):
        return [cls.locus_function]

    @classmethod
    def _downstream_element_opt(cls):
        return cls.downstream()

    @classmethod
    def get_documentation_recursive_roots(cls):
        return cls.root_elements()


class ScRnaCbrbManifestKey(AbstractManifestKey):
    cbrb_args = YamlSchemaElement(
        "cbrbArgs", doc="Additional arguments to pass to CBRB.",
        tyype=YamlSchemaElementType.DICT, list_allowed=True, validator=YamlPermissiveValidator(),
        opaque_dict=True)
    workflow_submission_date = YamlSchemaElement(
        "workflowSubmissionDate", doc="For regression testing only, to enable stable output.",
        tyype=YamlSchemaElementType.DATE)
    gls_template = YamlSchemaElement(
        "glsTemplate", doc="Optional path to a custom googl template.", tyype=YamlSchemaElementType.PATH)
    use_svm_parameter_estimation = YamlSchemaElement(
        "useSvmParameterEstimation",
        doc="SVM parameter estimation is enabled unless both --expected-cells and --total-droplets-included "
            "appear in cbrbArgs. Set this to false to disable SVM parameter estimation and let CBRB estimate "
            "the parameters itself.",
        tyype=YamlSchemaElementType.BOOLEAN, required=False)
    force_two_cluster_solution = YamlSchemaElement(
        "forceTwoClusterSolution",
        doc="If true, attempt to find a solution with two clusters. May be useful when data is overloaded.",
        tyype=YamlSchemaElementType.BOOLEAN, required=False)

    @classmethod
    def downstream(cls):
        return YamlSchemaElement(
            "downstream",
            doc="Settings passed to downstream workflows. To suppress invocation of a downstream workflow, "
                "set it to null, e.g. 'stdAnalysis: null' will suppress automatic invocation of standard "
                "analysis.",
            tyype=YamlSchemaElementType.DICT,
            children=[
                DownstreamManifestKey.cell_selection(),
                DownstreamManifestKey.std_analysis(),
                DownstreamManifestKey.cell_classification(),
                DownstreamManifestKey.mmc_from_specified_markers(),
            ])

    @classmethod
    def _root_elements_no_downstream(cls):
        return [cls.cbrb_args, cls.workflow_submission_date, cls.gls_template,
                cls.use_svm_parameter_estimation, cls.force_two_cluster_solution]

    @classmethod
    def _downstream_element_opt(cls):
        return cls.downstream()

    @classmethod
    def get_documentation_recursive_roots(cls):
        return cls.root_elements()


class ScRnaCellSelectionManifestKey(AbstractManifestKey):
    _THRESHOLD_DOC = ("Optional cell selection threshold.  If any threshold is specified, automatic methods "
                      "will not be used.")
    min_umis_per_cell = YamlSchemaElement("minUmisPerCell", doc=_THRESHOLD_DOC, tyype=YamlSchemaElementType.INT)
    max_umis_per_cell = YamlSchemaElement("maxUmisPerCell", doc=_THRESHOLD_DOC, tyype=YamlSchemaElementType.INT)
    max_rbmt_per_cell = YamlSchemaElement(
        "maxRbmtPerCell", doc=_THRESHOLD_DOC, tyype=YamlSchemaElementType.FLOAT)
    min_intronic_per_cell = YamlSchemaElement(
        "minIntronicPerCell", doc=_THRESHOLD_DOC, tyype=YamlSchemaElementType.FLOAT)
    max_intronic_per_cell = YamlSchemaElement(
        "maxIntronicPerCell", doc=_THRESHOLD_DOC, tyype=YamlSchemaElementType.FLOAT)
    efficiency_threshold_log10 = YamlSchemaElement(
        "efficiencyThresholdLog10",
        doc="Threshold for filtering cells that are too efficient, i.e. have too many UMIs/read. "
            "Does not disable automatic calling methods.",
        tyype=YamlSchemaElementType.FLOAT)
    call_stamps_method = YamlSchemaElement(
        "callSTAMPsMethod",
        doc="CallSTAMPs method to use, if automatic selection picks a bad one.",
        tyype=YamlSchemaElementType.ENUM, enum_values=enum_names(CallSTAMPsMethod))
    cell_probability_threshold = YamlSchemaElement(
        "cellProbabilityThreshold",
        doc="The probability threshold for selecting cells.  This value scales from 0-1, with 1 being "
            "extremely confident/stringent.  Set to null to use the SVM defaults (>0.5 = nuclei). This "
            "modifies plotting outputs and the output features file classification, but does not filter "
            "any cells from the output.",
        tyype=YamlSchemaElementType.FLOAT)
    use_cbrb_initialization = YamlSchemaElement(
        "useCBRBInitialization", doc="Set to false to disable CBRB initialization.  Default: true.",
        tyype=YamlSchemaElementType.BOOLEAN)

    @classmethod
    def downstream(cls):
        return YamlSchemaElement(
            "downstream",
            doc="Settings passed to downstream workflows. To suppress invocation of a downstream workflow, "
                "set it to null, e.g. 'stdAnalysis: null' will suppress automatic invocation of standard "
                "analysis.",
            tyype=YamlSchemaElementType.DICT,
            children=[
                DownstreamManifestKey.std_analysis(),
                DownstreamManifestKey.cell_classification(),
                DownstreamManifestKey.mmc_from_specified_markers(),
            ])

    @classmethod
    def _root_elements_no_downstream(cls):
        return [cls.min_umis_per_cell, cls.max_umis_per_cell, cls.max_rbmt_per_cell, cls.min_intronic_per_cell,
                cls.max_intronic_per_cell, cls.efficiency_threshold_log10, cls.call_stamps_method,
                cls.cell_probability_threshold, cls.use_cbrb_initialization]

    @classmethod
    def _downstream_element_opt(cls):
        return cls.downstream()

    @classmethod
    def get_documentation_recursive_roots(cls):
        return cls.root_elements()


class ScRnaStdAnalysisManifestKey(AbstractManifestKey):
    vcf = YamlSchemaElement("vcf", doc="Required for dropulation", tyype=YamlSchemaElementType.PATH)
    donor_file = YamlSchemaElement(
        "donorFile", doc="Required for dropulation", tyype=YamlSchemaElementType.PATH)
    donor = YamlSchemaElement(
        "donor", doc="Name of the donor for a non-dropulation library", tyype=YamlSchemaElementType.STRING)
    census_file = YamlSchemaElement(
        "censusFile", doc="Optional for dropulation", tyype=YamlSchemaElementType.PATH)
    assign_cells_to_samples_options = YamlSchemaElement(
        "assignCellsToSamplesOptions", doc="Custom arguments passed through to AssignCellsToSamples",
        tyype=YamlSchemaElementType.STRING, list_allowed=True)
    detect_doublets_options = YamlSchemaElement(
        "detectDoubletsOptions", doc="Custom arguments passed through to DetectDoublets",
        tyype=YamlSchemaElementType.STRING, list_allowed=True)
    compute_cbrb_adjusted_likelihoods = YamlSchemaElement(
        "computeCBRBAdjustedLikelihoods",
        doc="Set to false to disable use of background-removed per cell ambient DNA contamination "
            "estimates together with the estimates of the allele frequency  of ascertained SNPs to improve "
            "single donor and doublet likelihood calculations.",
        tyype=YamlSchemaElementType.BOOLEAN)
    is_cloud_analysis = YamlSchemaElement(
        "isCloudAnalysis",
        doc="Set to false to disable running dropulation in cloud even if the VCF is cloud-enabled. "
            "Default: cloud dropulation if VCF is cloud-enabled.",
        tyype=YamlSchemaElementType.BOOLEAN)
    meta_gene_dge_functional_strategy = YamlSchemaElement(
        "metaGeneDgeFunctionalStrategy",
        doc="Passed to metagene DigitalExpression FUNCTIONAL_STRATEGY.  Default: whatever the setting was "
            "in locus function workflow.",
        tyype=YamlSchemaElementType.ENUM, enum_values=enum_names(FunctionalDataProcessorStrategy))

    @classmethod
    def downstream(cls):
        return YamlSchemaElement(
            "downstream",
            doc="Settings passed to downstream workflows. Omitting this element will disable auto-launch "
                "of cell classification workflow.",
            tyype=YamlSchemaElementType.DICT,
            children=[
                DownstreamManifestKey.cell_classification(),
                DownstreamManifestKey.mmc_from_specified_markers(),
            ])

    @classmethod
    def _root_elements_no_downstream(cls):
        return [cls.vcf, cls.donor_file, cls.donor, cls.census_file, cls.assign_cells_to_samples_options,
                cls.detect_doublets_options, cls.compute_cbrb_adjusted_likelihoods, cls.is_cloud_analysis,
                cls.meta_gene_dge_functional_strategy]

    @classmethod
    def _downstream_element_opt(cls):
        return cls.downstream()

    @classmethod
    def get_documentation_recursive_roots(cls):
        return cls.root_elements()


class XipherFilterBamManifestKey(AbstractManifestKey):
    donors = YamlSchemaElement(
        "donors",
        doc="List of donors for which to created filtered BAMs.  If not specified, all female donors will "
            "be processed for dropulation, and the single donor for non-dropulation.  Maybe be used to "
            "specify donor name for a non-dropulation library in which donor has not been specified.",
        tyype=YamlSchemaElementType.STRING, list_allowed=True)

    @classmethod
    def _root_elements_no_downstream(cls):
        return [cls.donors]

    @classmethod
    def get_documentation_recursive_roots(cls):
        return cls.root_elements()


class ScRnaAggregationManifestKey(AbstractManifestKey):
    include_file = YamlSchemaElement(
        "includeFile", doc="Path to a file containing a list of values with which to inclusively filter.",
        tyype=YamlSchemaElementType.PATH)
    exclude_file = YamlSchemaElement(
        "excludeFile", doc="Path to a file containing a list of values with which to exclusively filter.",
        tyype=YamlSchemaElementType.PATH)
    include = YamlSchemaElement(
        "include", doc="One or more values with which to inclusively filter.",
        tyype=YamlSchemaElementType.STRING, list_allowed=True)
    exclude = YamlSchemaElement(
        "exclude", doc="One or more values with which to exclusively filter.",
        tyype=YamlSchemaElementType.STRING, list_allowed=True)
    min = YamlSchemaElement("min", doc="Minimum value to include.", tyype=YamlSchemaElementType.FLOAT)
    max = YamlSchemaElement("max", doc="Maximum value to include.", tyype=YamlSchemaElementType.FLOAT)

    filter = YamlSchemaElement(
        "*", doc="Filter to apply to the DGE.  The key should be the name of the column on which to filter",
        tyype=YamlSchemaElementType.DICT,
        children=[include_file, exclude_file, include, exclude, min, max])

    dge = YamlSchemaElement(
        "dge", doc="Path to a DGE (donor or not) to be aggregated.", tyype=YamlSchemaElementType.PATH,
        required=True)
    library_id = YamlSchemaElement(
        "libraryId", doc="Library ID to be used for this DGE.  Default: obtain via the DGE",
        tyype=YamlSchemaElementType.STRING, required=False)
    donor = YamlSchemaElement(
        "donor",
        doc="Donor ID to be used for this DGE.  Should only be used for non-village DGE.  Default: obtain "
            "via standard analysis properties",
        tyype=YamlSchemaElementType.STRING, required=False)
    filters = YamlSchemaElement(
        "filters", doc="List of filters to apply to the DGE.", tyype=YamlSchemaElementType.DICT,
        list_allowed=True, children=[filter])

    join_file = YamlSchemaElement(
        "joinFile", doc="Path to a file containing a list of values with which to join.",
        tyype=YamlSchemaElementType.PATH, required=True)
    left_column = YamlSchemaElement(
        "leftColumn", doc="Column in the cell metadata file (or a prior joined file) on which to join.",
        tyype=YamlSchemaElementType.STRING, required=True)
    join_column = YamlSchemaElement(
        "joinColumn", doc="Column in the join file on which to join.", tyype=YamlSchemaElementType.STRING,
        required=True)
    joins = YamlSchemaElement(
        "joins", doc="List of 'join' dictionaries.", tyype=YamlSchemaElementType.DICT, list_allowed=True,
        children=[join_file, left_column, join_column])

    dges = YamlSchemaElement(
        "dges", doc="List of 'dge' dictionaries.", tyype=YamlSchemaElementType.DICT, list_allowed=True,
        children=[dge, library_id, donor, filters, joins], required=True)
    dge_defaults = YamlSchemaElement(
        "dgeDefaults",
        doc="Dictionary of values to be projected onto each dge that does not set the value explicitly. "
            "See 'libraries' documentation for elements that can be used.",
        tyype=YamlSchemaElementType.DICT, children=[filters, joins])

    @classmethod
    def _root_elements_no_downstream(cls):
        return [cls.dges, cls.dge_defaults]

    @classmethod
    def get_documentation_recursive_roots(cls):
        return [cls.dges]

    @classmethod
    def get_documentation_non_recursive_roots(cls):
        return [cls.dge_defaults]


class DownstreamManifestKey:
    """Manifest definitions for elements passed through to downstream workflows.

    Each member is a classmethod (rather than a plain attribute) because it depends on the
    'no downstream' root elements of the corresponding *ManifestKey class, which in turn (for
    several classes) depends back on this class's own members for their own 'downstream' field.
    See AbstractManifestKey's docstring for why this needs to be lazy in Python.
    """

    @classmethod
    def alignment(cls):
        return YamlSchemaElement(
            "alignment", doc="Settings passed to downstream locus function workflow.",
            tyype=YamlSchemaElementType.DICT,
            children=ScRnaAlignmentManifestKey.root_elements_no_downstream() + [ScRnaDownstreamPropertyKey.launch])

    @classmethod
    def locus_function(cls):
        return YamlSchemaElement(
            "locusFunction", doc="Settings passed to downstream locus function workflow.",
            tyype=YamlSchemaElementType.DICT,
            children=ScRnaLocusFunctionManifestKey.root_elements_no_downstream() + [ScRnaDownstreamPropertyKey.launch])

    @classmethod
    def cbrb(cls):
        return YamlSchemaElement(
            "cbrb", doc="Settings passed to downstream cbrb workflow.",
            tyype=YamlSchemaElementType.DICT,
            children=ScRnaCbrbManifestKey.root_elements_no_downstream() + [ScRnaDownstreamPropertyKey.launch])

    @classmethod
    def cell_selection(cls):
        return YamlSchemaElement(
            "cellSelection", doc="Settings passed to downstream cell selection workflow.",
            tyype=YamlSchemaElementType.DICT,
            children=ScRnaCellSelectionManifestKey.root_elements_no_downstream() + [ScRnaDownstreamPropertyKey.launch])

    @classmethod
    def std_analysis(cls):
        return YamlSchemaElement(
            "stdAnalysis", doc="Settings passed to downstream standard analysis workflow.",
            tyype=YamlSchemaElementType.DICT,
            children=ScRnaStdAnalysisManifestKey.root_elements_no_downstream() + [ScRnaDownstreamPropertyKey.launch])

    @classmethod
    def cell_classification(cls):
        return YamlSchemaElement(
            "cellClassification", doc="Settings passed to downstream cellClassification workflow.",
            tyype=YamlSchemaElementType.DICT,
            children=CellClassificationManifestKey.root_elements_no_downstream() + [ScRnaDownstreamPropertyKey.launch])

    @classmethod
    def mmc_from_specified_markers(cls):
        return YamlSchemaElement(
            "mmcFromSpecifiedMarkers", doc="Settings passed to downstream MmcFromSpecifiedMarkers workflow.",
            tyype=YamlSchemaElementType.DICT,
            children=MmcFromSpecifiedMarkersManifestKey.root_elements_no_downstream() + [ScRnaDownstreamPropertyKey.launch])


class ScRnaUnmappedManifestKey:
    """Definitions shared by the various launchers of workflows for creating unmapped BAMs.

    Note: Scala's parseLibrary(), which builds a workflow Library object from these fields, is not
    translated here -- it depends on ScRnaAbstractBamWorkflow.Library, TenXVersionMetadata,
    BeadStructure and other classes that live outside the two yaml packages being translated.
    """
    library = YamlSchemaElement(
        "library", doc="Library name.", tyype=YamlSchemaElementType.STRING, required=True)
    library_directory = YamlSchemaElement(
        "libraryDirectory",
        doc="Use this to override the default library directory. Default: "
            "<outputRoot>/libraries/<experimentDate>_<libraryName>",
        tyype=YamlSchemaElementType.PATH,
        validator=YamlPathValidator(require_exists=False))
    experiment_date = YamlSchemaElement(
        "experimentDate", doc="Library directory is prepended with this date.  Default: flowcell run date.",
        tyype=YamlSchemaElementType.DATE)
    version10_x = YamlSchemaElement(
        "version10X", required=True, doc="Version of 10X chemistry.", tyype=YamlSchemaElementType.STRING)
    sample_type = YamlSchemaElement(
        "sampleType", required=True, tyype=YamlSchemaElementType.ENUM, enum_values=enum_names(SampleType))
    estimated_num_cells = YamlSchemaElement(
        "estimatedNumCells", required=True, doc="Estimated number of cells in the reaction.",
        tyype=YamlSchemaElementType.INT)
    strand_strategy = YamlSchemaElement(
        "strandStrategy",
        doc="Default: see readiterators.StrandStrategy / GeneFunctionCommandLineBase.DEFAULT_STRAND_STRATEGY",
        tyype=YamlSchemaElementType.ENUM, enum_values=enum_names(StrandStrategy))
    correct_cbcs = YamlSchemaElement(
        "correctCbcs",
        doc="Set to false to disable CBC correction, which otherwise is enabled if version10X has an "
            "allow list.",
        tyype=YamlSchemaElementType.BOOLEAN)

    @classmethod
    def downstream(cls):
        return YamlSchemaElement(
            "downstream",
            doc="Settings passed to downstream workflows. To suppress invocation of a downstream workflow, "
                "set it to null, e.g. 'stdAnalysis: null' will suppress automatic invocation of standard "
                "analysis.",
            tyype=YamlSchemaElementType.DICT,
            children=[
                DownstreamManifestKey.alignment(),
                DownstreamManifestKey.locus_function(),
                DownstreamManifestKey.cbrb(),
                DownstreamManifestKey.cell_selection(),
                DownstreamManifestKey.std_analysis(),
                DownstreamManifestKey.cell_classification(),
                DownstreamManifestKey.mmc_from_specified_markers(),
            ])


class ScRnaUnmappedBamManifestKey(AbstractManifestKey):
    experiment_date = YamlSchemaElement(
        "experimentDate", required=True, doc="Library directory is prepended with this date.",
        tyype=YamlSchemaElementType.DATE)

    @classmethod
    def _root_elements_no_downstream(cls):
        return [
            ScRnaUnmappedManifestKey.library, ScRnaUnmappedManifestKey.library_directory, cls.experiment_date,
            ScRnaUnmappedManifestKey.version10_x, ScRnaUnmappedManifestKey.sample_type,
            ScRnaUnmappedManifestKey.estimated_num_cells, ScRnaUnmappedManifestKey.strand_strategy,
            ScRnaUnmappedManifestKey.correct_cbcs,
        ]

    @classmethod
    def _downstream_element_opt(cls):
        return ScRnaUnmappedManifestKey.downstream()

    @classmethod
    def get_documentation_recursive_roots(cls):
        return cls.root_elements()


class ScRnaBasecallingManifestKey(AbstractManifestKey):
    """Note: Scala's parseLibraries(), which builds workflow Library/LaneSampleIndex objects from these
    fields, is not translated here -- see ScRnaUnmappedManifestKey's docstring for why."""
    lane = YamlSchemaElement(
        "lane",
        doc="Lane number, or 'all'.  If not present, a sample index is to be found in all lanes of the "
            "flowcell.",
        tyype=YamlSchemaElementType.STRING, list_allowed=True)
    sample_index = YamlSchemaElement(
        "sampleIndex",
        doc="A sample index, which may be a simple string, a comma-separated string (or a list) for "
            "multi-indices, or a symbolic index.  If a symbolic index, make sure the correct "
            "symbolic-to-sequence map is specified.",
        tyype=YamlSchemaElementType.STRING, list_allowed=True)
    sample_indices = YamlSchemaElement(
        "sampleIndices",
        doc="Container for sample indices. Use this if there is more than one sample index for the same "
            "library.",
        tyype=YamlSchemaElementType.DICT, children=[lane, sample_index], list_allowed=True)

    @classmethod
    def library_children(cls):
        return [
            ScRnaUnmappedManifestKey.library, ScRnaUnmappedManifestKey.library_directory,
            ScRnaUnmappedManifestKey.experiment_date, ScRnaUnmappedManifestKey.version10_x,
            ScRnaUnmappedManifestKey.sample_type, ScRnaUnmappedManifestKey.estimated_num_cells,
            ScRnaUnmappedManifestKey.strand_strategy, ScRnaUnmappedManifestKey.correct_cbcs,
            cls.lane, cls.sample_index, cls.sample_indices,
            ScRnaUnmappedManifestKey.downstream(),
        ]

    @classmethod
    def libraries(cls):
        return YamlSchemaElement(
            "libraries", doc="List of 'library' dictionaries.", tyype=YamlSchemaElementType.DICT,
            list_allowed=True, children=cls.library_children(), required=True)

    @classmethod
    def library_defaults(cls):
        return YamlSchemaElement(
            "libraryDefaults",
            doc="Dictionary of values to be projected onto each library that does not set the value "
                "explicitly. See 'libraries' documentation for elements that can be used.",
            tyype=YamlSchemaElementType.DICT, children=cls.library_children())

    @classmethod
    def _root_elements_no_downstream(cls):
        return [cls.libraries(), cls.library_defaults()]

    @classmethod
    def get_documentation_recursive_roots(cls):
        return [cls.libraries()]

    @classmethod
    def get_documentation_non_recursive_roots(cls):
        return [cls.library_defaults()]


class ScRnaFastqManifestKey(AbstractManifestKey):
    rgsm = YamlSchemaElement(
        "rgsm",
        doc="For Dragen output in which the RGSM field is not in the form <date>_<library>. Use this to "
            "specify the RGSM string for the library.  There may be more than one.",
        tyype=YamlSchemaElementType.STRING, list_allowed=True)

    @classmethod
    def library_children(cls):
        return [
            ScRnaUnmappedManifestKey.library, ScRnaUnmappedManifestKey.library_directory,
            ScRnaUnmappedManifestKey.experiment_date, ScRnaUnmappedManifestKey.version10_x,
            ScRnaUnmappedManifestKey.sample_type, ScRnaUnmappedManifestKey.estimated_num_cells,
            ScRnaUnmappedManifestKey.strand_strategy, ScRnaUnmappedManifestKey.correct_cbcs,
            ScRnaUnmappedManifestKey.downstream(), cls.rgsm,
        ]

    @classmethod
    def libraries(cls):
        return YamlSchemaElement(
            "libraries", doc="List of 'library' dictionaries.", tyype=YamlSchemaElementType.DICT,
            list_allowed=True, children=cls.library_children(), required=True)

    @classmethod
    def library_defaults(cls):
        return YamlSchemaElement(
            "libraryDefaults",
            doc="Dictionary of values to be projected onto each library that does not set the value "
                "explicitly. See 'libraries' documentation for elements that can be used.",
            tyype=YamlSchemaElementType.DICT, children=cls.library_children())

    @classmethod
    def _root_elements_no_downstream(cls):
        return [cls.libraries(), cls.library_defaults()]

    @classmethod
    def get_documentation_recursive_roots(cls):
        return [cls.libraries()]

    @classmethod
    def get_documentation_non_recursive_roots(cls):
        return [cls.library_defaults()]


class MultiomeMkfastqManifestKey:
    library = YamlSchemaElement(
        "library", doc="Library name.", tyype=YamlSchemaElementType.STRING, required=True)
    reaction = YamlSchemaElement(
        "reaction", doc="Typically rxn<number>.", tyype=YamlSchemaElementType.STRING, required=True)
    experiment_date = YamlSchemaElement(
        "experiment_date", doc="Library directory is prepended with this date.",
        tyype=YamlSchemaElementType.DATE)
    atac = YamlSchemaElement(
        "atac", doc="List of {lane, sample_index} for the ATAC-seq run folder.",
        tyype=YamlSchemaElementType.DICT, required=True, list_allowed=True, opaque_dict=True)
    rna = YamlSchemaElement(
        "rna", doc="List of {lane, sample_index} for the RNA-seq run folder.",
        tyype=YamlSchemaElementType.DICT, required=True, list_allowed=True, opaque_dict=True)
    discard = YamlSchemaElement(
        "discard", doc="If set to true in a library dictionary, this library is demultiplexed but not saved.",
        tyype=YamlSchemaElementType.BOOLEAN)
    lane = YamlSchemaElement(
        "lane",
        doc="Lane number, or 'all'.  If not present, a sample index is to be found in all lanes of the "
            "flowcell.",
        tyype=YamlSchemaElementType.STRING, list_allowed=True)
    sample_index = YamlSchemaElement(
        "sample_index", doc="A 10X symbolic sample index name, e.g. SI-TT-D3.",
        tyype=YamlSchemaElementType.STRING, required=True, list_allowed=True)
    # count/cbrb/std_analysis are opaque_dict=True (the Scala source omits this, which would make the
    # DICT-with-no-children construction fail there too -- see LaunchMultiomeMkfastq.scala, which never
    # actually triggers that path in practice).
    count = YamlSchemaElement(
        "count", doc="Dictionary passed through to cellrange-arc count workflow.",
        tyype=YamlSchemaElementType.DICT, list_allowed=True, opaque_dict=True)
    cbrb = YamlSchemaElement(
        "cbrb", doc="Dictionary passed through to CBRB workflow.",
        tyype=YamlSchemaElementType.DICT, list_allowed=True, opaque_dict=True)
    std_analysis = YamlSchemaElement(
        "std_analysis", doc="Dictionary passed through to standard analysis workflow.",
        tyype=YamlSchemaElementType.DICT, list_allowed=True, opaque_dict=True)

    _library_children = [library, reaction, experiment_date, atac, rna, discard, lane, sample_index, count,
                         cbrb, std_analysis]

    libraries = YamlSchemaElement(
        "libraries", doc="List of 'library' dictionaries.", tyype=YamlSchemaElementType.DICT,
        children=_library_children, list_allowed=True)
    library_defaults = YamlSchemaElement(
        "library_defaults", doc="Dictionary of values to be projected onto each library.",
        tyype=YamlSchemaElementType.DICT, children=_library_children)
