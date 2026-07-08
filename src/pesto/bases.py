from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Self

from .data_bases import DataBase
from .sentinels import MISSING

if TYPE_CHECKING:
    from typing import overload

    from .data_bases import DataBase


class Node[T](ABC):
    if TYPE_CHECKING:
        # Overloads for type checkers (can be collapsed)
        @overload
        def get(self, db: DataBase) -> T: ...
        @overload
        def get[D](self, db: DataBase, default: D) -> T | D: ...

    @abstractmethod
    def get[D](self, db: DataBase, default: D = MISSING) -> T | D:
        raise NotImplementedError

    def __getitem__(self, key: DataBase) -> T:
        return self.get(key)

    @abstractmethod
    def remove(self, db: DataBase) -> Self:
        raise NotImplementedError
