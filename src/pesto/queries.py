from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from .bases import Node
from .data_bases import DataBase

if TYPE_CHECKING:
    from .data_bases import DataBase


type QueryFn[T] = Callable[[DataBase], T]


class Query[T](Node[T]):
    del_fn: Callable[[], Any] | None

    __slots__ = ("__weakref__", "__wrapped__", "del_fn")

    def __init__(
        self,
        fn: QueryFn[T],
        del_fn: Callable[[], Any] | None = None,
    ) -> None:
        self.__wrapped__ = fn
        self.del_fn = del_fn

    def __call__(self, db: DataBase) -> T:
        return self.get(db)

    def __del__(self) -> None:
        if self.del_fn:
            self.del_fn()
