# AutomatonDB Design

This document contains durable starting decisions for the course. Sections use stable
anchors so lessons can load only the design material they need. Deliberately unresolved
items are marked explicitly and are expected to be resolved in later lessons.

## Table model {#table-model}

Tables are first-class logical database objects with explicit schemas. A table contains
partitions; a partition contains rows; a row contains named cells.

A useful logical hierarchy is:

```text
Table
  PartitionKey -> Partition
                    ClusteringKey -> Row
                                       column name -> Cell
```

Internally, multiple tables may eventually share a uniform physical ordered keyspace,
but that physical representation must not erase the logical table boundary.

## Partition key {#partition-key}

A partition key is exact for normal queries, typed by the table schema, potentially
composite, canonically encoded, and hashed for physical placement.

Automata do not normally select partition keys. A normal query identifies one exact
partition. The stable placement hash is a distributed-system concern and is distinct
from any process-local hash used by a language collection.

## Clustering key {#clustering-key}

A clustering key is typed, ordered, potentially composite, and automaton-queryable.

Component-wise predicates are compiled internally into an automaton over the canonical
binary representation of the whole clustering key. This must support useful predicates
in the middle of a composite key rather than only literal prefixes.

## Key component types {#key-component-types}

The initial semantic type set includes UTF-8 text and signed 64-bit integers. Likely
later additions include unsigned 64-bit integers, fixed-length bytes, and timestamps.

Avoid floating point initially because total ordering is subtle.

Schema determines the type of each component. Therefore a type discriminator in every
encoded key component may be unnecessary.

**Unresolved:** final primitive type set and whether encoded components need explicit
type tags.

## Key ordering {#key-ordering}

All physical clustering keys need a deterministic total order suitable for sorted
storage, range traversal, automaton traversal, and comparison across nodes.

For values `a` and `b` under the same schema, semantic ordering must agree with the
lexicographic ordering of their canonical encoded bytes.

A temporary in-memory enum ordering may be used while learning, but it is not the final
physical database ordering. Valid schemas should prevent arbitrary cross-type
comparisons at the same key position.

## Row and cell model {#row-cell-model}

A logical row is identified by the pair `(partition key, clustering key)` and contains
named cells.

The cell name is not part of the row's primary key. It identifies a value within the
row, similar to named non-key columns in a wide-column/row-oriented logical model.

Values are not ultimately restricted to strings. The logical layer should support
typed named columns. At the storage boundary, bytes plus codecs may be preferable.

## Values and codecs {#values}

Logical rows contain named, typed value columns. Users should eventually be able to add
value encodings through a codec-like abstraction.

Keys are intentionally less extensible because routing, ordering, and indexing need to
understand their semantics.

**Unresolved:** exact boundary between schema-level typed values and storage-level
opaque bytes.

## Temporal semantics {#temporal-semantics}

A cell initially has optional `valid_from` and `expires_at` bounds. A row initially has
optional `expires_at`.

Cell visibility uses a half-open interval:

```text
[valid_from, expires_at)
```

with absent bounds treated as unbounded. Row expiry is a hard upper visibility bound
for every cell in that row.

At time `t`, a cell is visible only if every present bound allows it:

```text
cell.valid_from <= t
t < cell.expires_at
t < row.expires_at
```

TTL is an API convenience. Convert TTL to an absolute expiry time before replication.

Normal reads initially mean visible now. Deterministic internal and test APIs should
accept an explicit time rather than consulting the wall clock implicitly.

Row-level `valid_from` is deliberately deferred. If added later, absence of that bound
should preserve immediate visibility for older rows.

## Deletion {#deletion}

Support row deletion and individual-cell deletion using tombstone semantics so replicas
can distinguish deletion from absence.

Tombstone retention and safe garbage collection depend on distributed convergence and
must not be guessed in the early in-memory implementation.

## Atomicity {#atomicity}

The initial atomicity guarantee is one logical row write. Multiple changed cells in one
row commit atomically.

Two rows in the same partition are not initially transactional, and cross-partition
operations are not transactional.

Partition-scoped transactions may be added later as an explicit stronger feature.

## Conditional operations {#conditional-operations}

Single-row operations should eventually support compare-and-set/version conditions,
`IF NOT EXISTS`, and read-modify-write behavior.

