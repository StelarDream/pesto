from contextvars import ContextVar
from operator import eq
from typing import TYPE_CHECKING, Any
from weakref import WeakKeyDictionary

from .cells import QueryCell, SourceCell
from .stacks import ContextStack

if TYPE_CHECKING:
    from .cells import Cell
    from .comparators import Comparator
    from .queries import Query
    from .sources import Source

type Node[T] = Source[T] | Query[T]


class DataBase:
    source_data: WeakKeyDictionary[Source[Any], SourceCell[Any]]
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

    def record_dependencies[V](
        self,
        cell: Cell[V, Any],
        comparator: Comparator[V],
    ) -> None:
        query = self.stack.peek()
        if query is not None:
            query_cell = self.query_data[query]
            query_cell.add_dep(cell, comparator)

    def get_source[T](self, source: Source[T], comparator: Comparator[T] = eq) -> T:
        cell = self.source_data.get(source)

        if cell is None:
            cell = SourceCell(self, source, source.get_initial_value())
            self.source_data[source] = cell

        self.record_dependencies(cell, comparator)

        return cell.value

    def set_source[T](self, source: Source[T], value: T) -> None:
        cell = self.source_data.get(source)
        if cell is None:
            cell = SourceCell(self, source, value)
            self.source_data[source] = cell
            return

        old = cell.value
        cell.value = value
        revision = self.update()
        cell.verify(old, value, revision)

    def get_query[T](self, query: Query[T], comparator: Comparator[T] = eq) -> T:
        query_cell = self.query_data.get(query)

        if query_cell is None:
            query_cell = QueryCell(self, query)
            self.query_data[query] = query_cell
            query_cell.value = self.run(query)
        else:
            self.refresh(query_cell)

        self.record_dependencies(query_cell, comparator)

        return query_cell.value

    def refresh(self, query_cell: QueryCell[Any]) -> None:
        """Ensure query_cell's value and verified_at reflect the current revision.

        Recomputes query_cell if (and only if) some dependency's value may have
        changed since query_cell was last verified. Dependencies that are
        themselves QueryCells are refreshed first (bottom-up), so a dependency
        being stale never by itself forces a recompute here -- only an actual
        change to its verified output does (early cutoff).
        """
        if query_cell.verified_at == self.now():
            return

        if self._deps_unchanged(query_cell):
            query_cell.verified_at = self.now()
            return

        query = query_cell.represents()
        if query is None:
            return

        query_cell.reset_deps()
        old = query_cell.value
        query_cell.value = self.run(query)
        query_cell.verify(old, query_cell.value, self.now())

    def _deps_unchanged(self, query_cell: QueryCell[Any]) -> bool:
        for depends_on, comparator in query_cell.dependencies.items():
            if isinstance(depends_on, QueryCell):
                self.refresh(depends_on)

            if (
                depends_on.comparator_states[comparator].changed_at
                > query_cell.verified_at
            ):
                return False

        return True

    def run[T](self, query: Query[T]) -> T:
        self.stack.push(query)
        try:
            return query.fn(self)
        except BaseException:
            self.query_data.pop(query, None)
            raise
        finally:
            self.stack.pop()

    def dependencies_of(self, query: Query[Any]) -> list[Node[Any]]:
        query_cell = self.query_data.get(query)
        if query_cell is None:
            return []

        nodes = (dep.represents() for dep in tuple(query_cell.dependencies))
        return [node for node in nodes if node is not None]
