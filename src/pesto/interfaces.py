from collections.abc import Callable
from operator import eq
from typing import TYPE_CHECKING, Any, Protocol, overload

from ._types import MapLike

if TYPE_CHECKING:
    from .data_bases import DataBase

type Dependencies = MapLike[INode[Any], Comparator[Any]]

# --- Comparators ---

type Comparator[T] = Callable[[T, T], bool]


# --- Cells ---


class ICell[T](Protocol):
    verified_at: int

    def get(self) -> T: ...

    def add_ref(self, query: IQuery[Any], comparator: Comparator[T]) -> None: ...
    def drop_ref(self, query: IQuery[Any], comparator: Comparator[T]) -> None: ...

    def changed_at(self, comparator: Comparator[T]) -> int: ...

    def update(self, db: DataBase, new_value: T) -> None: ...


class ISourceCell[T](ICell[T], Protocol):
    def get_source(self) -> ISource[T]: ...


class IQueryCell[T](ICell[T], Protocol):
    def get_query(self) -> IQuery[T]: ...

    def add_dependencies(self, db: DataBase, dependencies: Dependencies) -> None: ...
    def reset_dependencies(self, db: DataBase) -> None: ...
    def get_dependencies(self) -> dict[INode[Any], Comparator[Any]]: ...


# --- Nodes ---


class INode[T](Protocol):
    def current_cell[D](self, db: DataBase, default: D = None) -> ICell[T] | D: ...
    def cell(self, db: DataBase) -> ICell[T]: ...

    def get(self, db: DataBase, comparator: Comparator[T] = eq) -> T: ...


class ISource[T](INode[T], Protocol):
    def current_cell[D](
        self,
        db: DataBase,
        default: D = None,
    ) -> ISourceCell[T] | D: ...
    def cell(self, db: DataBase) -> ISourceCell[T]: ...

    def set(self, db: DataBase, value: T) -> None: ...


class IQuery[T](INode[T], Protocol):
    def current_cell[D](self, db: DataBase, default: D = None) -> IQueryCell[T] | D: ...
    def cell(self, db: DataBase) -> IQueryCell[T]: ...

    @overload
    def get_dependencies(self, db: DataBase) -> dict[INode[Any], Comparator[Any]]: ...
    @overload
    def get_dependencies[D](
        self,
        db: DataBase,
        default: D,
    ) -> dict[INode[Any], Comparator[Any]] | D: ...
