---
id: 10-storage-durability
title: Storage engine I: durability
design_refs: [durability, atomicity, deletion, temporal-semantics]
validators: [cargo-check, cargo-test]
---

## Purpose

Give the local database a durable write path and crash-recovery model before distribution adds more failure modes.

## Prerequisites

- The preceding course lesson.

## Learning objectives

- design a WAL
- frame records and checksum them
- recover after partial/corrupt tails
- introduce a memtable
- make one logical row write atomic in the WAL
- acknowledge default writes only after durability
- flush immutable sorted segments

## Theory

Durability is a contract between an acknowledgement and recoverable storage state. A WAL converts in-memory mutation into an ordered durable record stream. Framing and checksums let recovery distinguish complete valid records from torn/corrupt tails. Row atomicity must be represented in the log record boundary.

## Concepts to teach

- filesystem I/O
- `Read`/`Write`
- buffering
- RAII
- `Drop`
- binary parsing
- error propagation
- crash testing

## Constraints

- Do not acknowledge a default write before the chosen durability point.
- Recovery must tolerate an interrupted final record.
- Do not rely on destructor timing alone for durability guarantees.
- Crash tests must exercise awkward boundaries, not only clean shutdown.

## Suggested progression

1. Specify WAL record invariants.
2. Write and read framed records.
3. Add checksums and corruption detection.
4. Replay into a memtable.
5. Represent one row mutation atomically.
6. Define flush/sync acknowledgement behavior.
7. Crash/restart at controlled points.
8. Flush a sorted immutable segment.

## Completion conditions

- A successful default write survives process restart.
- Recovery ignores or rejects an incomplete/corrupt tail safely.
- Row-atomic writes do not recover partially.
- Crash/recovery tests cover multiple interruption points.
- The durability acknowledgement contract is documented.

## On completion, persist

Persist WAL/durability invariants in `DESIGN.md`; record filesystem/RAII/error concepts in `STATE.md`.

## Optional deeper paths

- Offer relevant papers, proofs, implementation archaeology, or formal models when the
  learner asks and the material would deepen the topic without replacing the main path.
