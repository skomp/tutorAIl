---
id: 00-retained-log
title: An append-only log that survives a restart
design_refs: [record-offset-model, durability-boundary]
validators: [go-build, go-test]
---

## Purpose

Get records onto disk in an order that survives a restart, so every later lesson
has something durable to read from.

## Learning objectives

- Append a length-prefixed record to a segment file
- Assign each record the offset that is its index in the partition
- Read a record back by offset after reopening the file

## Theory

A log is the simplest durable structure that answers "what happened, in what
order". Everything else in this course is a view over it.

## Completion conditions

`go test ./...` passes, and a test that writes three records, closes the file,
reopens it and reads offset 1 returns the second record.
