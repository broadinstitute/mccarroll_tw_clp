from abc import ABC, abstractmethod
from typing import Any, List


class YamlSchemaElementValidator(ABC):
    """Interface for validators hooked into YamlSchemaElements."""

    @abstractmethod
    def validate(self, value: Any, schema_element: Any, path_to_here: List[str]) -> List[str]:
        """
        :param value: The thing to be validated
        :param schema_element: What is expected to be found
        :param path_to_here: ancestor yaml keys that reached this item, nearest parent first, for error messages
        :return: Error messages, or [] if valid
        """
        raise NotImplementedError
