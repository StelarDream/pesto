from collections.abc import Callable
from operator import eq
from typing import TYPE_CHECKING, overload

from .cells import SourceCell
from .sentinels import MISSING

if TYPE_CHECKING:
    from collections.abc import Callable

    from .comparators import Comparator
    from .data_bases import DataBase


class Source[T]:
    initial_value_factory: Callable[[], T] | None

    __slots__ = ("__weakref__", "initial_value_factory")

    def __init__(self, initial_value_factory: Callable[[], T] | None = None) -> None:
        """Store the initial_value as a factory, not a value.

        A plain value would be shared and mutated across every DB instance
        that falls back to this initial_value; a factory produces a fresh one each time.
        """
        self.initial_value_factory = initial_value_factory

    # --- Initial Value ---

    def set_initial_value_factory(self, initial_value_factory: Callable[[], T]) -> None:
        """Set a initial value factory, not a value"""
        self.initial_value_factory = initial_value_factory

    def set_initial_value(self, initial_value: T) -> None:
        """Set a fixed initial value, avoid giving a mutable"""
        self.initial_value_factory = lambda: initial_value

    @overload
    def get_initial_value(self) -> T: ...
    @overload
    def get_initial_value[D](self, default: D) -> T | D: ...

    def get_initial_value[D](self, default: D = MISSING) -> T | D:
        """Return a fresh initial value value, or `default` if none is set (and raises if no default is given)."""
        if self.initial_value_factory is None:
            if default is MISSING:
                msg = "no initial_value found"
                raise AttributeError(msg)
            return default

        return self.initial_value_factory()

    # --- DataBase entries management ---

    def get(self, db: DataBase, comparator: Comparator[T] = eq) -> T:
        return db.get_source(self, comparator)

    def set(self, db: DataBase, value: T) -> None:
        return db.set_source(self, value)

    def resolve(self, db: DataBase) -> SourceCell[T] | None:
        return db.source_data.get(self)

    def ensure_cell(self, db: DataBase) -> SourceCell[T]:
        cell = db.source_data.get(self)
        if cell is None:
            cell = SourceCell(self, self.get_initial_value(), db.now())
            db.source_data[self] = cell
        return cell

    # --- Convenience methods ---

    def __repr__(self) -> str:
        return f"<Source {self.__class__.__name__}>"

    def __getstate__(self) -> Callable[[], T] | None:
        return self.initial_value_factory

    def __setstate__(self, state: Callable[[], T] | None) -> None:
        self.initial_value_factory = state
