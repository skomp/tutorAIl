---
id: 17-repair-convergence
title: Convergence and repair
design_refs: [replication, deletion, durability]
validators: [cargo-check, cargo-test]
---

## Purpose

Make eventual replicas converge after failures and connectivity restoration without operator reconstruction.

## Prerequisites

- The preceding course lesson.

## Learning objectives

- implement hinted handoff
- repair divergent reads
- design background anti-entropy
- detect divergence efficiently
- stream repair data
- propagate tombstones
- garbage-collect tombstones safely
- bound/prune causal metadata

## Theory

Eventual replication needs active convergence mechanisms because reads may never contact the newest replica. Tombstone deletion makes repair and garbage collection coupled: discarding a tombstone before every relevant replica has learned it can resurrect deleted data.

## Concepts to teach

- hinted handoff
- read repair
- anti-entropy
- Merkle-style divergence detection
- repair streams
- tombstone GC
- causal metadata pruning

## Constraints

- Repair must preserve sibling/causal semantics.
- Tombstone GC needs an explicit safety argument.
- Do not assume read traffic alone guarantees convergence.
- Test repairs across actual divergent replica states.

## Suggested progression

1. Add hinted handoff.
2. Add read repair.
3. Build background anti-entropy.
4. Add compact divergence detection.
5. Stream differences.
6. Integrate tombstones.
7. Define and test safe tombstone collection.
8. Measure/prune causal metadata growth.

## Completion conditions

- Disconnected replicas converge after reconnection without manual reconstruction.
- Deleted data does not resurrect under the tested GC assumptions.
- Repair preserves causal siblings.
- Background anti-entropy converges even without reads.

## On completion, persist

Persist repair and tombstone-GC invariants in `DESIGN.md`; record convergence concepts in `STATE.md`.

## Optional deeper paths

- Offer relevant papers, proofs, implementation archaeology, or formal models when the
  learner asks and the material would deepen the topic without replacing the main path.
