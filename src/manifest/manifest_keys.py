from typing import List

from manifest.enums import (
    FunctionalDataProcessorStrategy,
    LocusFunction,
    StrandStrategy,
    enum_names,
)
from manifest.util.schema_element import YamlSchemaElement
from manifest.util.validators import YamlPermissiveValidator
from manifest.enums import YamlSchemaElementType
from manifest.util.abstract_manifest_key import AbstractManifestKey






_THRESHOLD_DOC = ("Optional cell selection threshold.  If any threshold is specified, automatic methods "
                  "will not be used.")

experimentDate = YamlSchemaElement("experimentDate", doc="Library directory is prepended with this date.",
                            tyype=YamlSchemaElementType.DATE, required=True)
library = YamlSchemaElement("library", doc="Library name.", tyype=YamlSchemaElementType.STRING, required=True)
_lstSharedManifestKeys = [
    library,
    experimentDate,
YamlSchemaElement(
    "version10X", required=True, doc="Version of 10X chemistry.", tyype=YamlSchemaElementType.STRING),
YamlSchemaElement(
    "targetBamSizeMBytes", doc="Target BAM size in MB.  Default: 2048.", tyype=YamlSchemaElementType.INT),
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
    "dgeFunctionalStrategy",
    doc="Passed to DigitalExpression FUNCTIONAL_STRATEGY.  Default: DROPSEQ",
    tyype=YamlSchemaElementType.ENUM,
    enum_values=enum_names(FunctionalDataProcessorStrategy)),
YamlSchemaElement(
    "cbrbArgs", doc="Additional arguments to pass to CBRB.",
    tyype=YamlSchemaElementType.DICT, list_allowed=True, validator=YamlPermissiveValidator(),
    opaque_dict=True),
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
YamlSchemaElement("minUmisPerCell", doc=_THRESHOLD_DOC, tyype=YamlSchemaElementType.INT),
YamlSchemaElement("maxUmisPerCell", doc=_THRESHOLD_DOC, tyype=YamlSchemaElementType.INT),
YamlSchemaElement(
    "minIntronicPerCell", doc=_THRESHOLD_DOC, tyype=YamlSchemaElementType.FLOAT),
YamlSchemaElement(
    "maxIntronicPerCell", doc=_THRESHOLD_DOC, tyype=YamlSchemaElementType.FLOAT),
YamlSchemaElement(
    "metaGeneDgeFunctionalStrategy",
    doc="Passed to metagene DigitalExpression FUNCTIONAL_STRATEGY.  Default: whatever the setting was "
        "in locus function workflow.",
    tyype=YamlSchemaElementType.ENUM, enum_values=enum_names(FunctionalDataProcessorStrategy)),
YamlSchemaElement("vcf", doc="Required for dropulation", tyype=YamlSchemaElementType.PATH),
YamlSchemaElement(
    "donorFile", doc="Required for dropulation", tyype=YamlSchemaElementType.PATH),
YamlSchemaElement(
    "donor", doc="Name of the donor for a non-dropulation library", tyype=YamlSchemaElementType.STRING),
YamlSchemaElement(
    "mapMyCellsQueryMarkers",
    doc="Path to the query_markers.json to be used by MapMyCells.  It is assumed that there is a "
        "corresponding recomputed_stats.h5",
    tyype=YamlSchemaElementType.PATH),
YamlSchemaElement(
    "mmcArgs",
    doc="Additional arguments to pass to MapMyCells.",
    tyype=YamlSchemaElementType.STRING,
    list_allowed=True)
]

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
class snRnaDragenManifestKey(AbstractManifestKey):
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
    setattr(snRnaDragenManifestKey, manifestKey.name, manifestKey)

