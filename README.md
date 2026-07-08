# Pesto

Pesto is an Incremental Computation (IC) framework for Python, in the spirit of [Salsa](https://github.com/salsa-rs/salsa), with extras.

> Rust is red, Python is blue and yellow which makes green. Salsa is red so Pesto is green.

**Status: very early development.** No release yet, no stable API. The core execution engine (dependency tracking, invalidation, recompute) is still being built, see [TODO.md](TODO.md) for what's in progress and what's missing.

## What is Incremental Computation?

An IC framework memoizes the results of pure functions ("queries") over some mutable input state, and recomputes only what's actually affected when that input changes — skipping unaffected work and cutting off recomputation early when a query's output turns out unchanged even though its inputs changed.

## Motivation

Pesto's eventual target use case is powering a type checker with LSP (Language Server Protocol) capabilities: the kind of tool that needs to re-analyze a codebase after every keystroke, fast, by only recomputing what the edit actually touched.

## Core concepts (so far)

- **`Source`** — a named input slot a `DataBase` holds a value for, with an optional default.
- **`Query`** — a memoized, pure computation over a `DataBase`, with dependencies tracked automatically as it runs.
- **`DataBase`** — owns the current revision counter and the storage for inputs and query results.
- **`Cell`** / **`QueryCell`** — the versioned storage backing sources and queries, tracking `changed_at` / `verified_at` for early-cutoff.

## Development

```bash
uv sync
```

Type checking and linting are configured via `pyright` (strict mode) and `ruff` in [pyproject.toml](pyproject.toml).
