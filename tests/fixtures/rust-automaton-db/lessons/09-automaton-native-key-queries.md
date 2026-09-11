---
id: 09-automaton-native-key-queries
title: Automaton-native typed key queries
design_refs: [automaton-index, clustering-key, key-ordering, key-component-types]
validators: [cargo-check, cargo-test]
---

## Purpose

Compile the typed clustering-key query algebra into automata over canonical bytes and execute it against the stored-key automaton.

## Prerequisites

- The preceding course lesson.

## Learning objectives

- compile UTF-8 regex predicates
- compile integer equality/range predicates over canonical bytes
- compile fixed-byte predicates
- concatenate component automata according to schema framing
- intersect the whole query automaton with stored-key states
- stream matching rows
- demonstrate pruning for middle-key predicates

## Theory

Component predicates become languages over each component's physical bytes. Schema framing lets those languages be concatenated into one automaton over the full clustering key. The product with the finite stored-key automaton becomes an execution plan that can prune before reading rows.

## Concepts to teach

- automaton composition
- byte-level predicate compilation
- schema-directed compilation
- streaming traversal
- performance testing

## Constraints

- Do not fall back to prefix scan plus regex post-filter for the feature being taught.
- Preserve query semantics from the AST lesson.
- Keep partition selection exact and outside the clustering automaton.
- Measure middle-key pruning behavior.

## Suggested progression

1. Compile one UTF-8 component predicate.
2. Compile integer equality/ranges.
3. Add fixed-byte predicates if present in the schema.
4. Compose multiple components through canonical framing.
5. Connect product traversal to row lookup.
6. Stream results.
7. Benchmark a query whose selective predicate occurs after an unconstrained/weak leading component.

## Completion conditions

- `cargo test` succeeds.
- Typed component predicates compile to a full-key automaton.
- Product traversal returns semantically correct rows.
- A predicate in the middle of the clustering key demonstrably prunes traversal rather than requiring full prefix scanning.

## On completion, persist

Persist the query-compilation pipeline in `DESIGN.md`; record automaton-composition/performance concepts in `STATE.md`.

## Optional deeper paths

- Offer relevant papers, proofs, implementation archaeology, or formal models when the
  learner asks and the material would deepen the topic without replacing the main path.
