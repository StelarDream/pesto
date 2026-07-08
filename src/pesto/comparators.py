from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Self
from weakref import WeakSet

from .data_bases import DataBase

if TYPE_CHECKING:
    from .queries import Query

type ComparatorFn[T] = Callable[[DataBase, T, T], bool]


class ComparatorState:
    verified_at: int
    references: WeakSet[Query[Any]]

    __slots__ = ("references", "verified_at")

    def __init__(self, db: DataBase) -> None:
        self.references = WeakSet()
        self.verified_at = db.now

    @property
    def ref_count(self) -> int:
        return len(self.references)

    def add_ref(self, query: Query[Any]) -> Self:
        self.references.add(query)
        return self


# --- Comparators ---


def comparator_eq[T](db: DataBase, old: T, new: T) -> bool:  # noqa: ARG001
    return old == new
