from abc import ABC, abstractmethod
from operator import eq
from typing import TYPE_CHECKING, Any

from .cells import Cell
from .data_bases import Comparator, DataBase, INode

if TYPE_CHECKING:
    from collections.abc import Callable


class Source[T](INode[T], ABC):
    __slots__ = ("__weakref__",)

    def get_cell(self, db: DataBase) -> Cell[T] | None:
        return db.node_data.get(self)

    @property
    @abstractmethod
    def default(self) -> T:
        raise NotImplementedError

    def get(self, db: DataBase, comparator: Comparator[T] = eq) -> T:
        cell = self.get_cell(db)
        if cell is None:
            value = self.default
            db.node_data[self] = Cell(value, db.now())
        else:
            value = cell.value
        db.add_dep(self, comparator)
        return value

    def set(self, db: DataBase, value: T) -> None:
        cell = self.get_cell(db)
        if cell is None:
            db.node_data[self] = Cell(value, db.now())
            return

        now = db.update()
        cell.update(now, value)
        return

    def changed_at(self, db: DataBase, comparator: Comparator[T]) -> int:
        cell = self.get_cell(db)
        if cell is None:
            now = db.now()
            db.node_data[self] = Cell(self.default, now)
            return now

        return cell.changed_at(comparator)

    def track(
        self,
        db: DataBase,
        node: INode[Any],
        comparator: Comparator[T],
    ) -> None:
        cell = self.get_cell(db)
        if cell is None:
            cell = Cell(self.default, db.now())
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


class DefaultFactorySource[T](Source[T]):
    default_factory: Callable[[], T]

    __slots__ = ("default_factory",)

    def __init__(self, default_factory: Callable[[], T]) -> None:
        self.default_factory = default_factory

    @property
    def default(self) -> T:
        return self.default_factory()


class DefaultValueSource[T](Source[T]):
    default_value: T

    __slots__ = ("default_value",)

    def __init__(self, default_value: T) -> None:
        self.default_value = default_value

    @property
    def default(self) -> T:
        return self.default_value
