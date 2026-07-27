from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from .data_bases import DataBase
    from .types import Comparator, Dependencies


class INode[T, C: ICell[Any, Any] = ICell[T]](Protocol):
    def cell(self, db: DataBase) -> C | None:
        raise NotImplementedError

    def get(self, db: DataBase, comparator: Comparator[T]) -> T:
        raise NotImplementedError


class ISource[T, C: ISourceCell[Any, Any] = ISourceCell[T]](INode[T, C], Protocol):
    def set(self, db: DataBase, value: T) -> None:
        raise NotImplementedError


class IQuery[T, C: IQueryCell[Any, Any] = IQueryCell[T]](INode[T, C], Protocol): ...


class ICell[T, O: INode[Any, Any] = INode[T]](Protocol):
    def owner(self) -> O:
        raise NotImplementedError

    @classmethod
    def new(cls, owner: O, db: DataBase, comparator: Comparator[T]) -> T:
        raise NotImplementedError

    def get(self, db: DataBase, comparator: Comparator[T]) -> T:
        raise NotImplementedError

    def refresh(self, db: DataBase) -> T:
        raise NotImplementedError

    def add_ref(self, query: IQuery[Any, Any], comparator: Comparator[Any]) -> None:
        raise NotImplementedError

    def drop_ref(self, query: IQuery[Any, Any], comparator: Comparator[Any]) -> None:
        raise NotImplementedError

    def changed_at(self, comparator: Comparator[T]) -> int:
        raise NotImplementedError

    def verify_at(self, revision: int, new: T) -> None:
        raise NotImplementedError


class ISourceCell[T, O: ISource[Any, Any] = ISource[T]](ICell[T, O], Protocol): ...


class IQueryCell[T, O: IQuery[Any, Any] = IQuery[T]](ICell[T, O], Protocol):
    def add_dependencies(self, dependencies: Dependencies) -> None:
        raise NotImplementedError

    def reset_dependencies(self) -> None:
        raise NotImplementedError
