import inspect
from collections.abc import Callable, Hashable
from typing import Any, Concatenate

from .queries import QueryFn

type CallId = Hashable  # readability
type CallKeyGen = Callable[Concatenate[QueryFn[..., Any], ...], CallId]

def inspect_call_key_gen(
    fn: QueryFn[..., Any],
    *args: object,
    **kwargs: object,
) -> CallId:
    sig = inspect.signature(fn).bind(None, *args, **kwargs)
    sig.apply_defaults()
    return sig.args, sorted(sig.kwargs.items())
