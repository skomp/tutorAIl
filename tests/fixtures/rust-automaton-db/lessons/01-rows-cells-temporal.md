---
id: 01-rows-cells-temporal
title: Rows, cells, and temporal visibility
design_refs: [row-cell-model, temporal-semantics, deletion, atomicity]
validators: [cargo-check, cargo-test, manual]
---

## Purpose

Replace the simplistic one-key/one-string value model with logical rows containing
named cells and introduce deterministic temporal visibility.

This creates the first data model that resembles the intended database rather than a
generic map.

## Prerequisites

- `00-foundations`

## Learning objectives

- Model nested ownership with `Row` owning `Cell` values.
- Use `SystemTime` and `Duration` without hiding time behind wall-clock calls.
- Represent optional temporal bounds with `Option`.
- Write builder-style methods that consume and return `self`.
- Implement half-open visibility semantics.
- Borrow nested values safely from maps.
- Write table-driven tests and test boundary conditions.
- Understand why returning an owned value differs from returning a reference to removed
  data.

## Theory

A row is identified elsewhere by its key and contains named cells. Each cell owns its
value and may have temporal metadata.

Cell visibility uses `[valid_from, expires_at)`. Row expiry is an additional hard upper
bound. Explicit-time methods are preferable internally because deterministic tests and
future historical queries should not depend on whatever the wall clock happens to be.

Replacing a cell in a map returns the old owned cell. A reference into that removed
value would become invalid when the local value is dropped; the API must either return
owned data or borrow from data that remains stored.

## Concepts to teach

- nested ownership
- `Option<SystemTime>`
- pattern matching over optional bounds
- consuming builder methods
- `Display`, `Debug`, and `Formatter<'_>`
- borrowed nested lookup
- half-open intervals
- table-driven unit tests
- borrowed iteration in `for` loops
- owned replacement values versus borrowed stored values

## Constraints

- Keep cell values simple initially; richer typed value schemas belong later.
- Row-level `valid_from` is not part of the initial model.
- Use explicit instants for visibility methods.
- Test exact boundary behavior, not only points comfortably before/after a boundary.
- Do not introduce tombstone storage until the existing row/cell path is working and
  tested.

## Suggested progression

1. Introduce `Cell` with an owned value and optional validity bounds.
2. Add constructors/builders only when they are immediately exercised.
3. Implement and test `Cell::is_visible_at`.
4. Introduce `Row` as a map from cell name to `Cell`.
5. Add row expiry.
6. Implement insertion/replacement semantics for a named cell.
7. Implement row visibility.
8. Implement lookup that combines row and cell visibility.
9. Add tests for missing cells, row expiry, cell expiry, not-yet-valid cells, and exact
   boundaries.
10. Discuss tombstones conceptually and defer their storage representation until the
    surrounding update model is ready.

## Completion conditions

- `cargo test` succeeds.
- A row can store multiple named cells.
- Cell visibility obeys `[valid_from, expires_at)`.
- Row expiry suppresses every cell at and after the row expiry instant.
- Lookup returns no value for an absent or invisible cell.
- Tests cover exact cell and row boundaries.
- Replacement behavior does not return references to removed local values.
- The learner can explain why explicit-time visibility is easier to test and extend.

## On completion, persist

Record the demonstrated nested-ownership, time, formatting, borrowing, and testing
concepts in `STATE.md`.

Persist any deliberate change to temporal semantics under the relevant section of
`DESIGN.md`.

## Optional deeper paths

- Discuss monotonic versus wall-clock time and why persisted validity timestamps need
  wall-clock semantics.
- Explore `Copy` behavior of `SystemTime` and references.
- Compare builder methods returning concrete types with methods returning `Self`.
