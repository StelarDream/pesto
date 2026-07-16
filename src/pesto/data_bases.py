from typing import TYPE_CHECKING, Any
from weakref import WeakKeyDictionary

from .context_tools import ContextCounter, ContextStack

if TYPE_CHECKING:
    from .interfaces import Comparator, INode, IQuery, IQueryCell, ISource, ISourceCell


class DBStackFrame[T]:
    query: IQuery[T]
    dependencies: dict[INode[Any], Comparator[T]]

    def __init__(self, query: IQuery[T]) -> None:
        self.query = query
        self.dependencies = {}

    def add_dep(self, query: INode[Any], comparator: Comparator[Any]) -> None:
        self.dependencies[query] = comparator


class DataBase:
    source_data: WeakKeyDictionary[ISource[Any], ISourceCell[Any]]
    query_data: WeakKeyDictionary[IQuery[Any], IQueryCell[Any]]
    revision: ContextCounter
    stack: ContextStack[[IQuery[Any]], DBStackFrame[Any]]

    def __init__(self) -> None:
        self.source_data = WeakKeyDictionary()
        self.query_data = WeakKeyDictionary()
        self.revision = ContextCounter()
        self.stack = ContextStack(DBStackFrame)

    def now(self) -> int:
        return self.revision.now()

    def update(self) -> int:
        return self.revision.increment()

    def add_dep(self, query: INode[Any], comparator: Comparator[Any]) -> None:
        frame = self.stack.peek_or()
        if frame is None:
            return
        frame.add_dep(query, comparator)
