from collections.abc import Callable
from typing import TYPE_CHECKING, Concatenate

from .call_id import CallIdFn, inspect_call_id_fn
from .data_base import DataBase

if TYPE_CHECKING:
    from .call_id import CallId
    from .comparators import Comparator, ComparatorState

type QueryFn[**P, T] = Callable[Concatenate[DataBase, P], T]


class QueryCache[T]:
    value: T
    comparators: dict[Comparator[T], ComparatorState]

    __slots__ = ("comparators", "value")

    def __init__(self, value: T) -> None:
        self.value = value
        self.comparators = {}


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
