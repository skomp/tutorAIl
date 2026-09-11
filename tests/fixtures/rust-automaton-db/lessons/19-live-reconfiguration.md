---
id: 19-live-reconfiguration
title: Live cluster reconfiguration
design_refs: [live-reconfiguration, placement, topology, replication]
validators: [cargo-check, cargo-test]
---

## Purpose

Change ownership and replica sets while serving traffic, beginning with an availability-first transition model and making consistency weakening explicit.

## Prerequisites

- The preceding course lesson.

## Learning objectives

- version ownership metadata
- represent old/new replica sets
- stream partitions during movement
- handoff writes safely
- refresh stale clients
- change replication factor
- survive failure during movement
- reason about consistency during transitions

## Theory

Reconfiguration is a distributed protocol, not a metadata edit. During movement, old and new owners may both matter; clients can carry stale routing views; and failures can interrupt streaming. The transition model must define which replicas accept writes and what consistency guarantee applies.

## Concepts to teach

- versioned ownership
- transition states
- data streaming
- handoff
- stale-client redirects
- RF changes
- reconfiguration failure modes

## Constraints

- Serve traffic throughout the basic transition.
- If consistency weakens, state the weakening precisely.
- Never assume all clients refresh routing simultaneously.
- Test failures in the middle of movement.

## Suggested progression

1. Version ownership metadata.
2. Model old/new replica sets.
3. Add partition streaming.
4. Route writes during transition.
5. Refresh/redirect stale clients.
6. Handle node add/remove.
7. Handle RF increase/decrease.
8. Inject failures during each transition phase.
9. Evaluate a stronger reconfiguration protocol as an advanced path.

## Completion conditions

- Nodes can be added/removed without planned downtime.
- Replica sets/RF can change online.
- Interrupted movement has a recoverable state.
- Stale clients have defined behavior.
- Any temporary consistency weakening is explicitly documented and tested.

## On completion, persist

Persist the reconfiguration state machine and guarantees in `DESIGN.md`; record transition-protocol concepts in `STATE.md`.

## Optional deeper paths

- Offer relevant papers, proofs, implementation archaeology, or formal models when the
  learner asks and the material would deepen the topic without replacing the main path.
