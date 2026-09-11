---
id: 21-strong-consistency
title: Strong consistency mode
design_refs: [strong-consistency, conditional-operations, replication, quorums, live-reconfiguration]
validators: [cargo-check, cargo-test]
---

## Purpose

Add a second consistency mode with a precisely stated stronger guarantee instead of silently changing eventual semantics.

## Prerequisites

- The preceding course lesson.

## Learning objectives

- define the target guarantee precisely
- distinguish linearizability from weaker models
- compare quorum-register and consensus approaches
- choose and implement a partition-local protocol
- support strong CAS/conditional writes
- define failure behavior
- integrate topology/reconfiguration concerns
- compare performance with eventual mode

## Theory

Strong consistency is not 'more replicas' or 'bigger quorums'. The protocol must establish a specific ordering/visibility guarantee under a stated failure model. Consensus and quorum-register techniques solve related but different problems and have different operational costs.

## Concepts to teach

- linearizability
- consensus/quorum-register comparison
- partition-local coordination
- strong CAS
- failure semantics
- consistency/performance trade-offs

## Constraints

- Keep eventual mode unchanged as a separate semantic option.
- Write the guarantee before selecting the protocol.
- Do not imply cross-partition transactions.
- Integrate reconfiguration rather than assuming static membership.

## Suggested progression

1. Specify the strong guarantee and failure model.
2. Compare candidate protocol families.
3. Choose a protocol.
4. Implement it per partition.
5. Add strong conditional writes.
6. Test partitions/recovery.
7. Integrate topology/reconfiguration.
8. Benchmark against eventual mode.

## Completion conditions

- The strong mode's guarantee is stated precisely and tested.
- Conditional writes have unambiguous strong semantics.
- Failure behavior is explicit.
- Eventual mode remains available with its original meaning.
- Performance trade-offs are measured.

## On completion, persist

Persist the strong-mode guarantee/protocol in `DESIGN.md`; record consistency/protocol concepts in `STATE.md`.

## Optional deeper paths

- Offer relevant papers, proofs, implementation archaeology, or formal models when the
  learner asks and the material would deepen the topic without replacing the main path.
