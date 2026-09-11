---
id: 03-reading-files-draft
title: Reading the file without panicking
generated: true
generated_at: 2026-09-11
kind: main-path-draft
reason: "COURSE.md maps a fourth chapter on file reading that has no lesson file yet"
after: lessons/02-errors-and-tests.md
design_refs: [error-model, io-boundary]
validators: [cargo-check, cargo-test]
---

## Purpose

`COURSE.md` maps a chapter on reading the file properly, and the bundle ships no lesson
for it. This draft covers that chapter, written against the code this learner actually
has: one `expect` on the file read, and two counting functions that already borrow.

## Prerequisites

Lesson `02-errors-and-tests` finished, so `Result` and `?` are familiar.

## Learning objectives

- Replace the `expect` on the file read with a reported failure.
- Name the path in the message, and exit with the status the design assigns.
- Write a test that proves a missing file does not panic.

## Theory

**A failure the user can cause is a result, not a defect.** A path that does not exist is
an ordinary outcome of running the tool. It travels as `Result`, and it is reported as a
sentence on standard error.

**The message must name the path.** "No such file or directory" without the path makes the
user guess which argument was wrong.

## Material in this lesson

- `worked-example.rs` — the same file-reading shape written for a different tool, so it
  shows the structure without giving away this one. Offer it after the learner has tried
  a version of their own and is stuck on where the `?` goes.

## Concepts to teach

- `std::fs::read_to_string` and the `Result` it returns.
- Reporting an error with the value that caused it.
- Exit statuses as an interface, not as decoration.

## Constraints

- No new crates.
- The counting functions keep their signatures and still do no input or output.

## Suggested progression

1. Read the failing run together with the learner and name what the panic told them.
2. Replace the `expect` with a match on the `Result`.
3. Add the path to the message, and check the exit status from the shell.
4. Add a test for the missing-file path.

## Completion conditions

- No `expect` and no `unwrap` remains in `main`.
- A missing file prints a message naming the path on standard error and exits with `1`.
- `cargo test` passes, including a test for the missing-file path.

## On completion, persist

- In `STATE.md`, record that the marked `expect` is gone.
- If this draft proves useful, the bundle author copies it into `lessons/` and lists it.
