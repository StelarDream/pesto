from collections.abc import Callable

from .cells import QueryCell
from .data_bases import DataBase

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

    @property
    def cell(self) -> type[QueryCell[T]]:
        return QueryCell
