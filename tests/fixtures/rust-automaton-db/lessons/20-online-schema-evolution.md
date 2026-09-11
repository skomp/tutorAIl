---
id: 20-online-schema-evolution
title: Online schema evolution
design_refs: [schema-evolution, table-model, key-component-types, values]
validators: [cargo-check, cargo-test]
---

## Purpose

Evolve table schemas online across clients/nodes while preserving the append-only compatibility model and resolving old/new row semantics deliberately.

## Prerequisites

- The preceding course lesson.

## Learning objectives

- version distributed schemas
- propagate schema updates
- support client/server version compatibility
- append value columns
- append key components
- interpret old rows under new schemas
- keep encodings/querying compatible across versions

## Theory

Schema evolution changes both interpretation and sometimes physical encoding. Version coexistence is unavoidable during online rollout. Append-only rules reduce incompatibility but do not automatically define what a missing trailing clustering component means for already-stored rows.

## Concepts to teach

- versioned metadata
- compatibility rules
- schema propagation
- mixed-version operation
- migration semantics

## Constraints

- No permitted schema change requires downtime.
- Existing fields/components cannot be removed/reordered/retyped.
- Resolve the old-row trailing-clustering-component semantics explicitly here.
- Test mixed-version clients/nodes.

## Suggested progression

1. Distribute schema version identity.
2. Propagate updates.
3. Define compatibility negotiation.
4. Append value columns.
5. Append key components.
6. Resolve semantics for pre-existing rows.
7. Make encodings/querying version-aware.
8. Run mixed-version tests.

## Completion conditions

- Permitted schema changes occur without downtime.
- Old/new clients and nodes coexist within documented compatibility rules.
- The previously unresolved old-row semantics is explicitly decided and tested.
- Queries behave predictably across supported schema versions.

## On completion, persist

Persist the resolved schema-evolution semantics in `DESIGN.md`; record compatibility/versioning concepts in `STATE.md`.

## Optional deeper paths

- Offer relevant papers, proofs, implementation archaeology, or formal models when the
  learner asks and the material would deepen the topic without replacing the main path.
