import inspect
from collections.abc import Callable, Hashable
from typing import Any, Concatenate

from .rich_queries import RichQueryFn

type CallId = Hashable  # readability
type QueryIdFn[**P, K: CallId = CallId] = Callable[Concatenate[RichQueryFn[P, Any], P], K]


def inspect_call_id_fn[**P](
    fn: RichQueryFn[P, Any],
    *args: P.args,
    **kwargs: P.kwargs,
) -> tuple[tuple[Any, ...], list[tuple[str, Any]]]:
    sig = inspect.signature(fn).bind(None, *args, **kwargs)
    sig.apply_defaults()
    return sig.args, sorted(sig.kwargs.items())
