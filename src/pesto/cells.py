from abc import ABC
from typing import TYPE_CHECKING, Any
from weakref import ReferenceType, WeakKeyDictionary

from .comparators import ComparatorState

if TYPE_CHECKING:
    from .comparators import Comparator
    from .data_bases import DataBase, Node
    from .queries import Query
    from .sources import Source


class Cell[T](ABC):
    value: T
    verified_at: int
    comparators: WeakKeyDictionary[Comparator[T], ComparatorState]

    __slots__ = ("comparators", "value", "verified_at")

    def __init__(self, value: T, start: int) -> None:
        self.value = value
        self.verified_at = start
        self.comparators = WeakKeyDictionary()

    def add_ref(self, query: Query[Any], comparator: Comparator[T]) -> None:
        state = self.comparators.setdefault(
            comparator,
            ComparatorState(self.verified_at),
        )
        state.references.add(query)

    def drop_ref(self, query: Query[Any], comparator: Comparator[T]) -> None:
        state = self.comparators.get(comparator)
        if state is not None:
            state.references.discard(query)

    def update(self, value: T, now: int) -> None:
        for comparator, state in tuple(self.comparators.items()):
            if state.references_count == 0:
                del self.comparators[comparator]
            elif not comparator(self.value, value):
                state.changed_at = now

        self.value = value
        self.verified_at = now


class SourceCell[T](Cell[T]):
    source: ReferenceType[Source[T]]

    __slots__ = ("source",)

    def __init__(self, source: Source[T], value: T, start: int) -> None:
        super().__init__(value, start)
        self.source = ReferenceType(source)

    def __repr__(self) -> str:
        return (
            f"<SourceCell source={self.source()} value={self.value} "
            f"verified_at={self.verified_at} comparators_count={len(self.comparators)}>"
        )

    def __getstate__(
        self,
    ) -> tuple[
        ReferenceType[Source[T]],
        T,
        int,
        list[tuple[Comparator[T], ComparatorState]],
    ]:
        return self.source, self.value, self.verified_at, list(self.comparators.items())

    def __setstate__(
        self,
        state: tuple[
            ReferenceType[Source[T]],
            T,
            int,
            list[tuple[Comparator[T], ComparatorState]],
        ],
    ) -> None:
        self.source, self.value, self.verified_at, comparators = state
        self.comparators = WeakKeyDictionary(comparators)


class QueryCell[T](Cell[T]):
    query: ReferenceType[Query[T]]
    dependencies: WeakKeyDictionary[Node[Any], Comparator[Any]]

    __slots__ = ("dependencies", "query")

    def __init__(self, query: Query[T], value: T, start: int) -> None:
        super().__init__(value, start)
        self.query = ReferenceType(query)
        self.dependencies = WeakKeyDictionary()

    def add_dependencies(
        self,
        db: DataBase,
        dependencies: dict[Node[Any], Comparator[Any]],
    ) -> None:
        query = self.query()
        if query is None:
            msg = "QueryCell has no query reference"
            raise ReferenceError(msg)
        for node, comparator in dependencies.items():
            self.dependencies[node] = comparator
            node.ensure_cell(db).add_ref(query, comparator)

    def reset_dependencies(self, db: DataBase) -> None:
        query = self.query()
        if query is None:
            msg = "QueryCell has no query reference"
            raise ReferenceError(msg)
        for node, comparator in self.dependencies.items():
            node.ensure_cell(db).drop_ref(query, comparator)
        self.dependencies.clear()

    def __repr__(self) -> str:
        return (
            f"<QueryCell query={self.query()} value={self.value} "
            f"verified_at={self.verified_at} comparators_count={len(self.comparators)} "
            f"dependencies_count={len(self.dependencies)}>"
        )

    def __getstate__(
        self,
    ) -> tuple[
        ReferenceType[Query[T]],
        T,
        int,
        list[tuple[Comparator[T], ComparatorState]],
        list[tuple[Node[Any], Comparator[Any]]],
    ]:
        return (
            self.query,
            self.value,
            self.verified_at,
            list(self.comparators.items()),
            list(self.dependencies.items()),
        )

    def __setstate__(
        self,
        state: tuple[
            ReferenceType[Query[T]],
            T,
            int,
            list[tuple[Comparator[T], ComparatorState]],
            list[tuple[Node[Any], Comparator[Any]]],
        ],
    ) -> None:
        self.query, self.value, self.verified_at, comparators, dependencies = state
        self.comparators = WeakKeyDictionary(comparators)
        self.dependencies = WeakKeyDictionary(dependencies)
