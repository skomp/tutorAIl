# Build a Streaming Query Engine

## The goal

By the end of this course you have a query engine that reads a partitioned event
log and answers questions about it, both as a one-off over a fixed range and as
a standing query that keeps emitting as records arrive.

## How this course teaches

You write the parser, the plan and every operator. The tutor sets one task at a
time and reads what you wrote before moving on.

## What you are assumed to bring

This course does not teach the log it queries. `tutorial.yaml` lists the
concepts it assumes and how well you are expected to know each of them; read
that list and decide for yourself. Nothing checks it, and nothing asks you to
prove you took another course.

## Topics this course must cover

- stream query parsing
- bounded stream queries
- continuous stream queries
- windowed aggregation
- late and out-of-order records

## Where this course stops

Storage, replication and broker internals are outside this course. It reads a
log someone else's broker wrote.
