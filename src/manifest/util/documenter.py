import sys
from typing import List, TextIO

from manifest.util.schema_element import YamlSchemaElement


class YamlManifestDocumenter:
    """Interface for generating documentation for yaml manifests."""

    def document_element(self, element: YamlSchemaElement, nesting_level: int) -> None:
        raise NotImplementedError

    def document_element_recursive(self, element: YamlSchemaElement, nesting_level: int) -> None:
        self.document_element(element, nesting_level)
        for child in element.children:
            self.document_element_recursive(child, nesting_level + 1)


class TextYamlManifestDocumenter(YamlManifestDocumenter):
    """Generate yaml manifest documentation to a stream.

    :param out: where to write the doc
    :param indent_amount: how many spaces to indent a nested element
    :param line_length: for word-wrapping
    :param detail_indent_amount: the amount to indent the doc string and other details relative to the
        element itself.
    """
    DEFAULT_INDENT_AMOUNT = 4
    DEFAULT_LINE_LENGTH = 78
    DEFAULT_DETAIL_INDENT = 5

    def __init__(self,
                 out: TextIO = sys.stderr,
                 indent_amount: int = DEFAULT_INDENT_AMOUNT,
                 line_length: int = DEFAULT_LINE_LENGTH,
                 detail_indent_amount: int = DEFAULT_DETAIL_INDENT):
        self.out = out
        self.indent_amount = indent_amount
        self.line_length = line_length
        self.detail_indent_amount = detail_indent_amount

    def document_element(self, element: YamlSchemaElement, nesting_level: int) -> None:
        indent = self._indent_spaces(nesting_level)
        required = ", required" if element.required else ""
        list_allowed = ", listAllowed" if element.list_allowed else ""
        print(f"{indent}{element.name}: ({element.tyype.name}{required}{list_allowed})", file=self.out)
        detail_indent = indent + " " * self.detail_indent_amount
        wrap_length = self.line_length - len(detail_indent)
        if element.doc:
            for line in self._word_wrap(element.doc, wrap_length):
                print(detail_indent + line, file=self.out)
        if element.enum_values:
            print(detail_indent + "Possible values: " + ", ".join(element.enum_values), file=self.out)

    def _indent_spaces(self, nesting_level: int) -> str:
        return " " * self.indent_amount * nesting_level

    @staticmethod
    def _word_wrap(s: str, length: int) -> List[str]:
        words = s.split()
        lines: List[str] = []
        current = ""
        for word in words:
            if current and len(current) + 1 + len(word) > length:
                lines.append(current)
                current = ""
            current = f"{current} {word}" if current else word
        if current:
            lines.append(current)
        return lines
