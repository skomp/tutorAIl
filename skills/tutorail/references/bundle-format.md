# Tutorial Bundle Format — Authoring Contract

**Format version:** `bundle_format: 1`
**Status:** normative. A bundle that violates a MUST in this document is invalid.

This document is self-contained. You need nothing else to author a bundle.

---

## 0. Start here

A **bundle** is a course. It is written once and used by many learners.

An **instance** is one learner's copy of that course, with their progress in it.

**You are authoring a bundle. You are not authoring an instance.**

This is the single most common mistake, and it is easy to make when you already know
how one particular learner's run went. Everything you know about *a learner's progress*
must be left out of what you write.

| You know | Where it goes |
|---|---|
| What the course teaches | the bundle — you are writing this |
| The order of the lessons | the bundle |
| Design decisions about the subject | the bundle |
| That lesson 7 is finished | **not the bundle** |
| That the learner is on lesson 8 | **not the bundle** |
| What the learner's code looks like now | **not the bundle** |
| Which tests currently pass | **not the bundle** |

A bundle is used by a learner who has not started yet. Author it for them.

---

## 1. Layout

A bundle is a directory:

```
<bundle-name>/
├── tutorial.yaml         MUST exist
├── COURSE.md             MUST exist
├── DESIGN.md             MUST exist
├── STATE.template.md     MUST exist
└── lessons/              MUST exist, MUST contain at least one lesson
    ├── 00-<slug>.md              a lesson as a single file
    ├── 01-<slug>/                a lesson as a folder, when it has material
    │   ├── LESSON.md             the lesson itself; exact name, exact case
    │   └── <anything else>       diagrams, data, examples, references
    ├── <slug>.md                 an optional lesson: off the main path, no
    │                             number prefix, offered rather than sequenced
    └── ...
```

Every lesson lives in `lessons/`, whether the learner reaches it by walking the course
or by accepting an offer. There is no second lesson directory in a bundle.

### The rule that separates a bundle from an instance

> A bundle **MUST** contain `STATE.template.md`.
> A bundle **MUST NOT** contain `STATE.md`.

`STATE.md` is created by the runner when a learner starts the course. It does not exist
until then. If you have written a `STATE.md`, you have written an instance by mistake:
delete it, and move anything in it that describes *the course* (not the learner) into
`COURSE.md`, `DESIGN.md`, or a lesson.

There is no exception. A bundle containing `STATE.md` is rejected.

A second directory is instance-only in exactly the same way: `lessons.generated/`, where a
tutor writes lessons during a course. A bundle MUST NOT contain one. Section 8 says what
to do when you find one, and how to promote a lesson out of it properly.

---

## 2. `tutorial.yaml`

Keep it shallow. One level of nesting at most.

```yaml
bundle_format: 1
id: rust-automaton-db
title: Learn Rust by Building AutomatonDB
description: >
  Project-driven Rust taught by building a masterless, partitioned,
  automaton-indexed database from scratch.
subjects: [rust, databases, distributed-systems]
aliases: [cassandra-like, storage-engine]
level: intermediate-to-advanced
style: [project-driven, interactive, long-form]

lessons:
  - lessons/00-foundations.md
  - lessons/01-rows-cells-temporal.md
  - lessons/02-typed-keys-table-hierarchy.md

optional_lessons:
  lessons/interior-mutability.md:
    offer_at:      [lessons/02-typed-keys-table-hierarchy.md]
    offer_because: >
      A shared cache behind an immutable handle needs interior mutability, and
      the borrow checker will not explain which tool to reach for.
    anticipates:   [shared-cache-needs-refcell]
    repair_in:     lessons/02-typed-keys-table-hierarchy.md

failure_modes:
  shared-cache-needs-refcell:
    summary: >
      Two owners need to mutate one cache, so the design grows a clone per
      call rather than a shared cell.
    signals: [validator:cargo-check, diagnosis]

workspace_kind: existing-or-new-repository
tutor_owned:    [tutorial/STATE.md, tutorial/DESIGN.md]
learner_owned:  [src/**, tests/**, Cargo.toml]
ownership_policy: tutor-must-not-edit-learner-owned

validators:
  cargo-check: { kind: command, command: [cargo, check] }
  cargo-test:  { kind: command, command: [cargo, test] }
  has-lib:     { kind: file-exists, path: src/lib.rs }

one_task_at_a_time: true
solution_code: on-request-only
advance_on: validated-evidence-only
```

### Field reference

| Field | Required | Meaning |
|---|---|---|
| `bundle_format` | MUST | Always `1` for this document. |
| `id` | MUST | Stable, unique, `[a-z0-9-]+`. Never changes once published. |
| `title` | MUST | Human-facing course name. |
| `description` | MUST | One or two sentences. Shown when a learner is choosing. |
| `subjects` | MUST | Lowercase topic tags used for discovery, e.g. `[rust, databases]`. |
| `aliases` | SHOULD | Extra terms a learner might say instead of a subject. |
| `level` | MUST | e.g. `beginner`, `intermediate`, `intermediate-to-advanced`. |
| `style` | SHOULD | e.g. `project-driven`, `interactive`, `exercise-based`. |
| `lessons` | MUST | Ordered list of lesson paths — the main path. See below. |
| `optional_lessons` | MAY | Authored lessons off the main path, offered rather than sequenced. See **Optional lessons** below. |
| `failure_modes` | MAY | Stable ids for the ways a learner's work goes wrong. See **Failure modes** below. |
| `workspace_kind` | MUST | See below. |
| `tutor_owned` | MUST | Globs the tutor may modify. |
| `learner_owned` | MUST | Globs the tutor must not modify. |
| `ownership_policy` | MUST | See below. |
| `validators` | MUST (may be `{}`) | Named validators lessons may reference. |
| `one_task_at_a_time` | SHOULD | Default `true`. |
| `solution_code` | SHOULD | `on-request-only` or `freely`. |
| `advance_on` | SHOULD | `validated-evidence-only` or `learner-assertion`. |

**`lessons`** is the authoritative lesson sequence — the **main path**, which every
learner walks in order. It defines two things nothing else does:

- **which lesson is first** — it is `lessons[0]`. There is no separate `entry_lesson`
  field; one ordered list is the single source of truth.
