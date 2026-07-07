from typing import TYPE_CHECKING, Any, overload
from weakref import WeakKeyDictionary

from .cells import Cell, QueryCell
from .counters import Counter
from .sentinels import MISSING, MissingType

if TYPE_CHECKING:
    from .comparators import Comparator
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

    @property
    def stack_current(self) -> Query[Any]:
        msg = "work in progress"
        raise NotImplementedError(msg)

    @overload
    def get_input[T](
        self,
        source: Source[T],
        *,
        comparator: Comparator[T] | None = None,
    ) -> T: ...

    @overload
    def get_input[T, D](
        self,
        source: Source[T],
        *,
        comparator: Comparator[T] | None = None,
        default: D,
    ) -> T | D: ...

    def get_input[T, D](
        self,
        source: Source[T],
        *,
        comparator: Comparator[T] | None = None,
        default: D | MissingType = MISSING,
    ) -> T | D:
        if source in self.input_data:
            cell = self.input_data[source]
        elif source.has_default:
            source_default = source.default
            cell = Cell(source_default, self)
            self.input_data[source] = cell
        else:
            if default is MISSING:
                raise KeyError
            return default

        if comparator:
            cell.track_caller(self, comparator, self.stack_current)

        return cell.value

    def get_query[T](
        self,
        query: Query[T],
        comparator: Comparator[T] | None = None,
    ) -> T:
        msg = "work in progress"
        raise NotImplementedError(msg)

        missing = query not in self.query_data
        stale = bool("some predicate, no idea")

    def compute[T](self, query: Query[T]) -> T:
        msg = "work in progress"
        raise NotImplementedError(msg)
