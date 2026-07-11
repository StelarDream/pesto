from collections.abc import Callable
from typing import TYPE_CHECKING, Any
from weakref import WeakSet

if TYPE_CHECKING:
    from .cells import QueryCell


type Comparator[T] = Callable[[T, T], bool]


class ComparatorState:
    changed_at: int
    references: WeakSet[QueryCell[Any]]

    def __init__(self, start: int) -> None:
        self.changed_at = start
        self.references = WeakSet()

    @property
    def ref_count(self) -> int:
        return len(self.references)
