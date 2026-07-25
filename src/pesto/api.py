from typing import TYPE_CHECKING, cast, overload

from ._types import MISSING, MissingType
from .nodes import DefaultFactorySource, DefaultValueSource, Query, Source
from .rich_queries import RichQuery

if TYPE_CHECKING:
    from collections.abc import Callable

    from .interfaces import QueryFn
    from .rich_queries import RichQueryFn


@overload
def source[T](value: T) -> DefaultValueSource[T]: ...
@overload
def source[T](*, factory: Callable[[], T]) -> DefaultFactorySource[T]: ...


def source[T](
    value: T | MissingType = MISSING,
    *,
    factory: Callable[[], T] | None = None,
) -> Source[T]:

    if factory is None:
        return DefaultValueSource(cast("T", value))
    if value is MISSING:
        return DefaultFactorySource(factory)

    raise ValueError


class query:
    def __new__[**P, T](cls, fn: RichQueryFn[P, T]) -> RichQuery[P, T]:
        return RichQuery(fn)

    @staticmethod
    def plain[T](fn: QueryFn[T]) -> Query[T]:
        return Query(fn)

