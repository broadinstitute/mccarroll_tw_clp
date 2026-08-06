from typing import Any, Iterable, List, Mapping, Optional
from google.cloud import storage


class YamlValidator:

    @staticmethod
    def key_with_path(key: str, path_to_here: List[str]) -> str:
        """
        :param key: leaf key
        :param path_to_here: element names that led to this key. Nearest parent is the first item in the list.
        :return: Create a text representation of the path to a yaml key
        """
        if not path_to_here:
            return key
        return "/".join(reversed(path_to_here)) + "/" + key

    @staticmethod
    def validate(map_: Mapping[str, Any], allowed_elements: Iterable[Any],
                path_to_here: Optional[List[str]] = None) -> List[str]:
        """Detect problems with yaml manifest.

        :param map_: loaded yaml, so syntactically valid
        :param allowed_elements: definitions of what is expected in this map
        :param path_to_here: parent elements, for reporting. Nearest parent is the first item in the list.
        :return: list of problems
        """
        if path_to_here is None:
            path_to_here = []
        errors: List[str] = []
        allowed_element_map = {element.name: element for element in allowed_elements}
        allowed_keys = set(allowed_element_map.keys())

        # Are there any unexpected keys?
        if "*" not in allowed_keys:
            # Asterisk means any key is allowed
            errors.extend(
                f"Unexpected yaml key: {YamlValidator.key_with_path(key, path_to_here)}"
                for key in map_.keys() if key not in allowed_keys)

        # Are all required keys present?
        required_keys = [element.name for element in allowed_element_map.values() if element.required]
        errors.extend(
            f"Required yaml key not found: {YamlValidator.key_with_path(key, path_to_here)}"
            for key in required_keys if key not in map_)

        # Invoke the validator for the value
        for key, value in map_.items():
            if key in allowed_keys:
                element = allowed_element_map[key]
                errors.extend(element.validate(value, element, path_to_here))

        return errors
