from typing import Any, Dict, List, Optional

from manifest.util.schema_element import YamlSchemaElement, dedup_by_name
from manifest.util.validator import YamlValidator


class AbstractManifestKey:
    """Base for the yaml manifest-key definitions in this module.

    Concrete subclasses are used as singletons (never instantiated), mirroring the Scala
    `object X extends AbstractManifestKey` pattern. root_elements()/root_elements_no_downstream()
    and _root_elements_no_downstream()/_downstream_element_opt() are classmethods rather than
    plain class attributes because several manifest keys and DownstreamManifestKey refer to each
    other's derived element lists (e.g. ScRnaAlignmentManifestKey.downstream() needs
    DownstreamManifestKey.locus_function(), which in turn needs
    ScRnaLocusFunctionManifestKey.root_elements_no_downstream()). Scala breaks that cycle with
    lazily-initialized singleton objects; classmethods evaluated on demand (never at class-body /
    module-import time) do the same job here.
    """

    # downstream root element is kept separate because it should only be included when the
    # concrete manifest schema is root.
    @classmethod
    def _root_elements_no_downstream(cls) -> List[YamlSchemaElement]:
        raise NotImplementedError

    @classmethod
    def _downstream_element_opt(cls) -> Optional[YamlSchemaElement]:
        return None

    @classmethod
    def root_elements(cls) -> List[YamlSchemaElement]:
        """For validation and documentation when the concrete class is the root."""
        downstream = cls._downstream_element_opt()
        extra = [downstream] if downstream is not None else []
        return dedup_by_name(list(cls._root_elements_no_downstream()) + extra)

    @classmethod
    def root_elements_no_downstream(cls) -> List[YamlSchemaElement]:
        """For validation and documentation when the concrete class is in the downstream
        dictionary, so it should not have downstream enclosed within it."""
        return dedup_by_name(cls._root_elements_no_downstream())

    @classmethod
    def get_documentation_recursive_roots(cls) -> List[YamlSchemaElement]:
        """For generating documentation, some root elements should be recursed into, but some
        (e.g. libraryDefaults) should not because they'll be redundant with the recursed doc."""
        raise NotImplementedError

    @classmethod
    def get_documentation_non_recursive_roots(cls) -> List[YamlSchemaElement]:
        return []

    @classmethod
    def validate_manifest(cls, manifest_map: Dict[str, Any]) -> List[str]:
        return YamlValidator.validate(manifest_map, cls.root_elements())
