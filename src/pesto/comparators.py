from collections.abc import Callable
from typing import TYPE_CHECKING, Any
from weakref import WeakKeyDictionary

from .data_base import DataBase

if TYPE_CHECKING:
    from .queries import QueryDef

type ComparatorFn[T] = Callable[[DataBase, T, T], bool]


class Comparator[T]:
    fn: ComparatorFn[T]

    __slots__ = ("fn",)

    def __init__(self, fn: ComparatorFn[T]) -> None:
        self.fn = fn

    def __call__(self, db: DataBase, old: T, new: T) -> bool:
        return self.fn(db, old, new)


class ComparatorState:
    ref_counters: WeakKeyDictionary[QueryDef[Any], int]
    changed_at: int

    __slots__ = ("changed_at", "ref_counters")

    def __init__(self, db: DataBase) -> None:
        self.ref_counters = WeakKeyDictionary()
        self.changed_at = db.now()

    @property
    def ref_count(self) -> int:
        return sum(self.ref_counters.values())
