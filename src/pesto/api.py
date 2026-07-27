from typing import TYPE_CHECKING, cast, overload

from pesto._types import MISSING, MissingType
from pesto.impl.nodes import DefaultFactorySource, DefaultValueSource, Query, Source
from pesto.tooling.rich_queries import RichQuery, RichQueryFn

if TYPE_CHECKING:
    from collections.abc import Callable

    from pesto.core.types import QueryFn


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


class query:  # noqa: N801
    def __new__[**P, T](cls, fn: RichQueryFn[P, T]) -> RichQuery[P, T]:
        return RichQuery(fn)

    @staticmethod
    def plain[T](fn: QueryFn[T]) -> Query[T]:
        return Query(fn)
