from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from operator import eq
from typing import Any

from .cells import Cell, QueryCell
from .data_bases import Comparator, DataBase, INode

type QueryFn[T] = Callable[[DataBase], T]


class CircularDependencyError(Exception):
    def __init__(
        self,
        node: INode[Any, Any],
        chain: Sequence[INode[Any, Any]],
    ) -> None:
        self.node = node
        self.chain = chain
        super().__init__(
            f"Circular dependency detected: {node} depends on itself via {chain}",
        )


class Source[T](INode[T, Cell[T]], ABC):
    @property
    @abstractmethod
    def default(self) -> T:
        raise NotImplementedError

    def get(self, db: DataBase, comparator: Comparator[T] = eq) -> T:
        cell = db.get_data(self)
        if cell is None:
            value = self.default
            db.set_data(self, Cell(value, db.now()))
        else:
            value = cell.value
        db.add_dep(self, comparator)
        return value

    def set(self, db: DataBase, value: T) -> None:
        cell = db.get_data(self)
        if cell is None:
            db.set_data(self, Cell(value, db.now()))
            return

        now = db.update()
        cell.update(now, value)
        return

    def changed_at(self, db: DataBase, comparator: Comparator[T]) -> int:
        cell = db.get_data(self)
        if cell is None:
            now = db.now()
            db.set_data(self, Cell(self.default, now))
            return now

        return cell.changed_at(comparator)

    def track(
        self,
        db: DataBase,
        node: INode[Any, Any],
        comparator: Comparator[T],
    ) -> None:
        cell = db.get_data(self)
        if cell is None:
            cell = Cell(self.default, db.now())
            db.set_data(self, cell)

        cell.track(node, comparator)

    def untrack(
        self,
        db: DataBase,
        node: INode[Any, Any],
        comparator: Comparator[T],
    ) -> None:
        cell = db.get_data(self)
        if cell is None:
            return

        cell.untrack(node, comparator)


class DefaultFactorySource[T](Source[T]):
    default_factory: Callable[[], T]

    def __init__(self, default_factory: Callable[[], T]) -> None:
        self.default_factory = default_factory

    @property
    def default(self) -> T:
        return self.default_factory()


class DefaultValueSource[T](Source[T]):
    default_value: T

    def __init__(self, default_value: T) -> None:
        self.default_value = default_value

    @property
    def default(self) -> T:
        return self.default_value


class Query[T](INode[T, QueryCell[T]]):
    fn: QueryFn[T]

    def __init__(self, fn: QueryFn[T]) -> None:
        self.fn = fn

    def get(self, db: DataBase, comparator: Comparator[T] = eq) -> T:
        actives = [frame.active for frame in db.stack]
        if self in actives:
            chain = [*reversed(actives), self]
            raise CircularDependencyError(self, chain)

        cell = db.get_data(self)
        if cell is None:
            cell = self.make_new(db)
        elif not cell.is_green(db):
            cell = self.recompute(cell, db)

        db.add_dep(self, comparator)

        return cell.value

    def depend(self, db: DataBase, comparator: Comparator[T] = eq) -> None:
        db.add_dep(self, comparator)

    def get_dependencies(self, db: DataBase) -> dict[INode[Any, Any], Comparator[T]]:
        cell = db.get_data(self)
        if cell is None:
            return {}
        return dict(cell.dependencies)

    def make_new(self, db: DataBase) -> QueryCell[T]:
        db.stack.push(self)
        try:
            value = self.fn(db)
        except:
            db.node_data.pop(self, None)
            raise
        finally:
            frame = db.stack.pop()

        cell = QueryCell(value, db.now())
        db.set_data(self, cell)

        cell.add_dependencies(self, db, frame.dependencies)
        return cell

    def recompute(
        self,
        cell: QueryCell[T],
        db: DataBase,
    ) -> QueryCell[T]:
        cell.reset_dependencies(self, db)

        db.stack.push(self)
        try:
            new = self.fn(db)
        except:
            db.node_data.pop(self, None)
            raise
        finally:
            frame = db.stack.pop()

        cell.update(db.now(), new)

        cell.add_dependencies(self, db, frame.dependencies)
        return cell

    def changed_at(self, db: DataBase, comparator: Comparator[T]) -> int:
        cell = db.get_data(self)
        if cell is None:
            now = db.now()
            db.set_data(self, self.make_new(db))
            return now

        if not cell.is_green(db):
            cell = self.recompute(cell, db)

        return cell.changed_at(comparator)

    def track(
        self,
        db: DataBase,
        node: INode[Any, Any],
        comparator: Comparator[T],
    ) -> None:
        cell = db.get_data(self)
        if cell is None:
            cell = self.make_new(db)
            db.set_data(self, cell)

        cell.track(node, comparator)

    def untrack(
        self,
        db: DataBase,
        node: INode[Any, Any],
        comparator: Comparator[T],
    ) -> None:
        cell = db.get_data(self)
        if cell is None:
            return

        cell.untrack(node, comparator)
