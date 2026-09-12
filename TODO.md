# TODO

Deferred work for tutorAIl. Each item records what is decided and what is measured,
so a later session does not repeat the investigation.

---

## Dry-run harness (sub-project B) — deferred 2026-09-12

Build a harness that tests a course before a learner pays for it. An agent plays the
learner. The agent walks the course one task at a time. The agent does not read ahead.
The harness reports sequencing defects.

### Why this matters

Lessons 04 and later have never been exercised in either bundle. The AutomatonDB course
has one real learner at lesson 03. The WebGL course has no learner at all.

A build of the software does not test the course. An agent that builds AutomatonDB reads
all 23 lessons at once. A learner cannot do this. Only a harness that follows the
one-task-at-a-time rule tests the sequencing.

The defects this finds are the defects that cause refunds:

- a completion condition that the earlier lessons cannot satisfy
- a `design_refs` entry that does not answer the question the lesson asks
- dead code that accumulates because a type arrives before anything uses it
- a lesson that depends on a concept no earlier lesson teaches

### Measured facts — do not re-derive

Verified 2026-09-12 on this machine:

- `claude -p` runs headless on Claude Code product authentication. It needs no API key.
- A one-shot headless prompt returns in about 5 seconds.
- `claude -p --resume <session-id>` carries conversation state between separate
  processes. A value stored in one invocation was recalled by a later invocation.
- `claude -p` accepts `--output-format json`, which returns the `session_id`.
- `claude -p` also accepts `--append-system-prompt`, `--model`, `--permission-mode`
  and `--max-turns`.

### Architecture

Run two separately addressed headless sessions. Drive both from one script.

```
harness script
  |
  +-- TUTOR session
  |     reads the runner skill, the bundle, STATE.md and one lesson
  |     writes exactly one task
  |
  +-- LEARNER session
  |     reads the task and the workspace only
  |     reads no lesson file, no COURSE.md and no DESIGN.md
  |     writes code, command output and questions
  |
  +-- writes a turn log, then reports the defects
```

The isolation is real. The learner runs in a different process with a different
conversation. The learner cannot read the lesson that teaches it.

One agent must not play both parts. Such an agent has already read the answer. Every
finding from such a run is worthless.

### Decisions to make when this starts

1. Start the tutor session cold on every turn. The runner keeps state in `STATE.md` and
   not in the conversation. A harness that resumes the tutor tests an easier case than a
   real learner. A cold tutor tests scenario E on every turn.
2. Limit a run to a range of lessons. A course of 19 lessons needs several turns for each
   lesson. Each turn calls two sessions. Measure the cost of one lesson before you run a
   whole course.
3. Decide how the harness detects a stalled run. A learner that cannot satisfy a
   completion condition must stop the run and report the lesson.

### Dependencies

None. The harness drives the runner, which works today. It does not need the bundle
toolkit (sub-project A).

---

## Follow-up from multi-catalogue support — 2026-09-12

Multiple catalogues with remote sources are implemented. See the design spec, section 7.
Two items remain. Both are outside the runner.

### Give `tutorail-bundles` its own `catalog.yaml`

Put a `catalog.yaml` in the root of `skomp/tutorail-bundles`. List that repository's
bundles with relative paths. A learner then adds the whole repository with one entry in
`~/.config/tutorail/catalogs.yaml`, and the bundles arrive with it.

Check the file with `validate_bundle.py --catalog <path> --portable`. The `--portable`
option refuses a bundle path that leaves the catalogue's own directory, which is the rule
a repository catalogue must satisfy.

The maintenance skills must generate this file. The `create-bundle` skill must offer to
write it.

### Update `README.md`

The README describes the two-file model. Section "Register one by adding it to your
catalogue" names `~/.config/tutorail/catalog.yaml` as the only user file. That file still
works, because the runner uses it when `catalogs.yaml` is absent. The README does not
mention `catalogs.yaml`, remote catalogues, or the cache.

The README also says that a `git` source "will fail explicitly rather than silently until
implemented". This is still true for a **bundle** source. It is no longer true for a
**catalogue** source, which is implemented. Separate the two words in the text.
