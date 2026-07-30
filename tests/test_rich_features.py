from typing import Literal

import pytest

from pesto import DataBase, Query, RichQuery, query, source

# -- Basic wiring -------------------------------------------------------------


def test_query_decorator_produces_rich_query() -> None:
    @query
    def q(db: DataBase, x: int) -> int:
        return x * 2

    assert isinstance(q, RichQuery)


def test_query_plain_produces_query() -> None:
    @query.plain
    def q(db: DataBase) -> int:
        return 42

    assert isinstance(q, Query)
    assert q.get(DataBase()) == 42


def test_call_returns_underlying_query() -> None:
    @query
    def q(db: DataBase, x: int) -> int:
        return x * 2

    q_obj = q(5)
    assert isinstance(q_obj, Query)
    assert q_obj.get(DataBase()) == 10


# -- Cache keying -------------------------------------------------------------


def test_same_args_share_cell() -> None:
    db = DataBase()
    calls: list[int] = []

    @query
    def q(db: DataBase, x: int) -> int:
        calls.append(0)
        return x * 2

    assert q.get(db, 3) == 6
    assert q.get(db, 3) == 6
    assert len(calls) == 1


def test_different_args_produce_independent_cells() -> None:
    db = DataBase()
    calls: list[int] = []

    @query
    def q(db: DataBase, x: int) -> int:
        calls.append(0)
        return x * 2

    assert q.get(db, 1) == 2
    assert q.get(db, 2) == 4
    assert len(calls) == 2


def test_positional_and_keyword_resolve_to_same_cell() -> None:
    db = DataBase()
    calls: list[int] = []

    @query
    def q(db: DataBase, x: int) -> int:
        calls.append(0)
        return x * 2

    assert q.get(db, 5) == 10
    assert q.get(db, x=5) == 10
    assert len(calls) == 1


def test_explicit_default_and_omitted_resolve_to_same_cell() -> None:
    db = DataBase()
    calls: list[int] = []

    @query
    def q(db: DataBase, x: int = 5) -> int:
        calls.append(0)
        return x * 2

    assert q.get(db) == 10
    assert q.get(db, x=5) == 10
    assert len(calls) == 1


def test_unhashable_args_raise_type_error() -> None:
    db = DataBase()

    @query
    def q(db: DataBase, x: list[int]) -> int:
        return len(x)

    with pytest.raises(TypeError):
        q.get(db, [1, 2, 3])


# -- Invalidation -------------------------------------------------------------


def test_invalidation_recomputes_affected_args() -> None:
    db = DataBase()
    s = source(1)

    @query
    def q(db: DataBase, multiplier: int) -> int:
        return s.get(db) * multiplier

    assert q.get(db, 2) == 2
    assert q.get(db, 3) == 3

    s.set(db, 10)

    assert q.get(db, 2) == 20
    assert q.get(db, 3) == 30


def test_invalidation_is_independent_across_args() -> None:
    db = DataBase()
    s1 = source(1)
    s2 = source(1)
    calls_1: list[int] = []
    calls_2: list[int] = []

    @query
    def q(db: DataBase, which: int) -> int:
        if which == 1:
            calls_1.append(0)
            return s1.get(db)
        calls_2.append(0)
        return s2.get(db)

    q.get(db, 1)
    q.get(db, 2)

    s1.set(db, 99)

    assert q.get(db, 1) == 99
    assert q.get(db, 2) == 1
    assert len(calls_1) == 2
    assert len(calls_2) == 1


# -- getter -------------------------------------------------------------------


def test_getter_custom_comparator_suppresses_transitive_invalidation() -> None:
    db = DataBase()
    s = source(1)
    inner_calls: list[int] = []
    outer_calls: list[int] = []

    @query
    def inner(db: DataBase, x: int) -> int:
        inner_calls.append(0)
        return s.get(db)

    def always_equal(x: object, y: object) -> Literal[True]:
        return True

    get_inner = inner.getter(always_equal)

    def outer_fn(db: DataBase) -> int:
        outer_calls.append(0)
        return get_inner(db, 1) + 1

    outer = Query(outer_fn)

    assert outer.get(db) == 2

    s.set(db, 100)

    # inner recomputes (its dependency changed) but comparator says equal → outer stays green
    assert outer.get(db) == 2
    assert len(inner_calls) == 2
    assert len(outer_calls) == 1


# -- delete -------------------------------------------------------------------


def test_delete_removes_cache_entry_and_forces_recompute() -> None:
    db = DataBase()
    calls: list[int] = []

    @query
    def q(db: DataBase, x: int) -> int:
        calls.append(0)
        return x * 2

    assert q.get(db, 5) == 10
    assert len(calls) == 1

    q.delete(5)

    assert q.get(db, 5) == 10
    assert len(calls) == 2


# -- query.with_deps ----------------------------------------------------------


def test_with_deps_decorator_produces_rich_query() -> None:
    s = source(0)

    @query.with_deps(s)
    def q(db: DataBase, x: int) -> int:
        return x

    assert isinstance(q, RichQuery)


def test_with_deps_plain_produces_query() -> None:
    s = source(0)

    @query.with_deps(s).plain
    def q(db: DataBase) -> int:
        return s.get(db)

    assert isinstance(q, Query)
    assert q.get(DataBase()) == 0


def test_with_deps_registers_static_dep_on_call() -> None:
    db = DataBase()
    s = source(1)
    outer_calls: list[int] = []

    @query.with_deps(s)
    def q(db: DataBase) -> int:
        return s.get(db)

    @query.plain
    def outer(db: DataBase) -> int:
        outer_calls.append(0)
        return q.get(db)

    assert outer.get(db) == 1
    assert len(outer_calls) == 1

    s.set(db, 2)

    assert outer.get(db) == 2
    assert len(outer_calls) == 2


def test_with_deps_plain_registers_static_dep() -> None:
    db = DataBase()
    s = source(10)
    outer_calls: list[int] = []

    @query.with_deps(s).plain
    def q(db: DataBase) -> int:
        return s.get(db)

    @query.plain
    def outer(db: DataBase) -> int:
        outer_calls.append(0)
        return q.get(db)

    assert outer.get(db) == 10
    s.set(db, 20)
    assert outer.get(db) == 20
    assert len(outer_calls) == 2


def test_with_deps_custom_comparator_suppresses_recompute() -> None:
    db = DataBase()
    s = source(1)
    q_calls: list[int] = []

    def always_equal(x: object, y: object) -> Literal[True]:
        return True

    # q tracks s with always_equal but does NOT read s.get(db) inside,
    # so the comparator is not overridden by the implicit eq from s.get.
    @query.with_deps((s, always_equal)).plain
    def q(db: DataBase) -> int:
        q_calls.append(0)
        return 42

    assert q.get(db) == 42
    assert len(q_calls) == 1

    s.set(db, 99)
    # s changed but always_equal says "no change" → q should not recompute
    assert q.get(db) == 42
    assert len(q_calls) == 1


def test_with_deps_multiple_deps() -> None:
    db = DataBase()
    s1 = source(1)
    s2 = source(2)
    outer_calls: list[int] = []

    @query.with_deps(s1, s2)
    def q(db: DataBase) -> int:
        return s1.get(db) + s2.get(db)

    @query.plain
    def outer(db: DataBase) -> int:
        outer_calls.append(0)
        return q.get(db)

    assert outer.get(db) == 3

    s1.set(db, 10)
    assert outer.get(db) == 12
    assert len(outer_calls) == 2

    s2.set(db, 20)
    assert outer.get(db) == 30
    assert len(outer_calls) == 3
