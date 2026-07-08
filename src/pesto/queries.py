import weakref
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from .bases import Node
from .data_bases import DataBase

if TYPE_CHECKING:
    from .data_bases import DataBase


type QueryFn[T] = Callable[[DataBase], T]


class Query[T](Node[T]):
    fn: QueryFn[T]

    __slots__ = ("__weakref__", "del_fn", "fn")

    def __init__(
        self,
        fn: QueryFn[T],
        del_fn: Callable[[], Any] | None = None,
    ) -> None:
        self.fn = fn

        if del_fn is not None:
            weakref.finalize(self, del_fn)

    def __call__(self, db: DataBase) -> T:
        return self.get(db)

    @property
    def __wrapped__(self) -> QueryFn[T]:
        return self.fn
