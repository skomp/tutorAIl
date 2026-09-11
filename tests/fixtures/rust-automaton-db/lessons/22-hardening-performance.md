---
id: 22-hardening-performance
title: Hardening and performance
design_refs: [automaton-index, durability, replication, live-reconfiguration, strong-consistency]
validators: [cargo-check, cargo-test, git-diff, manual]
---

## Purpose

Make systematic reliability, observability, fuzzing, profiling, and performance regression work a first-class final phase after testing has already been used throughout the course.

## Prerequisites

- The preceding course lesson.

## Learning objectives

- benchmark responsibly
- profile allocations and CPU
- benchmark automata/storage separately
- fuzz parsers/codecs/protocols
- inject crashes and distributed faults
- simulate network partitions
- model/check invariants
- add metrics/tracing
- establish CI and reproducible test clusters
- protect protocol/performance regressions

## Theory

Optimization requires measurement, and distributed correctness requires adversarial execution. Benchmarks need stable workloads and baselines; fuzzers target parser/state-space surprises; fault injection and model/invariant testing explore interleavings ordinary unit tests cannot cover.

## Concepts to teach

- benchmark methodology
- allocation profiling
- flamegraphs
- fuzzing
- fault injection
- model/invariant testing
- metrics
- tracing
- CI
- reproducibility

## Constraints

- Never optimize solely from intuition.
- Keep correctness tests separate from microbenchmarks.
- Include Linux-specific I/O experiments where production behavior differs from macOS.
- Treat performance regressions as testable engineering outcomes.

## Suggested progression

1. Establish benchmark baselines.
2. Profile allocation and CPU hot spots.
3. Benchmark automaton and storage paths.
4. Add fuzz targets.
5. Automate crash tests.
6. Inject network faults/partitions.
7. Add model/invariant tests.
8. Instrument metrics/tracing.
9. Build CI and reproducible clusters.
10. Perform a final architecture/replacement review.

## Completion conditions

- Critical parsers/codecs/protocols have fuzz coverage.
- Crash and network-partition tests run reproducibly.
- Performance baselines exist for key paths.
- Profiling has informed concrete changes.
- Metrics/tracing expose major system behavior.
- CI protects correctness and compatibility.
- A final architecture review identifies which custom components should remain or be replaced.

## On completion, persist

Record final architecture/replacement decisions in `DESIGN.md`; record hardening/performance techniques in `STATE.md`.

## Optional deeper paths

- Offer relevant papers, proofs, implementation archaeology, or formal models when the
  learner asks and the material would deepen the topic without replacing the main path.
