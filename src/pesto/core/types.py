from collections.abc import Callable
from typing import Any

from pesto._types import MapLike

from .data_bases import DataBase
from .interfaces import ICell

type Comparator[T] = Callable[[T, T], bool]
type QueryFn[T] = Callable[[DataBase], T]
type Dependencies = MapLike[ICell[Any, Any], Comparator[Any]]
