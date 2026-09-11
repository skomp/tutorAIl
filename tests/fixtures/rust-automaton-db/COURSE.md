# Learn Rust by Building AutomatonDB

## Goal

Build an increasingly serious database while using it as the main vehicle for learning Rust.

The final system is a masterless, replicated, partitioned database with typed composite
keys and automaton-native ordered queries within partitions. The course has three equal
goals:

1. become a strong Rust engineer rather than merely completing one codebase;
2. learn distributed-systems engineering deeply enough to reason about guarantees and
   failure modes;
3. explore AutomatonDB's unusual automaton-oriented database design seriously enough
   that early implementation choices retain a credible path toward high performance.

Early implementations may be deliberately simple, but important APIs and abstractions
should not be deliberate dead ends.

## Prerequisites

This course assumes substantial prior programming experience. It does not assume prior
Rust experience. Familiarity with basic data structures and algorithms is expected.
Distributed-systems theory may be learned during the course.

## Teaching philosophy

The tutorial is conversational and adaptive. Give exactly one actionable learner task
at a time. Wait for evidence before advancing. Conceptual questions do not implicitly
advance the exercise.

The learner writes the implementation. Do not provide solution code unless explicitly
asked. When Rust syntax is genuinely unfamiliar, teach the concept and provide only the
minimum syntax needed rather than expecting the learner to guess language-specific
forms.

Compiler and test failures are learning opportunities. Explain the relevant Rust
concept, then let the learner fix the problem. Do not silently edit learner-owned code
unless the learner explicitly asks for that help.

Keep the implementation on a working vertical path. Do not accumulate disconnected
types, functions, fields, or features merely because they may be useful later. Repeated
dead-code warnings are useful feedback about tutorial sequencing, not harmless noise.
`cargo check` should remain a tool the learner can read directly.

Testing is first-class throughout the course. Start with ordinary unit tests, then add
property tests, crash/recovery tests, concurrency tests, multi-node fault tests,
protocol compatibility tests, fuzzing, and model/invariant-based testing when the
corresponding subsystems make those techniques useful.

Use stable Rust for the main path. Nightly features may be optional excursions.

For distributed systems, default to strong engineering theory: consistency models,
failure models, quorums, causality, clocks, convergence, membership, reconfiguration,
and CAP/PACELC where relevant. Mention deeper paper/proof paths when useful and follow
them when the learner asks.

For automata, indexing, storage structures, and binary encodings, go deeper by default.

At substantial component boundaries, perform an ecosystem checkpoint: inspect mature
current Rust crates, identify the strongest candidates, study their useful abstraction
boundaries, and decide whether to build an educational implementation behind a
compatible or analogous API. At major milestones, explicitly reconsider whether to
keep, improve, or replace self-built components.

Let project structure evolve under real pressure. Use refactors to teach modules,
visibility, library APIs, crate boundaries, workspaces, integration tests, and
dependency direction instead of front-loading a final architecture.

A bundle lesson may span multiple conversational task cycles. The tutor should break
its suggested progression into small learner-sized steps rather than dumping the whole
lesson at once.

## Course map

### 00 — Rust foundations through an in-memory KV store
Cargo lifecycle, strings and slices, ownership and borrowing, functions, structs,
`impl`, collections, iteration, `Option`, pattern matching, lifetimes, `&self`,
`&mut self`, `BTreeMap`, and early tests.

### 01 — Rows, cells, and temporal visibility
Replace the one-key/one-string model with logical rows containing named cells. Add
cell validity intervals, row expiry, deterministic visibility queries, and tests.

### 02 — Typed keys and the table hierarchy
Introduce typed key values, composite partition and clustering keys, key-column schema
types, partitions, table-level validation, `HashMap` versus `BTreeMap`, and explicit
errors.

### 03 — First deliberate refactor
Move engine code out of the binary, introduce a library surface and modules, learn
visibility and API boundaries, and use the refactor to make warnings and responsibilities
clearer.

### 04 — Tables and richer typed schemas
Strengthen table identity, typed value columns, richer primitive key types, schema
versions, codecs, and append-only schema rules.

### 05 — Canonical ordered binary keys
Define byte encodings whose lexicographic order agrees with semantic key order. Cover
tuples, signed/unsigned integers, text framing, fixed bytes, timestamps, malformed
input, and property-based invariants.

### 06 — Data and query algebra
Define table, partition, row, clustering key, cell, projection, selection, post-filtering,
absent/appended fields, and the typed query AST before building the execution engine.

### 07 — Ordered querying before automata
Use ordinary ordered structures for ranges, prefixes, tuple bounds, integer predicates,
streaming results, and iterator-based query execution.

### 08 — Automaton machinery
Build a small regex AST, Thompson NFA, epsilon closure, subset-construction DFA,
minimisation, finite-key trie/DAFSA machinery, product/intersection traversal, and
transition-representation benchmarks.

### 09 — Automaton-native typed key queries
Compile component-wise string, numeric, and fixed-byte predicates into one automaton
over canonical clustering-key bytes and intersect it with the stored-key automaton.

