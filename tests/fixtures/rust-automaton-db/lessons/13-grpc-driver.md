---
id: 13-grpc-driver
title: gRPC server and Rust driver
design_refs: [networking, smart-clients, table-model, conditional-operations]
validators: [cargo-check, cargo-test]
---

## Purpose

Expose the local engine through a language-neutral network boundary and build the first Rust driver without inventing a custom protocol.

## Prerequisites

- The preceding course lesson.

## Learning objectives

- define protobuf messages for typed keys and operations
- version the API deliberately
- build a single-node gRPC service
- build a Rust client
- stream result sets
- propagate cancellation/backpressure
- map internal errors to protocol errors
- test compatibility

## Theory

A wire protocol is a long-lived compatibility boundary. Protobuf/gRPC gives language neutrality and mature tooling so the course can focus on database semantics and async behavior. Internal Rust types should not leak directly into the protocol merely because serialization is convenient.

## Concepts to teach

- protobuf schemas
- code generation
- async service traits
- streaming RPCs
- error mapping
- protocol compatibility testing

## Constraints

- Perform an ecosystem checkpoint and use a mature Rust gRPC/protobuf stack.
- Keep the protocol language-neutral.
- Do not require server-side fanout for ordinary exact-partition requests.
- Treat cancellation and streaming backpressure as semantics, not polish.

## Suggested progression

1. Review current gRPC crates.
2. Define a minimal protobuf schema.
3. Serve single-node put/get operations.
4. Build a Rust client.
5. Add typed query messages.
6. Add result streaming.
7. Add cancellation/backpressure.
8. Map errors deliberately.
9. Add compatibility tests.

## Completion conditions

- A client can use the database through gRPC.
- Protocol messages represent typed keys without relying on Rust-specific layout.
- Streaming results honor cancellation/backpressure.
- Internal errors map consistently to protocol errors.
- Compatibility tests protect the published schema.

## On completion, persist

Persist protocol/API decisions in `DESIGN.md`; record gRPC/streaming/error-mapping concepts in `STATE.md`.

## Optional deeper paths

- Offer relevant papers, proofs, implementation archaeology, or formal models when the
  learner asks and the material would deepen the topic without replacing the main path.
