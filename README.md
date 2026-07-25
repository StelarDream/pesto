Pesto is an Incremental Computation (IC) framework for Python, in the spirit of
[Salsa](https://github.com/salsa-rs/salsa) — it memoizes pure functions ("queries") over
mutable source state and recomputes only what an edit actually touches.

> Rust is red, Python is blue and yellow which makes green. Salsa is red, so Pesto is green.

**Early alpha.** The core engine and decorator surface are in place and tested; declared
dependencies, serialization, and concurrency are not yet — see the roadmap below.

## What works in this release

- **Memoized queries** — a `Query` runs its function once and caches the result; repeat
  `get`s on the same revision return the cached value without re-running.
- **Automatic dependency tracking** — dependencies are captured as a query runs (via a
  `ContextVar`-backed call stack), so you never declare them by hand.
- **Revision-based invalidation** — setting a `Source` bumps a revision counter; dependent
  queries recompute lazily on next access instead of eagerly on write.
- **Early cutoff** — when a recomputed dependency produces an unchanged value (per its
  comparator), transitive recomputation stops there. Pluggable per-`get` comparators
  (`eq` by default) let you decide what "unchanged" means.
- **Cycle detection** — a query depending on itself, directly or transitively, raises
  `CircularDependencyError` (not a `RecursionError`), and the database stays usable afterward.
- **Clean failure semantics** — if a query raises mid-run, no partial cell is written, the
  call stack unwinds cleanly, sibling cache entries are untouched, and the next `get` re-runs.
- **Parameterized queries** — `@query` wraps `(db, *args, **kwargs) -> T` into a `RichQuery`
  that dispatches to one memoized cell per distinct argument set; `q(db, user_id=1)` and
  `q(db, 1)` always resolve to the same cell. `@query.plain` keeps the argument-free path.

## Public API

```python
from pesto import DataBase, Query, RichQuery, Source, Comparator, CircularDependencyError, query, source
```

- `source(value)` / `source(factory=fn)` — create a `Source[T]` leaf with a default value or factory.
- `@query` — decorator that wraps `(db, *args, **kwargs) -> T` into a `RichQuery[T]`; calling
  `q(db, x=1)` always resolves to the same memoized cell for equal arguments, regardless of
  positional-vs-keyword style or default-arg elision.
- `@query.plain` — decorator for the argument-free shape `(db) -> T`; produces a plain `Query[T]`
  with no per-call dispatch overhead.
- `RichQuery[T].getter(comparator)` — returns a bound callable that applies a custom comparator,
  enabling early cutoff for callers that depend on this query.
- `DataBase` — owns the revision counter and the storage for sources and query results.
- `Query[T]` / `Source[T]` — low-level node types; usable directly when the decorator surface is
  too much.

## Requirements

- **Python 3.14+** (the codebase uses PEP 695 type-parameter syntax throughout).
- No runtime dependencies.

## Install (from source)

```bash
git clone https://github.com/StelarDream/pesto
cd pesto
uv sync
```

## Not in this release (see [TODO.md](TODO.md))

- **v0.3** — declared dependencies (`db.depends(A, B, C)` and `@query(A, B, C)`).
- **v0.4** — serialization of a populated database.
- **v0.5** — concurrency (the engine is single-threaded today; `ContextVar` usage anticipates
  it but nothing is synchronized yet).