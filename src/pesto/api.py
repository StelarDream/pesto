from operator import eq
from typing import TYPE_CHECKING, Any, overload

from ._types import MISSING, MissingType
from .data_bases import Comparator, DataBase, Dependencies, INode  # noqa: TC001
from .nodes import DefaultFactorySource, DefaultValueSource, Query, QueryFn, Source
from .rich_queries import RichQuery, RichQueryFn

if TYPE_CHECKING:
    from collections.abc import Callable


@overload
def source[T](value: T) -> DefaultValueSource[T]: ...
@overload
def source[T](*, factory: Callable[[], T]) -> DefaultFactorySource[T]: ...


def source[T](
    value: T | MissingType = MISSING,
    *,
    factory: Callable[[], T] | None = None,
) -> Source[T]:

    if value is not MISSING:
        return DefaultValueSource(value)
    if factory is not None:
        return DefaultFactorySource(factory)

    raise ValueError


class query:  # noqa: N801
    __slots__ = ()

    def __new__[**P, T](cls, fn: RichQueryFn[P, T]) -> RichQuery[P, T]:
        if hasattr(fn, "__qualname__"):
            fn.__qualname__ = f"{fn.__qualname__}.__wrapped__"

        return RichQuery(fn)

    @staticmethod
    def plain[T](fn: QueryFn[T]) -> Query[T]:
        if hasattr(fn, "__qualname__"):
            fn.__qualname__ = f"{fn.__qualname__}.__wrapped__"

        return Query(fn)

    @staticmethod
    def with_deps(
        *deps: tuple[INode[Any, Any], Comparator[Any]] | INode[Any, Any],
    ) -> StaticDepQuery:
        deps_dict = dict(dep if isinstance(dep, tuple) else (dep, eq) for dep in deps)
        return StaticDepQuery(deps_dict)


class StaticDepWrapper[**P, T]:
    deps: Dependencies
    fn: RichQueryFn[P, T]

    __slots__ = ("deps", "fn")

    def __init__(self, deps: Dependencies, fn: RichQueryFn[P, T]) -> None:
        self.deps = deps
        self.fn = fn

    def __call__(self, db: DataBase, *args: P.args, **kwargs: P.kwargs) -> T:
        frame = db.stack.peek_or(None)
        if frame is not None:
            frame.dependencies.update(self.deps)
        return self.fn(db, *args, **kwargs)


class StaticDepQuery:
    static_deps: Dependencies

    __slots__ = ("static_deps",)

    def __init__(self, deps: Dependencies) -> None:
        self.static_deps = deps

    def __call__[**P, T](self, fn: RichQueryFn[P, T]) -> RichQuery[P, T]:
        if hasattr(fn, "__qualname__"):
            fn.__qualname__ = f"{fn.__qualname__}.__wrapped__.fn"

        return RichQuery(StaticDepWrapper(self.static_deps, fn))

    def plain[T](self, fn: QueryFn[T]) -> Query[T]:
        if hasattr(fn, "__qualname__"):
            fn.__qualname__ = f"{fn.__qualname__}.__wrapped__.fn"

        return Query(StaticDepWrapper(self.static_deps, fn))
