from collections.abc import Iterable
from typing import Protocol

type MapLike[K, V] = SupportsKeysAndGetitem[K, V] | Iterable[tuple[K, V]]


class SupportsKeysAndGetitem[K, V](Protocol):
    def keys(self) -> Iterable[K]: ...
    def __getitem__(self, key: K, /) -> V: ...
