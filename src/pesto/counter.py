import threading
from collections.abc import Iterator, Sized
from typing import Self


class Counter(Iterator[int], Sized):
    __slots__ = ("_count", "_lock")

    def __init__(self, start: int = 0) -> None:
        self._count = start
        self._lock = threading.Lock()

    def now(self) -> int:
        with self._lock:
            return self._count

    def __iter__(self) -> Self:
        return self

    def __len__(self) -> int:
        return self.now()

    def __next__(self) -> int:
        with self._lock:
            self._count += 1
            return self._count
