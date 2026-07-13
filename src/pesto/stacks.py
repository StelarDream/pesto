from contextvars import ContextVar
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Generator


class StackFrame[T]:
    value: T
    parent: StackFrame[T] | None

    __slots__ = ("parent", "value")

    def __init__(self, value: T, parent: StackFrame[T] | None = None) -> None:
        self.value = value
        self.parent = parent

    @property
    def root(self) -> StackFrame[T]:
        frame = self
        while frame.parent is not None:
            frame = frame.parent
        return frame

    def pop(self) -> StackFrame[T] | None:
        return self.parent

    def push(self, value: T) -> StackFrame[T]:
        return StackFrame(value, self)

    def __repr__(self) -> str:
        return f"StackFrame(value={self.value})"

    def __getstate__(self) -> list[T]:
        out: list[T] = []
        f = self
        while f is not None:
            out.append(f.value)
            f = f.parent
        return out[::-1]

    def __setstate__(self, state: list[T]) -> None:
        parent: StackFrame[T] | None = None
        for value in state[:-1]:
            parent = StackFrame(value, parent)

        self.value = state[-1]
        self.parent = parent

    def __iter__(self) -> Generator[T]:
        frame: StackFrame[T] | None = self
        while frame is not None:
            yield frame.value
            frame = frame.parent

    def __contains__(self, item: T) -> bool:
        frame = self
        while frame is not None:
            if frame.value == item:
                return True
            frame = frame.parent
        return False


class ContextStack[T]:
    context_stack: ContextVar[StackFrame[T] | None]

    __slots__ = ("context_stack",)

    def __init__(self) -> None:
        self.context_stack = ContextVar(
            f"<Context: for {type(self).__name__}:{id(self)}>",
            default=None,
        )

    def peek[D](self, default: D = None) -> T | D:
        frame = self.context_stack.get()
        if frame is None:
            return default

        return frame.value

    def root[D](self, default: D = None) -> T | D:
        frame = self.context_stack.get()
        if frame is None:
            return default

        return frame.root.value

    def pop[D](self, default: D = None) -> T | D:
        frame = self.context_stack.get()
        if frame is None:
            return default

        parent = frame.pop()
        self.context_stack.set(parent)

        if parent is None:
            return default

        return parent.value

    def push(self, value: T) -> None:
        frame = self.context_stack.get()
        new = frame.push(value) if frame is not None else StackFrame(value)

        self.context_stack.set(new)

    def __getstate__(self) -> list[T]:
        frame = self.context_stack.get()
        if frame is None:
            return []

        return frame.__getstate__()

    def __setstate__(self, state: list[T]) -> None:
        frame: StackFrame[T] | None = None
        if state:
            frame = StackFrame.__new__(StackFrame)
            frame.__setstate__(state)

        self.context_stack = ContextVar(
            f"<Context: for {type(self).__name__}:{id(self)}>",
            default=None,
        )
        self.context_stack.set(frame)

    def __iter__(self) -> Generator[T]:
        frame = self.context_stack.get()
        if frame is None:
            return
        yield from frame

    def __contains__(self, item: T) -> bool:
        frame = self.context_stack.get()
        if frame is None:
            return False

        return item in frame
