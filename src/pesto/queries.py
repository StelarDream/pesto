from collections.abc import Callable
from operator import eq
from typing import TYPE_CHECKING

from .cells import QueryCell
from .data_bases import DataBase

if TYPE_CHECKING:
    from .comparators import Comparator

type QueryFn[T] = Callable[[DataBase], T]


class Query[T]:
    fn: QueryFn[T]

    def __init__(
        self,
        fn: QueryFn[T],
    ) -> None:
        self.fn = fn

    @property
    def __wrapped__(self) -> QueryFn[T]:
        return self.fn

    # --- DataBase entries management ---

    def get(self, db: DataBase, comparator: Comparator[T] = eq) -> T:
        return db.get_query(self, comparator)

    def getter(self, comparator: Comparator[T]) -> Callable[[DataBase], T]:
        def inner(db: DataBase) -> T:
            return self.get(db, comparator)

        return inner

    @property
    def cell(self) -> type[QueryCell[T]]:
        return QueryCell