Their guarantees must be defined against the selected consistency mode. Do not present
conditional syntax without stating its consistency semantics.

## Durability {#durability}

By default, a replica acknowledges a write only after the write is locally durable.

Replication quorum determines how many replica acknowledgements are required; it does
not redefine what one replica acknowledgement means.

A weaker explicit in-memory acknowledgement mode may be added later.

## Automaton index {#automaton-index}

The stored clustering-key set is a finite language.

A trie is the obvious baseline representation. Prefix states with identical
right-continuation languages can be merged, yielding a minimal acyclic deterministic
automaton (DAFSA-like) for the finite stored-key language.

Query languages are general regular languages and their DFAs may contain cycles.

The central query operation is related to the product/intersection of:

```text
query DFA × stored-key automaton
```

Traversal must support predicates in the middle of clustering keys and should prune
based on automaton state rather than degrade to prefix scan plus post-filtering.

Performance is a first-class concern. Educational implementations should be compared
with mature Rust regex/automata/FST libraries at explicit ecosystem/replacement
checkpoints.

## Placement {#placement}

Normal distributed queries contain one exact partition key. Canonical partition-key
bytes are hashed using a deliberately specified stable placement hash to determine
physical ownership.

That placement hash is not the same thing as the implementation-defined hash used by a
local `HashMap`, and the partition key itself remains the logical identity even if a
placement hash collides.

## Smart clients {#smart-clients}

Clients should have enough cluster and placement metadata to determine the physical
replicas for `(table, partition key)`.

Avoid making one storage node a mandatory query coordinator that fans every request out
to the rest of the cluster.

The Rust driver is implemented first, while the protocol remains language-neutral.

## Networking {#networking}

Use gRPC rather than inventing a custom wire protocol.

Networking exists to expose the database model and to teach relevant async/concurrency
concepts; custom protocol design is not a primary learning goal.

## Replication {#replication}

Start with eventual consistency. Preserve concurrent writes rather than silently
resolving them with last-write-wins.

Use causal version metadata such as version vectors or dotted variants; the exact form
is chosen later. Reads that observe concurrent siblings initially return all siblings
to the client.

Version metadata only orders versions that are actually observed. It cannot prove that
a contacted replica has the globally newest version.

Convergence therefore also needs hinted handoff, read repair, and anti-entropy.

## Quorums {#quorums}

Quorum behavior is an extensible subsystem, not a hard-coded synonym for majority.

Explore majority, weighted, grid, hierarchical/tree, topology-aware, and
cross-datacenter quorum systems. The driver/query planner should consume a quorum
policy rather than contain majority assumptions.

Users should ultimately be able to implement their own quorum policies.

## Strong consistency {#strong-consistency}

The course starts eventual and later adds a second, explicitly stronger consistency
mode.

The stronger mode must define its guarantee precisely before implementation.
Linearizability, quorum-register approaches, and consensus-based approaches should be
compared rather than conflated.

The cluster may remain masterless globally even if stronger partition-local semantics
introduce coordination.

## Membership {#membership}

Start with a deliberately simple home-grown gossip/membership mechanism, then study
failure suspicion, false positives, convergence, and mature alternatives.

The mature system may still use a custom implementation; the replacement decision is
about quality and guarantees, not an automatic preference for external code.

## Live reconfiguration {#live-reconfiguration}

The system should eventually support zero-downtime node add/remove, partition
reassignment, replica-set changes, replication-factor changes, rebalancing, and
failure-domain topology changes.

The first implementation may prioritize availability and permit explicitly defined
temporary consistency weakening.

A later advanced implementation may preserve configured consistency guarantees
throughout reconfiguration.

## Topology {#topology}

Replica placement should understand failure domains and datacenters from the beginning
of distributed design.

Topology information is required by placement, hierarchical quorums, cross-datacenter
quorums, and reconfiguration.

## Schema evolution {#schema-evolution}

Existing key/value schema elements cannot be removed, reordered, or change type.
Permitted changes append new components or columns.

Schema changes must eventually be online and versioned so old clients and nodes can
coexist with new ones.

**Unresolved:** what an old row means after a trailing clustering-key component is
appended to an existing table. Resolve this deliberately in the schema-evolution
lesson rather than earlier.
