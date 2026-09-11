---
id: 16-general-quorums
title: General quorum systems
design_refs: [quorums, replication, topology]
validators: [cargo-check, cargo-test]
---

## Purpose

Turn read/write replica selection into an extensible quorum-policy subsystem and explore quorum systems beyond majority.

## Prerequisites

- The preceding course lesson.

## Learning objectives

- define a quorum-system abstraction
- reason about read/write intersection
- implement majority and weighted quorums
- explore grid and tree/hierarchical systems
- compose topology/datacenter-aware policies
- separate latency/availability/intersection trade-offs
- allow custom quorum strategies

## Theory

A quorum system is a family of acceptable read/write sets with intersection properties. Majority is only one construction. Weighted, grid, and hierarchical structures offer different latency, fault tolerance, and topology behavior. Correctness comes from the intersection property required by the chosen consistency semantics, not from the word 'quorum'.

## Concepts to teach

- set-system abstractions
- intersection reasoning
- policy traits
- topology-aware selection
- latency/availability trade-offs

## Constraints

- Do not hard-code `QUORUM = majority`.
- Keep quorum policy separate from replication transport.
- Require policies to state their relevant intersection/guarantee assumptions.
- Offer deeper academic material when the learner asks.

## Suggested progression

1. Define policy interface and required guarantees.
2. Implement majority.
3. Implement weighted quorums.
4. Explore grid construction.
5. Explore tree/hierarchical construction.
6. Add topology/datacenter composition.
7. Test failure and latency scenarios.
8. Implement one learner-defined policy behind the same interface.

## Completion conditions

- Replication consumes a quorum policy rather than majority-specific logic.
- At least three materially different quorum constructions work through the same abstraction.
- Tests exercise intersection/failure behavior.
- The learner can explain how topology and availability change the trade-offs.

## On completion, persist

Persist the quorum-policy abstraction and supported guarantees in `DESIGN.md`; record quorum theory in `STATE.md`.

## Optional deeper paths

- Offer relevant papers, proofs, implementation archaeology, or formal models when the
  learner asks and the material would deepen the topic without replacing the main path.
