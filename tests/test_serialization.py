import pickle
from operator import eq

import pytest

from pesto import DataBase, Query, query, source
from pesto.cells import Cell, ComparatorData, QueryCell
from pesto.context_tools import ContextCounter, ContextScopedStack
from pesto.data_bases import DBStackFrame
from pesto.nodes import DefaultValueSource


def roundtrip[T](obj: T) -> T:
    return pickle.loads(pickle.dumps(obj))  # noqa: S301


# --- ContextCounter -----------------------------------------------------------


def test_context_counter_roundtrip() -> None:
    c = ContextCounter(7)
    c2 = roundtrip(c)
    assert c2.now() == 7


def test_context_counter_roundtrip_after_increment() -> None:
    c = ContextCounter()
    c.increment(3)
    c2 = roundtrip(c)
    assert c2.now() == 3


# --- ContextScopedStack -------------------------------------------------------


def test_context_scoped_stack_empty_roundtrip() -> None:
    stack = ContextScopedStack(DBStackFrame)
    stack2 = roundtrip(stack)
    assert stack2.peek_or(None) is None


def test_context_scoped_stack_with_frames_roundtrip() -> None:
    node = DefaultValueSource(0)
    stack = ContextScopedStack(DBStackFrame)
    stack.push(node)
    node2, stack2 = roundtrip((node, stack))
    assert stack2.peek_or(None) is not None
    assert stack2.peek().active is node2


# --- Cell / ComparatorData ----------------------------------------------------


def test_comparator_data_roundtrip() -> None:
    node = DefaultValueSource(0)
    cd = ComparatorData(5)
    cd.add_ref(node)
    node2, cd2 = roundtrip((node, cd))
    assert cd2.changed_at == 5
    assert node2 in cd2.references


def test_cell_roundtrip() -> None:
    cell = Cell(42, 3)
    cell2 = roundtrip(cell)
    assert cell2.value == 42
    assert cell2.verified_at == 3


def test_query_cell_roundtrip() -> None:
    src = DefaultValueSource(0)
    query_cell = QueryCell(99, 1)
    query_cell.dependencies[src] = eq
    src2, query_cell_2 = roundtrip((src, query_cell))
    assert query_cell_2.value == 99
    assert src2 in query_cell_2.dependencies


# --- Nodes --------------------------------------------------------------------


def test_default_value_source_roundtrip() -> None:
    s = DefaultValueSource(10)
    s2 = roundtrip(s)
    db = DataBase()
    assert s2.get(db) == 10


def test_query_plain_roundtrip_local_fn_not_picklable() -> None:
    def fn(db: DataBase) -> int:
        return 42

    q = Query(fn)
    with pytest.raises(pickle.PicklingError):
        pickle.dumps(q)


# --- RichQuery / decorated ----------------------------------------------------


@query
def _parametric(db: DataBase, a: int) -> int:
    return a * 2


def test_rich_query_get_query_roundtrip() -> None:
    q = _parametric.get_query(5)
    q2 = roundtrip(q)
    db = DataBase()
    assert q2.get(db) == 10


def test_rich_query_roundtrip() -> None:
    rq2 = roundtrip(_parametric)
    db = DataBase()
    assert rq2.get(db, 3) == 6


# --- StaticDepWrapper ---------------------------------------------------------

_static_dep_src = DefaultValueSource(7)


@query.with_deps((_static_dep_src, eq))
def _q_with_deps(db: DataBase) -> int:
    return _static_dep_src.get(db) + 1


def test_static_dep_wrapper_roundtrip() -> None:
    inner_q = _q_with_deps.get_query()
    q2 = roundtrip(inner_q)
    db = DataBase()
    assert q2.get(db) == 8


# --- DataBase -----------------------------------------------------------------


def test_database_empty_roundtrip() -> None:
    db = DataBase()
    db2 = roundtrip(db)
    assert db2.now() == 0
    assert db2.stack.peek_or(None) is None


def test_database_with_source_data_roundtrip() -> None:
    db = DataBase()
    s = DefaultValueSource(5)
    s.set(db, 99)
    s2, db2 = roundtrip((s, db))
    data = db2.get_data(s2)
    assert data is not None
    assert data.value == 99


def test_database_with_query_cache_roundtrip_local_fn_not_picklable() -> None:
    db = DataBase()
    s = source(10)

    @query
    def q(db: DataBase, a: int) -> int:
        return s.get(db) + a

    inner = q.get_query(5)
    inner.get(db)

    with pytest.raises(pickle.PicklingError):
        pickle.dumps(db)


def test_database_roundtrip_preserves_revision() -> None:
    db = DataBase()
    s = DefaultValueSource(0)
    s.set(db, 1)
    s.set(db, 2)
    rev = db.now()
    db2 = roundtrip(db)
    assert db2.now() == rev


def test_database_raises_during_active_computation() -> None:
    db = DataBase()
    node = DefaultValueSource(0)

    with db.stack.scope(node), pytest.raises(ValueError, match="active computation"):
        pickle.dumps(db)
