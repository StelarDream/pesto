import contextvars

import pytest

from pesto.stacks import ContextStack, EmptyStackError, StackFrame


def identity(x: int) -> int:
    return x


def test_root_returns_deepest_ancestor() -> None:
    root = StackFrame(1)
    middle = StackFrame(2, root)
    leaf = StackFrame(3, middle)

    assert leaf.root is root
    assert middle.root is root
    assert root.root is root


def test_iter_yields_frames_from_leaf_to_root() -> None:
    root = StackFrame(1)
    middle = StackFrame(2, root)
    leaf = StackFrame(3, middle)

    assert list(leaf) == [leaf, middle, root]


def test_contains_checks_whole_chain() -> None:
    root = StackFrame(1)
    middle = StackFrame(2, root)
    leaf = StackFrame(3, middle)

    assert 3 in leaf
    assert 2 in leaf
    assert 1 in leaf
    assert 4 not in leaf


def test_getstate_returns_values_leaf_to_root() -> None:
    root = StackFrame(1)
    middle = StackFrame(2, root)
    leaf = StackFrame(3, middle)

    assert leaf.__getstate__() == [3, 2, 1]


def test_setstate_round_trips_single_frame() -> None:
    frame: StackFrame[int] = StackFrame.__new__(StackFrame)
    frame.__setstate__([1])

    assert frame.value == 1
    assert frame.parent is None


def test_setstate_round_trips_multiple_frames() -> None:
    original = StackFrame(3, StackFrame(2, StackFrame(1)))

    restored: StackFrame[int] = StackFrame.__new__(StackFrame)
    restored.__setstate__(original.__getstate__())

    assert [f.value for f in restored] == [f.value for f in original]


def test_pickle_round_trip() -> None:
    import pickle  # noqa: PLC0415

    original = StackFrame(3, StackFrame(2, StackFrame(1)))
    restored = pickle.loads(pickle.dumps(original))  # noqa: S301

    assert [f.value for f in restored] == [f.value for f in original]


def test_peek_and_pop_raise_when_empty() -> None:
    stack = ContextStack(lambda: 1)

    with pytest.raises(EmptyStackError):
        stack.peek()

    with pytest.raises(EmptyStackError):
        stack.pop()


def test_push_then_peek_returns_pushed_value() -> None:
    def times_two(x: float) -> float:
        return x * 2

    stack = ContextStack(times_two)

    assert stack.push(5) == 10
    assert stack.peek() == 10


def test_push_does_not_consume_fn_args_between_calls() -> None:
    def add(x: float, y: float = 0) -> float:
        return x + y

    stack = ContextStack(add)

    stack.push(1)
    stack.push(2, y=3)

    assert stack.peek() == 5
    assert stack.pop() == 5
    assert stack.peek() == 1


def test_pop_restores_previous_frame() -> None:
    stack = ContextStack(identity)

    stack.push(1)
    stack.push(2)

    assert stack.pop() == 2
    assert stack.peek() == 1
    assert stack.pop() == 1

    with pytest.raises(EmptyStackError):
        stack.pop()


def test_peek_or_returns_default_when_empty() -> None:
    stack = ContextStack(lambda: 1)

    assert stack.peek_or(42) == 42
    assert stack.peek_or() is None


def test_peek_or_returns_value_when_present() -> None:
    stack = ContextStack(identity)
    stack.push(7)

    assert stack.peek_or(42) == 7


def test_pop_or_returns_default_when_empty_and_does_not_raise() -> None:
    stack = ContextStack(lambda: 1)

    assert stack.pop_or(42) == 42


def test_pop_or_pops_value_when_present() -> None:
    stack = ContextStack(identity)
    stack.push(1)
    stack.push(7)

    assert stack.pop_or(42) == 7
    assert stack.peek() == 1


def test_peek_or_run_calls_factory_only_when_empty() -> None:
    calls: list[int] = []

    def factory() -> int:
        calls.append(1)
        return 99

    stack = ContextStack(identity)

    assert stack.peek_or_run(factory) == 99
    assert len(calls) == 1

    stack.push(1)

    assert stack.peek_or_run(factory) == 1
    assert len(calls) == 1


def test_pop_or_run_calls_factory_only_when_empty() -> None:
    calls: list[int] = []

    def factory() -> int:
        calls.append(1)
        return 99

    stack = ContextStack(identity)
    stack.push(1)

    assert stack.pop_or_run(factory) == 1
    assert len(calls) == 0
    assert stack.pop_or_run(factory) == 99
    assert len(calls) == 1


def test_iter_yields_values_leaf_to_root() -> None:
    stack = ContextStack(identity)
    stack.push(1)
    stack.push(2)
    stack.push(3)

    assert list(stack) == [3, 2, 1]


def test_iter_empty_yields_nothing() -> None:
    stack = ContextStack(lambda: 1)

    assert list(stack) == []


def test_contains() -> None:
    stack = ContextStack(identity)
    stack.push(1)
    stack.push(2)

    assert 1 in stack
    assert 2 in stack
    assert 3 not in stack


def test_contains_empty_is_false() -> None:
    stack = ContextStack(lambda: 1)

    assert 1 not in stack


def test_getstate_empty_stack() -> None:
    def fn(x: int) -> int:
        return x

    stack = ContextStack(fn)

    values, restored_fn = stack.__getstate__()

    assert values == []
    assert restored_fn is fn


def test_getstate_setstate_round_trip() -> None:
    def fn(x: int) -> int:
        return x

    stack = ContextStack(fn)
    stack.push(1)
    stack.push(2)
    stack.push(3)

    state = stack.__getstate__()

    restored: ContextStack[[int], int] = ContextStack.__new__(ContextStack)
    restored.__setstate__(state)

    assert list(restored) == [3, 2, 1]
    assert restored.fn is fn


def test_pickle_round_trip_empty[T]() -> None:
    import pickle  # noqa: PLC0415

    stack = ContextStack(identity)
    restored: ContextStack[[T], T] = pickle.loads(pickle.dumps(stack))  # noqa: S301

    with pytest.raises(EmptyStackError):
        restored.peek()


def test_pickle_round_trip_with_frames() -> None:
    import pickle  # noqa: PLC0415

    stack = ContextStack(identity)
    stack.push(1)
    stack.push(2)

    restored: ContextStack[[int], int] = pickle.loads(pickle.dumps(stack))  # noqa: S301

    assert list(restored) == [2, 1]


def test_frame_not_visible_across_unrelated_context() -> None:
    """Pushes made in one contextvars.Context aren't visible from an unrelated one."""
    stack = ContextStack(identity)
    stack.push(1)

    def check_in_new_context() -> None:
        with pytest.raises(EmptyStackError):
            stack.peek()

    ctx = contextvars.Context()
    ctx.run(check_in_new_context)

    # original context is unaffected
    assert stack.peek() == 1


def test_frame_isolated_per_context_after_copy() -> None:
    """A context copied via contextvars.copy_context() sees pushes made before the copy,
    but further pushes inside that copy don't leak back out."""
    stack = ContextStack(identity)
    stack.push(1)

    ctx = contextvars.copy_context()

    def push_in_copy() -> None:
        stack.push(2)
        assert stack.peek() == 2

    ctx.run(push_in_copy)

    assert stack.peek() == 1
