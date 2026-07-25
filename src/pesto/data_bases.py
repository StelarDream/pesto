from typing import TYPE_CHECKING, Any
from weakref import WeakKeyDictionary

from .context_tools import ContextCounter, ContextScopedStack

if TYPE_CHECKING:
    from .interfaces import Comparator, ICell, IQuery, ISource


class DBStackFrame[T]:
    query: IQuery[T]
    dependencies: dict[ICell[Any, Any], Comparator[T]]

    def __init__(self, query: IQuery[T]) -> None:
        self.query = query
        self.dependencies = {}

    def add_dep(self, cell: ICell[Any], comparator: Comparator[T]) -> None:
        self.dependencies[cell] = comparator

    def drop_dep(self, cell: ICell[T]) -> None:
        self.dependencies.pop(cell, None)


class DataBase:
    source_data: WeakKeyDictionary[ISource[Any, Any], Any]
    query_data: WeakKeyDictionary[IQuery[Any, Any], Any]
    revision: ContextCounter
    stack: ContextScopedStack[[IQuery[Any, Any]], DBStackFrame[Any]]

    def __init__(self) -> None:
        self.source_data = WeakKeyDictionary()
        self.query_data = WeakKeyDictionary()
        self.revision = ContextCounter()
        self.stack = ContextScopedStack(DBStackFrame)

    def now(self) -> int:
        return self.revision.now()

    def update(self) -> int:
        return self.revision.increment()

    def add_dep(self, cell: ICell[Any, Any], comparator: Comparator[Any]) -> None:
        frame = self.stack.peek_or(None)
        if frame is None:
            return
        frame.add_dep(cell, comparator)

    def drop_ref(self, cell: ICell[Any, Any]) -> None:
        frame = self.stack.peek_or(None)
        if frame is None:
            return
        frame.drop_dep(cell)
