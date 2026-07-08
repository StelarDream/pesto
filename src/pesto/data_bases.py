from typing import TYPE_CHECKING, Any
from weakref import WeakKeyDictionary

from .counters import Counter

if TYPE_CHECKING:
    from .cells import Cell, QueryCell
    from .queries import Query
    from .sources import Source


class DataBase:
    input_data: WeakKeyDictionary[Source[Any], Cell[Any]]
    query_data: WeakKeyDictionary[Query[Any], QueryCell[Any]]
    revision: Counter

    __slots__ = ("input_data", "query_data", "revision")

    def __init__(self) -> None:
        self.input_data = WeakKeyDictionary()
        self.query_data = WeakKeyDictionary()
        self.revision = Counter()

    @property
    def now(self) -> int:
        return self.revision.now()
