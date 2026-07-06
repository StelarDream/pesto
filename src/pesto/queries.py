from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Concatenate

from .call_id import CallIdFn, inspect_call_id_fn
from .data_base import Cell, DataBase

if TYPE_CHECKING:
    from .call_id import CallId
    from .comparators import Comparator
    from .data_base import NodeKey

type QueryFn[**P, T] = Callable[Concatenate[DataBase, P], T]


class QueryCache[T](Cell[T]):
    verified_at: int
    recorded_edges: dict[NodeKey[Any], Comparator[Any]]

    __slots__ = ("recorded_edges", "verified_at")

    def __init__(self, value: T, db: DataBase) -> None:
        self.value = value
        self.comparators = {}
        self.verified_at = db.now()


class QueryDef[T, **P = ...]:
    fn: QueryFn[P, T]
    call_id_fn: CallIdFn[P]

    __slots__ = ("__weakref__", "call_id_fn", "fn")

    def __init__(
        self,
        fn: QueryFn[P, T],
        *,
        call_id: CallIdFn[P] = inspect_call_id_fn,
    ) -> None:
        self.fn = fn
        self.call_id_fn = call_id

    def __call__(self, db: DataBase, *args: P.args, **kwargs: P.kwargs) -> T:
        msg = "missing db hook for cache and computation"
        raise NotImplementedError(msg)

    def call_id(self, *args: P.args, **kwargs: P.kwargs) -> CallId:
        return self.call_id_fn(self.fn, *args, **kwargs)
