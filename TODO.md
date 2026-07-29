# TODO

**Status:** `v0.2` — `RichQuery` and the `@query` decorator are in place. `@query` wraps
`(db, *args, **kwargs) -> T` into a `RichQuery` that dispatches to a single memoized `Query`
per distinct argument set; `@query.plain` keeps the old `(db) -> T` path. The default
`inspect_cell_key_gen` normalizes positional/keyword style and fills in defaults via
`inspect.signature.bind` so `q(db, x=1)` and `q(db, 1)` always hit the same cell.
`queries_cache` is a plain `dict` (strong refs)
`getter(comparator)` exposes the comparator-aware call path for callers that need early cutoff. All cases from the v0.2 test plan are covered.

---

## v0.5 — Concurrency

- [ ] Design pass first, code second. `ContextVar` usage anticipates it but nothing is synchronized:
      `Cell`/`QueryCell` are shared mutable state, `DataBase.update()` is read-modify-write.
- [ ] Decide the model: one db per thread (cheap, no sharing), or a shared db with per-cell locks and
      a "query already in flight elsewhere" wait state (Salsa's approach).
- [ ] `db.stack` is a `ContextVar`, so it's already per-task — verify that holds under
      `asyncio.TaskGroup` and `ThreadPoolExecutor`, since `ContextVar` copies differ between them.
- [ ] Tests: concurrent `get` of the same cold query computes `fn` exactly once; concurrent
      `set` + `get` doesn't produce a cell with a `changed_at` from the future.
