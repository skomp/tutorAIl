---
id: 00-dead-letter-stream
title: A dead letter stream that keeps its provenance
design_refs: [dead-letter-routing]
validators: [go-test]
---

## Purpose

Give a consumer somewhere to put a record it cannot process, so one bad record
stops neither the partition nor the consumer.

## Learning objectives

- Append a rejected record to a parallel stream
- Attach the rejection reason and the original offset
- Read the dead letter stream back and find the original record

## Theory

A dead letter stream is only useful if it says where the record came from.
Without the original offset it is a pile of bytes nobody can act on.

## Completion conditions

`go test ./...` passes, and a test that rejects one record of three finds the
rejected record in the dead letter stream with its original offset.
