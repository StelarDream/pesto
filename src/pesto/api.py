import functools
from operator import eq
from typing import TYPE_CHECKING, Any, cast, overload

from ._types import MISSING, MissingType
from .nodes import DefaultFactorySource, DefaultValueSource, Query, QueryFn, Source
from .rich_queries import RichQuery, RichQueryFn

if TYPE_CHECKING:
    from collections.abc import Callable

    from pesto.data_bases import Comparator, DataBase, Dependencies, INode


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

    @staticmethod
    def with_deps(
        *deps: tuple[INode[Any, Any], Comparator[Any]] | INode[Any, Any],
    ) -> StaticDepQuery:
        deps_dict = dict(dep if isinstance(dep, tuple) else (dep, eq) for dep in deps)
        return StaticDepQuery(deps_dict)


class StaticDepQuery:
    static_deps: Dependencies

    def __init__(self, deps: Dependencies) -> None:
        self.static_deps = deps

    def register_deps(self, db: DataBase) -> None:
        for dep, comp in self.static_deps.items():
            db.add_dep(dep, comp)

    def __call__[**P, T](self, fn: RichQueryFn[P, T]) -> RichQuery[P, T]:
        @functools.wraps(fn)
        def wrapper(db: DataBase, *args: P.args, **kwargs: P.kwargs) -> T:
            self.register_deps(db)
            return fn(db, *args, **kwargs)

        return RichQuery(wrapper)

    def plain[T](self, fn: QueryFn[T]) -> Query[T]:
        @functools.wraps(fn)
        def wrapper(db: DataBase) -> T:
            self.register_deps(db)
            return fn(db)

        return Query(wrapper)
