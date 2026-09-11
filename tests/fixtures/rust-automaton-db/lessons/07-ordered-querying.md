---
id: 07-ordered-querying
title: Ordered querying before automata
design_refs: [clustering-key, key-ordering, table-model]
validators: [cargo-check, cargo-test]
---

## Purpose

Exploit ordinary ordered storage first so the learner understands which query capabilities come from ordering alone and what automata must add.

## Prerequisites

- The preceding course lesson.

## Learning objectives

- use `BTreeMap` range access and `Bound`
- implement prefix and tuple-range traversal
- combine component predicates conservatively
- stream results instead of materializing them
- write custom iterators with lifetimes tied to the table/partition

## Theory

An ordered keyspace already provides efficient contiguous ranges. Prefix and leading-component constraints can often become range bounds. Predicates in the middle of a key are where ordinary ordered traversal becomes insufficient and motivate the automaton index.

## Concepts to teach

- range APIs
- `Bound`
- custom iterators
- iterator adaptors
- iterator lifetimes
- closure traits where useful

## Constraints

- Keep execution within one exact partition.
- Do not implement regex/automata yet.
- Prefer streaming iteration to collecting all rows.
- Make performance limitations of non-leading predicates explicit.

## Suggested progression

1. Implement exact ordered traversal.
2. Add range bounds.
3. Add prefix-like leading-component access.
4. Introduce a streaming query iterator.
5. Combine several component constraints.
6. Measure or reason about the cases that still require scanning.

## Completion conditions

- `cargo test` succeeds.
- Ordered range/prefix queries return correct rows within one partition.
- Results can be streamed.
- The learner can identify the class of middle-key predicates that motivates automata.

## On completion, persist

Record ordered-query limitations and iterator concepts in `STATE.md`; persist any durable query-planning decisions in `DESIGN.md`.

## Optional deeper paths

- Offer relevant papers, proofs, implementation archaeology, or formal models when the
  learner asks and the material would deepen the topic without replacing the main path.
