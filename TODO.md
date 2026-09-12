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

### What it must exercise once optional lessons exist — added 2026-09-12

The offer, defer and re-offer path has no test of any kind. The validator checks the
shape of `optional_lessons`, `failure_modes` and the `## Optional lessons` record in
`STATE.md`; nothing checks the behaviour those fields exist to produce.

A harness run must cover both paths in `bundle-format.md` section 12:

1. The learner accepts the lesson when it is first offered.
2. The learner defers it, meets the anticipated failure several lessons later, is told
   the connection, takes the lesson, and returns to repair the work `repair_in` names.

Three behaviours are the ones most likely to be wrong and are invisible to the validator:

- the tutor must not raise a deferred offer again with no new evidence;
- the tutor must not offer a lesson it has already recorded `complete`;
- a failure that persists after the lesson completed must become ordinary coaching, not
  another offer.

A learner agent that defers everything also tests the invariant nothing else can: that
the course finishes with every offer declined.

---

## Follow-up from multi-catalogue support — 2026-09-12

Multiple catalogues with remote sources are implemented. See the design spec, section 7.
One item remains, and it is outside the runner. Two others were closed on 2026-09-12 and
removed from this file: `tutorail-bundles` has its own `catalog.yaml`, and `README.md`
describes `catalogs.yaml` and the cache.

### Say in a catalogue that a course carries optional lessons — 2026-09-12

A catalogue entry carries `scope`, derived from the length of the manifest's `lessons`
list. A course with optional lessons has work the number does not describe:
`durable-event-broker` reads as "15 lessons; a few weeks" and also ships three optional
lessons, which a learner choosing between courses cannot see.

Deriving `scope` from the main path alone is right — the optional lessons are not part of
the sequence and a learner may decline every one of them. What is missing is a separate
signal. Decide between a count in `scope` ("15 lessons, 3 optional"), a dedicated field,
and leaving it out because a catalogue entry should stay short.

The change is in `tutorail-authoring`'s `catalog.py` and in `catalogue-format.md`, not in
the runner. Nothing is blocked on it: an unlisted optional lesson is still offered at the
point its bundle names.

---

## Wording follow-up after `supplies:` merges — owed 2026-09-12

Decisions 8 and 9 in the design spec settled two behaviours. The reference documents still
describe them in wording that admits the reading we ruled out. **Neither is a format
change** — no key added, no key removed, nothing an authored bundle must do differently.

**Do this only after the `supplies:` branch has merged**, and as its own commit. Two
unrelated contract changes in one diff put both in front of one reviewer.

### `bundle-format.md`, `runner-protocol.md`

A `required_for` gate is on the **failure standing**, not on the lesson having been taken.
The current phrase "cannot be completed while an anticipated failure stands" is correct but
reads both ways, and `required_for` being described as "the one way an optional lesson stops
being optional" pulls toward the wrong one.

A learner who declined the optional lesson and meets the gate gets the repair **coached
inline** in the current lesson — no transition, no fresh offer — and the gate opens when the
failure clears. Without this, the only exit is a lesson the learner refused twice, which
contradicts the rule that a course must be completable by a learner who declines every offer.

### `runner-protocol.md`, `state-lifecycle.md`

A complete lesson is **never** re-offered, whatever recurs. A failure that persists after its
lesson was taken is ordinary coaching, permanently. The loop guard is the feature.

Recurrence is evidence about the **lesson**, not the learner. It belongs to the quality
checker and the dry-run harness, not to the tutor mid-course.

### How to know the branch landed

Do not wait to be told. `git log --oneline` on main, or check whether `validate_bundle.py`
has a check 22 and `bundle-format.md` mentions `supplies`.
