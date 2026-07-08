from collections.abc import Callable
from typing import TYPE_CHECKING, Concatenate, Self

from .call_id_fns import inspect_call_id_fn
from .queries import Query, QueryFn

if TYPE_CHECKING:
    from .call_id_fns import CallId, QueryIdFn
    from .data_bases import DataBase


type RichQueryFn[**P, T] = Callable[Concatenate[DataBase, P], T]
type QueryFactory[**P, T] = Callable[P, QueryFn[T]]


class QueryDef[**P, T]:
    call_id_fn: QueryIdFn[P]

    # IMMENSELY IMPORTANT ! this is what keeps references to queries alive
    all_queries: dict[CallId, Query[T]]

    __slots__ = (
        "__wrapped__",
        "all_queries",
        "call_id_fn",
    )

    def __init__(
        self,
        fn: RichQueryFn[P, T],
        call_id_fn: QueryIdFn[P] = inspect_call_id_fn,
    ) -> None:
        self.__wrapped__ = fn
        self.call_id_fn = call_id_fn

        self.all_queries = {}

    # --- Query factory management ---

    def get_query_id(self, *args: P.args, **kwargs: P.kwargs) -> CallId:
        return self.call_id_fn(self.__wrapped__, *args, **kwargs)

    def get_query(self, *args: P.args, **kwargs: P.kwargs) -> Query[T] | None:
        call_id = self.get_query_id(*args, **kwargs)
        return self.all_queries.get(call_id, None)

    def get_from_id(self, call_id: CallId) -> Query[T] | None:
        return self.all_queries.get(call_id, None)

    def get_query_or_make(self, *args: P.args, **kwargs: P.kwargs) -> Query[T]:
        call_id = self.get_query_id(*args, **kwargs)
        if call_id in self.all_queries:
            return self.all_queries[call_id]

        query = Query(
            fn=lambda db: self.__wrapped__(db, *args, **kwargs),
            del_fn=lambda: self.all_queries.pop(call_id, None),
        )

        self.all_queries[call_id] = query
        return query

    def delete(self, *args: P.args, **kwargs: P.kwargs) -> Self:
        call_id = self.get_query_id(*args, **kwargs)
        del self.all_queries[call_id]
        return self

    def delete_from_id(self, call_id: CallId) -> Self:
        del self.all_queries[call_id]
        return self

    # --- DataBase entries management ---

    def __call__(self, db: DataBase, *args: P.args, **kwargs: P.kwargs) -> T:
        return self.get(db, *args, **kwargs)

    def get(self, db: DataBase, *args: P.args, **kwargs: P.kwargs) -> T:
        return self.get_query_or_make(*args, **kwargs).get(db)

    def remove(self, db: DataBase, *args: P.args, **kwargs: P.kwargs) -> Self:
        self.get_query_or_make(*args, **kwargs).remove(db)
        return self