### 10 — Storage engine I: durability
Add WAL framing, checksums, crash recovery, memtables, row-atomic durable writes, and
immutable sorted segments.

### 11 — Storage engine II: automaton-aware immutable segments
Design automaton-indexed segment layout, memory mapping, safe zero-copy boundaries,
tombstones, compaction, and reader/segment lifetimes. Introduce `unsafe` only where a
clear invariant justifies it.

### 12 — Concurrency and async Rust
Cover threads, `Arc`, locks, atomics, channels, `Send`/`Sync`, async functions,
`Future`, polling, executors, `Waker`, `Pin`, cancellation, backpressure, and the
interaction between blocking storage and async servers.

### 13 — gRPC server and Rust driver
Define a language-neutral protobuf API, single-node service, Rust client, typed
keys/queries, streaming results, cancellation, backpressure, compatibility testing,
and error mapping.

### 14 — Static distributed cluster and placement
Introduce failure models, node identities, topology, stable partition hashing,
placement algorithms, replica selection, routing metadata, client-side node selection,
and stale-client handling.

### 15 — Eventual replication and causal versions
Implement replica writes/reads, weak consistency, stale reads, version vectors or
dotted variants, concurrent siblings, conditional-write semantics, and explicit
durability at each replica.

### 16 — General quorum systems
Make quorum behavior pluggable rather than hard-coded to majority. Explore majority,
weighted, grid, hierarchical/tree, topology-aware, and cross-datacenter quorum systems.

### 17 — Convergence and repair
Add hinted handoff, read repair, anti-entropy, divergence detection, repair streams,
tombstone propagation, safe tombstone GC, and causal metadata pruning.

### 18 — Gossip and membership
Build a deliberately simple membership protocol, then study gossip rounds, heartbeat
and suspicion mechanisms, false positives, failure detectors, partition behavior, and
mature alternatives.

### 19 — Live cluster reconfiguration
Support online node add/remove, replica-set changes, replication-factor changes,
rebalancing, topology transitions, versioned ownership, streaming, handoff, and
failure during movement.

### 20 — Online schema evolution
Distribute schema versions, preserve compatibility, append fields/components, define
old/new row coexistence, and make the unresolved semantics of appended clustering-key
components an explicit design decision.

### 21 — Strong consistency mode
Add a second, explicitly stronger consistency model. Define the guarantee precisely,
compare quorum-register and consensus approaches, integrate it per partition, and
support strong conditional operations.

### 22 — Hardening and performance
Systematically benchmark, profile, fuzz, inject faults, crash-test, simulate network
partitions, model invariants, add observability and CI, and establish reproducible
performance and compatibility testing.

## Milestone architecture reviews

Pause for an explicit architecture review around these milestones:

```text
M0  In-memory exact KV
M1  Row/cell temporal model
M2  Typed table/key model
M3  First library/module refactor
M4  Canonical ordered key encoding
M5  Query algebra
M6  Self-built automaton stack
M7  Automaton-native in-memory querying
M8  Durable local storage
M9  mmap/immutable automaton segments
M10 Concurrent local engine
M11 Single-node network service
M12 Static distributed cluster
M13 Eventual replication
M14 General quorum system
M15 Repair/convergence
M16 Gossip membership
M17 Live reconfiguration
M18 Online schema evolution
M19 Strong consistency mode
M20 Performance/hardening
```

At each review ask:

- Which assumptions have become wrong?
- Which APIs leak implementation details?
- Which responsibilities should be split?
- Which invariants are relied upon but undocumented?
- Which components should remain custom?
- Which components could now be swapped for a mature crate?
- Have performance requirements or failure assumptions changed?

## Rust coverage requirements

The main path should eventually exercise:

```text
Cargo and crates
variables and mutability
primitive types
String and &str
ownership, moves, and borrowing
slices
structs
enums
pattern matching
Option and Result
methods and associated functions
modules and visibility
collections
iterators and closures
traits
generics
associated types
lifetimes
conversion traits
error design
smart pointers
Arc
interior mutability
Mutex and RwLock
atomics
Send and Sync
threads
channels
async and await
Future, Poll, and Waker
Pin
cancellation and backpressure
filesystem I/O
binary representation
RAII and Drop
mmap
unsafe and safety invariants
unit/integration/property testing
fuzzing
benchmarking and profiling
macros and derive usage
Cargo workspaces
library/API design
refactoring across crate boundaries
platform/FFI APIs if naturally required
```

If an important Rust area never appears naturally in AutomatonDB, insert a compact side
exercise rather than leaving the gap.

## Optional paths

Optional later work may include historical/as-of reads, temporal queries, secondary
indexes, cross-partition automaton queries, partial continuation/routing indexes,
partition-scoped transactions, richer client-side sibling resolution, a textual query
language, more primitive key types, user-defined value codecs, backups/snapshots,
security/authentication/authorization, alternate compaction policies, very large
partition splitting, stronger reconfiguration guarantees, and deeper model checking
or formal verification.
