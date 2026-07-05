from collections.abc import Callable
from typing import TYPE_CHECKING, Concatenate

from .call_key_generators import CallKeyGen, inspect_call_key_gen
from .data_base import DataBase

if TYPE_CHECKING:
    from .comparators import Comparator, ComparatorState

type QueryFn[**P, T] = Callable[Concatenate[DataBase, P], T]


class QueryCache[T]:
    value: T
    comparators: dict[Comparator[T], ComparatorState]

    __slots__ = ("comparators", "value")

    def __init__(self) -> None:
        self.comparators = {}


class QueryDef[T, **P = ...]:
    fn: QueryFn[P, T]
    call_key_gen: CallKeyGen = inspect_call_key_gen

    __slots__ = ("fn",)

    def __init__(self, fn: QueryFn[P, T]) -> None:
        self.fn = fn

    def __call__(self, db: DataBase, *args: P.args, **kwargs: P.kwargs) -> T:
        msg = "missing db hook for cache and computation"
        raise NotImplementedError(msg)
