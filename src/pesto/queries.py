from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Concatenate

from .call_id import inspect_call_id_fn

if TYPE_CHECKING:
    from .call_id import CallId, QueryIdFn
    from .data_base import DataBase


type QueryFn[**P, T] = Callable[Concatenate[DataBase, P], T]


class QueryDef[**P, T]:
    fn: QueryFn[P, T]
    query_id_fn: QueryIdFn[P]

    # IMMENSELY IMPORTANT ! this is what keeps references to queries alive
    all_queries: dict[CallId, Query[T]]

    __slots__ = ("all_queries", "fn", "query_id_fn")

    def __init__(
        self,
        fn: QueryFn[P, T],
        call_id_fn: QueryIdFn[P] = inspect_call_id_fn,
    ) -> None:
        self.fn = fn
        self.query_id_fn = call_id_fn
        self.all_queries = {}

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Query[T]:
        return self.get_query(*args, **kwargs)

    def get_query_id(self, *args: P.args, **kwargs: P.kwargs) -> CallId:
        return self.query_id_fn(self.fn, *args, **kwargs)

    def get_query(self, *args: P.args, **kwargs: P.kwargs) -> Query[T]:
        call_id = self.get_query_id(*args, **kwargs)
        if call_id in self.all_queries:
            return self.all_queries[call_id]

        query = Query(
            fn=lambda db: self.fn(db, *args, **kwargs),
            del_fn=lambda: self.all_queries.pop(call_id, None),
        )

        self.all_queries[call_id] = query
        return query

    def del_query(self, *args: P.args, **kwargs: P.kwargs) -> None:
        call_id = self.get_query_id(*args, **kwargs)
        del self.all_queries[call_id]


class Query[T]:
    fn: Callable[[DataBase], T]
    del_fn: Callable[[], Any] | None

    __slots__ = ("__weakref__", "del_fn", "fn")

    def __init__(
        self,
        fn: Callable[[DataBase], T],
        del_fn: Callable[[], Any] | None = None,
    ) -> None:
        self.fn = fn
        self.del_fn = del_fn

    def __call__(self, db: DataBase) -> T:
        raise NotImplementedError

    def __del__(self) -> None:
        if self.del_fn:
            self.del_fn()
