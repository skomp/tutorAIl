---
id: 06-data-query-algebra
title: Define the data and query algebra
design_refs: [table-model, partition-key, clustering-key, values, temporal-semantics]
validators: [cargo-check, cargo-test]
---

## Purpose

State precisely what AutomatonDB queries mean before building the sophisticated execution mechanism.

## Prerequisites

- The preceding course lesson.

## Learning objectives

- define the logical relation formed by table, partition, row, clustering key, and cell
- define projection and key selection separately from value post-filtering
- define current-time visibility within query semantics
- define absent/appended field semantics
- design a typed query AST instead of a textual parser

## Theory

Automata are an execution technique, not query semantics. A typed algebra gives an implementation-independent meaning to exact partition selection, component predicates, projection, temporal visibility, and post-filtering. This prevents the automaton engine from accidentally defining the public model.

## Concepts to teach

- algebraic data types
- recursive enums
- query ASTs
- separation of semantics from execution
- API design

## Constraints

- A normal query names exactly one partition.
- Clustering predicates are component-wise and schema-aware.
- Value predicates may initially be post-filters.
- Do not build a textual query language yet.

## Suggested progression

1. Write precise definitions for data entities.
2. Define projection.
3. Define typed component predicates.
4. Define value post-filter predicates.
5. Define temporal visibility interaction.
6. Represent the algebra as a typed Rust AST.
7. Write semantic tests against the existing in-memory engine.

## Completion conditions

- The query AST represents exact partition selection, clustering predicates, projection, and optional value post-filters.
- Tests establish the intended semantics independent of automata.
- No textual parser is required.
- The learner can explain which operations belong to logical semantics and which belong to execution.

## On completion, persist

Persist query semantics in `DESIGN.md`; record AST/API-design concepts in `STATE.md`.

## Optional deeper paths

- Offer relevant papers, proofs, implementation archaeology, or formal models when the
  learner asks and the material would deepen the topic without replacing the main path.
