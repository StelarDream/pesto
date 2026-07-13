# TODO

**Status:** `v0.1` — core engine (`Query`, `QueryCell`, `Source`, `DataBase`) works: memoized
queries, dependency tracking, cycle detection, and revision-based invalidation are all in place
and tested. Every `Query` is still constructed by hand as `Query(fn)` with `fn: Callable[[DataBase], T]` —
no decorator, no support for queries that take arguments beyond `db`.

---

## v0.2 — Rich queries and decorators

Query fns are currently locked to `(db) -> T`. Anything parameterized ("user by id") has no first-class representation: callers fall back to `functools.partial` or closures, and since each one is a distinct object, `db.query_data` can't recognize two calls with the same arguments as the same query — no cache hit, no shared invalidation. `RichQuery` needs to fix that: one `RichQuery` dispatching to a single memoized `Query` per distinct argument set, so `q(db, user_id=1)` always resolves to the same cell.

A prior version of this existed at `rich_queries.py` + `call_id_fns.py` (deleted at `0b5db4d` during the engine rework) 

- [ ] `RichQuery[**P, T, K]`: `fn: RichQueryFn[P, T]` (`(db, *args, **kwargs) -> T`), a pluggable
      `call_id_fn` mapping call args → cache key `K`, and a `K -> Query[T]` cache.
- [ ] **Fix the cache's lifetime model.** The old `queries_cache` was a
      `WeakValueDictionary[K, Query[T]]`, but nothing holds a strong ref to a freshly-made `Query`
      — `DataBase.query_data` is *also* weak-keyed on the `Query` itself, and callers do
      `qdef.get(db, x)` without keeping the object around. The only strong ref was local to
      `get_query_or_make`, so entries could be collected before ever being reused — a no-op cache.
      Use a plain `dict` (strong refs) and drive eviction from something real instead — tie it to
      cell eviction (v0.3 / Backlog), not to refcount on the `Query` wrapper.
- [ ] Default `call_id_fn`: `inspect_call_id_fn` — bind via `inspect.signature(fn).bind(...)`,
      `apply_defaults()`, key on `(args, sorted(kwargs.items()))` so identity is independent of
      positional-vs-keyword style and default-arg elision. Require hashable args; let that surface
      as a plain `TypeError` from the dict lookup rather than adding bespoke validation.
- [ ] `get_query_or_make(*args, **kwargs)`: look up by call id; on miss, build
      `Query(fn=lambda db: self.fn(db, *args, **kwargs))` and cache it. For eviction: the old code
      used `Query(del_fn=...)` to pop the cache entry on finalization — current `Query` has no
      `del_fn` slot (dead per Backlog), so wire this through `weakref.finalize` instead.
- [ ] `@query` — wraps `(db, *args, **kwargs) -> T` into a `QueryDef`.
- [ ] `@query.plain` — keeps the existing `(db) -> T` shape, skips the dispatcher entirely (one
      `Query`, no args to key on).
- [ ] **Tests to write:** equal args (incl. default-arg / positional-vs-kwarg equivalence) resolve
      to the same cell and share invalidation; different args → independent cells; unhashable args
      raise; a `Query` evicted from `queries_cache` after going out of scope leaves no dangling entry.

---

## v0.3 — Declared dependencies

Lets a user avoid the "conditional `.get` means the dep is invisible until it's too late" problem.

- [ ] `db.depends(A, B, C)` — register deps on the currently-running query without computing them.
      Cheap: it's an append to the current `QueryCell.dependencies`.
- [ ] `@query(A, B, C)` — static deps attached to the `QueryDef`. Harder: these must be materialized
      into every `Query` the def produces, and they exist before any `DataBase` does. Decide where
      they live — on `QueryDef`, and merged into `QueryCell.dependencies` on first run.
- [ ] Reconcile the two systems. Dynamic deps are per-`(query, db)`; static deps are per-`QueryDef`.
      Union them at verify time. Also decide what a *declared but never `.get`'d* dep means for
      eviction/GC — a static dep is a strong ref, which changes the `WeakValueDictionary` lifetime
      story in `QueryDef.queries_cache`.
- [ ] Tests: declared dep invalidates without ever being `.get`'d; conditional-`.get` query with a
      declared dep behaves identically on both branches; static + dynamic dep on the same node
      doesn't double-count.

---

## v0.4 — Serialization

- [ ] `DataBase.__getstate__` / `__setstate__`. `ContextStack` already has the pattern; `revision`
      (a `ContextVar`) and both `WeakKeyDictionary` caches need the same treatment.
- [ ] Weak entries: snapshot whatever is live at `__getstate__` time rather than trying to preserve
      weak-ref semantics across the boundary. Accept that a round-trip strengthens the graph, and say
      so in the docs.
- [ ] `Query.fn` is a closure (`lambda db: self.fn(db, *args, **kwargs)` in `get_query_or_make`) and
      is not picklable. This is the real obstacle — a `Query` must be reconstructible from
      `(QueryDef, call_id)` instead of from its fn. Probably means `QueryDef` needs a stable
      registry key.
- [ ] Tests: round-trip a db with a populated cache; assert cache hits survive; assert a `set` after
      restore still invalidates correctly.

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
