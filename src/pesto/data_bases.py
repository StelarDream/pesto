from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any
from weakref import WeakKeyDictionary

from .context_tools import ContextCounter, ContextScopedStack

type Comparator[T] = Callable[[T, T], bool]
type Dependencies = dict[INode[Any], Comparator[Any]]


# --- expected contract ---
class INode[T](ABC):
    __slots__ = ()

    @abstractmethod
    def changed_at(self, db: DataBase, comparator: Comparator[T]) -> int:
        raise NotImplementedError

    @abstractmethod
    def track(
        self,
        db: DataBase,
        node: INode[Any],
        comparator: Comparator[T],
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def untrack(
        self,
        db: DataBase,
        node: INode[Any],
        comparator: Comparator[T],
    ) -> None:
        raise NotImplementedError


class DBStackFrame:
    active: INode[Any]
    dependencies: Dependencies

    __slots__ = ("active", "dependencies")

    def __init__(self, query: INode[Any]) -> None:
        self.active = query
        self.dependencies = {}

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(active={self.active!r}, deps={self.dependencies!r})"
        )


class DataBase:
    node_data: WeakKeyDictionary[Any, Any]
    stack: ContextScopedStack[[INode[Any]], DBStackFrame]
    revisions: ContextCounter

    __slots__ = ("node_data", "revisions", "stack")

    def __init__(self) -> None:
        self.node_data = WeakKeyDictionary()
        self.stack = ContextScopedStack(DBStackFrame)
        self.revisions = ContextCounter()

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}("
            f"revision={self.revisions.now()!r}, "
            f"stack={self.stack!r}, "
            f"data={self.node_data!r}"
            ")"
        )

    def add_dep[T](self, dep: INode[T], comparator: Comparator[T]) -> None:
        stack = self.stack.peek_or(None)
        if stack is None:
            return
        stack.dependencies[dep] = comparator

    def drop_dep(self, dep: INode[Any]) -> None:
        stack = self.stack.peek_or(None)
        if stack is None:
            return
        stack.dependencies.pop(dep, None)

    def update(self) -> int:
        return self.revisions.increment(1)

    def now(self) -> int:
        return self.revisions.now()
