---
id: 04-richer-typed-schemas
title: Tables and richer typed schemas
design_refs: [table-model, key-component-types, values, schema-evolution, key-ordering]
validators: [cargo-check, cargo-test, manual]
---

## Purpose

Strengthen the provisional table/key schema into a model suitable for later canonical
encoding, query compilation, storage, and online schema evolution.

## Prerequisites

- `03-first-refactor`

## Learning objectives

- Distinguish table identity, key-column schema, and value-column schema.
- Add richer primitive types without making the core model unmaintainable.
- Introduce typed value columns.
- Use traits and conversion APIs where they genuinely simplify extensibility.
- Model schema versions and append-only compatibility rules.
- Decide which validation belongs at construction boundaries.
- Prepare keys and values for later codec abstractions without implementing the physical
  encoding yet.

## Theory

Schemas define the meaning of positional key components and named value columns. Runtime
keys stay compact; schema metadata supplies names and allowed semantic types.

Key types are constrained because ordering and routing must understand them. Value
types can be more extensible because codecs can translate between typed logical values
and bytes.

Schema evolution is append-only in the initial model: existing fields/components cannot
be removed, reordered, or change type. The difficult semantics of appending a clustering
component to already-stored rows remain deliberately unresolved.

## Concepts to teach

- richer enums
- traits and trait bounds
- generics where useful
- `From` and `TryFrom`
- associated types when justified
- owned versus borrowed schema/value representations
- error design for schema construction
- versioned immutable metadata

## Constraints

- Do not finalize canonical bytes in this lesson.
- Do not add arbitrary user-defined key types.
- Avoid generic abstractions that are not exercised by real schema/value operations.
- Keep append-only evolution rules explicit and testable.
- Leave the old-row meaning of an appended clustering-key component unresolved.

## Suggested progression

1. Introduce explicit table identity.
2. Refine primitive key types and decide which ones belong in the first stable set.
3. Add named typed value-column definitions.
4. Validate table schema construction.
5. Add schema version identity.
6. Model permitted append-only schema changes.
7. Introduce codec-shaped abstractions for values only when a concrete typed value needs
   conversion.
8. Test valid and invalid schema evolution operations.

## Completion conditions

- `cargo test` succeeds.
- Table schemas distinguish partition keys, clustering keys, and ordinary value columns.
- The initial primitive key type set is explicit.
- Invalid schema construction/evolution is rejected with typed errors.
- Schema versions are represented explicitly.
- Append-only rules are covered by tests.
- No physical binary key encoding has been prematurely frozen.
- The unresolved appended-clustering-component semantics remains documented rather than
  silently assumed.

## On completion, persist

Record the finalized initial primitive type set and any schema-model decisions in
`DESIGN.md`.

Record demonstrated Rust trait/conversion/error concepts in `STATE.md`.

## Optional deeper paths

- Compare enum-based dynamic values with generic compile-time table APIs.
- Explore zero-sized marker types and phantom types as an alternative API style.
