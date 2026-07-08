# TODO

- [ ] Set up the first version of `db.get_input` (rename to avoid shadowing `input` builtin — `get_source`?) now that the stack system is implemented (first working build, yay)
  - [ ] `db.get_source` / `db.get_query` will push/pop `DataBase.stack` directly or via shared helpers — this is also where dynamic dependency recording happens
- [ ] Set up static dependency optionals so the user can avoid blinking if they only `db.get` conditionally
  - [ ] `@query(A, B, C)` — static/declared deps
  - [ ] `db.depends(A, B, C)` — registers a dep with no computation
- [ ] Think through how to implement picklability at all stages of the system, so you can "freeze and send" to disk or another process
  - [ ] Idea: WeakRef-stored entries are unlikely to matter much, so snapshot the current live items at `__getstate__` time instead of preserving weak-ref semantics
  - [ ] `DataBase.revision` (ContextVar) and the two WeakKeyDictionary caches need the same `__getstate__`/`__setstate__` treatment `ContextStack` already has

## Execution engine (core, nothing works end-to-end yet)

- [ ] Implement `Query.get` (currently just inherits the abstract `Node.get` stub) and `Source.get`/`set`/`setdefault` (currently `NotImplementedError`)
- [ ] Dependency tracking loop: push query onto `db.stack` before running its fn, record everything `.get()`'d during the run as a dependency, pop after
- [ ] Invalidation / recompute algorithm: walk `QueryCell.dependencies`, use `changed_at` / `verified_at` to decide stale vs. early-cutoff-verify vs. recompute — the actual Salsa-style algorithm; current data structures (`Cell.changed_at`, `QueryCell.dependencies`, `ComparatorState.verified_at`) are waiting on this

## Correctness / robustness (needed before this is reliable)

- [ ] Cycle detection — need an efficient "is this query already in the stack" view on `ContextStack`/ `DataBase.stack` (e.g. a set alongside the linked list) so recursive queries error instead of infinite-looping/stack-overflowing
- [ ] Decide error/panic semantics: what happens to a query's cache entry and its dependents when the query fn raises
- [ ] Dual dependency system: dynamic deps (recorded through the stack window during fn execution) vs. static deps (declared via `@query(...)` / `db.depends(...)`) — needs to inform eviction/GC strategy too, not just correctness
- [ ] Parallelism: ContextVar usage already anticipates this, but no concrete design yet for where synchronization goes (shared `Cell`/`QueryCell` access, `DataBase.revision` updates, etc.) — revisit once execution engine lands

## Later

- [ ] Tests — hold off until past early scaffolding, but needed before the execution engine solidifies (cache hit/miss and early-cutoff behavior are easy to silently break under refactors)
