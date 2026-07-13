from contextvars import ContextVar
from operator import eq
from typing import TYPE_CHECKING, Any
from weakref import WeakKeyDictionary

from .cells import QueryCell, SourceCell
from .query_frame import QueryFrame
from .sources import Source
from .stacks import ContextStack

if TYPE_CHECKING:
    from .comparators import Comparator
    from .queries import Query

type Node[T] = Query[T] | Source[T]


class CircularDependencyError(Exception):
    def __init__(self, query: Query[Any], chain: list[Query[Any]]) -> None:
        self.query = query
        self.chain = chain
        super().__init__(f"Circular dependency detected: {query} depends on itself via {chain}")


class DataBase:
    source_data: WeakKeyDictionary[Source[Any], SourceCell[Any]]
    query_data: WeakKeyDictionary[Query[Any], QueryCell[Any]]
    revision: ContextVar[int]
    stack: ContextStack[QueryFrame[Any]]

    def __init__(self) -> None:
        self.source_data = WeakKeyDictionary()
        self.query_data = WeakKeyDictionary()
        self.revision = ContextVar("revision", default=0)
        self.stack = ContextStack()

    def now(self) -> int:
        return self.revision.get()

    def increment(self) -> int:
        new = self.revision.get() + 1
        self.revision.set(new)
        return new

    def add_dependency[T](
        self,
        node: Node[T],
        comparator: Comparator[T],
    ) -> None:
        frame = self.stack.peek()
        if frame is not None:
            frame.add_dependency(node, comparator)

    def get_source[T](
        self,
        source: Source[T],
        comparator: Comparator[T] = eq,
    ) -> T:
        cell = source.ensure_cell(self)

        self.add_dependency(source, comparator)

        return cell.value

    def set_source[T](
        self,
        source: Source[T],
        value: T,
    ) -> None:
        if self.stack.peek() is not None:
            msg = "Cannot set source value while in a query context"
            raise RuntimeError(msg)

        now = self.increment()

        cell = self.source_data.get(source)

        if cell is None:
            cell = SourceCell(source, value, now)
            self.source_data[source] = cell
        else:
            cell.update(value, now)

    def dependencies_of(self, query: Query[Any]) -> dict[Node[Any], Comparator[Any]]:
        query_cell = self.query_data.get(query)
        if query_cell is None:
            return {}

        return dict(query_cell.dependencies)

    def get_query[T](self, query: Query[T], comparator: Comparator[T] = eq) -> T:
        active = [frame.query for frame in self.stack]
        if query in active:
            chain = [*reversed(active), query]
            raise CircularDependencyError(query, chain)

        cell = query.ensure_cell(self)
        self.add_dependency(query, comparator)
        return cell.value

    def recompute[T](self, query: Query[T]) -> QueryCell[T]:
        cell = self.query_data.get(query)
        if cell is not None:
            cell.reset_dependencies(self)

        frame = QueryFrame(query)
        self.stack.push(frame)
        try:
            new = query.fn(self)
        except BaseException:
            self.query_data.pop(query, None)
            raise
        finally:
            self.stack.pop()

        now = self.now()
        if cell is None:
            cell = QueryCell(query, new, now)
            self.query_data[query] = cell
        else:
            cell.update(new, now)

        cell.add_dependencies(self, frame.get_dependencies())
        return cell

    def is_green(self, cell: QueryCell[Any]) -> bool:
        now = self.now()
        if cell.verified_at == now:
            return True

        for node, comparator in cell.dependencies.items():
            dep_cell = node.ensure_cell(self)  # recomputes if stale; no-op for sources

            state = dep_cell.comparators.get(comparator)
            changed_at = state.changed_at if state is not None else dep_cell.verified_at
            if changed_at > cell.verified_at:
                return False

        cell.verified_at = now
        return True
