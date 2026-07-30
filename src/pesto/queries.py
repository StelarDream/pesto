from collections.abc import Callable, Sequence
from operator import eq
from typing import Any

from .cells import QueryCell
from .data_bases import Comparator, DataBase, INode

type QueryFn[T] = Callable[[DataBase], T]


class CircularDependencyError(Exception):
    def __init__(
        self,
        node: INode[Any],
        chain: Sequence[INode[Any]],
    ) -> None:
        self.node = node
        self.chain = chain
        super().__init__(
            f"Circular dependency detected: {node} depends on itself via {chain}",
        )


class Query[T](INode[T]):
    fn: QueryFn[T]

    __slots__ = ("__weakref__", "fn")

    def __init__(self, fn: QueryFn[T]) -> None:
        self.fn = fn

    def get_cell(self, db: DataBase) -> QueryCell[T] | None:
        return db.node_data.get(self)

    def get(self, db: DataBase, comparator: Comparator[T] = eq) -> T:
        actives = [frame.active for frame in db.stack]
        if self in actives:
            chain = [*reversed(actives), self]
            raise CircularDependencyError(self, chain)

        cell = self.get_cell(db)
        if cell is None:
            cell = self.make_new(db)
        elif not cell.is_green(db):
            cell = self.recompute(cell, db)

        db.add_dep(self, comparator)

        return cell.value

    def depend(self, db: DataBase, comparator: Comparator[T] = eq) -> None:
        db.add_dep(self, comparator)

    def get_dependencies(self, db: DataBase) -> dict[INode[Any], Comparator[T]]:
        cell = self.get_cell(db)
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
        db.node_data[self] = cell

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
        cell = self.get_cell(db)
        if cell is None:
            now = db.now()
            db.node_data[self] = cell
            return now

        if not cell.is_green(db):
            cell = self.recompute(cell, db)

        return cell.changed_at(comparator)

    def track(
        self,
        db: DataBase,
        node: INode[Any],
        comparator: Comparator[T],
    ) -> None:
        cell = self.get_cell(db)
        if cell is None:
            cell = self.make_new(db)
            db.node_data[self] = cell

        cell.track(node, comparator)

    def untrack(
        self,
        db: DataBase,
        node: INode[Any],
        comparator: Comparator[T],
    ) -> None:
        cell = self.get_cell(db)
        if cell is None:
            return

        cell.untrack(node, comparator)

    @property
    def __wrapped__(self) -> QueryFn[T]:
        return self.fn
