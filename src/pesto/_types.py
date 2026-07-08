from collections.abc import Callable
from typing import TYPE_CHECKING, Any, ParamSpec, TypeVar, TypeVarTuple

if TYPE_CHECKING:
    from annotationlib import Format
    from collections.abc import Callable

type AnnotateFunc = Callable[[Format], dict[str, Any]]
type TypeParams = TypeVar | ParamSpec | TypeVarTuple
