---
id: lifetimes-and-borrows
title: Borrowing, just enough to unblock the dispatch
generated: true
generated_at: 2026-09-11
kind: side-lesson
reason: "The learner cannot explain why count_lines takes &str rather than String"
after: lessons/00-hello-args.md
design_refs: [io-boundary, counting-rules]
validators: [cargo-check, explains-choice]
---

## Purpose

The learner wrote `count_lines(text: String)` and then had to clone the file contents to
call it twice. The main path does not stop to explain borrowing, and this learner cannot
continue without it. This detour teaches the smallest amount of borrowing that makes the
signature `&str` obviously right.

## Prerequisites

The crate compiles and both counting functions exist, whatever their signatures are.

## Learning objectives

- Say what a reference is, in terms of who owns the data.
- Explain why a function that only reads its argument should borrow it.
- Convert a `String` parameter to a `&str` parameter and fix the call sites.

## Theory

**Ownership is about who frees the value.** A `String` owns a heap buffer. Passing it by
value moves that ownership into the function, and the caller can no longer use it. That is
why the learner had to clone: the first call consumed the text.

**A reference borrows without moving.** `&str` is a view into text somebody else owns. The
function reads through it and gives nothing back to free. The caller keeps the `String`
and can call again.

**`String` coerces to `&str`.** A function that takes `&str` accepts a `String`, a
`&String` and a literal, because the compiler inserts the conversion. This is the reason
the borrowed form is the more useful parameter type, not merely the cheaper one.

## Concepts to teach

- Ownership, and what a move costs the caller.
- `&` as a read-only view.
- Why `&str` accepts more argument kinds than `String` does.

## Constraints

- No new crates, and no change to what the tool prints.
- The counting functions still do no input or output.

## Suggested progression

1. Call `count_words` twice on the same `String` and read the compiler error together.
2. Change one signature to `&str` and let the compiler point at the call sites.
3. Change the other, and remove the clone the learner added.

## Completion conditions

- Both counting functions take `&str` and return `usize`.
- `cargo check` passes with no errors and no clone remains in `main`.
- The learner can say, in their own words, why the borrowed parameter accepts more kinds
  of argument than the owned one.

## On completion, persist

- In `STATE.md`, record that the counting functions now borrow their input.
- Return to `lessons/01-subcommands/LESSON.md` and finish the usage-error task.