- **what "the next lesson" means** when one completes. Do not rely on filenames sorting
  correctly; the list is the order.

Every entry MUST resolve to a real file, and every **lesson** in `lessons/` MUST be
listed exactly once — in `lessons` when it is on the main path, or in `optional_lessons`
when it is not. A lesson in neither list is invisible to the runner and is reported as an
error, not silently skipped. A lesson in both is reported too: the main path is walked in
order and an optional lesson is offered, and nothing can be both.

"Every lesson" means every top-level `.md` file plus every folder containing a
`LESSON.md`. Supporting files inside a lesson folder are material, not lessons, and MUST
NOT appear in either list.

Name lessons by path, the same form used by `active_lesson`, so every reference to a
lesson looks identical everywhere. An entry always names the Markdown file, whether the
lesson is a single file or a folder:

```yaml
lessons:
  - lessons/00-foundations.md                 # single-file lesson
  - lessons/01-automaton-machinery/LESSON.md  # foldered lesson
```

Both forms may appear in the same bundle. Nothing else in the format changes.

**`workspace_kind`** — one of:

- `existing-or-new-repository` — the course builds software; use the learner's repo or make one
- `new-repository` — the course must start from a fresh repository
- `none` — the course builds no software; the instance lives in a plain directory

Not every tutorial builds software. If yours does not, use `none` and leave
`learner_owned` as an empty list.

**`ownership_policy`** — one of:

- `tutor-must-not-edit-learner-owned` — the normal choice for a course where the learner writes the code
- `on-request` — the tutor may edit learner files when explicitly asked
- `unrestricted` — the tutor may edit freely (rare; use only for courses where the learner is not writing the artifact)

**Ownership globs are relative to the learner's workspace, not to the bundle.** They
describe the world *after* materialization, when the bundle has been copied into
`<workspace>/tutorial/` and sits beside the learner's own files. So `tutorial/STATE.md`
is the instance's state file, and `src/**` is the learner's source. Neither path exists
inside the bundle you are writing, which is why you cannot verify them by looking — write
them for the workspace the course will be taken in.

`tutor_owned` should stay small. `tutorial/STATE.md` and `tutorial/DESIGN.md` are the
normal contents. **Do not add `tutorial/lessons/**`**: lesson copies are read-only in an
instance, because all progress belongs in `STATE.md` and a lesson carrying progress is
rejected by the same rule as section 3. **Do not add `tutorial/lessons.generated/**`**
either: that directory belongs to an instance you cannot see from here, and the runner
treats it as tutor-owned without being told (section 8).

**`validators`** — a map of name to definition. Valid `kind` values:

| `kind` | Extra fields | Meaning |
|---|---|---|
| `command` | `command: [prog, arg, ...]` | Run it; exit zero is success. |
| `file-exists` | `path:` | The path exists. |
| `file-contains` | `path:`, `pattern:` | The file matches the pattern. |
| `git-diff` | — | Inspect the working-tree diff. |
| `manual` | — | The learner supplies evidence; the tutor judges it. |

Validator names are referenced by lessons. A lesson referencing an undeclared validator
is invalid.

Do **not** put "which warnings are currently acceptable" here. That is a property of one
learner's run, not of the course. It belongs in the instance's `STATE.md`.

### Optional lessons — `optional_lessons`

**This is not the same thing as a lesson's *Optional deeper paths* section.** That is
material inside one lesson, read on request, and section 6 keeps it. It is also not a
generated side lesson, which one tutor writes for one learner during one course
(section 8). An **optional lesson** is authored by you, shipped in the bundle, available
to every learner, and simply not on the main path.

The main path is `lessons`, and every learner walks it in order. An optional lesson is
one the tutor **offers**: the learner takes it, or declines it and carries on.

Two author intentions share one mechanism:

- **enrichment** — a topic worth an hour to a learner who wants it. It is offered once at
  the point you name, and if they decline, that is the end of it;
- **anticipation** — you can see that a choice the learner is about to make leads to a
  recognisable failure. The tutor warns them briefly, offers the lesson, and lets them
  defer it. When the failure actually arrives, the tutor connects it to the topic they
  set aside and offers the lesson again.

The second is what this part of the format is really for, and it is the only one that
needs `failure_modes`. An optional lesson that declares no `anticipates` is enrichment,
which keeps ordinary optional material possible without inventing a failure for it.

```yaml
optional_lessons:
  lessons/event-time-and-watermarks.md:
    offer_at:      [lessons/04-window-execution.md]
    offer_because: >
      Windows keyed on arrival time put a delayed record in whichever window is
      open when it arrives, not the one it belongs to.
    anticipates:   [late-event-wrong-window, window-never-closes]
    repair_in:     lessons/04-window-execution.md
    required_for:  [lessons/06-correctness-under-delay.md]
```

| Field | Required | Meaning |
|---|---|---|
| the key | MUST | The lesson's path, in the form `lessons` uses. It MUST resolve to a lesson, and MUST NOT also appear in `lessons`. |
| `offer_at` | MUST | Non-empty list of `lessons` entries. The tutor raises the offer when one of them becomes the active lesson, before that lesson's first task. |
| `offer_because` | MUST | One or two sentences, written for the learner, that the tutor says when it offers the lesson. For an anticipatory lesson, this names the risk. |
| `anticipates` | SHOULD | Failure-mode ids declared in `failure_modes`. Omit it for enrichment. |
| `repair_in` | SHOULD | The `lessons` entry whose implementation the learner repairs after taking this lesson. Meaningful only with `anticipates`. |
| `required_for` | MAY | `lessons` entries that cannot be completed while an anticipated failure stands. Requires a non-empty `anticipates`. |

**`offer_at` is what makes the lesson reachable**, and it is the same rule the main path
obeys: a lesson nothing can reach is invisible. An empty `offer_at` is rejected rather
than read as "offer it whenever you like".

**`offer_because` lives in the manifest and not in the lesson, deliberately.** The tutor
reads `tutorial.yaml` every turn and opens exactly one lesson file. If the sentence it
needs in order to *offer* a lesson lived inside that lesson, offering would cost one file
open per optional lesson per turn — which is the cost this whole format exists to avoid.
`anticipates`, `repair_in` and `required_for` are here for the same reason: the tutor has
to act on them without opening anything.

