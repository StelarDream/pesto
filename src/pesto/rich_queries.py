from collections.abc import Callable
from typing import TYPE_CHECKING, Concatenate, Self
from weakref import WeakValueDictionary

from .call_id_fns import inspect_call_id_fn
from .queries import Query, QueryFn

if TYPE_CHECKING:
    from .call_id_fns import CallId, QueryIdFn
    from .data_bases import DataBase


type RichQueryFn[**P, T] = Callable[Concatenate[DataBase, P], T]
type QueryFactory[**P, T] = Callable[P, QueryFn[T]]


class QueryDef[**P, T, K: CallId = CallId]:
    fn: RichQueryFn[P, T]
    call_id_fn: QueryIdFn[P, K]

    queries_cache: WeakValueDictionary[K, Query[T]]

    __slots__ = (
        "call_id_fn",
        "fn",
        "queries_cache",
    )

    def __init__(
        self,
        fn: RichQueryFn[P, T],
        call_id_fn: QueryIdFn[P, K] = inspect_call_id_fn,
    ) -> None:
        self.fn = fn
        self.call_id_fn = call_id_fn

        self.queries_cache = WeakValueDictionary()

    # --- Query factory management ---

    def get_query_id(self, *args: P.args, **kwargs: P.kwargs) -> K:
        return self.call_id_fn(self.fn, *args, **kwargs)

    def get_query(self, *args: P.args, **kwargs: P.kwargs) -> Query[T] | None:
        call_id = self.get_query_id(*args, **kwargs)
        return self.queries_cache.get(call_id, None)

    def get_from_id(self, call_id: K) -> Query[T] | None:
        return self.queries_cache.get(call_id, None)

    def get_query_or_make(self, *args: P.args, **kwargs: P.kwargs) -> Query[T]:
        call_id = self.get_query_id(*args, **kwargs)
        if call_id in self.queries_cache:
            return self.queries_cache[call_id]

        query = Query(
            fn=lambda db: self.fn(db, *args, **kwargs),
            del_fn=lambda: self.queries_cache.pop(call_id, None),
        )

        self.queries_cache[call_id] = query
        return query

    def delete(self, *args: P.args, **kwargs: P.kwargs) -> Self:
        call_id = self.get_query_id(*args, **kwargs)
        del self.queries_cache[call_id]
        return self

    def delete_from_id(self, call_id: K) -> Self:
        del self.queries_cache[call_id]
        return self

    # --- DataBase entries management ---

    def __call__(self, db: DataBase, *args: P.args, **kwargs: P.kwargs) -> T:
        return self.get(db, *args, **kwargs)

    def get(self, db: DataBase, *args: P.args, **kwargs: P.kwargs) -> T:
        return self.get_query_or_make(*args, **kwargs).get(db)

    def remove(self, db: DataBase, *args: P.args, **kwargs: P.kwargs) -> Self:
        self.get_query_or_make(*args, **kwargs).remove(db)
        return self

    @property
    def __wrapped__(self) -> QueryFn[T]:
        return self.fn
