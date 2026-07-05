from typing import TYPE_CHECKING, Any
from weakref import WeakKeyDictionary

if TYPE_CHECKING:
    from .call_key_generators import CallId
    from .queries import QueryCache, QueryDef


class DataBase:
    query_caches: WeakKeyDictionary[QueryDef[Any], dict[CallId, QueryCache[Any]]]

    __slots__ = ("query_caches",)

    def __init__(self) -> None:
        self.query_caches = WeakKeyDictionary()

    def now(self) -> int:
        msg = "no timer yet"
        raise NotImplementedError(msg)
