from contextvars import ContextVar
from typing import TYPE_CHECKING, Any
from weakref import WeakKeyDictionary

from .stacks import ContextStack

if TYPE_CHECKING:
    from .cells import Cell, QueryCell
    from .queries import Query
    from .sources import Source


class DataBase:
    input_data: WeakKeyDictionary[Source[Any], Cell[Any]]
    query_data: WeakKeyDictionary[Query[Any], QueryCell[Any]]
    revision: ContextVar[int]
    stack: ContextStack[Query[Any]]

    __slots__ = ("input_data", "query_data", "revision", "stack")

    def __init__(self) -> None:
        self.input_data = WeakKeyDictionary()
        self.query_data = WeakKeyDictionary()
        self.revision = ContextVar(
            f"<Context[int] for {type(self).__name__}:{id(self)}>",
            default=0,
        )
        self.stack = ContextStack()

    @property
    def now(self) -> int:
        return self.revision.get()

    def update(self) -> int:
        new_revision = self.revision.get() + 1
        self.revision.set(new_revision)
        return new_revision
