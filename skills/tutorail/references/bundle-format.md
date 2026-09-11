# Tutorial Bundle Format — Authoring Contract

**Format version:** `bundle_format: 1`
**Status:** normative. A bundle that violates a MUST in this document is invalid.

This document is self-contained. You need nothing else to author a bundle.

---

## 0. Read this part first

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

A bundle is used by a learner who has not started yet. Write it for them.

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
    ├── 00-<slug>.md
    ├── 01-<slug>.md
    └── ...
```

### The rule that separates a bundle from an instance

> A bundle **MUST** contain `STATE.template.md`.
> A bundle **MUST NOT** contain `STATE.md`.

`STATE.md` is created by the runner when a learner starts the course. It does not exist
until then. If you have written a `STATE.md`, you have written an instance by mistake:
delete it, and move anything in it that describes *the course* (not the learner) into
`COURSE.md`, `DESIGN.md`, or a lesson.

There is no exception. A bundle containing `STATE.md` is rejected.

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

workspace_kind: existing-or-new-repository
tutor_owned:    [tutorial/STATE.md, tutorial/DESIGN.md, tutorial/lessons/**]
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
| `lessons` | MUST | Ordered list of lesson paths. See below. |
| `workspace_kind` | MUST | See below. |
| `tutor_owned` | MUST | Globs the tutor may modify. |
| `learner_owned` | MUST | Globs the tutor must not modify. |
| `ownership_policy` | MUST | See below. |
| `validators` | MUST (may be `{}`) | Named validators lessons may reference. |
| `one_task_at_a_time` | SHOULD | Default `true`. |
| `solution_code` | SHOULD | `on-request-only` or `freely`. |
| `advance_on` | SHOULD | `validated-evidence-only` or `learner-assertion`. |

**`lessons`** is the authoritative lesson sequence. It defines two things nothing else
does:

- **which lesson is first** — it is `lessons[0]`. There is no separate `entry_lesson`
  field; one ordered list is the single source of truth.
- **what "the next lesson" means** when one completes. Do not rely on filenames sorting
  correctly; the list is the order.

Every entry MUST resolve to a real file, and every file in `lessons/` MUST appear in the
list exactly once. A lesson file that is not listed is invisible to the runner and is
reported as an error, not silently skipped.

Name lessons by path (`lessons/00-foundations.md`), the same form used by
`active_lesson`, so every reference to a lesson looks identical everywhere.

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

---

## 3. `COURSE.md`

Stable, global course material. Written for a learner who has not started.

MUST contain:

- the overall goal of the course
- the teaching philosophy specific to this course
- a high-level map of the chapters or lessons, in order
- milestone or checkpoint structure, if the course has one

MAY contain: topic-coverage requirements, optional paths, prerequisites.

MUST NOT contain:

- any statement about what has been completed
- any statement about where a learner is
- `Status: Complete`, `In progress`, `Next`, `Current lesson`, `resume marker`,
  or any equivalent
- a snapshot of anyone's code

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
decisions the learner makes. Write the starting state.

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

Write it for a learner who has not started. If your `STATE.template.md` mentions
anything that was completed, you have written an instance again.

---

## 6. Lessons

One file per lesson in `lessons/`. Name them so they sort in order: `00-`, `01-`, `02-`.

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
| `id` | MUST | Unique within the bundle. Match the filename stem. |
| `title` | MUST | Human-facing lesson name. |
| `design_refs` | SHOULD | `DESIGN.md` anchors this lesson needs. MUST all resolve. |
| `validators` | SHOULD | Validator names from `tutorial.yaml`. MUST all be declared. |

`design_refs` is how a lesson stays cheap. A lesson about splitting a file into a
library declares only the anchors it truly needs. It does not pull in storage,
networking or replication design that belongs to a later chapter. List the minimum.

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

A 22-chapter course does not need 22 detailed lesson files to be valid. It needs every
entry in `lessons` to resolve and every lesson file to be well-formed. Chapters without
a lesson file yet are simply not listed.

Prefer a small number of good lessons over a large number of thin ones.

---

## 8. Common mistakes

1. **Writing `STATE.md` into the bundle.** The most common. Delete it.
2. **Progress markers in `COURSE.md` or lessons.** `Complete`, `In progress`, `Next`.
   Delete them. They describe one learner.
3. **A `STATE.template.md` that is not empty of progress.** It must describe a learner
   who has not started.
4. **A lesson file that is not listed in `lessons`.** It will never be reached.
5. **`design_refs` pointing at anchors that do not exist**, usually after renaming a
   `DESIGN.md` heading.
6. **Lessons referencing validators not declared in `tutorial.yaml`.**
7. **Accepted warnings in `tutorial.yaml`.** Those belong to a learner's run.
8. **Lesson files written as dialogue.** Give objectives, not turns.
9. **Assuming the course builds software.** Set `workspace_kind: none` if it does not.
10. **Pasting a learner's current code into the bundle.** Source code belongs in the
   learner's workspace; the bundle describes what to build, not what was built.
11. **Renaming `id` after publication.** It is the stable identity.

---

## 9. Self-check before you deliver

Confirm each of these by looking, not by remembering:

- [ ] `STATE.md` does **not** exist anywhere in the bundle
- [ ] `STATE.template.md` exists and describes a learner who has not started
- [ ] `tutorial.yaml`, `COURSE.md`, `DESIGN.md`, `lessons/` all exist
- [ ] every `lessons` entry resolves to a file that exists
- [ ] every file in `lessons/` appears in `lessons` exactly once
- [ ] `STATE.template.md`'s `tutorial_id` equals `tutorial.yaml`'s `id`
- [ ] `STATE.template.md`'s `active_lesson` equals the first `lessons` entry
- [ ] every lesson file has `id` and `title` in frontmatter
- [ ] every `design_refs` entry resolves to a real anchor in `DESIGN.md`
- [ ] every lesson `validators` entry is declared in `tutorial.yaml`
- [ ] no file under `lessons/` and not `COURSE.md` contains `Status: Complete`,
      `In progress`, `Next:`, `current lesson`, or `resume marker`
- [ ] `workspace_kind` is one of the three permitted values
- [ ] no learner's source code appears anywhere in the bundle

A bundle that passes all of these is structurally valid. It does not mean the course is
good — that is your judgement, not the format's.

---

## 10. Minimal complete example

```
rust-cli-basics/
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
id: rust-cli-basics
title: Rust Fundamentals Through a CLI
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
- Read arguments from the environment
- Recognise that the first argument is the program name

## Completion conditions

`cargo check` passes, and running the binary with two arguments prints both,
excluding the program name.
```

That is a complete, valid bundle.
