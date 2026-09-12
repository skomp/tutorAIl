# Design

## Record and offset model {#record-offset-model}

A record is an opaque byte string plus a timestamp. Its offset is its index
within one partition, assigned by the broker at append time and never reused.
Offsets are dense: partition n holds offsets 0..n-1 with no gaps.

## Durability boundary {#durability-boundary}

An append is acknowledged only after the segment file has been fsynced. A batch
of appends waiting on one fsync is a group commit, and every writer in the batch
is acknowledged together or not at all.
