---
id: 05-canonical-ordered-keys
title: Canonical ordered binary keys
design_refs: [key-ordering, partition-key, clustering-key, key-component-types]
validators: [cargo-check, cargo-test]
---

## Purpose

Define canonical physical encodings whose lexicographic byte order agrees with semantic key order and whose decoding rejects malformed input.

## Prerequisites

- The preceding course lesson.

## Learning objectives

- reason about lexicographic byte ordering and tuple ordering
- encode signed integers while preserving numeric order
- encode unsigned integers, fixed bytes, UTF-8 components, and timestamps
- frame variable-length components without ambiguous concatenation
- decode safely and report malformed data with explicit errors
- verify round-trip and ordering invariants with property-based tests
- decide whether schema knowledge makes per-component type tags unnecessary

## Theory

Sorted storage and automaton traversal operate on bytes, so the encoding is part of database semantics. For one schema, semantic comparison and encoded-byte comparison must agree. Signed integers need a transformation that maps signed order into unsigned lexicographic order; variable-length fields need framing or escaping whose byte ordering is itself deliberate.

## Concepts to teach

- byte slices
- endianness
- binary representation
- iterators
- custom comparison
- error types
- property-based testing

## Constraints

- Keep the encoding canonical and deterministic across machines.
- Do not use native memory layout as a persistent format.
- Do not add a type tag unless the schema/compatibility design requires it.
- Property tests must exercise both round-trip and ordering invariants.

## Suggested progression

1. Specify ordering invariants before writing encoders.
2. Implement one fixed-width type and test its order.
3. Add the remaining fixed-width types.
4. Design and test variable-length UTF-8 framing.
5. Compose components into tuple keys.
6. Implement decoding and malformed-input errors.
7. Add property-based tests over generated keys.
8. Resolve the type-tag decision.

## Completion conditions

- `cargo test` succeeds.
- Every supported key type round-trips through encode/decode.
- Property tests show semantic order agrees with encoded-byte order for values under one schema.
- Composite encodings preserve tuple order.
- Malformed encodings return errors rather than panicking.
- The type-tag decision is recorded.

## On completion, persist

Persist the canonical encoding rules and type-tag decision in `DESIGN.md`; record binary-representation/property-testing concepts in `STATE.md`.

## Optional deeper paths

- Offer relevant papers, proofs, implementation archaeology, or formal models when the
  learner asks and the material would deepen the topic without replacing the main path.