**`repair_in` is not the way back.** The lesson a detour returns to is recorded in the
instance, at the moment the detour starts, from where the learner is actually standing —
that is `resume_at`, and `state-lifecycle.md` section 8.3 explains why it is never
derived from a declared field. `repair_in` answers a different question: *whose work is
now wrong?* The two differ whenever a failure surfaces later than the code that caused
it, which is the ordinary case for an anticipated failure. A learner who defers at lesson
04 and trips the failure while standing in lesson 06 returns to **06**, and repairs what
**04** built.

**`required_for` is the one way an optional lesson stops being optional.** It says these
main-path lessons cannot be completed while an anticipated failure stands, so once that
failure is observed the tutor tells the learner the lesson is now required in order to
continue. Use it sparingly and only where the blocked lesson genuinely cannot be
finished. Everything else stays an offer, and a learner who declines everything must
still be able to finish the course — section 13.

Nothing here records whether any learner was offered a lesson, deferred it or took it.
That is progress: it lives in the instance's `STATE.md`, in the section
`state-lifecycle.md` section 9 defines.

### Failure modes — `failure_modes`

A **failure mode** is a stable name for a recognisable way a learner's work goes wrong.
It is the middle of three terms, and keeping the three apart is the point of having it at
all:

| Layer | What it is | Where it lives |
|---|---|---|
| evidence | what was observed — a validator failed, an output carried a token, you read the code | the learner's workspace and the validator output |
| failure mode | what the tutor concluded from that evidence | `failure_modes`, by id |
| the lesson | what addresses it | an optional lesson's `anticipates` |

```yaml
failure_modes:
  late-event-wrong-window:
    summary: >
      A record that arrives after its window closed is counted in whichever
      window is open when it arrives.
    signals:
      - validator:late-events
      - token:LATE_EVENT_MISBINNED
      - diagnosis
  window-never-closes:
    summary: A window that receives no later record never emits its result.
    signals: [validator:test-suite, diagnosis]
```

| Field | Required | Meaning |
|---|---|---|
| the key | MUST | A stable id, `[a-z0-9-]+`. Never reuse one for a different failure. |
| `summary` | MUST | One sentence in the learner's terms naming what goes wrong. This is what the tutor says when it connects an observed failure to a deferred lesson. |
| `signals` | SHOULD | The forms of evidence that may indicate this failure mode. |

A `signals` entry is one of three forms:

| Entry | Means |
|---|---|
| `validator:<name>` | that validator failing. `<name>` MUST be declared in `validators`. |
| `token:<TOKEN>` | a stable identifier appearing in a check's output, emitted by a check you control. |
| `diagnosis` | the tutor inferred it from the learner's code or from observed behaviour. |

**`signals` is evidence, not a rule.** It tells the tutor which observations are worth
weighing. It never decides that a failure mode occurred — the diagnosis stays with the
tutor, exactly as every other judgement in this format does, and `runner-protocol.md`
section 8.4 states that normatively.

This is why there is no field that matches raw compiler or test output. A course whose
re-offer depends on an error string breaks the first time a toolchain rewords it, and it
cannot express the cases that matter most: a named test failing, a fault-injection run
behaving exactly as designed, or a design you can see is wrong before it has failed
anything. Name the failure, and let the evidence point at the name.

**Prefer `token:` to `diagnosis` when a check you wrote can emit one.** A test that prints
`LATE_EVENT_MISBINNED` on the assertion that catches the bug turns a judgement into an
observation, and it survives every rewording of everything around it.

**A failure mode no optional lesson anticipates can never do anything.** Declare the ones
your optional lessons name, and no others.

---

## 3. `COURSE.md`

Stable, global course material. Written for a learner who has not started.

MUST contain:

- the overall goal of the course
- the teaching philosophy specific to this course
- a high-level map of the chapters or lessons, in order
- milestone or checkpoint structure, if the course has one
- the optional lessons the course carries, if it has any, marked as optional. They are
  not part of the order, so do not number them into the map

SHOULD contain: a coverage list, described below.

MAY contain: optional paths, prerequisites.

MUST NOT contain:

- any statement about what has been completed
- any statement about where a learner is
- `Status: Complete`, `In progress`, `Next`, `Current lesson`, `resume marker`,
  or any equivalent
- a snapshot of anyone's code

### The coverage list

> A `COURSE.md` **SHOULD** declare a **coverage list**: a section naming the topics the
> course must eventually cover.

Give it a heading that says what it is — "Rust coverage requirements", "Topics this course
must cover" — and then a plain list of topic names, one per line. Name each topic the way
a learner would ask about it (`lifetimes`, `interior mutability`, `error design`), not the
way one of your lessons happens to title it. A topic MAY have no lesson yet: the list
states what the course owes its learners, not what it currently contains.

Keep it a list of **topics**, not of lessons. A list that names lesson files duplicates
the chapter map above it, and the two then drift apart.

**What the list is used for at teaching time.** Every other part of `COURSE.md` is prose
for a learner to read. This one part is read by the tutor, mechanically, and it is the
reason the section is worth writing carefully rather than as an afterthought.

A tutor may write an extra lesson into one learner's instance when the course does not
carry what that learner needs (section 8). The hard case is a learner who is stuck, because
two opposite situations look identical from outside: stuck because a concept they need was
never taught, and stuck because the exercise is hard. The first wants a side lesson. The
second **is** the lesson, and writing anything for it takes the exercise away. Your
coverage list is what decides between them. The tutor names the concept blocking the
learner and looks it up:

| The blocking concept | What the tutor does |
|---|---|
| is in your list, and no completed lesson taught it | writes a side lesson for it — your course has a genuine hole here |
| is in your list, and was taught already | coaches, and writes nothing |
| is not in your list | tells the learner the topic is outside this course, rather than quietly widening it |

**A topic an optional lesson teaches is in the course.** Put it in the coverage list like
any other, and the first row above then resolves correctly: the tutor finds the topic
listed, finds an authored lesson that teaches it, and **offers that lesson** instead of
writing a side lesson for a hole the course does not have. `runner-protocol.md` section
8.9 is that rule. Leaving an optional lesson's topic out of the list produces the
opposite and worse outcome — every learner who needs it gets a different improvised
version of a lesson you already wrote.

