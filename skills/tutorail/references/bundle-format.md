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

Every entry MUST resolve to a real file, and every **lesson** in `lessons/` MUST appear
in the list exactly once. A lesson that is not listed is invisible to the runner and is
reported as an error, not silently skipped.

"Every lesson" means every top-level `.md` file plus every folder containing a
`LESSON.md`. Supporting files inside a lesson folder are material, not lessons, and MUST
NOT appear in the list.

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

A twenty-chapter course does not need twenty detailed lesson files to be valid. It needs
every entry in `lessons` to resolve and every listed lesson to be well-formed. Chapters
without a lesson file yet are simply not listed, and are added to `lessons` when written.

Know what this costs at teaching time. A tutor that reaches a chapter `COURSE.md` maps and
`lessons` does not carry may draft one into the learner's instance — a *main-path draft*,
section 8. That draft is one learner's, written against one learner's code, and it is not
your lesson until you promote it.

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

`reason:` is the field that carries this signal, which is why the format requires it and
why it is written for you rather than for the learner.

---

## 9. Common mistakes

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
12. **A lesson folder whose `LESSON.md` never mentions its own material.** The tutor
    cannot discover files the lesson does not name; they are dead weight.
13. **Shipping a `lessons.generated/` directory.** An instance was mixed into the bundle.
    Delete it, and promote what belongs to the course by section 8.
14. **Promoting a generated lesson with its provenance frontmatter still attached.**
    `generated`, `generated_at`, `kind`, `reason` and `after` all describe one learner's
    run. Strip all five.
15. **Promoting a generated lesson without re-checking `design_refs`.** The instance's
    `DESIGN.md` grew during the course; your bundle's did not.
16. **Naming a foldered lesson's body anything but `LESSON.md`.** `index.md` and
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
- [ ] every lesson in `lessons/` appears in `lessons` exactly once — counting both
      top-level `.md` files and folders containing `LESSON.md`
- [ ] every folder directly under `lessons/` contains a `LESSON.md`
- [ ] every supporting file in a lesson folder is mentioned by its `LESSON.md`
- [ ] `STATE.template.md`'s `tutorial_id` equals `tutorial.yaml`'s `id`
- [ ] `STATE.template.md`'s `active_lesson` equals the first `lessons` entry
- [ ] every lesson file has `id` and `title` in frontmatter
- [ ] every `design_refs` entry resolves to a real anchor in `DESIGN.md`
- [ ] every lesson `validators` entry is declared in `tutorial.yaml`
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
