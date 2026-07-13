from collections.abc import Callable
from operator import eq
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .comparators import Comparator
    from .data_bases import DataBase, Node

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

    def get_dependencies(self, db: DataBase) -> list[Node[Any]]:
        return db.dependencies_of(self)