**Word the entry so a tutor can match it**, which is a real obligation and not a style
note. Nothing in `optional_lessons` states what a lesson *teaches*: the tutor has the
lesson's path, its `offer_because`, and your coverage-list entry, and it may not open the
lesson to settle the question. So a topic listed as `stream time semantics`, offered by a
lesson at `lessons/event-time-and-watermarks.md`, whose `offer_because` talks about
delayed records, gives the tutor three vocabularies for one thing and no way to know they
are one thing. Use one name in all three places. This is the same rule that governs
everything else in this format — one word, one meaning — and here it decides whether an
authored lesson gets offered or improvised over.

So the list does two jobs at once: it records what the course owes, and it tells every
tutor teaching your course where your course stops.

**A bundle with no coverage list still works.** The tutor falls back to its own judgement
of whether a blocking concept is a missing prerequisite or intended difficulty, and makes
that call separately for every learner who gets stuck. Nothing breaks, and you lose the
only means the format gives you to say "that one is not mine to teach". Declare the list.

### Worked example of the mistake

A course playbook written during a live tutorial commonly ends up with progress recorded
in several places at once — a "current state" section near the top, per-lesson markers
inside the curriculum list, and a "resume marker" at the bottom. All three must agree,
and they drift.

When converting such a document into a bundle:

- the curriculum, minus the markers → `COURSE.md` and `lessons/`
- the durable subject decisions → `DESIGN.md`
- the teaching rules → `COURSE.md`
- **every trace of progress → deleted from the bundle entirely**

The progress is not lost. It lives in the learner's instance, which the runner creates.
It is simply not yours to write.

---

## 4. `DESIGN.md`

Durable decisions about the *subject* that later lessons depend on. For a database
course: the key model, the row model, temporal semantics, storage direction,
replication, and so on. For a compiler course: the IR shape, the calling convention.

This is subject knowledge, not learner progress.

**Every section MUST have a stable anchor**, because lessons reference sections
individually and the tutor loads only the ones a lesson needs:

```markdown
## Key ordering {#key-ordering}

All encoded keys need a total order...

## Temporal semantics {#temporal-semantics}

Cell visibility is the half-open interval...
```

Anchors MUST be stable once published — a lesson pointing at `#key-ordering` breaks if
you rename it.

Include deliberately unresolved decisions, marked as such. They are useful context, and
a later lesson may be where they get resolved.

`DESIGN.md` is seeded by you and **grows during the course**: the tutor appends
decisions the learner makes. Seed the starting state.

---

## 5. `STATE.template.md`

The shape a fresh instance starts in. The runner copies this to `STATE.md` when a
learner begins, then keeps it updated.

```markdown
---
tutorial_id: rust-automaton-db
active_lesson: lessons/00-foundations.md
status: not-started
updated: null
---

## Last completed task

None. The course has not started.

## Concepts demonstrated

None yet.

## Decisions made in discussion

None yet.

## Known intentional or incomplete state

None yet.

## Accepted warnings

None.

## Next task

Begin the first lesson.

## Deferred items

None.
```

Requirements:

- `tutorial_id` MUST equal `id` in `tutorial.yaml`
- `active_lesson` MUST equal the first entry of `lessons` in `tutorial.yaml`
- `status` MUST be `not-started`
- the section headings above MUST all be present, even if empty

Author it for a learner who has not started. If your `STATE.template.md` mentions
anything that was completed, you have written an instance again.

---

## 6. Lessons

A lesson is **either** a single Markdown file **or** a folder containing `LESSON.md`
plus supporting material. Name lessons so they sort in order: `00-`, `01-`, `02-`.

```
lessons/
├── 00-foundations.md                  single file — use this unless you need material
└── 08-automaton-machinery/            folder — when the lesson ships material
    ├── LESSON.md                      required; exact name, exact case
    ├── worked-example.md
    └── assets/dafsa.svg
```

Both forms are lessons. They are identical in every other respect: same frontmatter,
same sections, same treatment by the runner.

Only `id` and `title` in frontmatter are strictly REQUIRED. The section list in
"Lesson file structure" below is the expected shape, and a lesson missing
"Completion conditions" is a lesson the tutor cannot decide when to leave — so write
them all unless you have a reason not to.

### When to use a folder

Use a folder when the lesson ships something alongside the prose — a diagram, a data
file, a longer worked example, a reference the learner opens on request. Use a single
file otherwise. A folder holding only `LESSON.md` is pointless; make it a file.

### Loading material — important

`LESSON.md` is the lesson. **Everything else in the folder is loaded only when
`LESSON.md` explicitly directs it to be.** A tutor does not read a lesson folder
wholesale, because the entire point of the format is that a tutor holds one lesson in
context, not a course.

So a folder lesson MUST name its material and say when to use it:

```markdown
For the state-merging walkthrough, read `worked-example.md`.
If the learner asks how minimisation differs from a trie, show `assets/dafsa.svg`.
```

Material that `LESSON.md` never mentions is unreachable. That is not a subtle failure:
the tutor has no way to know the file exists.

### Naming and ids

The lesson's slug is the file stem (`00-foundations.md` -> `00-foundations`) or the
folder name (`08-automaton-machinery/` -> `08-automaton-machinery`). The `id` in
frontmatter MUST equal that slug.

Anything under `lessons/` that is neither a top-level `.md` file nor a folder containing
`LESSON.md` is not a lesson. A folder directly under `lessons/` without a `LESSON.md` is
an error — it is either a broken lesson or material filed at the wrong level, and in
both cases something is silently unreachable.

### Lesson file structure

The same for both forms. A foldered lesson's `LESSON.md` looks exactly like this.

```markdown
---
id: 02-first-refactor
title: The first deliberate refactor
design_refs: [key-ordering]
validators: [cargo-check, cargo-test]
---

## Purpose

Why this lesson exists and what pressure motivates it.

## Prerequisites

What must already be true. Reference earlier lesson ids.

## Learning objectives

- objective one
- objective two

## Theory

The concepts the learner needs. Teach them; do not assume them.

## Concepts to teach

Named concepts the tutor must actually cover, not skip past.

## Constraints

What the learner's solution must and must not do.

## Suggested progression

A rough sequence of tasks. NOT a script of conversational turns.

## Completion conditions

Checkable conditions. Be specific enough that "looks plausible" is not enough.

## On completion, persist

What to record in the instance's DESIGN.md or STATE.md when this lesson finishes.

## Optional deeper paths

Material available if the learner asks. Not required.
```

