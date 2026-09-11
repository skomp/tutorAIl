---
id: 15-eventual-replication
title: Eventual replication and causal versions
design_refs: [replication, durability, conditional-operations, topology]
validators: [cargo-check, cargo-test]
---

## Purpose

Replicate writes/reads across the static cluster while preserving concurrent versions instead of hiding conflicts with last-write-wins.

## Prerequisites

- The preceding course lesson.

## Learning objectives

- send writes to multiple replicas
- acknowledge only durable local writes
- support weak write/read policies
- observe stale reads deliberately
- represent causal version order
- preserve concurrent siblings
- return siblings to clients
- define conditional-write behavior under eventual consistency

## Theory

Eventual consistency permits stale observations. Version vectors compare versions that are observed but cannot prove that an uncontacted replica has no newer value. Concurrent versions must remain siblings until a resolution policy chooses otherwise. Durability at one replica and replication strength are separate dimensions.

## Concepts to teach

- causality
- version vectors/dotted variants
- concurrent siblings
- stale reads
- parallel client requests
- eventual conditional semantics

## Constraints

- Do not silently collapse concurrent writes with LWW.
- Keep replica acknowledgement tied to local durability.
- Make weak consistency observable in tests.
- Do not claim freshness merely because version metadata compares observed values.

## Suggested progression

1. Replicate writes in parallel.
2. Add configurable weak read/write policies.
3. Create stale-read tests.
4. Introduce causal version metadata.
5. Detect concurrent versions.
6. Return siblings through the driver.
7. Define conditional-write outcomes under weak reads.
8. Test network partitions and concurrent updates.

## Completion conditions

- Network partitions/concurrent writes can create preserved siblings.
- Weak reads can demonstrably be stale.
- Version metadata orders observed causality correctly.
- No replica acknowledgement violates the durability contract.
- Conditional-write semantics under eventual mode are documented and tested.

## On completion, persist

Persist causal metadata and eventual-consistency semantics in `DESIGN.md`; record replication/causality concepts in `STATE.md`.

## Optional deeper paths

- Offer relevant papers, proofs, implementation archaeology, or formal models when the
  learner asks and the material would deepen the topic without replacing the main path.
