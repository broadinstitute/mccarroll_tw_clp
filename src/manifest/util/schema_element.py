from typing import Iterable, List, Optional

from manifest.enums import YamlSchemaElementType
from manifest.util import validators
from manifest.util.schema_element_validator import YamlSchemaElementValidator


def dedup_by_name(elements: Iterable["YamlSchemaElement"]) -> List["YamlSchemaElement"]:
    """Equivalent of building a Scala LinkedHashSet: keeps first-seen order, drops later
    duplicates by name."""
    seen = {}
    for element in elements:
        seen.setdefault(element.name, element)
    return list(seen.values())


class YamlSchemaElement(YamlSchemaElementValidator):
    """Defines an element in a yaml schema, for parsing, validation and doc generation.

    :param name: yaml key
    :param tyype: either a dictionary or one of the primitive types
    :param doc: documentation string
    :param children: if tyype DICT, the possible children
    :param required: for validation, complain if a required element is not present
    :param list_allowed: for validation, complain if there is a list (of primitives or dict) when not allowed
    :param enum_values: for tyype ENUM, the possible values
    :param validator: if None, the default validator for the given type is used.
    :param opaque_dict: for some DICT elements, children are not described, so don't complain if children is empty
    """

    def __init__(self,
                 name: str,
                 tyype: YamlSchemaElementType,
                 doc: str = "",
                 children: Iterable["YamlSchemaElement"] = (),
                 required: bool = False,
                 list_allowed: bool = False,
                 enum_values: Iterable[str] = (),
                 validator: Optional[YamlSchemaElementValidator] = None,
                 opaque_dict: bool = False):
        self.name = name
        self.doc = doc
        self.tyype = tyype
        self.children: List["YamlSchemaElement"] = dedup_by_name(children)
        self.required = required
        self.list_allowed = list_allowed
        self.enum_values: List[str] = list(dict.fromkeys(enum_values))
        self.opaque_dict = opaque_dict
        # The explicitly-supplied override, if any; kept separately from the resolved
        # _validator so that copy() can recompute the right default when tyype changes.
        self.validator = validator

        if tyype != YamlSchemaElementType.DICT and self.children:
            raise ValueError(f"Non-DICT YamlSchemaElement {name} has children.")
        if tyype == YamlSchemaElementType.DICT:
            if not self.children and not opaque_dict:
                raise ValueError(f"DICT YamlSchemaElement {name} has no children.")
        if tyype == YamlSchemaElementType.ENUM:
            if not self.enum_values:
                raise ValueError(f"ENUM YamlSchemaElement {name} has no enumValues.")
        elif self.enum_values:
            raise ValueError(f"Non-ENUM YamlSchemaElement {name} has enumValues.")

        self._validator = validator if validator is not None else _default_validator(tyype)

    def validate(self, value, schema_element, path_to_here) -> List[str]:
        return self._validator.validate(value, self, path_to_here)

    def copy(self, **overrides) -> "YamlSchemaElement":
        """Equivalent of Scala case-class .copy(...)."""
        kwargs = dict(
            name=self.name, tyype=self.tyype, doc=self.doc, children=self.children,
            required=self.required, list_allowed=self.list_allowed, enum_values=self.enum_values,
            validator=self.validator, opaque_dict=self.opaque_dict,
        )
        kwargs.update(overrides)
        return YamlSchemaElement(**kwargs)

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return self.name

    def __hash__(self) -> int:
        return hash(self.name)

    def __eq__(self, other) -> bool:
        if isinstance(other, YamlSchemaElement):
            if self.name != other.name:
                return False
            if self._functionally_equivalent(other):
                return True
            raise RuntimeError(f"Non-identical YamlSchemaElements with same name {self.name}")
        return False

    def _functionally_equivalent(self, other: "YamlSchemaElement") -> bool:
        """Confirm that objects with same name are equal in functional respects (ignoring doc string)."""
        return (self.name == other.name and self.tyype == other.tyype and
                self.children == other.children and self.required == other.required and
                self.list_allowed == other.list_allowed and
                set(self.enum_values) == set(other.enum_values))


def _default_validator(tyype: YamlSchemaElementType) -> YamlSchemaElementValidator:
    if tyype == YamlSchemaElementType.STRING:
        return validators.YamlPrimitiveValidator()
    if tyype == YamlSchemaElementType.PATH:
        return validators.YamlPathValidator()
    if tyype == YamlSchemaElementType.BOOLEAN:
        return validators.YamlTypedPrimitiveValidator(bool, tyype.name)
    if tyype == YamlSchemaElementType.INT:
        return validators.YamlTypedPrimitiveValidator(int, tyype.name)
    if tyype == YamlSchemaElementType.DATE:
        return validators.YamlSimpleDateValidator()
    if tyype == YamlSchemaElementType.DICT:
        return validators.YamlDictValidator()
    if tyype == YamlSchemaElementType.FLOAT:
        return validators.YamlFloatValidator()
    if tyype == YamlSchemaElementType.ENUM:
        return validators.YamlEnumValidator()
    raise ValueError("unpossible!")