### Frontmatter

| Field | Required | Meaning |
|---|---|---|
| `id` | MUST | Unique within the bundle. Match the lesson slug (file stem, or folder name). |
| `title` | MUST | Human-facing lesson name. |
| `design_refs` | SHOULD | `DESIGN.md` anchors this lesson needs. MUST all resolve. |
| `validators` | SHOULD | Validator names from `tutorial.yaml`. MUST all be declared. |
| `optional` | MUST on an optional lesson | `true`, on every lesson listed in `optional_lessons` and on no other. |

`design_refs` is how a lesson stays cheap. A lesson about splitting a file into a
library declares only the anchors it truly needs. It does not pull in storage,
networking or replication design that belongs to a later chapter. List the minimum.

### Writing an optional lesson

An optional lesson is an ordinary lesson file in `lessons/`. Same frontmatter, same
sections, same material rules, same treatment once it is active. Three things differ:

- **it is listed in `optional_lessons`, not in `lessons`** (section 2). That list is also
  where its offer metadata lives, because the tutor must be able to offer it without
  opening it;
- **its frontmatter declares `optional: true`.** The manifest already knows, so this is a
  second statement of one fact — deliberately, in the same way `id` restates the slug. A
  lesson file that does not say it is optional reads as main path to everyone who opens
  it alone, including you, six months later. A main-path lesson MUST NOT declare it;
- **do not give it a number prefix.** The prefix is a convention that follows the main
  path's order, and an optional lesson has no position in that order. Write
  `lessons/event-time-and-watermarks.md`, not `lessons/04b-event-time.md`. This is the
  same reasoning that keeps a number off a generated lesson (section 8).

Its completion conditions bind exactly like any other lesson's. *Optional* describes how
the learner arrives at the lesson, never how carefully it is taught or how it is left.

Write it so it stands alone. It is reached from at least one point you named and possibly
from a failure several lessons later, so it cannot assume the learner arrived with a
particular task half-finished. State what it needs in *Prerequisites*, the same as any
lesson, and keep it short — a detour that costs more than the lesson it interrupts is a
detour nobody finishes.

### A lesson is not a script

Do not write the conversation. The tutor generates each task from the objectives, the
learner's current state, the actual workspace, and the learner's last response. Give it
objectives, constraints and completion conditions — not dialogue.

### Completion conditions must be checkable

Weak: *"the learner understands modules."*
Strong: *"`cargo test` passes with tests in `src/lib.rs` or `tests/`; `main.rs` declares
no types; the learner can explain why `pub` was required."*

---

## 7. Depth: write the lessons you need now

Detailed lesson files are only required for lessons a learner will reach soon. A long
course may keep its later chapters as a high-level map in `COURSE.md` and gain lesson
files as it goes.

A twenty-chapter course does not need twenty detailed lesson files to be valid. It needs
every entry in `lessons` to resolve and every listed lesson to be well-formed. Chapters
without a lesson file yet are simply not listed, and are added to `lessons` when written.

Know what this costs at teaching time. A tutor that reaches a chapter `COURSE.md` maps and
`lessons` does not carry may draft one into the learner's instance — a *main-path draft*,
section 8. That draft is one learner's, written against one learner's code, and it is not
your lesson until you promote it. The learner is told, in so many words, that the chapter
was not written and is being drafted as they arrive at it — so an unwritten chapter is
visible to them, not a seam they never notice.

Prefer a small number of good lessons over a large number of thin ones.

---

## 8. Generated lessons, and how to promote one

Something happens in an **instance** that you need to know about, because two parts of it
are yours.

During a course, a tutor may write a lesson into the instance's
`tutorial/lessons.generated/` — either a **side lesson**, a compact detour for a concept
the main path does not reach, or a **main-path draft**, a chapter `COURSE.md` maps that has
no lesson file yet. Those files are tutor-owned, they belong to one learner, and they carry
provenance frontmatter recording when they were written and why.

A third route produces one: the learner asks for a side lesson outright, on a topic outside
the lesson they are in. Those carry the same provenance, and `reason:` records that the
learner asked.

**`after:` is placement, and placement only.** It tells you where the lesson belongs in
the sequence, which is what step 7 of the promotion procedure below uses. It is not where
the learner went back to: a detour often starts part-way through a lesson, and the way
back is recorded separately, in the instance's `STATE.md`. So a detour placed after lesson
03 may well have returned the learner into lesson 04, and that is not a contradiction.

Whether a tutor may write a side lesson unprompted is decided against the coverage list
your `COURSE.md` declares (section 3). A concept in your list that no lesson taught is a
hole and gets a lesson; a concept your list does not name is reported to the learner as
outside the course instead. That is the mechanical use of the list, and it is why a bundle
that declares one keeps tighter control of its own scope.

### A bundle MUST NOT contain `lessons.generated/`

> A bundle **MUST NOT** contain a `lessons.generated/` directory, at any level.

This is the same class of error as shipping a `STATE.md`, and it means the same thing: you
have written an instance. The files in it describe what one learner needed, on one day,
about code that only they wrote.

Delete the directory. Anything in it that belongs to the *course* enters `lessons/` by the
promotion procedure below — which is more than a copy, because a generated lesson is
written for one learner and a bundle lesson is written for all of them.

For the same reason, do not list `tutorial/lessons.generated/**` in `tutor_owned`. That
directory belongs to an instance which does not exist while you are authoring, and the
runner owns it there without being told.

### Promotion

**Nothing flows from an instance into a bundle automatically.** Promotion is a deliberate
authoring act that you perform, on the bundle, using a generated lesson as source material.

1. **Copy the file into `lessons/`** — from the instance's
   `tutorial/lessons.generated/<slug>.md` — renamed to this course's numbering convention,
   for example `lessons/04-lifetimes-and-borrows.md`. Copy it; do not move it. The
   learner's instance keeps its own.
