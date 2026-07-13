Pesto is an Incremental Computation (IC) framework for Python, in the spirit of
[Salsa](https://github.com/salsa-rs/salsa) — it memoizes pure functions ("queries") over
mutable source state and recomputes only what an edit actually touches.

> Rust is red, Python is blue and yellow which makes green. Salsa is red, so Pesto is green.

**This is the first tagged release and it's an early alpha.** The core engine works and is
tested, but the ergonomic surface (decorators, parameterized queries) isn't here yet — see
the roadmap below.

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

## Public API

```python
from pesto import DataBase, Query, Source, Comparator, CircularDependencyError
```

- `Source[T]` — a named leaf slot with an optional initial-value factory.
- `Query[T]` — wraps a `fn: (DataBase) -> T`. Constructed by hand as `Query(fn)` for now.
- `DataBase` — owns the revision counter and the storage for sources and query results.

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

- **v0.2** — `@query` decorator and `RichQuery` for parameterized queries (`user_by_id(db, 1)`).
- **v0.3** — declared dependencies (`db.depends(...)`).
- **v0.4** — serialization of a populated database.
- **v0.5** — concurrency (the engine is single-threaded today; `ContextVar` usage anticipates
  it but nothing is synchronized yet).