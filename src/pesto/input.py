from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


class Input[T]:
    __slots__ = ("__weakref__",)

    @property
    def default(self) -> T:
        msg = "input has no default"
        raise NotImplementedError(msg)

    @staticmethod
    def set_default[V](default: V) -> Input[V]:
        return _InputWithDefaultValue(default)

    @staticmethod
    def set_default_factory[V](default_factory: Callable[[], V]) -> Input[V]:
        return _InputWithDefaultFactory(default_factory)


class _InputWithDefaultValue[T](Input[T]):
    default_value: T

    __slots__ = ("__weakref__", "default_value")

    def __init__(self, default_value: T) -> None:
        self.default_value = default_value

    @property
    def default(self) -> T:
        return self.default_value


class _InputWithDefaultFactory[T](Input[T]):
    default_factory: Callable[[], T]

    __slots__ = ("__weakref__", "default_factory")

    def __init__(self, default_factory: Callable[[], T]) -> None:
        self.default_factory = default_factory

    @property
    def default(self) -> T:
        return self.default_factory()
