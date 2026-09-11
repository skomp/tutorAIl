---
id: 11-automaton-aware-segments
title: Storage engine II: automaton-aware immutable segments
design_refs: [automaton-index, durability, deletion, temporal-semantics, key-ordering]
validators: [cargo-check, cargo-test]
---

## Purpose

Make immutable on-disk segments specific to AutomatonDB by integrating the finite-state key index, memory mapping, tombstones, and compaction.

## Prerequisites

- The preceding course lesson.

## Learning objectives

- design a sorted segment layout
- map accepting key states to records
- memory-map immutable structures
- introduce `unsafe` only behind explicit invariants
- merge memtable and segment views
- apply tombstone/expiry rules
- compact and replace segments safely

## Theory

Immutable segments enable stable offsets, memory mapping, and index structures that do not require ordinary heap reconstruction. `unsafe` is justified only where the implementation must express invariants the type system cannot encode directly; every unsafe operation needs a safe boundary with documented aliasing/lifetime/layout assumptions.

## Concepts to teach

- mmap
- zero-copy reads
- unsafe blocks
- safety invariants
- alignment/layout
- reader lifetimes
- compaction
- resource replacement

## Constraints

- Develop portably on macOS but treat Linux as the production optimization target.
- Never add `unsafe` merely because it might be faster.
- Readers must not observe unmapped/replaced storage.
- Compaction must preserve tombstone and temporal semantics.

## Suggested progression

1. Specify segment blocks and index mapping.
2. Write/read a minimal immutable segment.
3. Integrate the stored-key automaton.
4. Add mmap.
5. Document and encapsulate any unsafe operations.
6. Merge memtable/segments in reads.
7. Integrate tombstones/expiry.
8. Implement compaction and safe segment replacement.
9. Measure heap usage and traversal performance.

## Completion conditions

- Large immutable key sets can be queried without rebuilding the complete key set as ordinary heap structures.
- Unsafe code, if any, has explicit documented invariants and a safe external API.
- Compaction preserves visible data/deletion semantics.
- Reader lifetime remains correct across segment replacement.

## On completion, persist

Persist segment layout and unsafe invariants in `DESIGN.md`; record mmap/unsafe/compaction concepts in `STATE.md`.

## Optional deeper paths

- Offer relevant papers, proofs, implementation archaeology, or formal models when the
  learner asks and the material would deepen the topic without replacing the main path.
