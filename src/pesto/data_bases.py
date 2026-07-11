from contextvars import ContextVar
from operator import eq
from typing import TYPE_CHECKING, Any
from weakref import WeakKeyDictionary

from .stacks import ContextStack

if TYPE_CHECKING:
    from .cells import Cell, QueryCell
    from .comparators import Comparator
    from .queries import Query
    from .sources import Source


class DataBase:
    source_data: WeakKeyDictionary[Source[Any], Cell[Any]]
    query_data: WeakKeyDictionary[Query[Any], QueryCell[Any]]
    revision: ContextVar[int]
    stack: ContextStack[Query[Any]]

    def __init__(self) -> None:
        self.source_data = WeakKeyDictionary()
        self.query_data = WeakKeyDictionary()
        self.revision = ContextVar(
            f"<Context[int] for {type(self).__name__}:{id(self)}>",
            default=0,
        )
        self.stack = ContextStack()

    def now(self) -> int:
        return self.revision.get()

    def update(self) -> int:
        new_revision = self.revision.get() + 1
        self.revision.set(new_revision)
        return new_revision

    def record_dependencies[V](self, cell: Cell[V], comparator: Comparator[V]) -> None:
        query = self.stack.peek()
        if query is not None:
            query_cell = self.query_data[query]
            query_cell.add_dep(cell, comparator)

    def get_source[T](self, source: Source[T], comparator: Comparator[T] = eq) -> T:
        cell = self.source_data.get(source)

        if cell is None:
            cell = source.cell(self)
            cell.value = source.get_initial_value()
            self.source_data[source] = cell

        self.record_dependencies(cell, comparator)

        return cell.value

    def set_source[T](self, source: Source[T], value: T) -> None:
        cell = self.source_data.get(source)
        if cell is None:
            cell = source.cell(self)
            cell.value = value
            self.source_data[source] = cell
            return

        old = cell.value
        cell.value = value
        revision = self.update()
        cell.verify(old, value, revision)

    def get_query[T](self, query: Query[T], comparator: Comparator[T] = eq) -> T:
        query_cell = self.query_data.get(query)

        if query_cell is None:
            query_cell = query.cell(self)
            query_cell.value = self.run(query)
            self.query_data[query] = query_cell
        elif not query_cell.is_up_to_date():
            query_cell.reset_deps()
            old = query_cell.value
            query_cell.value = self.run(query)
            query_cell.verify(old, query_cell.value, self.now())

        self.record_dependencies(query_cell, comparator)

        return query_cell.value

    def run[T](self, query: Query[T]) -> T:
        self.stack.push(query)
        try:
            return query.fn(self)
        except BaseException:
            self.query_data.pop(query, None)
            raise
        finally:
            self.stack.pop()
