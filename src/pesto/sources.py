from typing import TYPE_CHECKING

from .cells import Cell
from .sentinels import MISSING

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import overload


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

    if TYPE_CHECKING:
        # Overloads for type checkers (can be collapsed)
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

    @property
    def cell(self) -> type[Cell[T]]:
        return Cell
