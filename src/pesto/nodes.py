from abc import ABC, abstractmethod
from collections.abc import Callable
from operator import eq
from typing import TYPE_CHECKING, Any

from .cells import Cell, QueryCell, SourceCell
from .interfaces import INode, IQuery, ISource

if TYPE_CHECKING:
    from collections.abc import Callable

    from .data_bases import DataBase
    from .interfaces import Comparator, QueryFn


class Node[T, C: Cell[Any, Any] = Cell[T]](INode[T, C], ABC): ...


class Source[T](ISource[T, SourceCell[T]], Node[T, SourceCell[T]], ABC):
    @property
    @abstractmethod
    def default(self) -> T:
        raise NotImplementedError

    def cell(self, db: DataBase) -> SourceCell[T] | None:
        return db.source_data.get(self)

    def get(self, db: DataBase, comparator: Comparator[T] = eq) -> T:
        cell = self.cell(db)
        if cell is None:
            return SourceCell[T].new(self, db, comparator)
        return cell.get(db, comparator)

    def set(self, db: DataBase, value: T) -> None:
        cell = self.cell(db)
        if cell is None:
            SourceCell(self, db, value)
            return
        cell.set(db, value)


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


class Query[T](IQuery[T, QueryCell[T]], Node[T, QueryCell[T]]):
    fn: QueryFn[T]

    def __init__(self, fn: QueryFn[T]) -> None:
        self.fn = fn

    def cell(self, db: DataBase) -> QueryCell[T] | None:
        return db.query_data.get(self)

    def get(self, db: DataBase, comparator: Comparator[T] = eq) -> T:
        cell = self.cell(db)
        if cell is None:
            return QueryCell[T].new(self, db, comparator)
        return cell.get(db, comparator)

    def get_dependencies(self, db: DataBase) -> dict[Node[Any], Comparator[Any]]:
        cell = self.cell(db)
        if cell is None:
            return {}
        return {
            cell.owner(): comparator
            for cell, comparator in cell.get_dependencies().items()
        }

    def is_green(self, db: DataBase) -> bool:
        cell = self.cell(db)
        if cell is None:
            return False
        return cell.is_green(db)

    def __call__(self, db: DataBase, comparator: Comparator[T] = eq) -> T:
        return self.get(db, comparator)

    @property
    def __wrapped__(self) -> QueryFn[T]:
        return self.fn
