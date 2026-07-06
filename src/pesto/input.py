from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


class Input[T]:
    __slots__ = ("__weakref__",)

    @property
    def default(self) -> T:
        msg = "input has no default"
        raise NotImplementedError(msg)

    @property
    def has_default(self) -> bool:
        return False

    @staticmethod
    def set_default[V](default: V) -> Input[V]:
        return _InputWithDefaultValue(default)

    @staticmethod
    def set_default_factory[V](default_factory: Callable[[], V]) -> Input[V]:
        return _InputWithDefaultFactory(default_factory)

    def __init_subclass__(cls, *, has_default: bool = False, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        if has_default:
            cls.has_default = property(lambda _: True) # pyright: ignore[reportAttributeAccessIssue]



class _InputWithDefaultValue[T](Input[T], has_default=True):
    default_value: T

    __slots__ = ("default_value",)

    def __init__(self, default_value: T) -> None:
        self.default_value = default_value

    @property
    def default(self) -> T:
        return self.default_value


class _InputWithDefaultFactory[T](Input[T], has_default=True):
    default_factory: Callable[[], T]

    __slots__ = ("default_factory",)

    def __init__(self, default_factory: Callable[[], T]) -> None:
        self.default_factory = default_factory

    @property
    def default(self) -> T:
        return self.default_factory()
