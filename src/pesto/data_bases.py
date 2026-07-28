from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any
from weakref import WeakKeyDictionary

from pesto.context_tools.counter import ContextCounter
from pesto.context_tools.stacks import ContextScopedStack

type Comparator[T] = Callable[[T, T], bool]
type Dependencies = dict[INode[Any, Any], Comparator[Any]]


# --- expected contract ---
class INode[T, C](ABC):
    @abstractmethod
    def changed_at(self, db: DataBase, comparator: Comparator[T]) -> int:
        raise NotImplementedError

    @abstractmethod
    def add_ref(
        self,
        db: DataBase,
        node: INode[Any, Any],
        comparator: Comparator[T],
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def drop_ref(
        self,
        db: DataBase,
        node: INode[Any, Any],
        comparator: Comparator[T],
    ) -> None:
        raise NotImplementedError


class DBStackFrame:
    active: INode[Any, Any]
    dependencies: Dependencies

    __slots__ = ("active", "dependencies")

    def __init__(self, query: INode[Any, Any]) -> None:
        self.active = query
        self.dependencies = {}


class DataBase:
    node_data: WeakKeyDictionary[INode[Any, Any], Any]
    stack: ContextScopedStack[[INode[Any, Any]], DBStackFrame]
    revisions: ContextCounter

    __slots__ = ("node_data", "revisions", "stack")

    def __init__(self) -> None:
        self.node_data = WeakKeyDictionary()
        self.stack = ContextScopedStack(DBStackFrame)
        self.revisions = ContextCounter()

    def get_data[C](self, node: INode[Any, C]) -> C | None:
        return self.node_data.get(node, None)

    def set_data[C](self, node: INode[Any, C], data: C) -> None:
        self.node_data[node] = data

    def add_dep[T](self, dep: INode[T, Any], comparator: Comparator[T]) -> None:
        stack = self.stack.peek_or(None)
        if stack is None:
            return
        stack.dependencies[dep] = comparator

    def drop_dep(self, dep: INode[Any, Any]) -> None:
        stack = self.stack.peek_or(None)
        if stack is None:
            return
        stack.dependencies.pop(dep, None)

    def update(self) -> int:
        return self.revisions.increment(1)

    def now(self) -> int:
        return self.revisions.now()
