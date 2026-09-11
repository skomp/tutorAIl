---
id: 00-foundations
title: Rust foundations through an in-memory KV store
validators: [cargo-check, cargo-run, cargo-test, manual]
---

## Purpose

Build the smallest useful in-memory key/value store while establishing the Rust
ownership and borrowing model that every later AutomatonDB component depends on.

The lesson begins with ordinary Cargo binary development and intentionally keeps the
data model simple. Structural complexity belongs later, after the learner has enough
Rust vocabulary to understand why a refactor is needed.

## Prerequisites

- Substantial programming experience in at least one other language.
- A working stable Rust toolchain.
- A terminal and editor.

## Learning objectives

- Create and run a Cargo binary project.
- Distinguish `String` from `&str`.
- Predict when values move and when they are borrowed.
- Use immutable and mutable references deliberately.
- Define functions, structs, methods, and associated constructors.
- Use `Vec<T>`, slices, iterators, and closures.
- Use `Option<T>` and `match`.
- Return borrowed values and understand why lifetimes appear.
- Use `&self` and `&mut self`.
- Replace a linear collection with `BTreeMap` when exact-key lookup demands it.
- Write and run ordinary Rust unit tests.

## Theory

Rust's ownership system is the central topic. Treat moves, immutable borrows, mutable
borrows, and lifetimes as a coherent model rather than a set of compiler obstacles.

A `String` owns heap-allocated UTF-8 bytes. An `&str` borrows a UTF-8 string slice.
Returning an `&str` from a database lookup therefore means the reference is tied to
data owned by the database.

Collection choice should follow semantics. A vector of entries teaches iteration and
borrowing, but exact-key lookup naturally motivates moving to a map.

## Concepts to teach

- Cargo project lifecycle
- variable bindings and mutability
- `String` and `&str`
- ownership and moves
- borrowing and deref coercion
- functions and return values
- structs and `impl`
- constructors as associated functions
- `Vec`, slices, iteration, closures
- `Option`, `Some`, `None`, `match`
- explicit and elided lifetimes
- `&self`, `&mut self`
- `BTreeMap`
- basic `#[test]` modules and assertions

## Constraints

- Give one learner task at a time.
- Do not provide complete solution code unless asked.
- Begin with a simple representation and let the need for `BTreeMap` emerge naturally.
- Do not introduce modules/workspaces merely for style.
- Keep every declaration connected to code the learner actually uses.
- Prefer compiler errors that teach ownership over artificial ownership quizzes.

## Suggested progression

1. Create `automaton-db` with Cargo and run the generated binary.
2. Experiment with bindings, `String`, `&str`, function arguments, moves, and borrows.
3. Introduce a small entry struct and a `Vec<Entry>`.
4. Implement insertion and exact lookup by iterating the vector.
5. Use `Option` to represent missing keys.
6. Encounter and reason about returning a borrowed value from stored data.
7. Move behavior into a `Database` type with methods using `&self` and `&mut self`.
8. Replace the linear entry vector with `BTreeMap<String, String>`.
9. Add tests that protect insert/replace/lookup semantics.
10. Remove obsolete representations once the map replaces them.

## Completion conditions

- `cargo check` succeeds.
- `cargo test` succeeds.
- The project contains an in-memory database using `BTreeMap<String, String>`.
- Exact `put` and `get` operations work.
- `get` returns a borrowed string value through `Option`.
- The old vector-entry representation is no longer required by the implementation.
- The learner can explain the difference between moving `String`, borrowing `&String`,
  and borrowing `&str`.
- The learner can explain why a returned borrowed value cannot outlive the database.

## On completion, persist

Record in `STATE.md` the Rust concepts actually demonstrated, especially ownership,
borrowing, `Option`, lifetime reasoning, methods, and the collection refactor.

Do not add learner-specific progress to `COURSE.md`.

## Optional deeper paths

- Inspect `BTreeMap` complexity and compare it with `HashMap`.
- Explore deref coercion from `&String` to `&str`.
- Explore iterator ownership differences for `Vec<T>`, `&Vec<T>`, and `&mut Vec<T>`.
