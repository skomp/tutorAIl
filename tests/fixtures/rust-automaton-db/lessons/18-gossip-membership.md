---
id: 18-gossip-membership
title: Gossip and membership
design_refs: [membership, topology, live-reconfiguration]
validators: [cargo-check, cargo-test]
---

## Purpose

Replace static membership knowledge with a deliberately simple gossip-based system and reason about failure suspicion and convergence.

## Prerequisites

- The preceding course lesson.

## Learning objectives

- disseminate membership state
- run gossip rounds
- track liveness signals
- separate failure suspicion from proof
- measure false positives
- reason about partitioned-cluster views
- compare with mature membership protocols

## Theory

In an asynchronous network, timeout-based failure detection produces suspicion rather than certainty. Gossip spreads state probabilistically; convergence speed and false-positive behavior depend on fanout, timing, and failure detector design.

## Concepts to teach

- gossip dissemination
- heartbeats
- failure suspicion
- failure detectors
- probabilistic convergence
- partition behavior

## Constraints

- Start simple enough to understand every state transition.
- Do not treat a missed heartbeat as proof of failure.
- Keep topology metadata compatible with placement/reconfiguration.
- Perform a replacement checkpoint against mature protocols.

## Suggested progression

1. Disseminate static membership via gossip.
2. Add liveness/heartbeat information.
3. Introduce suspicion state.
4. Create delay/packet-loss tests.
5. Observe false positives.
6. Test partition/split views.
7. Compare with mature membership designs.
8. Harden or replace behind the existing abstraction.

## Completion conditions

- Membership state converges in healthy networks.
- Failure suspicion behavior is explicit and tested under delay/loss.
- Network partitions produce understood views rather than undefined behavior.
- A replacement checkpoint records whether the custom design remains appropriate.

## On completion, persist

Persist membership/failure-detector semantics in `DESIGN.md`; record gossip/failure-detection concepts in `STATE.md`.

## Optional deeper paths

- Offer relevant papers, proofs, implementation archaeology, or formal models when the
  learner asks and the material would deepen the topic without replacing the main path.
