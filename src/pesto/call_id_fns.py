import inspect
from collections.abc import Callable, Hashable
from typing import Any, Concatenate

from .rich_queries import RichQueryFn

type CallId = Hashable  # readability
type QueryIdFn[**P] = Callable[Concatenate[RichQueryFn[P, Any], P], CallId]


def inspect_call_id_fn[**P](
    fn: RichQueryFn[P, Any],
    *args: P.args,
    **kwargs: P.kwargs,
) -> CallId:
    sig = inspect.signature(fn).bind(None, *args, **kwargs)
    sig.apply_defaults()
    return sig.args, sorted(sig.kwargs.items())
