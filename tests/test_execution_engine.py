from typing import TYPE_CHECKING

import pytest

from pesto import CircularDependencyError, DataBase, Query, Source

if TYPE_CHECKING:
    from collections.abc import Callable


def counting[T](fn: Callable[[DataBase], T]) -> tuple[Callable[[DataBase], T], list[int]]:
    """Wrap fn so each call is counted; returns (wrapped_fn, calls) where len(calls) == call count."""
    calls: list[int] = []

    def wrapped(db: DataBase) -> T:
        calls.append(len(calls))
        return fn(db)

    return wrapped, calls


def test_get_source_and_query_over_it() -> None:
    db = DataBase()
    s = Source(lambda: 1)

    def double(db: DataBase) -> int:
        return s.get(db) * 2

    q = Query(double)

    assert s.get(db) == 1
    assert q.get(db) == 2


def test_cache_hit_same_query_twice_calls_fn_once() -> None:
    db = DataBase()
    s = Source(lambda: 1)
    fn, calls = counting(lambda db: s.get(db) * 2)
    q = Query(fn)

    assert q.get(db) == 2
    assert q.get(db) == 2
    assert len(calls) == 1


def test_cache_miss_after_source_set_calls_fn_again() -> None:
    db = DataBase()
    s = Source(lambda: 1)
    fn, calls = counting(lambda db: s.get(db) * 2)
    q = Query(fn)

    assert q.get(db) == 2
    assert len(calls) == 1

    s.set(db, 5)

    assert q.get(db) == 10
    assert len(calls) == 2


def test_early_cutoff_stops_transitive_recompute_on_unchanged_output() -> None:
    db = DataBase()
    s = Source(lambda: 4)

    # direct dependent: output changes with |s|'s sign, so setting -4 keeps it unchanged
    direct_fn, direct_calls = counting(lambda db: abs(s.get(db)))
    direct = Query(direct_fn)

    transitive_fn, transitive_calls = counting(lambda db: direct.get(db) + 1)
    transitive = Query(transitive_fn)

    assert transitive.get(db) == 5
    assert len(direct_calls) == 1
    assert len(transitive_calls) == 1

    s.set(db, -4)

    assert transitive.get(db) == 5
    assert len(direct_calls) == 2
    assert len(transitive_calls) == 1


def test_dependencies_of_reports_recorded_dep_set() -> None:
    db = DataBase()
    s1 = Source(lambda: 1)
    s2 = Source(lambda: 2)

    def fn(db: DataBase) -> int:
        return s1.get(db) + s2.get(db)

    q = Query(fn)

    assert q.get(db) == 3
    assert set(q.get_dependencies(db)) == {s1, s2}


def test_diamond_graph_recomputes_once_per_revision() -> None:
    db = DataBase()
    a = Source(lambda: 1)

    b_fn, b_calls = counting(lambda db: a.get(db) + 1)
    b = Query(b_fn)

    c_fn, c_calls = counting(lambda db: a.get(db) + 2)
    c = Query(c_fn)

    d_fn, d_calls = counting(lambda db: b.get(db) + c.get(db))
    d = Query(d_fn)

    assert d.get(db) == 5
    assert len(b_calls) == 1
    assert len(c_calls) == 1
    assert len(d_calls) == 1

    a.set(db, 10)

    assert d.get(db) == 23
    assert len(b_calls) == 2
    assert len(c_calls) == 2
    assert len(d_calls) == 2


def test_conditional_dependency_set_changes_between_runs() -> None:
    db = DataBase()
    flag = Source(lambda: True)
    on_branch = Source(lambda: 1)
    off_branch = Source(lambda: 100)

    def fn(db: DataBase) -> int:
        if flag.get(db):
            return on_branch.get(db)
        return off_branch.get(db)

    q = Query(fn)

    assert q.get(db) == 1
    assert set(q.get_dependencies(db)) == {flag, on_branch}

    flag.set(db, False)

    assert q.get(db) == 100
    assert set(q.get_dependencies(db)) == {flag, off_branch}

    # on_branch is no longer a dependency: changing it must not force a recompute
    off_branch.set(db, 200)
    on_branch.set(db, 999)

    assert q.get(db) == 200
    assert set(q.get_dependencies(db)) == {flag, off_branch}


# -- Error semantics ---------------------------------------------------------


def test_raise_mid_query_writes_no_cell_and_leaves_stack_clean() -> None:
    db = DataBase()

    def boom(db: DataBase) -> int:
        msg = "boom"
        raise ValueError(msg)

    q = Query(boom)

    with pytest.raises(ValueError, match="boom"):
        q.get(db)

    assert q.resolve(db) is None
    assert list(db.stack) == []


def test_raise_mid_query_next_get_reruns_fn() -> None:
    db = DataBase()
    attempts = []

    def flaky(db: DataBase) -> int:
        attempts.append(len(attempts))
        if len(attempts) == 1:
            msg = "first attempt fails"
            raise ValueError(msg)
        return 42

    q = Query(flaky)

    with pytest.raises(ValueError, match="first attempt fails"):
        q.get(db)

    assert q.get(db) == 42
    assert len(attempts) == 2


