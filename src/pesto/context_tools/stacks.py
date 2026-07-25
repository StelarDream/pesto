from collections.abc import Callable
from contextlib import contextmanager
from contextvars import ContextVar
from itertools import islice
from typing import TYPE_CHECKING, Self

if TYPE_CHECKING:
    from collections.abc import Callable, Generator


class EmptyStackError(ValueError):
    def __init__(self, *args: object) -> None:
        if not args:
            args = ("no frame yet pushed",)
        super().__init__(*args)


class StackFrame[T]:
    value: T
    parent: Self | None

    __slots__ = ("parent", "value")

    def __init__(self, value: T, parent: Self | None = None) -> None:
        self.value = value
        self.parent = parent

    @property
    def root(self) -> Self:
        frame = self
        while frame.parent is not None:
            frame = frame.parent
        return frame

    def __repr__(self) -> str:
        return f"{type(self).__name__}(value={self.value})"

    def __getstate__(self) -> list[T]:
        return [frame.value for frame in self]

    def __setstate__(self, state: list[T]) -> None:
        self.value = state[0]
        parent = None
        for value in islice(reversed(state), len(state) - 1):
            parent = type(self)(value, parent)
        self.parent = parent

    def __iter__(self) -> Generator[StackFrame[T]]:
        frame: StackFrame[T] | None = self
        while frame is not None:
            yield frame
            frame = frame.parent

    def __contains__(self, item: T) -> bool:
        frame = self
        while frame is not None:
            if frame.value == item:
                return True
            frame = frame.parent
        return False


class ContextScopedStack[**P, T]:
    context_frame: ContextVar[StackFrame[T] | None]
    fn: Callable[P, T]

    def __init__(self, fn: Callable[..., T]) -> None:
        self.fn = fn
        self.context_frame = ContextVar(
            f"{type(self).__name__}.context_frame",
            default=None,
        )

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(fn={self.fn!r}, frame={self.context_frame.get()!r})"
        )

    def peek(self) -> T:
        frame = self.context_frame.get()
        if frame is None:
            raise EmptyStackError
        return frame.value

    def pop(self) -> T:
        frame = self.context_frame.get()
        if frame is None:
            raise EmptyStackError
        self.context_frame.set(frame.parent)
        return frame.value

    def push(self, *args: P.args, **kwargs: P.kwargs) -> T:
        value = self.fn(*args, **kwargs)
        frame = StackFrame(value, self.context_frame.get())
        self.context_frame.set(frame)
        return value

    @contextmanager
    def scope(self, *args: P.args, **kwargs: P.kwargs) -> Generator[T]:
        value = self.push(*args, **kwargs)
        try:
            yield value
        finally:
            self.pop()

    def peek_or[D](self, default: D) -> T | D:
        frame = self.context_frame.get()
        if frame is None:
            return default
        return frame.value

    def pop_or[D](self, default: D) -> T | D:
        frame = self.context_frame.get()
        if frame is None:
            return default
        self.context_frame.set(frame.parent)
        return frame.value

    def peek_or_run[D](self, default_factory: Callable[[], D]) -> T | D:
        frame = self.context_frame.get()
        if frame is None:
            return default_factory()
        return frame.value

    def pop_or_run[D](self, default_factory: Callable[[], D]) -> T | D:
        frame = self.context_frame.get()
        if frame is None:
            return default_factory()
        self.context_frame.set(frame.parent)
        return frame.value

    def __getstate__(self) -> tuple[list[T], Callable[P, T]]:
        frame = self.context_frame.get()
        if frame is None:
            return [], self.fn

        return frame.__getstate__(), self.fn

    def __setstate__(self, state: tuple[list[T], Callable[P, T]]) -> None:
        value, self.fn = state
        frame: StackFrame[T] | None = None
        if value:
            frame = StackFrame.__new__(StackFrame)
            frame.__setstate__(value)

        self.context_frame = ContextVar(
            f"{type(self).__name__}.context_frame",
            default=None,
        )
        self.context_frame.set(frame)

    def __iter__(self) -> Generator[T]:
        current = self.context_frame.get()
        if current is None:
            return
        for frame in current:
            yield frame.value

    def __contains__(self, item: T) -> bool:
        frame = self.context_frame.get()
        if frame is None:
            return False

        return item in frame
