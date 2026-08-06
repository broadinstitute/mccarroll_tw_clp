"""Python equivalents of the Java/Scala enums referenced by the yaml schema definitions.

These enums live outside org.broadinstitute.dropseq.zamboni.{util.yaml,yaml} in the Scala
codebase (in the `workflows` and `dropseqrna` packages), but the yaml schema definitions
being translated here depend on their member names, so minimal equivalents are provided.
"""
from enum import Enum
from typing import Set, Type


def enum_names(enum_cls: Type[Enum]) -> Set[str]:
    """Equivalent of Scala's EnumClass.values().map(_.name()).toSet"""
    return {member.name for member in enum_cls}


class YamlSchemaElementType(Enum):
    STRING = "Quoting not required unless the value can be mistaken for another type (e.g. floating-point)."
    FLOAT = "A floating-point number, e.g. 6.8523015e+5, 685230.15 or 685_230.15 (underscores ignored)."
    INT = "An integer."
    PATH = "A file or directory."
    DATE = "'YYYY-MM-DD' format.  Must be quoted to suppress yaml parser date handling."
    DICT = "Non-primitive container for key-value pairs or list of key-value pairs."
    BOOLEAN = "Any of {yes,Yes,YES,no,No,NO,true,True,TRUE,false,False,FALSE,on,On,ON,off,Off,OFF}"
    ENUM = "See manifest documentation for list of possible values for an enum."

    @property
    def doc(self) -> str:
        return self.value


class FunctionalDataProcessorStrategy(Enum):
    DROPSEQ = "ds"
    STARSOLO = "ss"

    def __init__(self, abbreviation):
        self.abbreviation = abbreviation


class StrandStrategy(Enum):
    SENSE = "SENSE"
    ANTISENSE = "ANTISENSE"
    BOTH = "BOTH"


class LocusFunction(Enum):
    EXONIC = "exonic"
    INTRONIC = "intronic"
    EXONIC_INTRONIC = "exonic+intronic"

    @property
    def label(self) -> str:
        return self.value
