from collections.abc import Callable
from typing import TYPE_CHECKING, Any
from weakref import WeakSet

from .data_base import DataBase

if TYPE_CHECKING:
    from pesto.queries import Query

type ComparatorFn[T] = Callable[[DataBase, T, T], bool]


class Comparator[T]:
    fn: ComparatorFn[T]

    __slots__ = ("fn",)

    def __init__(self, fn: ComparatorFn[T]) -> None:
        self.fn = fn

    def __call__(self, db: DataBase, old: T, new: T) -> bool:
        return self.fn(db, old, new)


class ComparatorState:
    verified_at: int
    references: WeakSet[Query[Any]]

    __slots__ = ("references", "verified_at")

    def __init__(self, db: DataBase) -> None:
        self.references = WeakSet()
        self.verified_at = db.now()

    @property
    def ref_count(self) -> int:
        return len(self.references)
