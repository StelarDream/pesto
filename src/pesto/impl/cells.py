from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any
from weakref import ReferenceType, WeakKeyDictionary, WeakSet

from pesto.core.interfaces import ICell, IQuery, IQueryCell, ISourceCell

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from pesto.core.data_bases import DataBase
    from pesto.core.types import Comparator, Dependencies

    from .nodes import Node, Query, Source


class CircularDependencyError(Exception):
    def __init__(
        self,
        query: IQuery[Any, Any],
        chain: Sequence[IQuery[Any, Any]],
    ) -> None:
        self.query = query
        self.chain = chain
        super().__init__(
            f"Circular dependency detected: {query} depends on itself via {chain}",
        )


class ComparatorState:
    changed_at: int
    references: WeakSet[IQuery[Any, Any]]

    def __init__(self, start: int) -> None:
        self.changed_at = start
        self.references = WeakSet()

    @property
    def ref_count(self) -> int:
        return len(self.references)

    def add_ref(self, query: IQuery[Any, Any]) -> None:
        self.references.add(query)

    def drop_ref(self, query: IQuery[Any, Any]) -> None:
        self.references.discard(query)


class Cell[T, O: Node[Any, Any] = Node[T]](ICell[T, O], ABC):
    value: T
    verified_at: int
    comparators: WeakKeyDictionary[Comparator[T], ComparatorState]

    def __init__(self, db: DataBase, value: T) -> None:
        self.value = value
        self.verified_at = db.now()
        self.comparators = WeakKeyDictionary()

    @abstractmethod
    def owner(self) -> O:
        raise NotImplementedError

    @abstractmethod
    def get(self, db: DataBase, comparator: Comparator[T]) -> T:
        raise NotImplementedError

    @abstractmethod
    def refresh(self, db: DataBase) -> T:
        raise NotImplementedError

    def add_ref(self, query: IQuery[Any, Any], comparator: Comparator[T]) -> None:
        state = self.comparators.get(comparator)
        if state is None:
            state = ComparatorState(self.verified_at)
            self.comparators[comparator] = state
        state.add_ref(query)

    def drop_ref(self, query: IQuery[Any, Any], comparator: Comparator[T]) -> None:
        state = self.comparators.get(comparator)
        if state is None:
            return

        state.drop_ref(query)

    def changed_at(self, comparator: Comparator[T]) -> int:
        state = self.comparators.get(comparator)
        if state is None:
            return -1
        return state.changed_at

    def verify_at(self, revision: int, new: T) -> None:
        for comparator, state in tuple(self.comparators.items()):
            if state.ref_count <= 0:
                self.comparators.pop(comparator, None)
            elif not comparator(self.value, new):
                state.changed_at = revision

        self.verified_at = revision
        self.value = new


class SourceCell[T](ISourceCell[T, "Source[T]"], Cell[T, "Source[T]"]):
    source: ReferenceType[Source[T]]

    def __init__(
        self,
        source: Source[T],
        db: DataBase,
        value: T,
    ) -> None:
        super().__init__(db, value)
        db.source_data[source] = self
        self.source = ReferenceType(source)

    def owner(self) -> Source[T]:
        ref = self.source()
        if ref is None:
            raise ReferenceError
        return ref

    @classmethod
    def new(
        cls,
        owner: Source[T],
        db: DataBase,
        comparator: Comparator[T],
    ) -> T:
        value = owner.default
        cell: SourceCell[T] = cls(owner, db, value)
        db.add_dep(cell, comparator)
        return value

    def get(self, db: DataBase, comparator: Comparator[T]) -> T:
        db.add_dep(self, comparator)
        return self.value

    def refresh(self, db: DataBase) -> T:  # noqa: ARG002
        return self.value

    def set(self, db: DataBase, value: T) -> None:
        if db.stack.peek_or(None) is not None:
            raise RuntimeError

        self.verify_at(db.update(), value)


class QueryCell[T](IQueryCell[T, "Query[T]"], Cell[T, "Query[T]"]):
    query: ReferenceType[Query[T]]
    dependencies: WeakKeyDictionary[ICell[Any, Any], Comparator[Any]]

    def __init__(
        self,
        query: Query[T],
        db: DataBase,
        value: T,
    ) -> None:
        super().__init__(db, value)
        db.query_data[query] = self
        self.query = ReferenceType(query)
        self.dependencies = WeakKeyDictionary()

    def owner(self) -> Query[T]:
        ref = self.query()
        if ref is None:
            raise ReferenceError
        return ref

    def add_dependencies(self, dependencies: Dependencies) -> None:
        query = self.owner()  # to avoid mid-loop dereferencing
        for cell, comparator in dict(dependencies).items():
            self.dependencies[cell] = comparator
            cell.add_ref(query, comparator)

    def reset_dependencies(self) -> None:
        query = self.owner()
        for cell, comparator in tuple(self.dependencies.items()):
            cell.drop_ref(query, comparator)

        self.dependencies.clear()

    def get_dependencies(self) -> dict[ICell[Any, Any], Comparator[Any]]:
        return dict(self.dependencies)

    @classmethod
    def new(
        cls,
        owner: Query[T],
        db: DataBase,
        comparator: Comparator[T],
    ) -> T:
        active = [frame.query for frame in db.stack]
        if owner in active:
            chain = [*reversed(active), owner]
            raise CircularDependencyError(owner, chain)

        db.stack.push(owner)
        try:
            value = owner.fn(db)
        except:
            db.query_data.pop(owner, None)
            raise
        finally:
            frame = db.stack.pop()

        cell = QueryCell(owner, db, value)
        db.add_dep(cell, comparator)
        cell.add_dependencies(frame.dependencies)
        return value

    def get(self, db: DataBase, comparator: Callable[[T, T], bool]) -> T:
        query = self.owner()
        active = [frame.query for frame in db.stack]
        if query in active:
            chain = [*reversed(active), query]
            raise CircularDependencyError(query, chain)

        value = self.refresh(db)

        db.add_dep(self, comparator)
        return value

    def refresh(self, db: DataBase) -> T:
        if not self.is_green(db):
            return self.recompute(db)
        return self.value

    def is_green(self, db: DataBase) -> bool:
        now = db.now()
        if self.verified_at == now:
            return True

        for cell, comparator in tuple(self.dependencies.items()):
            cell.refresh(db)
            changed_at = cell.changed_at(comparator)
            if changed_at > self.verified_at:
                return False

        self.verified_at = now
        return True

    def recompute(self, db: DataBase) -> T:
        query = self.owner()

        self.reset_dependencies()

        db.stack.push(query)
        try:
            new = query.fn(db)
        except:
            db.query_data.pop(query, None)
            raise
        finally:
            frame = db.stack.pop()

        self.verify_at(db.now(), new)
        self.add_dependencies(frame.dependencies)
        return new
