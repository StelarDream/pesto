from typing import TYPE_CHECKING, Any, Self, overload
from weakref import WeakKeyDictionary

from pesto.sentinels import MISSING, MissingType

from .comparators import ComparatorState
from .counter import Counter
from .input import Input

if TYPE_CHECKING:
    from .comparators import Comparator
    from .queries import Query

type Node[T] = Input[T] | Query[T]


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
    input_data: WeakKeyDictionary[Input[Any], Cell[Any]]
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
        inpt: Input[T],
        *,
        comparator: Comparator[T] | None = None,
    ) -> T: ...

    @overload
    def get_input[T, D](
        self,
        inpt: Input[T],
        *,
        default: D,
        comparator: Comparator[T] | None = None,
    ) -> T | D: ...

    def get_input[T, D](
        self,
        inpt: Input[T],
        *,
        comparator: Comparator[T] | None = None,
        default: D | MissingType = MISSING,
    ) -> T | D:
        if inpt in self.input_data:
            return self.input_data[inpt].value

        if not inpt.has_default:
            if default is MISSING:
                raise KeyError
            return default

        input_default = inpt.default
        cell = Cell(input_default, self)

        if comparator:
            cell.add_ref(self, comparator, self.stack_current())

        self.input_data[inpt] = cell
        return input_default

    @overload
    def get_query[T](
        self,
        query: Query[T],
        *,
        comparator: Comparator[T] | None = None,
    ) -> T: ...

    @overload
    def get_query[T, D](
        self,
        query: Query[T],
        *,
        default: D,
        comparator: Comparator[T] | None = None,
    ) -> T | D: ...

    def get_query[T, D](
        self,
        query: Query[T],
        comparator: Comparator[T] | None = None,
        default: D | MissingType = MISSING,
    ) -> T | D:
        msg = "work in progress"
        raise NotImplementedError(msg)

        missing = query not in self.query_data
        stale = bool("some predicate, no idea")

    def compute[T](self, query: Query[T]) -> T:
        msg = "work in progress"
        raise NotImplementedError(msg)
