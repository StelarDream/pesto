from typing import TYPE_CHECKING, Any
from weakref import WeakKeyDictionary, WeakSet

if TYPE_CHECKING:
    from pesto.data_bases import Comparator, DataBase, Dependencies, INode
    from pesto.nodes import Query


class ComparatorData:
    changed_at: int
    references: WeakSet[INode[Any, Any]]

    def __init__(self, now: int) -> None:
        self.changed_at = now
        self.references = WeakSet()

    @property
    def ref_count(self) -> int:
        return len(self.references)

    def add_ref(self, node: INode[Any, Any]) -> None:
        self.references.add(node)

    def drop_ref(self, node: INode[Any, Any]) -> None:
        self.references.discard(node)


class Cell[T]:
    value: T
    verified_at: int
    comparators: WeakKeyDictionary[Comparator[T], ComparatorData]

    def __init__(self, value: T, now: int) -> None:
        self.value = value
        self.verified_at = now
        self.comparators = WeakKeyDictionary()

    def changed_at(self, comparator: Comparator[T]) -> int:
        data = self.comparators.get(comparator)
        if data is None:
            return -1
        return data.changed_at

    def add_ref(self, node: INode[Any, Any], comparator: Comparator[T]) -> None:
        data = self.comparators.get(comparator)
        if data is None:
            data = ComparatorData(self.verified_at)
            self.comparators[comparator] = data
        data.add_ref(node)

    def drop_ref(self, node: INode[Any, Any], comparator: Comparator[T]) -> None:
        data = self.comparators.get(comparator)
        if data is None:
            return
        data.drop_ref(node)

    def update(self, now: int, new: T) -> None:
        for comparator, state in tuple(self.comparators.items()):
            if state.ref_count <= 0:
                self.comparators.pop(comparator, None)
            elif not comparator(self.value, new):
                state.changed_at = now

        self.verified_at = now
        self.value = new


class QueryCell[T](Cell[T]):
    dependencies: WeakKeyDictionary[INode[Any, Any], Comparator[T]]

    def __init__(self, value: T, now: int) -> None:
        super().__init__(value, now)
        self.dependencies = WeakKeyDictionary()

    def is_green(self, db: DataBase) -> bool:
        now = db.now()
        if self.verified_at == now:
            return True

        for node, comparator in tuple(self.dependencies.items()):
            changed_at = node.changed_at(db, comparator)
            if changed_at > self.verified_at:
                return False

        self.verified_at = now
        return True

    def add_dependencies(
        self,
        query: Query[T],
        db: DataBase,
        dependencies: Dependencies,
    ) -> None:
        for node, comparator in dependencies.items():
            self.dependencies[node] = comparator
            node.add_ref(db, query, comparator)

    def reset_dependencies(
        self,
        query: Query[T],
        db: DataBase,
    ) -> None:
        for node, comparator in tuple(self.dependencies.items()):
            node.drop_ref(db, query, comparator)

        self.dependencies.clear()