2. **Set `id` to the new slug.** The rename changed the slug, and `id` MUST equal it
   (section 6). Generated lessons carry no number prefix, so this step applies every time
   and is the easiest one to forget.
3. **Strip the provenance frontmatter**: `generated`, `generated_at`, `kind`, `reason` and
   `after`. All five. Each one describes one learner's run, and any one left behind puts
   progress into a bundle.
4. **Rewrite it for a learner who has not started.** It was written against one learner's
   code and it will name their types, their file, their error message. Generalise those.
   Section 0 is the test, and it is the same test that rejects a pasted snapshot of
   anybody's source.
5. **Check that `design_refs` still resolve.** This one is neither optional nor obvious:
   the instance's `DESIGN.md` **grows during a course**, so a generated lesson may point at
   an anchor the tutor appended, which your bundle's `DESIGN.md` has never had. For each
   anchor, either add the section to `DESIGN.md` or remove the reference.
6. **Check that every `validators` name is declared** in your `tutorial.yaml`.
7. **Add the path to `lessons`, at the right position.** For a side lesson that is normally
   directly after the lesson its `after:` named. For a main-path draft it is the position
   `COURSE.md` already maps. The list is the order; the filename prefix is a convention
   that follows the list, not the other way round.
8. **Update `COURSE.md`** when the course now covers a chapter its map did not mention.
9. **Say what happens to the learner's copy.** Promotion is a bundle-side act, so the
   instance that produced the draft still holds it, and the promoted lesson and the draft
   now share a slug. That is only a problem once that learner takes a revision of the
   bundle: at re-materialization the draft becomes a duplicate of an authored lesson and
   is reported. The tutor deletes the draft at that point. Until then the learner keeps
   working from their copy and nothing breaks.
10. **Re-run the self-check in section 10, and the validator.** A promoted lesson is a new
   lesson, and every rule in this document applies to it.

#### Promoting a side lesson as an *optional* lesson

A promoted side lesson does not have to join the main path. When the evidence says that
*some* learners need it at a particular point and others do not, the honest outcome is an
optional lesson: step 7 puts the path in `optional_lessons` instead of `lessons`, with
`offer_at` naming the lesson the drafts' `after:` values cluster around. Every other step
is unchanged, and `optional: true` goes into the frontmatter beside the `id` you fixed in
step 2.

That is also the moment to ask whether the detour was *anticipating* a failure. If the
reason a learner needed it was a mistake your course could see coming, declare the failure
mode and the next learner gets to defer it knowingly instead of meeting it blind. The
`reason:` fields you are already reading are where that pattern shows: three learners
detouring after the same lesson, for the same concept, is an anticipated failure with no
name yet.

A learner who is already partway through the previous revision does not receive the new
lesson. Revising a bundle while an instance is live has no reconciliation story yet.
Promotion improves the course for the learners who come after.

### Generated lessons are this course's quality signal

They are the only feedback the format gives you from real use, and it is good feedback,
because each one is a recorded moment where the course did not carry what a learner needed.

**Three learners all needing the same detour after the same lesson is not three side
lessons. It is a missing lesson, and the generated files are the evidence.**

Compare `kind`, `after:` and `reason:` across the instances you can see:

- **the same `after:`, from different learners** — the course has a hole immediately after
  that lesson. Promote the best of the drafts, or fold the material into the lesson before
  it.
- **the same concept at scattered points** — a prerequisite is missing, earlier than any of
  the detours.
- **repeated `main-path-draft`s after one chapter** — section 7 lets a course keep a later
  chapter as a map with no lesson file, and this is what that costs: every learner's tutor
  drafts it again, differently. Author the lesson.
- **one `side-lesson`, once** — usually one learner's background rather than a gap in the
  course. Evidence of nothing. Leave it.
- **a lesson the learner asked for** — `reason:` says so. That is one learner's curiosity
  or one learner's background, not a hole in your course. Take it as interest in the topic
  and weigh it far below a detour the tutor judged necessary. Several learners asking for
  the same topic is worth a look, but it is a signal about the topic, not about the lesson
  they were in when they asked.

`reason:` is the field that carries this signal, which is why the format requires it and
why it is written for you rather than for the learner.

---

## 9. Common mistakes

1. **Writing `STATE.md` into the bundle.** The most common. Delete it.
2. **Progress markers in `COURSE.md` or lessons.** `Complete`, `In progress`, `Next`.
   Delete them. They describe one learner.
3. **A `STATE.template.md` that is not empty of progress.** It must describe a learner
   who has not started.
4. **A lesson file that is in neither `lessons` nor `optional_lessons`.** It will
   never be reached, by walking or by an offer.
5. **`design_refs` pointing at anchors that do not exist**, usually after renaming a
   `DESIGN.md` heading.
6. **Lessons referencing validators not declared in `tutorial.yaml`.**
7. **Accepted warnings in `tutorial.yaml`.** Those belong to a learner's run.
8. **Lesson files written as dialogue.** Give objectives, not turns.
9. **Assuming the course builds software.** Set `workspace_kind: none` if it does not.
10. **Pasting a learner's current code into the bundle.** Source code belongs in the
   learner's workspace; the bundle describes what to build, not what was built.
11. **Renaming `id` after publication.** It is the stable identity.
12. **A lesson folder whose `LESSON.md` never mentions its own material.** The tutor
    cannot discover files the lesson does not name; they are dead weight.
13. **Shipping a `lessons.generated/` directory.** An instance was mixed into the bundle.
    Delete it, and promote what belongs to the course by section 8.
14. **Promoting a generated lesson with its provenance frontmatter still attached.**
    `generated`, `generated_at`, `kind`, `reason` and `after` all describe one learner's
    run. Strip all five.
15. **Promoting a generated lesson without re-checking `design_refs`.** The instance's
    `DESIGN.md` grew during the course; your bundle's did not.
16. **An optional lesson listed in `lessons` as well.** The main path is walked and an
    optional lesson is offered. Nothing can be both.
17. **An optional lesson with no `offer_at`.** Nothing reaches it, so it is as invisible
    as a lesson that is in no list at all.
18. **A failure mode no optional lesson anticipates.** It can never re-offer anything.
    Name it from a lesson, or delete it.
