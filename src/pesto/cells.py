from typing import TYPE_CHECKING, Any, Self
from weakref import WeakSet

from .comparators import ComparatorState
from .data_bases import DataBase

if TYPE_CHECKING:
    from .comparators import Comparator
    from .data_bases import DataBase
    from .queries import Query
    from .sources import Source


class Cell[T]:
    value: T
    changed_at: int
    comparators: dict[Comparator[T], ComparatorState]

    __slots__ = ("changed_at", "comparators", "value")

    def __init__(self, value: T, db: DataBase) -> None:
        self.value = value
        self.comparators = {}
        self.changed_at = db.now

    def track_caller(
        self,
        db: DataBase,
        comparator: Comparator[T],
        caller: Query[Any],
    ) -> Self:
        self.comparators.setdefault(comparator, ComparatorState(db)).add_ref(caller)
        return self


class QueryCell[T](Cell[T]):
    dependencies: WeakSet[Query[Any] | Source[Any]]

    __slots__ = ("dependencies",)

    def __init__(self, value: T, db: DataBase) -> None:
        super().__init__(value, db)
        self.dependencies = WeakSet()
