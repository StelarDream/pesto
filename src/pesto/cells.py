from typing import TYPE_CHECKING, Any
from weakref import ReferenceType, WeakKeyDictionary

from .comparators import Comparator, ComparatorState
from .queries import Query
from .sentinels import MISSING, MissingType
from .sources import Source

if TYPE_CHECKING:
    from .data_bases import DataBase, Node


class Cell[T, V = Any]:
    verified_at: int
    represents: ReferenceType[V]
    comparator_states: dict[Comparator[Any], ComparatorState]

    _cache: T | MissingType

    def __init__(
        self,
        db: DataBase,
        represents: V,
        value: T | MissingType = MISSING,
    ) -> None:
        self._cache = value
        self.represents = ReferenceType(represents)
        self.verified_at = db.now()
        self.comparator_states = {}

    def add_ref(self, query_cell: QueryCell[Any], comparator: Comparator[T]) -> None:
        state = self.comparator_states.setdefault(
            comparator,
            ComparatorState(self.verified_at),
        )
        state.references.add(query_cell)

    def drop_ref(self, query_cell: QueryCell[Any], comparator: Comparator[T]) -> None:
        state = self.comparator_states.get(comparator)
        if state is None:
            return

        state.references.discard(query_cell)

    def verify(self, old: T, new: T, revision: int) -> None:
        self.comparator_states = {
            comparator: state
            for comparator, state in self.comparator_states.items()
            if state.ref_count > 0
        }

        for comparator, state in self.comparator_states.items():
            if not comparator(old, new):
                state.changed_at = revision

        self.verified_at = revision

    @property
    def value(self) -> T:
        if self._cache is MISSING:
            msg = f"{type(self).__name__} has no value assigned yet"
            raise AttributeError(msg)
        return self._cache

    @value.setter
    def value(self, value: T) -> None:
        self._cache = value


class SourceCell[T](Cell[T, Source[T]]): ...


class QueryCell[T](Cell[T, Query[T]]):
    dependencies: WeakKeyDictionary[Cell[Any, Node[Any]], Comparator[Any]]

    def __init__(self, db: DataBase, represents: Query[T]) -> None:
        super().__init__(db, represents)
        self.dependencies = WeakKeyDictionary()

    def add_dep[V](
        self,
        depends_on: Cell[V, Node[V]],
        comparator: Comparator[V],
    ) -> None:
        self.dependencies[depends_on] = comparator
        depends_on.add_ref(self, comparator)

    def reset_deps(self) -> None:
        for depends_on, comparator in tuple(self.dependencies.items()):
            depends_on.drop_ref(self, comparator)

        self.dependencies.clear()
