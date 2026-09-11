---
id: 03-first-refactor
title: The first deliberate refactor
design_refs: [table-model, row-cell-model, partition-key, clustering-key]
validators: [cargo-check, cargo-test, has-lib, git-diff, manual]
---

## Purpose

Use real structural pressure in a growing `main.rs` to teach Rust's binary/library
distinction, modules, visibility, imports, and API boundaries.

This refactor happens because domain responsibilities and tests have become substantial,
not because every Rust project should begin with a large module tree.

## Prerequisites

- `02-typed-keys-table-hierarchy`

## Learning objectives

- Understand the difference between a binary crate root and a library crate root.
- Move engine code out of `main.rs` without changing behavior.
- Learn `mod`, `pub`, imports, and re-exports as actual compiler-enforced boundaries.
- Decide which types/functions are public rather than making everything `pub`.
- Keep unit tests near internals when appropriate.
- Recognize when warnings reveal structural problems versus ordinary private
  implementation detail.
- Perform API-preserving refactors under tests.

## Theory

`src/main.rs` is the root of a binary target. `src/lib.rs` is the root of the package's
library target. A package may contain both.

Visibility is not file-based encapsulation. Rust items are private by default, and
module boundaries determine what parent/sibling/external code may access. A public type
whose useful fields or constructors remain private may still be unusable from the
binary; conversely, exposing fields can freeze representation unnecessarily.

Tests provide a safety net for structural change. The objective is not to invent a
perfect final module tree; it is to create the smallest structure that reflects
responsibilities already present.

## Concepts to teach

- binary versus library targets
- `src/main.rs` and `src/lib.rs`
- `mod`
- `pub`
- `use`
- re-exports
- crate paths
- unit-test placement and visibility
- public API versus internal representation
- refactoring with compiler/test feedback

## Constraints

- Preserve behavior; this is a structural refactor.
- Do not redesign storage, keys, or schema at the same time.
- Do not make every item public merely to silence compiler errors.
- Prefer a small number of meaningful modules over one file per type.
- Keep the learner source under learner control; the tutor explains and validates but
  does not perform the refactor unless asked.
- Use warnings as input, but do not suppress them wholesale with `allow(dead_code)`.

## Suggested progression

1. Introduce `lib.rs` and move the existing engine implementation/tests out of the
   binary while preserving compilation.
2. Make the binary depend on the package library through a deliberately small public
   API.
3. Use compiler visibility errors to decide what truly needs `pub`.
4. Identify the first natural module boundaries among model, keys/schema, and table
   responsibilities.
5. Move code in small increments and keep tests passing.
6. Re-export only the API that the binary or future clients should consume.
7. Inspect the final diff for accidental behavior changes or representation leaks.

## Completion conditions

- `src/lib.rs` exists.
- `cargo check` succeeds.
- `cargo test` succeeds.
- `main.rs` contains executable orchestration rather than database model type
  declarations.
- The library owns the database implementation and its relevant tests.
- Public visibility is no broader than required by actual callers.
- The learner can explain why at least one `pub` boundary was necessary.
- The learner can explain how the package can contain both library and binary targets.
- The refactor does not change table/key/row semantics.

## On completion, persist

Record module/crate/visibility concepts demonstrated in `STATE.md`.

If the refactor creates durable subsystem boundaries, record those architectural
boundaries in `DESIGN.md` without embedding learner-specific file history.

## Optional deeper paths

- Inspect how integration tests under `tests/` differ from unit tests inside modules.
- Explore `pub(crate)` and narrower visibility forms.
- Inspect Cargo target discovery rules.
