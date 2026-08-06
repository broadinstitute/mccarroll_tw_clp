from typing import Any, List, Type

from util.simple_date import SimpleDate
from manifest.util.prop_manifest_util import YamlPropManifestUtil
from manifest.util.schema_element_validator import YamlSchemaElementValidator
from manifest.util.validator import YamlValidator
import util.gcs_util as gcs_util


class YamlPrimitiveValidator(YamlSchemaElementValidator):
    def validate(self, value: Any, schema_element: Any, path_to_here: List[str]) -> List[str]:
        if isinstance(value, dict):
            return [f"Dictionary not allowed for {YamlValidator.key_with_path(schema_element.name, path_to_here)}"]
        if isinstance(value, list) and not schema_element.list_allowed:
            return [f"List not allowed for {YamlValidator.key_with_path(schema_element.name, path_to_here)}"]
        return []


class YamlTypedPrimitiveValidator(YamlPrimitiveValidator):
    """Validate that a value is of the expected type, and if not, produce an error message.

    :param expected_type: the type being validated, e.g. bool or int.
    :param type_label: used in the error message.
    """

    def __init__(self, expected_type: Type, type_label: str):
        self.expected_type = expected_type
        self.type_label = type_label

    def validate(self, value: Any, schema_element: Any, path_to_here: List[str]) -> List[str]:
        errors = super().validate(value, schema_element, path_to_here)
        if errors:
            return errors
        values = YamlPropManifestUtil.force_list(value)
        return [
            f"Expected {self.type_label} for {YamlValidator.key_with_path(schema_element.name, path_to_here)} "
            f"but found {v}"
            for v in values if not self._is_instance(v)
        ]

    def _is_instance(self, v: Any) -> bool:
        # bool is a subclass of int in Python, but Java's Integer and Boolean are distinct types.
        if self.expected_type is int:
            return isinstance(v, int) and not isinstance(v, bool)
        if self.expected_type is bool:
            return isinstance(v, bool)
        return isinstance(v, self.expected_type)


class YamlPathValidator(YamlPrimitiveValidator):
    def __init__(self, require_exists: bool = True):
        self.require_exists = require_exists

    def validate(self, value: Any, schema_element: Any, path_to_here: List[str]) -> List[str]:
        errors = super().validate(value, schema_element, path_to_here)
        if errors:
            return errors
        if not self.require_exists:
            return []
        missing = [p for p in YamlPropManifestUtil.force_list(value) if not gcs_util.gcs_path_is_file(p)]
        return [
            f"Required file or directory {p} not found at "
            f"{YamlValidator.key_with_path(schema_element.name, path_to_here)}"
            for p in missing
        ]


class YamlSimpleDateValidator(YamlPrimitiveValidator):
    """Note that our dates must be quoted strings in yaml file, e.g. '2023-01-26' to avoid yaml parser date
    handling."""

    def validate(self, value: Any, schema_element: Any, path_to_here: List[str]) -> List[str]:
        errors = super().validate(value, schema_element, path_to_here)
        if errors:
            return errors
        path_to_value = YamlValidator.key_with_path(schema_element.name, path_to_here)
        date_strs = [str(v) for v in YamlPropManifestUtil.force_list(value)]
        result = []
        for s in date_strs:
            try:
                SimpleDate(s)
            except ValueError:
                result.append(f"Cannot parse as date '{s}' from {path_to_value}'")
        return result


class YamlDictValidator(YamlSchemaElementValidator):
    def validate(self, value: Any, schema_element: Any, path_to_here: List[str]) -> List[str]:
        nested_path = [schema_element.name] + list(path_to_here)
        if value is None:
            return []
        if isinstance(value, dict):
            return YamlValidator.validate(value, schema_element.children, nested_path)
        if isinstance(value, list):
            if not schema_element.list_allowed:
                return [f"List not allowed at {YamlValidator.key_with_path(schema_element.name, path_to_here)}"]
            if not all(isinstance(m, dict) for m in value):
                return [
                    f"Non-dictionary found in list at "
                    f"{YamlValidator.key_with_path(schema_element.name, path_to_here)}"
                ]
            errors: List[str] = []
            for m in value:
                errors.extend(YamlValidator.validate(m, schema_element.children, nested_path))
            return errors
        return [f"Non-dictionary found at {YamlValidator.key_with_path(schema_element.name, path_to_here)}"]


class YamlFloatValidator(YamlPrimitiveValidator):
    """Floats are special because our yaml parser converts floats that are very close to an integer to integer
    type."""

    def validate(self, value: Any, schema_element: Any, path_to_here: List[str]) -> List[str]:
        errors = super().validate(value, schema_element, path_to_here)
        if errors:
            return errors
        values = YamlPropManifestUtil.force_list(value)
        bad = [v for v in values if isinstance(v, bool) or not isinstance(v, (int, float))]
        return [
            f"Expected float for {YamlValidator.key_with_path(schema_element.name, path_to_here)} but found {v}"
            for v in bad
        ]


class YamlEnumValidator(YamlPrimitiveValidator):
    def validate(self, value: Any, schema_element: Any, path_to_here: List[str]) -> List[str]:
        errors = super().validate(value, schema_element, path_to_here)
        if errors:
            return errors
        invalid = [v for v in YamlPropManifestUtil.force_list(value) if str(v) not in schema_element.enum_values]
        if not invalid:
            return []
        invalid_str = "', '".join(str(v) for v in invalid)
        allowed_str = "', '".join(str(v) for v in schema_element.enum_values)
        return [
            f"Invalid enum value(s) '{invalid_str}' at "
            f"{YamlValidator.key_with_path(schema_element.name, path_to_here)}. "
            f"Allowed values '{allowed_str}'"
        ]


class YamlStringValidator(YamlPrimitiveValidator):
    # str() should be used and not an isinstance(value, str) check, because anything can be a string.
    pass


class YamlPermissiveValidator(YamlSchemaElementValidator):
    def validate(self, value: Any, schema_element: Any, path_to_here: List[str]) -> List[str]:
        return []
