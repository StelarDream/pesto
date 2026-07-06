from typing import TYPE_CHECKING, Any
from weakref import WeakKeyDictionary

from .counter import Counter
from .input import Input

if TYPE_CHECKING:
    from .comparators import Comparator, ComparatorState
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

    def get[T](self, key: Input[T] | Query[T], comparator: Comparator[T]) -> T:
        raise NotImplementedError
