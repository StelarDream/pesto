from typing import TYPE_CHECKING

from pesto import DataBase, Query, Source

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
