from collections.abc import Callable
from operator import eq
from typing import Any, NoReturn, overload

from pesto.sentinels import MISSING, MissingType

from .cells import QueryCell, SourceCell
from .data_bases import DataBase
from .interfaces import Comparator, INode, IQuery, IQueryCell, ISource, ISourceCell

type QueryFn[T] = Callable[[DataBase], T]


class CircularDependencyError(Exception):
    def __init__(self, query: IQuery[Any], chain: list[IQuery[Any]]) -> None:
        self.query = query
        self.chain = chain
        super().__init__(
            f"Circular dependency detected: {query} depends on itself via {chain}",
        )


class Source[T](ISource[T]):
    default_factory: Callable[[], T]

    @overload
    def __init__(self, default_factory: Callable[[], T]) -> None: ...
    @overload
    def __init__(self, *, default_value: T) -> None: ...

    def __init__(
        self,
        default_factory: Callable[[], T] | None = None,
        *,
        default_value: T | None = None,
    ) -> None:
        def lazy_boom() -> NoReturn:
            msg = "no default available on get"
            raise ValueError(msg)

        self.default_factory = (
            (lambda: default_value)
            if default_value is not None
            else default_factory or lazy_boom
        )

    def current_cell[D](self, db: DataBase, default: D = None) -> ISourceCell[T] | D:
        return db.source_data.get(self, default)

    def cell(self, db: DataBase) -> ISourceCell[T]:
        cell = self.current_cell(db)
        if cell is None:
            cell = SourceCell(db, self.default_factory(), self)
        return cell

    def get(self, db: DataBase, comparator: Callable[[T, T], bool] = eq) -> T:
        cell = self.cell(db)
        db.add_dep(self, comparator)
        return cell.get()

    def set(self, db: DataBase, value: T) -> None:
        if db.stack.peek_or() is not None:
            msg = "Cannot set source value while in a query context"
            raise RuntimeError(msg)

        cell = self.current_cell(db)
        if cell is None:
            cell = SourceCell(db, value, self)
        else:
            cell.update(db, value)


class Query[T](IQuery[T]):
    fn: QueryFn[T]

    def __init__(self, fn: QueryFn[T]) -> None:
        self.fn = fn

    def current_cell[D](self, db: DataBase, default: D = None) -> IQueryCell[T] | D:
        return db.query_data.get(self, default)

    def cell(self, db: DataBase) -> IQueryCell[T]:
        cell = self.current_cell(db)
        if cell is None or not self.is_green(db, cell):
            cell = self.recompute(db, cell)
        return cell

    def get(self, db: DataBase, comparator: Callable[[T, T], bool] = eq) -> T:
        active = [frame.query for frame in db.stack]
        if self in active:
            chain = [*reversed(active), self]
            raise CircularDependencyError(self, chain)

        cell = self.cell(db)
        db.add_dep(self, comparator)
        return cell.get()

    @overload
    def get_dependencies(self, db: DataBase) -> dict[INode[Any], Comparator[Any]]: ...
    @overload
    def get_dependencies[D](
        self,
        db: DataBase,
        default: D,
    ) -> dict[INode[Any], Comparator[Any]] | D: ...

    def get_dependencies[D](
        self,
        db: DataBase,
        default: D | MissingType = MISSING,
    ) -> dict[INode[Any], Comparator[Any]] | D:
        cell = self.current_cell(db)
        if cell is None:
            if default is MISSING:
                msg = "no cell registered, no dependencies can be found"
                raise ValueError(msg)
            return default
        return cell.get_dependencies()

    def is_green(self, db: DataBase, cell: IQueryCell[T]) -> bool:
        now = db.now()
        if cell.verified_at == now:
            return True

        for node, comparator in cell.get_dependencies().items():
            dep_cell = node.cell(db)

            changed_at = dep_cell.changed_at(comparator)
            if changed_at > cell.verified_at:
                return False

        cell.verified_at = now
        return True

    def recompute(self, db: DataBase, cell: IQueryCell[T] | None) -> IQueryCell[T]:
        if cell is not None:
            cell.reset_dependencies(db)

        db.stack.push(self)
        try:
            new = self.fn(db)
        except:
            db.query_data.pop(self, None)
            raise
        finally:
            frame = db.stack.pop()

        if cell is None:
            cell = QueryCell(db, new, self)
        else:
            cell.update(db, new)

        cell.add_dependencies(db, frame.dependencies)
        return cell
