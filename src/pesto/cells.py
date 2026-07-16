from abc import ABC
from typing import TYPE_CHECKING, Any
from weakref import ReferenceType, WeakKeyDictionary, WeakSet

from .interfaces import (
    Comparator,
    Dependencies,
    ICell,
    INode,
    IQuery,
    IQueryCell,
    ISource,
    ISourceCell,
)

if TYPE_CHECKING:
    from .data_bases import DataBase


class ComparatorState:
    changed_at: int
    references: WeakSet[IQuery[Any]]

    def __init__(self, start: int) -> None:
        self.changed_at = start
        self.references = WeakSet()

    @property
    def ref_count(self) -> int:
        return len(self.references)

    def add_ref(self, query: IQuery[Any]) -> None:
        self.references.add(query)

    def drop_ref(self, query: IQuery[Any]) -> None:
        self.references.discard(query)


class Cell[T](ICell[T], ABC):
    value: T
    verified_at: int
    comparators: WeakKeyDictionary[Comparator[T], ComparatorState]

    def __init__(self, db: DataBase, value: T) -> None:
        self.value = value
        self.verified_at = db.now()
        self.comparators = WeakKeyDictionary()

    def get(self) -> T:
        return self.value

    def add_ref(self, query: IQuery[Any], comparator: Comparator[T]) -> None:
        self.comparators.setdefault(
            comparator,
            ComparatorState(self.verified_at),
        ).add_ref(query)

    def drop_ref(self, query: IQuery[Any], comparator: Comparator[T]) -> None:
        state = self.comparators.get(comparator)
        if state is None:
            return

        state.drop_ref(query)

    def changed_at(self, comparator: Comparator[T]) -> int:
        state = self.comparators.get(comparator)
        if state is None:
            return -1
        return state.changed_at

    def update(self, db: DataBase, new_value: T) -> None:
        now = db.update()
        for comparator, state in tuple(self.comparators.items()):
            if state.ref_count <= 0:
                self.comparators.pop(comparator, None)
            elif not comparator(self.value, new_value):
                state.changed_at = now

        self.value = new_value
        self.verified_at = now


class SourceCell[T](Cell[T], ISourceCell[T]):
    source: ReferenceType[ISource[T]]

    def __init__(self, db: DataBase, value: T, source: ISource[T]) -> None:
        super().__init__(db, value)
        self.source = ReferenceType(source)

        db.source_data[source] = self

    def get_source(self) -> ISource[T]:
        source = self.source()
        if source is None:
            raise ReferenceError
        return source


class QueryCell[T](Cell[T], IQueryCell[T]):
    query: ReferenceType[IQuery[T]]
    dependencies: WeakKeyDictionary[INode[Any], Comparator[Any]]

    def __init__(self, db: DataBase, value: T, query: IQuery[T]) -> None:
        super().__init__(db, value)
        self.query = ReferenceType(query)
        self.dependencies = WeakKeyDictionary()

        db.query_data[query] = self

    def get_query(self) -> IQuery[T]:
        query = self.query()
        if query is None:
            raise ReferenceError
        return query

    def add_dependencies(self, db: DataBase, dependencies: Dependencies) -> None:
        query = self.get_query()
        for node, comparator in dict(dependencies).items():
            self.dependencies[node] = comparator
            node.cell(db).add_ref(query, comparator)

    def reset_dependencies(self, db: DataBase) -> None:
        query = self.get_query()
        for node, comparator in tuple(self.dependencies.items()):
            cell = node.current_cell(db)
            if cell is not None:
                cell.drop_ref(query, comparator)

        self.dependencies.clear()

    def get_dependencies(self) -> dict[INode[Any], Comparator[Any]]:
        return dict(self.dependencies)
