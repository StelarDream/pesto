from typing import TYPE_CHECKING, Any, overload
from weakref import WeakKeyDictionary

from .counter import Counter
from .input import Input

if TYPE_CHECKING:
    from .call_id import CallId
    from .queries import QueryCache, QueryDef


class DataBase:
    query_caches: WeakKeyDictionary[QueryDef[Any], dict[CallId, QueryCache[Any]]]
    input_values: WeakKeyDictionary[Input[Any], Any]
    revision: Counter

    __slots__ = ("__weakref__", "query_caches", "revision")

    def __init__(self) -> None:
        self.query_caches = WeakKeyDictionary()
        self.revision = Counter()

    def now(self) -> int:
        return self.revision.now()

    def compute[**P, T](
        self,
        query: QueryDef[T, P],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> T:
        raise NotImplementedError

    @overload
    def get[**P, T](
        self,
        key: QueryDef[T, P],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> T: ...
    @overload
    def get[T](self, key: Input[T]) -> T: ...

    def get[**P, T](
        self,
        key: QueryDef[T, P] | Input[T],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> T:
        if isinstance(key, Input):
            return self.input_values.setdefault(key, key.default)

        msg = "the query code path is no yet made"
        raise NotImplementedError(msg)

        # call_key = key.call_id(*args, **kwargs)  # noqa: ERA001
