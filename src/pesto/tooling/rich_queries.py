import functools
import inspect
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Concatenate

from pesto.core.data_bases import DataBase
from pesto.impl.nodes import Query

if TYPE_CHECKING:
    from pesto.core.types import Comparator

type RichQueryFn[**P, T] = Callable[Concatenate[DataBase, P], T]
type CallKeyGen[**P, K] = Callable[Concatenate[RichQueryFn[P, Any], P], K]


def inspect_cell_key_gen[**P](
    fn: RichQueryFn[P, Any],
    *args: P.args,
    **kwargs: P.kwargs,
) -> tuple[tuple[Any, ...], tuple[tuple[str, Any], ...]]:
    sig = inspect.signature(fn).bind(None, *args, **kwargs)
    sig.apply_defaults()
    return sig.args, tuple(sorted(sig.kwargs.items()))


class RichQuery[**P, T, K = Any]:
    fn: RichQueryFn[P, T]
    call_key_gen: CallKeyGen[P, K]

    queries_cache: dict[K, Query[T]]

    def __init__(
        self,
        fn: RichQueryFn[P, T],
        call_key_gen: CallKeyGen[P, K] = inspect_cell_key_gen,
    ) -> None:
        self.fn = fn
        self.call_key_gen = call_key_gen
        self.queries_cache = {}

    def get_query(self, *args: P.args, **kwargs: P.kwargs) -> Query[T]:
        key = self.call_key_gen(self.fn, *args, **kwargs)
        query = self.queries_cache.get(key)
        if query is not None:
            return query

        query = Query(lambda db: self.fn(db, *args, **kwargs))
        self.queries_cache[key] = query
        return query

    def delete(self, *args: P.args, **kwargs: P.kwargs) -> None:
        call_id = self.call_key_gen(self.fn, *args, **kwargs)
        del self.queries_cache[call_id]

    def getter(
        self,
        comparator: Comparator[T],
    ) -> Callable[Concatenate[DataBase, P], T]:
        @functools.wraps(self.fn)
        def inner(db: DataBase, *args: P.args, **kwargs: P.kwargs) -> T:
            return self.get_query(*args, **kwargs).get(db, comparator)

        return inner

    def get(self, db: DataBase, *args: P.args, **kwargs: P.kwargs) -> T:
        return self.get_query(*args, **kwargs).get(db)

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Query[T]:
        return self.get_query(*args, **kwargs)

    @property
    def __wrapped__(self) -> RichQueryFn[P, T]:
        return self.fn
