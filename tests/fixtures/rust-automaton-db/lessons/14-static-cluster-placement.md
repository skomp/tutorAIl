---
id: 14-static-cluster-placement
title: Static distributed cluster and placement
design_refs: [placement, topology, smart-clients, partition-key]
validators: [cargo-check, cargo-test]
---

## Purpose

Distribute partitions across a static set of nodes and make the smart client determine which physical replicas own an exact partition.

## Prerequisites

- The preceding course lesson.

## Learning objectives

- define node identities and failure assumptions
- represent datacenter/failure-domain topology
- hash canonical partition keys stably
- compare placement algorithms
- select topology-aware replica sets
- publish routing metadata
- handle stale routing generations
- support host-process, Docker Compose, and mixed development modes

## Theory

Placement maps logical partitions to replica sets. The placement function must be deterministic across clients/nodes and must distinguish failure domains. Routing metadata is versioned because smart clients can become stale during cluster changes.

## Concepts to teach

- stable hashing
- placement algorithms
- topology models
- epochs/generations
- client-side routing
- multi-process testing

## Constraints

- Normal queries must not require a mandatory server coordinator.
- Do not use Rust `HashMap` hashing as placement semantics.
- Address advertisement must work across host and container environments.
- Topology must be present before later topology-aware quorums.

## Suggested progression

1. Define static cluster config and node IDs.
2. Define failure domains/datacenters.
3. Implement stable partition hashing.
4. Compare/select placement strategy.
5. Compute replica sets.
6. Expose routing metadata to the client.
7. Add routing generation handling.
8. Run multi-process and Compose clusters.
9. Exercise mixed host/container debugging.

## Completion conditions

- The same partition key maps to the same replica set across processes.
- Replica selection honors configured failure domains.
- A Rust client can determine nodes for a request without server-side fanout.
- Stale routing metadata has defined behavior.
- The development cluster works in at least local multi-process and Compose modes.

## On completion, persist

Persist placement/topology/routing decisions in `DESIGN.md`; record distributed-routing concepts in `STATE.md`.

## Optional deeper paths

- Offer relevant papers, proofs, implementation archaeology, or formal models when the
  learner asks and the material would deepen the topic without replacing the main path.
