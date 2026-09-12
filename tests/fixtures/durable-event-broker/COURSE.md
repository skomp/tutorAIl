# Build a Durable Event Broker

## The goal

By the end of this course you have a single-node event broker you wrote
yourself: producers append records, consumers read them back at their own pace,
and a restart loses nothing that was acknowledged.

## How this course teaches

You write every line of the broker. The tutor sets one task at a time, reads
what you wrote, and moves on when the code does what the task asked.

## Topics this course must cover

- retained event logs
- partition offsets
- topic partitions
- group commit
- crash recovery

## Where this course stops

Replication, multi-node placement and query languages are outside this course.
The follow-ups named in `tutorial.yaml` are where those live.
