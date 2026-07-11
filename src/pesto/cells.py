from typing import TYPE_CHECKING, Any

from .comparators import Comparator, ComparatorState

if TYPE_CHECKING:
    from .data_bases import DataBase


class Cell[T]:
    value: T
    verified_at: int
    comparator_states: dict[Comparator[Any], ComparatorState]

    def __init__(self, db: DataBase) -> None:
        self.verified_at = db.now()
        self.comparator_states = {}

    def add_ref(self, query_cell: QueryCell[Any], comparator: Comparator[T]) -> None:
        state = self.comparator_states.setdefault(
            comparator,
            ComparatorState(self.verified_at),
        )
        state.references.add(query_cell)

    def drop_ref(self, query_cell: QueryCell[Any], comparator: Comparator[T]) -> None:
        state = self.comparator_states.get(comparator)
        if state is None:
            return

        state.references.discard(query_cell)

    def verify(self, old: T, new: T, revision: int) -> None:
        self.comparator_states = {
            comparator: state
            for comparator, state in self.comparator_states.items()
            if state.ref_count > 0
        }

        for comparator, state in self.comparator_states.items():
            if not comparator(old, new):
                state.changed_at = revision

        self.verified_at = revision

    def is_up_to_date(self) -> bool:
        return True


class QueryCell[T](Cell[T]):
    dependencies: dict[Cell[Any], Comparator[Any]]

    def __init__(self, db: DataBase) -> None:
        super().__init__(db)
        self.dependencies = {}

    def add_dep[V](self, depends_on: Cell[V], comparator: Comparator[V]) -> None:
        self.dependencies[depends_on] = comparator
        depends_on.add_ref(self, comparator)

    def reset_deps(self) -> None:
        for depends_on, comparator in self.dependencies.items():
            depends_on.drop_ref(self, comparator)

        self.dependencies.clear()

    def is_up_to_date(self) -> bool:

        return all(
            depends_on.is_up_to_date()
            and depends_on.comparator_states[comparator].changed_at <= self.verified_at
            for depends_on, comparator in self.dependencies.items()
        )
