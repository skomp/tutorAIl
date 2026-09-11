---
id: 08-automaton-machinery
title: Build the automaton machinery
design_refs: [automaton-index, key-ordering]
validators: [cargo-check, cargo-test]
---

## Purpose

Build enough finite-automata machinery to compile a useful regex subset and intersect query languages with the finite language of stored keys.

## Prerequisites

- The preceding course lesson.

## Learning objectives

- represent a small regex AST
- construct a Thompson-style NFA
- compute epsilon closure
- perform subset construction to DFA
- execute and minimize DFAs
- understand right-continuation equivalence and Myhill–Nerode intuition
- build a trie/DAFSA-like automaton for finite stored keys
- traverse DFA × stored-key automaton intersection
- compare sparse and dense transition representations

## Theory

Stored keys form a finite language; equivalent prefixes can be merged when their right-continuation languages are identical. Query DFAs may contain productive cycles. Intersection via a product traversal prunes stored-key exploration whenever the query automaton cannot continue.

## Concepts to teach

- recursive enums
- graph representations
- state IDs instead of pointer graphs
- hash maps and sets
- custom iterators
- generics
- traits
- memory representation
- benchmarking

## Constraints

- Perform an ecosystem checkpoint before implementing substantial machinery.
- Implement a deliberately bounded regex subset first.
- Use explicit state IDs/indices unless pointer ownership is genuinely justified.
- Keep public abstraction boundaries compatible/analogous to mature libraries where practical.
- Benchmark transition/layout choices before claiming performance benefits.

## Suggested progression

1. Review current Rust regex/automata/FST crates and select comparison targets.
2. Define a small regex AST.
3. Implement Thompson NFA construction.
4. Implement epsilon closure and subset construction.
5. Execute and test DFAs.
6. Implement DFA minimization.
7. Build a finite-key trie.
8. Merge equivalent continuation states into an acyclic deterministic automaton.
9. Implement product/intersection traversal.
10. Compare transition representations and allocations.

## Completion conditions

- Supported regex expressions compile and execute correctly.
- DFA minimization preserves language behavior.
- A finite set of stored keys can be represented as an acyclic deterministic automaton.
- Product traversal returns exactly the stored keys accepted by the query DFA.
- Benchmarks or measurements inform at least one representation decision.
- A replacement checkpoint compares the implementation with mature crates.

## On completion, persist

Persist the chosen automaton abstractions and representation decisions in `DESIGN.md`; record automata/graph/performance concepts in `STATE.md`.

## Optional deeper paths

- Offer relevant papers, proofs, implementation archaeology, or formal models when the
  learner asks and the material would deepen the topic without replacing the main path.
