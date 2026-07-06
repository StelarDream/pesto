from enum import Enum, auto
from typing import Literal


class Sentinel(Enum):
    MISSING = auto()


MissingType = Literal[Sentinel.MISSING]
MISSING = Sentinel.MISSING
