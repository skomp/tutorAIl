---
id: 02-typed-keys-table-hierarchy
title: Typed keys and the table hierarchy
design_refs: [table-model, partition-key, clustering-key, key-component-types, key-ordering, row-cell-model, values]
validators: [cargo-check, cargo-test, manual]
---

## Purpose

Introduce enough schema and key structure to stop treating every row key as one string,
while immediately connecting each new type to a working table write path.

The lesson establishes the hierarchy:

```text
Table
  PartitionKey -> Partition
                    ClusteringKey -> Row
                                       column name -> Cell
```

without yet solving final binary encoding or rich schema evolution.

## Prerequisites

- `01-rows-cells-temporal`

## Learning objectives

- Model heterogeneous scalar key values with enums carrying data.
- Distinguish a scalar key value from a composite partition/clustering key.
- Understand why schema column names/types are separate from runtime key tuples.
- Learn derived equality, hashing, partial ordering, and total ordering.
- Understand how derived enum ordering treats variant order.
- Use `HashMap` where exact partition lookup is the semantic operation.
- Use `BTreeMap` where clustering-key order is semantically important.
- Use the `Entry` API and `or_insert_with` to create nested structures lazily.
- Validate key lengths and component types before mutating storage.
- Introduce `Result` and an explicit error enum for malformed keys.

## Theory

The complete logical row identity is `(PartitionKey, ClusteringKey)`. A partition key
selects a partition; a clustering key identifies and orders a row within that
partition.

Both keys may contain multiple typed components. Component names live in the table
schema, not in each runtime key instance. The schema provides meaning such as
`category: Utf8`; the runtime key stores the corresponding ordered value tuple.

For the provisional in-memory representation, derived enum `Ord` may establish a total
order between variants by declaration order. That satisfies `BTreeMap`, but it is not
the final database byte ordering. Valid schema positions should prevent meaningful
cross-type comparisons at one position.

`HashMap`'s process-local hashing is only an implementation detail for exact local
lookup. Distributed placement later uses a specified stable hash over canonical
partition-key bytes.

## Concepts to teach

- enums with associated data
- `matches!`
- `PartialEq`, `Eq`, `Hash`, `PartialOrd`, `Ord`
- recursive trait requirements through `Vec<T>`
- lexicographic vector ordering
- `HashMap` versus `BTreeMap`
- `Entry` and `or_insert_with`
- `Result<T, E>`
- domain error enums
- schema/runtime separation
- validation-before-mutation

## Constraints

- Start with UTF-8 and signed 64-bit key values.
- Do not pretend derived enum ordering is the final physical key encoding.
- Keep the partition key and clustering key as distinct Rust types even if both contain
  vectors of the same scalar type.
- Do not store schema column names redundantly inside every runtime key.
- Every introduced key/schema declaration should be connected promptly to a real
  validation or storage path.
- Validate both component count and type before creating a partition or row.
- Invalid keys must not panic and must not be confused with the absence of a previous
  cell value.

## Suggested progression

1. Introduce a `KeyValue` enum with UTF-8 and signed 64-bit variants.
2. Introduce distinct composite `PartitionKey` and `ClusteringKey` types.
3. Add only the traits demanded by `HashMap` and `BTreeMap`, using compiler diagnostics
   to understand recursive trait bounds.
4. Introduce `Partition` and establish `ClusteringKey -> Row`.
5. Introduce `KeyType` and `KeyColumn` only when they are immediately used to validate
   runtime key values.
6. Introduce `Table` as the owner of partition/clustering schema and the partition map.
7. Use `KeyColumn::matches` to connect schema types to runtime `KeyValue` variants.
8. Implement the hierarchical write path with entry APIs.
9. Add explicit table errors for invalid partition and clustering keys.
10. Validate shape and type before mutating the table.
11. Add tests for valid writes, replacement results, wrong key lengths, wrong key types,
    and absence of mutation after invalid input.

## Completion conditions

- `cargo test` succeeds.
- Runtime scalar keys support at least UTF-8 and signed 64-bit values.
- Partition and clustering keys are distinct composite types.
- A table owns partition-key and clustering-key column definitions.
- Exact partitions use a `HashMap`; ordered rows within a partition use a `BTreeMap`.
- Invalid partition/clustering key length or type returns a distinct error.
- Invalid input creates neither a partition nor a row.
- A valid table write reaches the named cell through partition and clustering keys.
- The learner can explain why the local `HashMap` hash is unrelated to future placement
  hashing.
- The learner can explain the temporary meaning of derived enum ordering.

## On completion, persist

Record the key/schema/collection/error concepts demonstrated in `STATE.md`.

Persist any changes to key semantics or the logical table hierarchy in the referenced
`DESIGN.md` sections.

## Optional deeper paths

- Compare `matches!` with a full `match` expression.
- Explore why there is no universal standard-library Kotlin-style `.apply()` and how
  ownership modes (`T`, `&T`, `&mut T`) affect such APIs.
- Inspect `Hash`, `Eq`, and `Ord` trait contracts.
