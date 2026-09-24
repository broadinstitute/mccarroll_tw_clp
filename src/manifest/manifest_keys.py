from typing import List

from manifest.enums import (
    FunctionalDataProcessorStrategy,
    LocusFunction,
    StrandStrategy,
    enum_names,
    StartAt
)
from manifest.util.schema_element import YamlSchemaElement
from manifest.util.validators import YamlPermissiveValidator
from manifest.enums import YamlSchemaElementType
from manifest.util.abstract_manifest_key import AbstractManifestKey






_THRESHOLD_DOC = ("Optional cell selection threshold.  If any threshold is specified, automatic methods "
                  "will not be used.")

lstAlignmentSchemaElements = [
    YamlSchemaElement(
        "reference", required=True, doc="Reference fasta(.gz).", tyype=YamlSchemaElementType.PATH),
    YamlSchemaElement(
        "locusFunction",
        doc=f"Default: {LocusFunction.EXONIC_INTRONIC.label}",
        tyype=YamlSchemaElementType.ENUM,
        enum_values={lf.label for lf in LocusFunction}),
    YamlSchemaElement(
        "strandStrategy",
        doc="Default: see readiterators.StrandStrategy / GeneFunctionCommandLineBase.DEFAULT_STRAND_STRATEGY",
        tyype=YamlSchemaElementType.ENUM, enum_values=enum_names(StrandStrategy)),
    YamlSchemaElement(
        "dgeMinReadMq",
        doc="Minimum mapping quality for reads to be included in DGE counting.  Default: 10",
        tyype=YamlSchemaElementType.INT),
    YamlSchemaElement(
        "dgeFunctionalStrategy",
        doc="Passed to DigitalExpression FUNCTIONAL_STRATEGY.  Default: DROPSEQ",
        tyype=YamlSchemaElementType.ENUM,
        enum_values=enum_names(FunctionalDataProcessorStrategy)),
]

lstCbrbSchemaElements = [
YamlSchemaElement(
    "cbrbArgs", doc="Additional arguments to pass to CBRB.  Arguments with values must use an equals sign, e.g. --expected-cells=1000.",
    tyype=YamlSchemaElementType.STRING,
    required=False),
YamlSchemaElement(
    "useSvmParameterEstimation",
    doc="SVM parameter estimation is enabled unless both --expected-cells and --total-droplets-included "
        "appear in cbrbArgs. Set this to false to disable SVM parameter estimation and let CBRB estimate "
        "the parameters itself.",
    tyype=YamlSchemaElementType.BOOLEAN, required=False),
YamlSchemaElement(
    "forceTwoClusterSolution",
    doc="If true, attempt to find a solution with two clusters. May be useful when data is overloaded.",
    tyype=YamlSchemaElementType.BOOLEAN, required=False),
]

lstCellSelectionSchemaElements = [
    YamlSchemaElement("minUmisPerCell", doc=_THRESHOLD_DOC, tyype=YamlSchemaElementType.INT),
    YamlSchemaElement("maxUmisPerCell", doc=_THRESHOLD_DOC, tyype=YamlSchemaElementType.INT),
    YamlSchemaElement(
        "minIntronicPerCell", doc=_THRESHOLD_DOC, tyype=YamlSchemaElementType.FLOAT),
    YamlSchemaElement(
        "maxIntronicPerCell", doc=_THRESHOLD_DOC, tyype=YamlSchemaElementType.FLOAT),
]

lstStandardAnalysisSchemaElements = [
YamlSchemaElement(
    "donor", doc="Name of the donor for a non-dropulation library", tyype=YamlSchemaElementType.STRING),
YamlSchemaElement(
    "metaGeneDgeFunctionalStrategy",
    doc="Passed to metagene DigitalExpression FUNCTIONAL_STRATEGY.  Default: whatever the setting was "
        "in locus function workflow.",
    tyype=YamlSchemaElementType.ENUM, enum_values=enum_names(FunctionalDataProcessorStrategy)),
]

lstDropulationSchemaElements = [
YamlSchemaElement("vcf", doc="Required for dropulation", tyype=YamlSchemaElementType.PATH),
YamlSchemaElement(
    "donorFile", doc="Required for dropulation", tyype=YamlSchemaElementType.PATH),
]

lstMmcSchemaElements = [
    YamlSchemaElement(
        "mmcQueryMarkers",
        doc="Path to the query_markers.json to be used by MMC.  It is assumed that there is a " \
            "corresponding recomputed_stats.h5",
        tyype=YamlSchemaElementType.PATH),
    YamlSchemaElement(
        "mmcArgs",
        doc="Additional arguments to pass to MMC.",
        tyype=YamlSchemaElementType.STRING,
        list_allowed=True)
]

dctStageSchemaElements = {
    StartAt.alignment.value: lstAlignmentSchemaElements,
    StartAt.cbrb.value: lstCbrbSchemaElements,
    StartAt.cell_selection.value: lstCellSelectionSchemaElements,
    StartAt.standard_analysis.value: lstStandardAnalysisSchemaElements,
    StartAt.dropulation.value: lstDropulationSchemaElements,
    StartAt.mmc.value: lstMmcSchemaElements,
}


experimentDate = YamlSchemaElement("experimentDate",
                                   doc="Library directory is prepended with this date. "
                                       "This must be in 'YYYY-MM-DD' format, and must be quoted to suppress yaml parser date handling.",
                            tyype=YamlSchemaElementType.DATE, required=True)
