import inspect
from collections.abc import Callable
from typing import Any, Concatenate

from .queries import CallId, QueryFn

type CallKeyGen[**P] = Callable[Concatenate[QueryFn[P, Any], P], CallId]


def inspect_call_key_gen[**P](
    fn: QueryFn[P, Any],
    *args: P.args,
    **kwargs: P.kwargs,
) -> CallId:
    sig = inspect.signature(fn).bind(None, *args, **kwargs)
    sig.apply_defaults()
    return sig.args, sorted(sig.kwargs.items())
