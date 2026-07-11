# TODO

**Status:** pre-`v0.1`. The core data structures exist (`Cell`, `QueryCell`, `ContextStack`,
`ComparatorState`, `QueryDef`); the execution engine does not. `Node.get` / `Node.remove` are
abstract and unimplemented in both subclasses, so `Query` and `Source` cannot currently be
instantiated. Nothing runs end-to-end.

**Testing policy (from v0.1 onward):** no feature merges without tests in the same commit. The
invalidation algorithm is the kind of thing that silently degrades into "recompute everything" under
refactor — a passing suite is the only signal that early-cutoff still cuts off.

---

## v0.1 — Execution engine

Goal: `source.set(db, x)`, `query.get(db)` works, recomputes when `x` changes, doesn't when it doesn't.

### Unblock

- [ ] Circular import: `rich_queries` imports `inspect_call_id_fn` eagerly, `call_id_fns` imports
      `RichQueryFn` eagerly. Both orders fail. `RichQueryFn` is only used in lazy `type` aliases →
      move it under `TYPE_CHECKING`.


### `Source`


- [ ] `Source.set` / `setdefault` / `remove` — write through `db.source_data`, bump `db.update()`,
      set `Cell.changed_at` to the new revision. `set` to an equal value: decide whether it bumps
      `changed_at` or is a no-op (this is where early-cutoff starts, and getting it wrong here makes
      every downstream cutoff test lie).
- [ ] Rename `DataBase.input_data` → `source_data`, and `db.get_input` → `db.get_source`.
      `Source` is the README's word; `input` shadows the builtin. Do it before there are callers.

### `Query`

- [ ] `Query.get(db, default=MISSING)` — the dependency-tracking loop:
      push onto `db.stack`, run `fn(db)`, pop in a `finally`. Every `.get()` during the run appends
      to the running query's `QueryCell.dependencies`.
- [ ] `Query.remove` — evict the `QueryCell`. Decide whether dependents are evicted too or just
      left to re-verify.
- [ ] Invalidation / recompute (Salsa `maybe_changed_after`): walk `QueryCell.dependencies`,
      compare `Cell.changed_at` against `ComparatorState.verified_at` to pick
      *fresh* / *verify-then-cutoff* / *recompute*. Pull-based, so no dependents index is required —
      `ComparatorState.references` is currently the only reverse edge; either justify it or drop it.
- [ ] `QueryCell.dependencies` is a `WeakSet`. A `Source` that only the dep set references will be
      collected mid-flight and silently disappear from the graph. Decide: strong refs for deps, or
      explicit "dep died → recompute" semantics. Not optional; it's a correctness hole.
- [ ] Populate `__init__.py`. It's empty — there is no public API surface.

### Tests (first suite)

Written in this order; each layer catches a different class of bug.

- [ ] Get a source, get a query over it. Baseline.
- [ ] Cache hit: same query twice, no revision bump → `fn` called once. Use a call counter.
- [ ] Cache miss: `source.set` → `fn` called again.
- [ ] Early cutoff: `source.set` to a value that leaves the query's *output* unchanged → direct
      dependents recompute, transitive dependents do not.
- [ ] Dependency-graph introspection: assert on the actual recorded dep set after a run, not just on
      call counts. Needs a public read path (`db.dependencies_of(query)` or similar) — design it now,
      it's the API a user will want for debugging anyway.
- [ ] Diamond graph (`A → B, C → D`) and a query whose dep set changes between runs (conditional
      `.get`). The second one is where most naive implementations break.

---

## v0.2 — Correctness

- [ ] **Error semantics.** A query fn raises: what happens to its `QueryCell`, and to the stack?
      Decide and document: no cache entry written, stack unwound (already handled if the pop is in
      `finally`), exception propagates unmemoized. Dependents on the next `get` must re-run rather
      than see a half-written cell.
  - [ ] Tests: raise mid-query, assert no cell written, assert `db.stack` is empty, assert the next
        `get` re-runs. Raise mid-*nested*-query, assert the whole chain unwinds.
- [ ] **Cycle detection.** `ContextStack` is a linked list — membership is O(depth) per `get`, on
      the hottest path there is. Add a `set`/`Counter` alongside the frames; raise a dedicated
      `CycleError` carrying the participating queries, before recursion blows the Python stack.
  - [ ] Tests: self-cycle, two-query cycle, long cycle. Assert `CycleError` (not `RecursionError`),
        assert the error names the cycle, assert `db.stack` is clean afterward and the db is still
        usable.

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