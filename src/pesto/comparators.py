from collections.abc import Callable
from typing import TYPE_CHECKING, Any
from weakref import WeakSet

if TYPE_CHECKING:
    from .queries import Query


type Comparator[T] = Callable[[T, T], bool]


class ComparatorState:
    changed_at: int
    references: WeakSet[Query[Any]]

    __slots__ = ("changed_at", "references")

    def __init__(self, start: int) -> None:
        self.changed_at = start
        self.references = WeakSet()

    @property
    def references_count(self) -> int:
        return len(self.references)

    def __repr__(self) -> str:
        return f"<ComparatorState changed_at={self.changed_at} references_count={self.references_count}>"

    def __getstate__(self) -> tuple[int, list[Query[Any]]]:
        return self.changed_at, list(self.references)

    def __setstate__(self, state: tuple[int, list[Query[Any]]]) -> None:
        self.changed_at, references = state
        self.references = WeakSet(references)