library = YamlSchemaElement("library", doc="Library name.", tyype=YamlSchemaElementType.STRING, required=True)

_lstSharedManifestKeys = ([
    library,
    experimentDate,
YamlSchemaElement(
    "version10X", required=True,
    doc="Version of 10X chemistry. This must be quoted so yaml parser does not interpret it as a number.",
    tyype=YamlSchemaElementType.STRING),
YamlSchemaElement(
    "targetBamSizeMBytes", doc="Target BAM size in MB.  Default: 2048.", tyype=YamlSchemaElementType.INT),] +
                          lstAlignmentSchemaElements + lstCbrbSchemaElements + lstCellSelectionSchemaElements +
                          lstStandardAnalysisSchemaElements + lstDropulationSchemaElements + lstMmcSchemaElements)

_lstSnRnaManifestKeys = [
YamlSchemaElement(
    "fastq_read1", doc="Path to the FASTQ file(s) for read 1.", tyype=YamlSchemaElementType.PATH, required=True,
    list_allowed=True),
YamlSchemaElement(
    "fastq_read2", doc="Path to the FASTQ file(s) for read 2.", tyype=YamlSchemaElementType.PATH, required=True,
    list_allowed=True)
] + _lstSharedManifestKeys

class SnRnaManifestKey(AbstractManifestKey):
    @classmethod
    def _root_elements_no_downstream(cls):
        return _lstSnRnaManifestKeys

    @classmethod
    def get_documentation_recursive_roots(cls):
        return cls.root_elements()

for manifestKey in _lstSnRnaManifestKeys:
    setattr(SnRnaManifestKey, manifestKey.name, manifestKey)

rgsm = YamlSchemaElement("rgsm",
                            doc="For Dragen output in which the RGSM field is not in the form <date>_<library>. " \
                                "Use this to specify the RGSM string for the library. There may be more than one.",
                            tyype=YamlSchemaElementType.STRING, list_allowed=True)
_lstSnRnaDragenLibraryManifestKeys = _lstSharedManifestKeys + [
    rgsm
]
libraries = YamlSchemaElement("libraries", doc="List of 'library' dictionaries.", tyype=YamlSchemaElementType.DICT,
                            list_allowed=True, children=_lstSnRnaDragenLibraryManifestKeys, required=True)
libraryDefaults = YamlSchemaElement("libraryDefaults",
                            doc="Dictionary of values to be projected onto each library that does not set the value explicitly. " + "See 'libraries' documentation for elements that can be used.",
                            tyype=YamlSchemaElementType.DICT, children=_lstSnRnaDragenLibraryManifestKeys)
_lstSnRnaDragenManifestKeys = [
    libraries,
    libraryDefaults
]
class SnRnaDragenManifestKey(AbstractManifestKey):
    @classmethod
    def _root_elements_no_downstream(cls):
        return _lstSnRnaDragenManifestKeys

    @classmethod
    def get_documentation_recursive_roots(cls):
        return [libraries]

    @classmethod
    def get_documentation_non_recursive_roots(cls) -> List[YamlSchemaElement]:
        return [libraryDefaults]


for manifestKey in _lstSnRnaDragenManifestKeys:
    setattr(SnRnaDragenManifestKey, manifestKey.name, manifestKey)


def makeStartAtManifestKey(startAt: str, schemaElements: List[YamlSchemaElement]) -> AbstractManifestKey:
    className = startAt + "ManifestKey"
    classDict = {
        "_root_elements_no_downstream": classmethod(lambda cls: schemaElements),
        "get_documentation_recursive_roots": classmethod(lambda cls: schemaElements),
    }
    ret = type(className, (AbstractManifestKey,), classDict)
    for schemaElement in schemaElements:
        setattr(ret, schemaElement.name, schemaElement)
    return ret

# Iterate over the StartAt enum to create a manifest key class for each value
dctStartAtManifestKeys = {}
_lstStartAtSchemaElements = lstMmcSchemaElements
dctStartAtManifestKeys[StartAt.mmc.value] = makeStartAtManifestKey(StartAt.mmc.value, _lstStartAtSchemaElements)
_lstStartAtSchemaElements = lstDropulationSchemaElements + _lstStartAtSchemaElements
dctStartAtManifestKeys[StartAt.dropulation.value] = makeStartAtManifestKey(StartAt.dropulation.value, _lstStartAtSchemaElements)
_lstStartAtSchemaElements = lstStandardAnalysisSchemaElements + _lstStartAtSchemaElements
dctStartAtManifestKeys[StartAt.standard_analysis.value] = makeStartAtManifestKey(StartAt.standard_analysis.value, _lstStartAtSchemaElements)
_lstStartAtSchemaElements = lstCellSelectionSchemaElements + _lstStartAtSchemaElements
dctStartAtManifestKeys[StartAt.cell_selection.value] = makeStartAtManifestKey(StartAt.cell_selection.value, _lstStartAtSchemaElements)
_lstStartAtSchemaElements = lstCbrbSchemaElements + _lstStartAtSchemaElements
dctStartAtManifestKeys[StartAt.cbrb.value] = makeStartAtManifestKey(StartAt.cbrb.value, _lstStartAtSchemaElements)
_lstStartAtSchemaElements = lstAlignmentSchemaElements + _lstStartAtSchemaElements
dctStartAtManifestKeys[StartAt.alignment.value] = makeStartAtManifestKey(StartAt.alignment.value, _lstStartAtSchemaElements)