def test_raise_mid_nested_query_unwinds_whole_chain() -> None:
    db = DataBase()

    def inner_fn(db: DataBase) -> int:
        msg = "inner boom"
        raise ValueError(msg)

    inner = Query(inner_fn)

    def outer_fn(db: DataBase) -> int:
        return inner.get(db) + 1

    outer = Query(outer_fn)

    with pytest.raises(ValueError, match="inner boom"):
        outer.get(db)

    assert inner.resolve(db) is None
    assert outer.resolve(db) is None
    assert list(db.stack) == []


def test_raise_mid_nested_query_next_get_reruns_whole_chain() -> None:
    db = DataBase()
    inner_calls: list[int] = []
    outer_calls: list[int] = []

    def inner_fn(db: DataBase) -> int:
        inner_calls.append(len(inner_calls))
        if len(inner_calls) == 1:
            msg = "inner boom"
            raise ValueError(msg)
        return 10

    inner = Query(inner_fn)

    def outer_fn(db: DataBase) -> int:
        outer_calls.append(len(outer_calls))
        return inner.get(db) + 1

    outer = Query(outer_fn)

    with pytest.raises(ValueError, match="inner boom"):
        outer.get(db)

    assert outer.get(db) == 11
    assert len(inner_calls) == 2
    assert len(outer_calls) == 2


def test_raise_does_not_corrupt_sibling_dependency_state() -> None:
    # A cache entry that exists before a failed recompute must survive untouched.
    db = DataBase()
    s = Source(lambda: 1)

    def fn(db: DataBase) -> int:
        return s.get(db) * 2

    q = Query(fn)
    assert q.get(db) == 2

    def other_fn(db: DataBase) -> int:
        msg = "boom"
        raise ValueError(msg)

    other = Query(other_fn)
    with pytest.raises(ValueError, match="boom"):
        other.get(db)

    # unrelated, previously-cached query is unaffected
    assert q.get(db) == 2
    assert list(db.stack) == []


# -- Cycle detection ----------------------------------------------------------


def test_self_cycle_raises_circular_dependency_error() -> None:
    db = DataBase()

    def self_cycle(db: DataBase) -> int:
        return q.get(db)

    q = Query(self_cycle)

    with pytest.raises(CircularDependencyError) as exc_info:
        q.get(db)

    assert exc_info.value.query is q
    assert exc_info.value.chain == [q, q]
    assert list(db.stack) == []


def test_two_query_cycle_raises_circular_dependency_error() -> None:
    db = DataBase()

    def a_fn(db: DataBase) -> int:
        return b.get(db)

    a = Query(a_fn)

    def b_fn(db: DataBase) -> int:
        return a.get(db)

    b = Query(b_fn)

    with pytest.raises(CircularDependencyError) as exc_info:
        a.get(db)

    assert exc_info.value.chain == [a, b, a]
    assert list(db.stack) == []


def test_long_cycle_raises_circular_dependency_error() -> None:
    db = DataBase()
    queries: list[Query[int]] = []

    def make_fn(i: int) -> Callable[[DataBase], int]:
        def fn(db: DataBase) -> int:
            return queries[(i + 1) % len(queries)].get(db)

        return fn

    queries.extend(Query(make_fn(i)) for i in range(5))

    with pytest.raises(CircularDependencyError) as exc_info:
        queries[0].get(db)

    assert exc_info.value.chain == [*queries, queries[0]]
    assert list(db.stack) == []


def test_cycle_error_not_recursion_error() -> None:
    db = DataBase()

    def self_cycle(db: DataBase) -> int:
        return q.get(db)

    q = Query(self_cycle)

    with pytest.raises(CircularDependencyError):
        q.get(db)


def test_db_still_usable_after_cycle_error() -> None:
    db = DataBase()

    def self_cycle(db: DataBase) -> int:
        return q.get(db)

    q = Query(self_cycle)

    with pytest.raises(CircularDependencyError):
        q.get(db)

    s = Source(lambda: 9)
    assert s.get(db) == 9

    def ok_fn(db: DataBase) -> int:
        return s.get(db) + 1

    ok = Query(ok_fn)
    assert ok.get(db) == 10


def test_cycle_detected_partway_through_chain_leaves_earlier_cells_uncached() -> None:
    # a -> b -> c -> b (cycle starts at b, not at the root a)
    db = DataBase()

    def a_fn(db: DataBase) -> int:
        return b.get(db)

    a = Query(a_fn)

    def b_fn(db: DataBase) -> int:
        return c.get(db)

    b = Query(b_fn)

    def c_fn(db: DataBase) -> int:
        return b.get(db)

    c = Query(c_fn)

    with pytest.raises(CircularDependencyError) as exc_info:
        a.get(db)

    assert exc_info.value.chain == [a, b, c, b]
    assert a.resolve(db) is None
    assert b.resolve(db) is None
    assert c.resolve(db) is None
    assert list(db.stack) == []
