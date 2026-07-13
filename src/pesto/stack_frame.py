import threading
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable

    from .comparators import Comparator
    from .data_bases import Node
    from .queries import Query


class StackFrame[T]:
    query: Query[T]
    dependencies: dict[Node[Any], Comparator[Any]]

    __slots__ = ("_lock", "dependencies", "query")

    def __init__(self, query: Query[T]) -> None:
        self.query = query
        self.dependencies = {}
        self._lock = threading.Lock()

    def add_dependency(self, query: Node[T], comparator: Comparator[T]) -> None:
        with self._lock:
            self.dependencies[query] = comparator

    def update_dependencies(
        self,
        dependencies: Iterable[tuple[Node[T], Comparator[T]]],
    ) -> None:
        with self._lock:
            self.dependencies.update(dependencies)

    def remove_dependency(self, query: Node[T]) -> None:
        with self._lock:
            self.dependencies.pop(query, None)

    def clear_dependencies(self) -> None:
        with self._lock:
            self.dependencies.clear()

    def has_dependency(self, query: Node[T]) -> bool:
        with self._lock:
            return query in self.dependencies

    def get_comparator(self, query: Node[T]) -> Comparator[T] | None:
        with self._lock:
            return self.dependencies.get(query)

    def get_dependencies(self) -> dict[Node[Any], Comparator[Any]]:
        with self._lock:
            return self.dependencies.copy()

    def __repr__(self) -> str:
        return f"<StackFrame query={self.query} dependencies_count={len(self.dependencies)}>"

    def __getstate__(self) -> tuple[Query[T], list[tuple[Node[Any], Comparator[Any]]]]:
        with self._lock:
            return self.query, list(self.dependencies.items())

    def __setstate__(
        self,
        state: tuple[Query[T], list[tuple[Node[Any], Comparator[Any]]]],
    ) -> None:
        self.query, dependencies = state
        self.dependencies = dict(dependencies)
        self._lock = threading.Lock()
