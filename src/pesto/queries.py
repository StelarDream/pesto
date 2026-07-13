from collections.abc import Callable
from operator import eq
from typing import TYPE_CHECKING, Any

from .data_bases import DataBase

if TYPE_CHECKING:
    from .cells import QueryCell
    from .comparators import Comparator
    from .sources import Source

type QueryFn[T] = Callable[[DataBase], T]


class Query[T]:
    fn: QueryFn[T]

    __slots__ = ("__weakref__", "fn")

    def __init__(self, fn: QueryFn[T]) -> None:
        self.fn = fn

    def __call__(self, db: DataBase, comparator: Comparator[T] = eq) -> T:
        return self.get(db, comparator=comparator)

    def get(self, db: DataBase, comparator: Comparator[T] = eq) -> T:
        return db.get_query(self, comparator=comparator)

    def get_dependencies(
        self,
        db: DataBase,
    ) -> dict[Query[Any] | Source[Any], Comparator[Any]]:
        return db.dependencies_of(self)

    def resolve(self, db: DataBase) -> QueryCell[T] | None:
        return db.query_data.get(self)

    def ensure_cell(self, db: DataBase) -> QueryCell[T]:
        cell = db.query_data.get(self)
        if cell is None:
            cell = db.recompute(self)
        return cell

    @property
    def __wrapped__(self) -> QueryFn[T]:
        return self.fn

    def __repr__(self) -> str:
        return f"<Query {self.fn.__qualname__}>"

    def __getstate__(self) -> QueryFn[T]:
        return self.fn

    def __setstate__(self, state: QueryFn[T]) -> None:
        self.fn = state
