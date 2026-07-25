from collections.abc import Iterator, Sized
from contextvars import ContextVar
from typing import Self


class ContextCounter(Iterator[int], Sized):
    count: ContextVar[int]

    def __init__(self, start: int = 0) -> None:
        self.count = ContextVar(f"{type(self)}.context_int", default=start)

    def now(self) -> int:
        return self.count.get()

    def increment(self, amount: int = 1) -> int:
        count = self.count.get() + amount
        self.count.set(count)
        return count

    def __iter__(self) -> Self:
        return self

    def __len__(self) -> int:
        return self.count.get()

    def __next__(self) -> int:
        count = self.count.get() + 1
        self.count.set(count)
        return count
