# TODO

**Status:** pre-`v0.1`. The core data structures exist (`Cell`, `QueryCell`, `ContextStack`,
`ComparatorState`, `QueryDef`); the execution engine does not. `Node.get` / `Node.remove` are
abstract and unimplemented in both subclasses, so `Query` and `Source` cannot currently be
instantiated. Nothing runs end-to-end.

**Testing policy (from v0.1 onward):** no feature merges without tests in the same commit. The
invalidation algorithm is the kind of thing that silently degrades into "recompute everything" under
refactor — a passing suite is the only signal that early-cutoff still cuts off.

---

## v0.2 — Rich queries and decorators

Introduce decorator for queries, and create a per argument query dispatcher
to allow queries with external args to also exist inside the system, instead of the user having to write partials or other means of archiving this result

- [ ] (Re-)Introduce RichQuery
- [ ] @query decorator and optional @query.

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

---

## Backlog

- [ ] `Query.__slots__` declares `del_fn`, but it's never assigned — `weakref.finalize` is used
      instead. Dead slot.
- [ ] `QueryDef.__wrapped__` is annotated `QueryFn[T]` but returns a `RichQueryFn[P, T]`.
- [ ] `pyproject.toml` still has `description = "Add your description here"`.
- [ ] Eviction / GC strategy beyond what weakrefs give for free (LRU? revision-based?). Blocked on
      v0.3 — declared deps change what's reachable.
- [ ] Custom comparators past `comparator_eq`: the `Cell.comparators` dict is built for this but
      nothing constructs a non-default one yet.


```python

```