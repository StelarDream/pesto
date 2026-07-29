import inspect
from collections.abc import Callable
from functools import Placeholder, cache, partial, wraps
from typing import Any, Concatenate

from .data_bases import Comparator, DataBase
from .nodes import Query

type RichQueryFn[**P, T] = Callable[Concatenate[DataBase, P], T]
type CallKeyGen[**P, K] = Callable[Concatenate[RichQueryFn[P, Any], P], K]


@cache
def inspect_signature(fn: Callable[..., Any]) -> inspect.Signature:
    return inspect.signature(fn)


def inspect_call_key_gen[**P](
    fn: RichQueryFn[P, Any],
    *args: P.args,
    **kwargs: P.kwargs,
) -> tuple[tuple[Any, ...], tuple[tuple[str, Any], ...]]:
    sig = inspect_signature(fn).bind(None, *args, **kwargs)
    sig.apply_defaults()
    return sig.args, tuple(sorted(sig.kwargs.items()))


class RichQuery[**P, T, K = Any]:
    fn: RichQueryFn[P, T]
    call_key_gen: CallKeyGen[P, K]

    queries_cache: dict[K, Query[T]]

    __slots__ = ("call_key_gen", "fn", "queries_cache")

    def __init__(
        self,
        fn: RichQueryFn[P, T],
        call_key_gen: CallKeyGen[P, K] = inspect_call_key_gen,
    ) -> None:
        self.fn = fn
        self.call_key_gen = call_key_gen
        self.queries_cache = {}

    def get_query(self, *args: P.args, **kwargs: P.kwargs) -> Query[T]:
        key = self.call_key_gen(self.fn, *args, **kwargs)
        query = self.queries_cache.get(key)
        if query is not None:
            return query

        if args or kwargs:
            query = Query(partial(self.fn, Placeholder, *args, **kwargs))
        else:
            query = Query(self.fn)

        self.queries_cache[key] = query
        return query

    def delete(self, *args: P.args, **kwargs: P.kwargs) -> None:
        call_id = self.call_key_gen(self.fn, *args, **kwargs)
        self.queries_cache.pop(call_id, None)

    def getter(
        self,
        comparator: Comparator[T],
    ) -> Callable[Concatenate[DataBase, P], T]:
        @wraps(self.fn)
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

    def __getstate__(
        self,
    ) -> tuple[RichQueryFn[P, T], CallKeyGen[P, K], dict[K, Query[T]]]:
        return self.fn, self.call_key_gen, self.queries_cache

    def __setstate__(
        self,
        state: tuple[RichQueryFn[P, T], CallKeyGen[P, K], dict[K, Query[T]]],
    ) -> None:
        self.fn, self.call_key_gen, self.queries_cache = state