19. **Putting `offer_because` in the lesson instead of the manifest.** The tutor would
    have to open every optional lesson every turn to know what it could offer, which is
    the cost the format exists to avoid.
20. **Giving an optional lesson a number prefix.** It has no position in the order.
21. **Writing `repair_in` as the way back.** It names whose work is wrong, not where the
    learner stands. The way back is recorded in the instance when the detour starts.
22. **Recording in the bundle that a learner deferred something.** An offer and a
    deferral are progress. They belong in the instance's `STATE.md`.
23. **Naming a foldered lesson's body anything but `LESSON.md`.** `index.md` and
    `README.md` are not recognised. `lesson.md` is worse than not recognised: macOS and
    Windows filesystems are case-insensitive, so it appears to work locally and then
    fails on Linux. Match the case exactly.

---

## 10. Self-check before you deliver

Confirm each of these by looking, not by remembering:

- [ ] `STATE.md` does **not** exist anywhere in the bundle
- [ ] `lessons.generated/` does **not** exist anywhere in the bundle
- [ ] no promoted lesson still carries `generated`, `generated_at`, `kind`, `reason` or
      `after` in its frontmatter
- [ ] `STATE.template.md` exists and describes a learner who has not started
- [ ] `tutorial.yaml`, `COURSE.md`, `DESIGN.md`, `lessons/` all exist
- [ ] every `lessons` entry resolves to a file that exists
- [ ] every lesson in `lessons/` is listed exactly once — in `lessons` **or** in
      `optional_lessons`, never in both — counting both top-level `.md` files and
      folders containing `LESSON.md`
- [ ] every folder directly under `lessons/` contains a `LESSON.md`
- [ ] every supporting file in a lesson folder is mentioned by its `LESSON.md`
- [ ] `STATE.template.md`'s `tutorial_id` equals `tutorial.yaml`'s `id`
- [ ] `STATE.template.md`'s `active_lesson` equals the first `lessons` entry
- [ ] every lesson file has `id` and `title` in frontmatter
- [ ] every `design_refs` entry resolves to a real anchor in `DESIGN.md`
- [ ] every lesson `validators` entry is declared in `tutorial.yaml`
- [ ] every `optional_lessons` key resolves to a lesson, and its `offer_at`,
      `repair_in` and `required_for` entries are all entries in `lessons`
- [ ] every `offer_at` is non-empty and every entry has an `offer_because`
- [ ] every `anticipates` id is declared in `failure_modes`, and every declared failure
      mode is anticipated by at least one optional lesson
- [ ] every `signals` entry of the form `validator:<name>` names a declared validator
- [ ] every lesson listed in `optional_lessons` declares `optional: true` in its
      frontmatter, and no main-path lesson declares it
- [ ] the course can be finished by a learner who declines every offer — unless a
      `required_for` gate says otherwise and you meant it (section 13)
- [ ] neither `COURSE.md` nor any file under `lessons/` carries a progress marker in a
      structural position — a heading annotated with a status, a `Status:` label, a ticked
      checklist box, a bold `**Next:**` label, a "current lesson" or "resume marker"
      heading, or a status field in lesson frontmatter. Ordinary prose using those words
      is fine: "while the refactor is in progress" is teaching, not progress.
- [ ] every foldered lesson's body is named `LESSON.md` in exact case — confirm with a
      directory listing, because a case-insensitive filesystem will hide a mistake
- [ ] `workspace_kind` is one of the three permitted values
- [ ] no learner's source code appears anywhere in the bundle

A bundle that passes all of these is structurally valid. It does not mean the course is
good — that is your judgement, not the format's.

---

## 11. Minimal complete example

This is the smallest thing that is still a valid bundle. (The bundle shipped with the
runner at `examples/rust-cli-basics/` is a fuller worked example; this one is trimmed to
the bare minimum so the required shape is visible at a glance.)

```
tiny-cli-course/
├── tutorial.yaml
├── COURSE.md
├── DESIGN.md
├── STATE.template.md
└── lessons/
    └── 00-hello-args.md
```

`tutorial.yaml`:

```yaml
bundle_format: 1
id: tiny-cli-course
title: A Tiny CLI Course
description: Learn core Rust by building a small command-line tool.
subjects: [rust, cli]
aliases: [command-line, argv]
level: beginner
style: [project-driven, interactive]
lessons:
  - lessons/00-hello-args.md
workspace_kind: new-repository
tutor_owned:   [tutorial/STATE.md, tutorial/DESIGN.md]
learner_owned: [src/**, Cargo.toml]
ownership_policy: tutor-must-not-edit-learner-owned
validators:
  cargo-check: { kind: command, command: [cargo, check] }
  cargo-test:  { kind: command, command: [cargo, test] }
one_task_at_a_time: true
solution_code: on-request-only
advance_on: validated-evidence-only
```

`DESIGN.md`:

```markdown
# Design

## Argument model {#argument-model}

The tool takes a subcommand followed by zero or more positional arguments.
No flags in the first version; flags arrive once a subcommand needs one.
```

`lessons/00-hello-args.md`:

```markdown
---
id: 00-hello-args
title: Reading command-line arguments
design_refs: [argument-model]
validators: [cargo-check]
---

## Purpose

Get a Rust binary reading its own arguments, so later lessons have input to work with.

## Learning objectives

- Run a binary with `cargo run`
- Obtain the arguments from the environment
- Recognise that the first argument is the program name

## Completion conditions

`cargo check` passes, and running the binary with two arguments prints both,
excluding the program name.
```

`STATE.template.md` is required too, exactly as shown in section 5, with
`tutorial_id: tiny-cli-course` and `active_lesson: lessons/00-hello-args.md`.

That is a complete, valid bundle.

To make `00-hello-args` a foldered lesson instead, the only changes are:

```
lessons/
└── 00-hello-args/
    ├── LESSON.md          the same file, renamed
    └── sample-output.txt  material, mentioned by LESSON.md
```

```yaml
lessons:
  - lessons/00-hello-args/LESSON.md
```

The `id` stays `00-hello-args`, because the slug is now the folder name. Nothing else
changes.

---

## 12. Worked example: an optional lesson that anticipates a failure

A streaming course. Lesson 04 has the learner implement windowed aggregation. The author
knows what almost everyone writes first — a window keyed on the time the record arrived —
and knows what it costs two lessons later, when a delayed record turns up.

