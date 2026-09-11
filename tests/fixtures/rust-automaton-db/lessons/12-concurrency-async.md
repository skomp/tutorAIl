---
id: 12-concurrency-async
title: Concurrency and async Rust
design_refs: [durability, atomicity]
validators: [cargo-check, cargo-test]
---

## Purpose

Give the local engine a defensible concurrency model and teach Rust's thread-safety and async execution model deeply enough to reason about the networked service.

## Prerequisites

- The preceding course lesson.

## Learning objectives

- use threads and ownership transfer
- share state with `Arc`
- choose locks deliberately
- use channels
- understand `Send` and `Sync`
- understand `Future`, polling, executors, `Waker`, and `Pin`
- reason about cancellation and backpressure
- integrate blocking storage with async code

## Theory

Rust's concurrency safety comes from ownership plus `Send`/`Sync` trait bounds, not from an absence of synchronization. Async Rust is cooperative state-machine execution: futures are polled, wakers schedule progress, and pinning protects self-referential state where movement would be unsound.

## Concepts to teach

- threads
- `Arc`
- `Mutex`/`RwLock`
- atomics
- channels
- `Send`/`Sync`
- async/await
- `Future`
- `Poll`
- `Waker`
- `Pin`
- cancellation
- backpressure

## Constraints

- Choose synchronization from actual access patterns rather than wrapping everything in one mutex.
- Do not block executor threads with storage work accidentally.
- Use Tokio after understanding the conceptual model rather than reimplementing a production runtime.
- Offer a tiny-executor side path only if the learner wants it.

## Suggested progression

1. Introduce threads with owned data.
2. Share engine state through `Arc`.
3. Add the smallest justified synchronization.
4. Use channels for ownership transfer where natural.
5. Inspect `Send`/`Sync` compiler constraints.
6. Build/inspect simple futures and polling.
7. Explain wakers and pinning.
8. Adopt Tokio.
9. Add cancellation/backpressure and a blocking-I/O strategy.
10. Stress-test concurrent operations.

## Completion conditions

- Concurrent local operations preserve documented invariants.
- `cargo test` succeeds under concurrency tests.
- The learner can explain why a relevant type is or is not `Send`/`Sync`.
- The learner can explain polling, wakeups, and why `Pin` exists at a practical level.
- Async code does not accidentally perform unbounded blocking work on executor threads.

## On completion, persist

Persist the engine concurrency model in `DESIGN.md`; record concurrency/async concepts in `STATE.md`.

## Optional deeper paths

- Offer relevant papers, proofs, implementation archaeology, or formal models when the
  learner asks and the material would deepen the topic without replacing the main path.
