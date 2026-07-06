from typing import TYPE_CHECKING, Any, Self, overload
from weakref import WeakKeyDictionary

from pesto.sentinels import MISSING, MissingType

from .comparators import ComparatorState
from .counter import Counter
from .source import Source

if TYPE_CHECKING:
    from .comparators import Comparator
    from .queries import Query

type Node[T] = Source[T] | Query[T]


class Cell[T]:
    value: T
    comparators: dict[Comparator[T], ComparatorState]
    changed_at: int

    __slots__ = ("changed_at", "comparators", "value")

    def __init__(self, value: T, db: DataBase) -> None:
        self.value = value
        self.comparators = {}
        self.changed_at = db.now()

    def add_ref(
        self,
        db: DataBase,
        comparator: Comparator[Any],
        caller: Query[Any],
    ) -> Self:
        self.comparators.setdefault(comparator, ComparatorState(db)).add_ref(caller)
        return self


class DataBase:
    input_data: WeakKeyDictionary[Source[Any], Cell[Any]]
    query_data: WeakKeyDictionary[Query[Any], Cell[Any]]
    revision: Counter

    __slots__ = ("input_data", "query_data", "revision")

    def __init__(self) -> None:
        self.input_data = WeakKeyDictionary()
        self.query_data = WeakKeyDictionary()
        self.revision = Counter()

    def now(self) -> int:
        return self.revision.now()

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
        default: D,
        comparator: Comparator[T] | None = None,
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
            cell.add_ref(self, comparator, self.stack_current())

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