`tutorial.yaml`, the relevant parts only:

```yaml
lessons:
  - lessons/00-records-and-streams.md
  - lessons/04-window-execution.md
  - lessons/06-correctness-under-delay.md

validators:
  test-suite:  { kind: command, command: [pytest, -q] }
  late-events: { kind: command, command: [pytest, -q, tests/test_late_events.py] }

optional_lessons:
  lessons/event-time-and-watermarks.md:
    offer_at:      [lessons/04-window-execution.md]
    offer_because: >
      Windows keyed on arrival time put a delayed record in whichever window is
      open when it arrives, not the one it belongs to. There is a lesson on event
      time and watermarks whenever you want it.
    anticipates:   [late-event-wrong-window, window-never-closes]
    repair_in:     lessons/04-window-execution.md
    required_for:  [lessons/06-correctness-under-delay.md]

failure_modes:
  late-event-wrong-window:
    summary: >
      A record that arrives after its window closed is counted in whichever
      window is open when it arrives.
    signals: [validator:late-events, token:LATE_EVENT_MISBINNED, diagnosis]
  window-never-closes:
    summary: A window that receives no later record never emits its result.
    signals: [validator:test-suite, diagnosis]
```

`lessons/event-time-and-watermarks.md` is an ordinary lesson file with `optional: true` in
its frontmatter and no number prefix.

### Path 1 — the learner takes it when it is offered

1. Lesson 04 becomes the active lesson. Before its first task the tutor states the risk
   in the two sentences of `offer_because`, says the lesson is optional, and asks. It
   teaches no event time while offering; the offer is a warning and a question, not a
   lecture.
2. The learner says yes. `active_lesson` becomes `lessons/event-time-and-watermarks.md`
   and `resume_at` becomes `lessons/04-window-execution.md` — the lesson they were
   standing in. `STATE.md` records the optional lesson as `in-progress`.
3. The lesson is taught and its completion conditions are checked, like any lesson.
   `STATE.md` records it `complete`.
4. `active_lesson` goes back to `resume_at`, the `resume_at` field is removed, and lesson
   04 begins with the learner able to key a window on event time. `repair_in` names lesson
   04 as well, and there is nothing to repair, because nothing was built yet.

### Path 2 — the learner defers it, and the failure arrives

1. The same offer, at the same point.
2. The learner says "not now". `STATE.md` records the lesson `deferred`, at lesson 04,
   with the date. **The tutor does not raise it again** — not later in lesson 04, not at
   its end, not in lesson 05. Nothing new has happened, and saying it twice is nagging.
3. Lesson 04 completes on its own terms. The learner keyed the window on arrival time and
   every check lesson 04 declares passes, because none of them delays a record. That is
   not a defect in the course. It is what an anticipated failure looks like before it
   happens.
4. In lesson 06 the `late-events` validator fails, and its output carries
   `LATE_EVENT_MISBINNED`.
5. The tutor has evidence: a named validator failed, and a token appeared in its output.
   Both are `signals` of `late-event-wrong-window`. It reads the learner's window key,
   confirms the diagnosis, and now holds a failure mode rather than an error message.
6. `late-event-wrong-window` is in `anticipates` for a lesson `STATE.md` records as
   `deferred`. So the tutor says, in this order: what failed; what that means, in the
   words of `summary`; that this is the topic set aside at lesson 04; and that the lesson
   is available now. It reports the connection neutrally. It does not say "as I warned".
7. The learner accepts. `active_lesson` becomes the optional lesson and `resume_at`
   becomes `lessons/06-correctness-under-delay.md`, because that is where they are
   standing. **Not lesson 04** — `repair_in` is not the way back.
8. The lesson completes. `active_lesson` returns to lesson 06, and the first task there is
   the repair: rework the window assignment that lesson 04 built — which is what
   `repair_in` names — and re-run `late-events`.
9. `STATE.md` records the optional lesson `complete`. If a similar failure appears again
   it is now an ordinary failure and the tutor coaches. A completed optional lesson is
   never offered a second time.

### If the learner defers it again at step 7

That is allowed, and it is recorded. Because lesson 06 appears in `required_for`, the
tutor also says what the gate means: lesson 06 cannot be completed while this failure
stands. The learner can stop there or take the lesson; what they cannot do is finish
lesson 06 with the failure in place.

Without `required_for` the tutor would simply coach them through the failure as an
ordinary failure, one correction at a time, which for many courses is the better answer.
Reach for the gate only when the blocked lesson genuinely cannot be finished.

---

## 13. Older runners, and bundles that predate this

`bundle_format` stays `1`. `optional_lessons` and `failure_modes` are additive: a bundle
written before this section existed is valid exactly as it stands, nothing in this
document changes what it means, and no edit is implied. Run the validator over it and see.

The other direction is the one to understand before you ship a course that uses the
feature. A runner that predates it reads `tutorial.yaml`, does not recognise the two new
keys, and ignores them. The effect on a learner is precise, and worth stating plainly:

- **every optional lesson is never offered.** The learner walks `lessons` and finishes the
  course without meeting one;
- **every `required_for` gate goes unenforced.** The learner is not stopped. They meet the
  failure, and the tutor coaches them through it as an ordinary failure;
- **nothing is taught wrongly.** The main path is untouched, because an optional lesson is
  never in it.

So the invariant that makes this safe is one you hold, and no validator can check it:

> **The course MUST be completable by a learner who declines every offer.**

That is worth insisting on for a reason beyond old runners: the old-runner case is
identical to a learner who says no to everything, and you have to support that learner
anyway. A `required_for` gate is the single exception, and it fails in the direction of
coaching rather than of a wrong result.

Two things follow:

- **never put a concept the main path depends on into an optional lesson alone.** If a
  later main-path lesson cannot be completed without it, it belongs on the main path.
  `required_for` is for a mistake the learner has already made, never for a prerequisite;
- **an older copy of `validate_bundle.py` reports every optional lesson as unlisted.**
  That is a stale validator, not a defect in the bundle: the check it runs was written
  before `optional_lessons` existed. Update the validator rather than the bundle, and do
  not "fix" the finding by moving the lesson into `lessons`.

