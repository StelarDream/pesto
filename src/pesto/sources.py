from typing import TYPE_CHECKING

from pesto.sentinels import MISSING, MissingType

if TYPE_CHECKING:
    from collections.abc import Callable


class Source[T]:
    __slots__ = ("__weakref__",)

    @classmethod
    def create(
        cls,
        *,
        default_value: T | MissingType = MISSING,
        default_factory: Callable[[], T] | None = None,
    ) -> Source[T]:
        if default_value is not MISSING and default_factory is not None:
            msg = "can't have both default_value and default_factory"
            raise ValueError(msg)

        if default_value is not MISSING:
            return cls.set_default(default_value)

        if default_factory is not None:
            return cls.set_default_factory(default_factory)

        return cls()

    @property
    def default(self) -> T:
        msg = "source has no default"
        raise NotImplementedError(msg)

    @property
    def has_default(self) -> bool:
        return False

    @staticmethod
    def set_default[V](default: V) -> Source[V]:
        return _SourceWithDefaultValue(default)

    @staticmethod
    def set_default_factory[V](default_factory: Callable[[], V]) -> Source[V]:
        return _SourceWithDefaultFactory(default_factory)

    def __init_subclass__(cls, *, has_default: bool = False, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        if has_default:
            cls.has_default = property(lambda _: True)  # pyright: ignore[reportAttributeAccessIssue]


class _SourceWithDefaultValue[T](Source[T], has_default=True):
    default_value: T

    __slots__ = ("default_value",)

    def __init__(self, default_value: T) -> None:
        self.default_value = default_value

    @property
    def default(self) -> T:
        return self.default_value


class _SourceWithDefaultFactory[T](Source[T], has_default=True):
    default_factory: Callable[[], T]

    __slots__ = ("default_factory",)

    def __init__(self, default_factory: Callable[[], T]) -> None:
        self.default_factory = default_factory

    @property
    def default(self) -> T:
        return self.default_factory()


def source[T](
    *,
    default_value: T | MissingType = MISSING,
    default_factory: Callable[[], T] | None = None,
) -> Source[T]:
    return Source[T].create(
        default_factory=default_factory,
        default_value=default_value,
    )
