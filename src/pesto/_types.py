from collections.abc import Iterable
from enum import Enum, auto
from typing import Literal, Protocol

type MapLike[K, V] = SupportsKeysAndGetitem[K, V] | Iterable[tuple[K, V]]


class SupportsKeysAndGetitem[K, V](Protocol):
    def keys(self) -> Iterable[K]: ...
    def __getitem__(self, key: K, /) -> V: ...


class Sentinel(Enum):
    MISSING = auto()


MissingType = Literal[Sentinel.MISSING]
MISSING = Sentinel.MISSING
