# State Lifecycle — `STATE.md` From Materialization to Completion

**Status:** normative for the runner. Load this when materializing a new instance, the
first time in a session you are about to change `STATE.md`, when a task completes, when a
lesson completes, when an offer of an optional lesson is accepted or deferred, or when you
need to advance `active_lesson`.

`STATE.md` is the only place a learner's progress is recorded. Nothing in the bundle
records progress; nothing outside `STATE.md` in the instance records it either. If you
find progress recorded in a second place, the second place is wrong.

---

## 1. The governing rule

> **Progress is recorded only after it has been demonstrated.**

`STATE.md` is a log of what happened, not a plan of what is about to happen. The one
forward-looking field, *Next task*, is explicitly labelled as the next task and is never
treated as achievement.

Concretely, do not:

- mark a task complete because you are about to ask for the next one;
- advance `active_lesson` because the remaining work "is only" cleanup;
- record a concept as demonstrated because you explained it — the learner demonstrates
  concepts, you do not;
- record a decision the learner has not actually made.

The cost of this rule being broken is not cosmetic. `active_lesson` is what a cold
session resumes from. A lesson advanced early sends the next session to the wrong file
and loses the learner's real place.

---

## 2. Shape of `STATE.md`

Frontmatter is machine-checkable. The body is what the tutor reads.

```markdown
---
tutorial_id: rust-automaton-db
active_lesson: lessons/03-first-refactor.md
status: in-progress
updated: 2026-09-11
---

## Last completed task

## Concepts demonstrated

## Decisions made in discussion

## Known intentional or incomplete state

## Accepted warnings

## Next task

## Deferred items
```

### Frontmatter fields

| Field | Meaning | Constraint |
|---|---|---|
| `tutorial_id` | which course this instance is | MUST equal `id` in the instance `tutorial.yaml` |
| `active_lesson` | the lesson file to load now | MUST be a path, and MUST appear in the manifest's `lessons` list — unless it names a generated lesson (section 8) or a key in the manifest's `optional_lessons` (section 9) |
| `resume_at` | the lesson to make active when a detour finishes | present **exactly** while `active_lesson` names a generated lesson or an optional lesson; see sections 8.3 and 9.3 |
| `status` | `not-started`, `in-progress`, `complete` | set by the runner |
| `updated` | date of the last change | update whenever you change the file |

**`active_lesson` is a path, never a description.** "Chapter 1, lesson 10" would force a
fresh session to read `COURSE.md` to resolve it, which defeats cold resume. A path is
directly openable. This single field is what makes a new conversation with no history
work.

### Body sections

All seven headings are always present, even when a section says "None". Two further
sections appear only once the instance needs them: *Generated lessons*, once a lesson has
been written into this instance (section 8.5), and *Optional lessons*, once one has been
offered (section 9.1).

| Section | Holds | Does not hold |
|---|---|---|
| Last completed task | the most recent task that was validated | anything still in progress |
| Concepts demonstrated | concepts the learner has shown they can use | concepts you explained |
| Decisions made in discussion | choices the learner made that later lessons depend on | decisions about the subject that belong in `DESIGN.md` |
| Known intentional or incomplete state | deliberate gaps, stubs, commented-out code | bugs the learner has not seen yet |
| Accepted warnings | the YAML list in section 6, with expiries | warnings nobody has accepted |
| Next task | the single task to ask for next | a plan for the rest of the lesson |
| Deferred items | work explicitly postponed, with why | vague intentions |

`STATE.md` never duplicates learner source code. The source is authoritative for
implementation state; `STATE.md` is authoritative for progress. A paste of the learner's
current types into `STATE.md` goes stale within one turn and then actively misleads.

---

## 3. Materialization

This happens once, when a learner starts a course. Load this section before creating any
file.

Preconditions:

- the learner has chosen a tutorial from the catalogue (see `catalogue-format.md`);
- the entry's `source` has been resolved to a readable bundle directory;
- the workspace root is known, and satisfies the bundle's `workspace_kind`;
- there is no existing `tutorial/` in that workspace. If there is, stop — `tutorial/` is
  singular, and overwriting it destroys a learner's progress. Ask.

Steps, in order:

1. **Create the instance directory** `tutorial/` at the workspace root.
2. **Copy the bundle's files into it**: `tutorial.yaml`, `COURSE.md`, `DESIGN.md`, and
   `lessons/` in full, including lesson folders and their material. The instance is
   self-contained; teaching never reaches back into the bundle source afterwards.
3. **Convert the state file.** Copy `STATE.template.md` to `STATE.md` **in the instance**,
   then delete `STATE.template.md` from the instance. Both steps matter: an instance that
   still holds `STATE.template.md` is indistinguishable from a half-materialized bundle,
   and a validator in instance mode reports it.
4. **Initialise `STATE.md`.** Set `status` to `in-progress` when the first lesson begins,
   set `updated` to today, and confirm `active_lesson` equals the manifest's `lessons[0]`
   and `tutorial_id` equals the manifest's `id`. The template should already satisfy
   both; if it does not, the bundle is defective — report it rather than silently
   correcting.
5. **Stamp the instance.** Append one block to the *instance's* copy of `tutorial.yaml`:

   ```yaml
   instance:
     materialized_from: local:../tutorail-bundles/rust-automaton-db
     materialized_at: 2026-09-11
     runner_version: 1
   ```

   `materialized_from` records the resolved source in provider-qualified form
   (`local:` plus the path, and for future provider types the equivalent locator).
   This block is **provenance only**. Nothing in the teaching loop reads it. It exists so
   a learner, or a future update mechanism, can tell where the instance came from. It
   never appears in a bundle.
6. **Verify the invariant**, by looking: the instance has `STATE.md` and does not have
   `STATE.template.md`. Say that you checked.
7. **Report what was created** — the instance path, the course title, the first lesson.
8. **Place what the manifest supplies, then report it.** When `tutorial.yaml` declares
   `supplies` at the top level, place those entries now: the instance exists, no lesson
   has opened yet, and this is the one moment manifest-scope entries are placed. `from`
   is relative to the **bundle** root, and a trailing `/` means that directory's
   contents, recursively; `to` is relative to the **workspace** root and never inside
   `tutorial/`. Four rules govern the placement, and `bundle-format.md` section 2 states
   them in full:

   1. **Never overwrite.** A target that already exists is left exactly as it is.
   2. **Say nothing when every target of an entry already exists.** The entry has been
      applied already. This is what makes re-entry idempotent with **no new state**:
      nothing is written to `STATE.md`, nothing is consulted in the instance stamp, and
      the workspace itself is the only record of what has been placed.
   3. **When some targets were missing, place those, name them, and name the ones you
      left alone.** Report a partial placement in full — these are new, these were
      already here and were not touched. A learner must never be left wondering whether
      a file of their own was replaced.
   4. **Name it as setup, not as a lesson.** Placed files are not an accomplishment and
      are not progress; nothing about them goes into `STATE.md`.

   Say the entry's `describe` line when you report it — it is the author's sentence about
   what these files are, and telling the learner is the only reason the field exists.
   Under `ownership_policy: tutor-must-not-edit-learner-owned` **and under `on-request`**
   you MAY **create** a declared target that does not exist, even where it falls under a
   `learner_owned` glob, and under `on-request` you do not ask first: placing a declared
   supply is not the tutor being asked for a change, and a course using that policy would
   otherwise have to interrupt the learner for permission to unpack its own fixtures.
   `unrestricted` needs no exemption at all. Under **every** policy, `unrestricted`
   included, you may **never modify** a target that already exists — placement never
   rewrites a file that is already there, whatever the policy would otherwise allow. The
   exemption is create-only and covers declared paths only. Then start teaching.

### Workspace kinds

| `workspace_kind` | What the runner needs |
|---|---|
| `existing-or-new-repository` | use the learner's current repository, or create a directory if they prefer a fresh start. Ask which. |
| `new-repository` | a fresh, empty repository. Do not materialize into a workspace that already holds a project. |
| `none` | any plain directory. `learner_owned` is empty; there is no code to protect. |

Creating the workspace itself — initialising a repository, creating a project skeleton —
is the learner's action unless they ask you to do it, with one qualification: files the
bundle **declares** in `supplies` are the runner's to place, not a skeleton the learner
builds, however much they look like one. Materializing `tutorial/` is yours.

---

## 4. What a completed task updates

After a task validates successfully, and not before:

1. **Last completed task** — replace with what was just demonstrated. One or two
   sentences, concrete enough that a fresh session knows what exists now. "Moved `Table`,
   `Row` and `Cell` into `src/lib.rs` with `pub` where the binary needs them;
   `cargo test` 5/5" beats "did the refactor".
2. **Concepts demonstrated** — append any concept the learner actually used. Do not
   append concepts you explained and they did not apply.
3. **Decisions made in discussion** — append a choice the learner made that later lessons
   depend on. A decision about the *subject* that is durable belongs in the instance's
   `DESIGN.md` instead; this section is for the smaller choices that shape the rest of
   this run.
4. **Known intentional or incomplete state** — add a deliberate gap, remove one that has
   been closed. This is where "`Table::get` is commented out on purpose" lives, so the
   next session does not report it as a bug.
5. **Accepted warnings** — add, expire or remove entries per section 6.
6. **Next task** — replace with the single next task.
7. **Deferred items** — add anything explicitly postponed, with the reason. An intention
   that exists only in the conversation is lost at the end of the session.
8. **`updated`** — set to today.

`active_lesson` does **not** change when a task completes. Only a completed lesson moves
it.

---

## 5. What a completed lesson updates

Only once the lesson's own completion conditions are met and confirmed — the procedure is
in `runner-protocol.md` section 6.

1. **Persist what the lesson names.** The lesson's *On completion, persist* section says
   what to append to the instance's `DESIGN.md`, under which anchor. Append; do not
   rewrite existing sections, and do not renumber or rename anchors — lessons reference
   them by name.
2. **Expire acceptances** whose `until_lesson` is the lesson being left or the lesson
   being entered. Remove them and say what they were covering.
3. **Advance `active_lesson`.** Find the current value in the manifest's `lessons` list
   and take the **next entry in that list**. The list is the order. Filename sort is not
   the order, lesson `id` is not the order, and the number prefix is a convention rather
   than a rule. When the instance has a `lessons.generated/` directory, an incomplete
   generated lesson whose `after:` is the lesson just finished comes first instead —
   section 8, and `runner-protocol.md` section 7.3. **An optional lesson is never reached
   by advancing.** It is not in `lessons`, so this step cannot arrive at one; the only way
   in is an accepted offer, section 9.3.
4. **Reset the body for the new lesson.** *Last completed task* becomes the lesson
   completion. *Next task* becomes the first task of the new lesson. *Concepts
   demonstrated* and *Decisions made in discussion* accumulate across lessons — do not
   clear them. *Known intentional or incomplete state* carries forward only what is still
   true.
5. **`updated`** — set to today.

### Reaching the end

When the completed lesson is the last entry in `lessons`, leave `active_lesson` on that
entry and set `status` to `complete`. Do not point `active_lesson` at a lesson that does
not exist, and do not invent an extra lesson. Say what the learner built and which
concepts they demonstrated.

---

## 6. Accepted warnings

`accepted_warnings` lives in the body of `STATE.md`, as a YAML block:

```yaml
accepted_warnings:
  - pattern: "is never used"
    reason: "Engine unreachable from the binary while main() is empty"
    until_lesson: lessons/03-first-refactor.md
```

| Field | Meaning |
|---|---|
| `pattern` | text that identifies the warning |
| `reason` | why this is currently acceptable, in the learner's terms |
| `until_lesson` | the lesson path at which the acceptance expires |

Rules:

- **`until_lesson` is mandatory.** An acceptance with no expiry becomes permanent cover
  and makes the underlying rule unenforceable. Choose the lesson that removes the cause.
- **Never put this in `tutorial.yaml`.** Validator *definitions* are configuration and
  belong in the manifest. Which warnings are currently tolerated is progress, and belongs
  here.
- **The learner accepts, you record.** Do not accept a warning on the learner's behalf to
  make a validator quieter.
- **Expiry is checked against the active lesson.** The matching procedure is in
  `runner-protocol.md` section 4.

---

## 7. Repairing a stale or inconsistent `STATE.md`

`STATE.md` can fall behind the workspace — a learner works between sessions, or a session
ended without recording. When `STATE.md` and the source disagree, **the source wins**.

Procedure:

1. measure. Inspect the actual files and run the declared validators. Do not infer the
   state from what `STATE.md` claims, and do not infer it from what the lesson expected.
2. say what you found and how it differs from the record.
3. rewrite the affected sections to match what you measured, including `active_lesson` if
   the learner has plainly moved on or plainly not started what was recorded.
4. record nothing you did not measure.

The failure this avoids: a resume marker that describes work the learner finished two
lessons ago sends the tutor to re-teach it. A marker that describes work they have not
started lets the tutor assume it exists.

### Inconsistencies to report rather than repair

- `active_lesson` names a path that is in none of three places: the manifest's `lessons`
  list, the manifest's `optional_lessons` map, or `lessons.generated/` (sections 8.3 and
  9.3 permit the last two, and only with `resume_at` set);
- `active_lesson` names a generated lesson that is not there, or names one while
  `resume_at` is absent or is not an entry in `lessons`;
- `active_lesson` names an optional lesson while `resume_at` is absent, or while
  `resume_at` is not an entry in `lessons`;
- the *Optional lessons* section records a path that is not a key in the manifest's
  `optional_lessons`;
- an *Optional lessons* entry is recorded `in-progress` while `active_lesson` names
  something else. One of the two is wrong and nothing in the file says which;
- a file under `lessons.generated/` whose `after:` is not an entry in `lessons`, or which
  is missing any of the five provenance fields;
- `tutorial_id` does not match the manifest's `id`;
- `STATE.template.md` is present in the instance;
- the manifest names a lesson file that does not exist.

These are structural defects, not stale progress. Guessing at the intent will lose the
learner's place. Say what is wrong and let the learner decide.

---

## 8. Generated lessons

A tutor may write a lesson **during** a course, into `tutorial/lessons.generated/`. This
section is the mechanics. Whether to write one at all is the harder half, and it is in
`runner-protocol.md` section 7 — settle that question there before creating any file here.

### 8.1 Where they live

```
tutorial/
├── tutorial.yaml
├── COURSE.md
├── DESIGN.md
├── STATE.md
├── lessons/              the author's lessons, copied at materialization, read-only
└── lessons.generated/    lessons the tutor wrote during this course, tutor-owned
```

`lessons.generated/` exists **only in an instance**. It is never part of a bundle, it is
never created by materialization, and it does not exist until the first generated lesson
needs it.

It is tutor-owned in every instance, whether or not the manifest's `tutor_owned` lists it.
A bundle cannot list a directory that belongs to an instance it has never seen, so
ownership of this one path is settled by the runner and not by the manifest.

### 8.2 Creating one

1. **Settle the case for generating at all** — `runner-protocol.md` section 7.2. A defect
   in the bundle is reported, never drafted over.
2. **Create `tutorial/lessons.generated/`** if it is not already there.
3. **Choose a slug that names the concept** — `lifetimes-and-borrows`, not `03b` or
   `extra-lesson`. It SHOULD NOT reuse the `id` of a lesson in `lessons/`: the format
   permits the overlap, but two lessons with one `id` make the record in section 8.5 and
   any later promotion ambiguous. Give it no number prefix — position comes from `after:`,
   never from the name.
4. **Create `tutorial/lessons.generated/<slug>.md` with the ordinary lesson structure** —
   purpose, prerequisites, learning objectives, theory, concepts to teach, constraints,
   suggested progression, completion conditions, on completion persist.
   `bundle-format.md` section 6 defines that shape and a generated lesson does not get a
   lighter one. A lesson with no completion conditions is a lesson you cannot decide to
   leave.
5. **Add the provenance frontmatter** below, alongside the ordinary lesson fields.
6. **Record the way back before you teach a word of it.** Set `active_lesson` to the
   generated lesson and `resume_at` to the lesson the learner returns to — section 8.3.
   Record it now, while you still know where the learner was standing; a session that
   starts after the detour cannot recover it.
7. **Say what you wrote and why, before teaching it.** A lesson that appears in the
   learner's workspace unannounced is indistinguishable from the course changing
   underneath them. For a `main-path-draft` this is not optional and not a footnote:
   `runner-protocol.md` section 7.4 says what the learner must be told, and when.

A generated lesson SHOULD be a single file. It MAY be a folder containing `LESSON.md` when
it genuinely ships material, and every folder rule then applies unchanged: exact case, and
material is invisible until the body names it.

#### Provenance frontmatter

```yaml
---
id: lifetimes-and-borrows
title: Lifetimes, just enough to unblock the borrow
generated: true
generated_at: 2026-09-11
kind: side-lesson            # | main-path-draft
reason: "The borrow in Table::get_cell_at cannot be explained without lifetimes"
after: lessons/03-first-refactor.md
design_refs: [row-cell-model]
validators: [cargo-check]
---
```

| Field | Required | Meaning |
|---|---|---|
| `id` | MUST | The slug: file stem, or folder name. Unique across `lessons/` and `lessons.generated/`. |
| `title` | MUST | Human-facing lesson name. |
| `generated` | MUST | Always `true`. Marks the file as an overlay rather than an authored lesson. |
| `generated_at` | MUST | The date it was written. Orders two detours that share one `after:`. |
| `kind` | MUST | `side-lesson` or `main-path-draft`. |
| `reason` | MUST | One sentence, written for a bundle author who was not in the room. When the learner asked for this lesson rather than you judging it necessary, `reason` MUST say so and say what they asked for — the two mean different things about the course. This is the evidence `bundle-format.md` section 8 depends on. |
| `after` | MUST | Where this lesson belongs in the course sequence: the authored lesson it follows. MUST be an entry in the manifest's `lessons` list — an authored lesson, never another generated one. |
| `design_refs` | SHOULD | Anchors that already exist in the instance's `DESIGN.md`. |
| `validators` | SHOULD | Names already declared in the manifest's `validators` map. |

Never invent a validator name or a `DESIGN.md` anchor for a generated lesson. Either one
manufactures exactly the defect `runner-protocol.md` section 7.2 tells you to report, and
it would then be your own defect.

#### `after:` is placement, not the way back

`after:` answers one question only: **where does this lesson belong in the course?** A
bundle author reading the instance later uses it to decide where a promoted lesson goes
(`bundle-format.md` section 8), and the runner uses it to decide which detours are waiting
at which point in `lessons`.

It does **not** say where the detour returns to. That is `resume_at` in `STATE.md`, it is
a separate field, and section 8.3 sets it explicitly. Do not compute one from the other in
either direction.

How to choose `after:`:

| The detour starts | `after:` is |
|---|---|
| part-way through lesson L, because L needs a concept the course never taught | the last **completed** authored lesson — the detour belongs **before** L, because L depends on it |
| part-way through lesson L, on a topic L does not depend on (a learner asked for it) | L — nothing in L needs it, so it belongs after L |
| at a boundary, after L completed and before the next entry began | L |

When the learner is part-way through the **first** entry in `lessons`, no authored lesson
is complete and there is no earlier entry to name. Use that first entry.

### 8.3 `active_lesson` may point into `lessons.generated/`

While a detour is active, `STATE.md` looks like this:

```yaml
---
tutorial_id: rust-automaton-db
active_lesson: lessons.generated/lifetimes-and-borrows.md
resume_at: lessons/04-storage-engine.md
status: in-progress
updated: 2026-09-11
---
```

| Field | Meaning | Constraint |
|---|---|---|
| `resume_at` | the `lessons` entry to make active when the detour finishes | present exactly while `active_lesson` names a generated lesson or an optional lesson; absent otherwise |

**This is one of the two exceptions to "`active_lesson` MUST appear in the manifest's
`lessons` list"** — the other is an optional lesson, and it works identically (section
9.3). A path under `lessons.generated/` is deliberately not in the list, and the
presence of `resume_at` is what says so. Everything else about the field is unchanged:
it is a path, it is the file a cold session opens, and it is still the single field that
makes a conversation with no history work.

**The field names the lesson to make active, not a lesson to move past.** `resume_at:
lessons/04-storage-engine.md` means lesson 04 becomes the active lesson. It does not mean
"the lesson after 04". The example above is a detour taken part-way through lesson 04: the
learner goes back into 04 and finishes it.

#### Recording it

**Set `resume_at` when the detour becomes active, not when it finishes**, and write the
value you already know rather than one you derive. `after:` records placement and
`resume_at` records the way back; they are independent fields and neither is computed from
the other.

| The detour starts | `resume_at` is |
|---|---|
| part-way through lesson L | **L** — the interrupted lesson. The learner has unfinished work in it |
| at a boundary, after L completed and before the next entry began | the entry **after** L in `lessons` |

`resume_at` MUST itself be an entry in `lessons`: a detour returns to the main path, never
to another detour. Recording it once, at the moment you know it, is what stops a later
session guessing.

When there is nothing further to return to — a boundary detour off the **last** entry in
`lessons` — set `resume_at` to that last entry anyway, so the field stays a real lesson
path, and when the detour completes set `active_lesson` to it with `status: complete` —
the course is finished, per section 5, "Reaching the end". Do not re-teach it.

> **Do not derive `resume_at` from `after:`.** An earlier revision of this document said
> the value was "the entry after the detour's `after:` in `lessons`". That rule silently
> skips work. A learner who is halfway through lesson L and needs a prerequisite has only
> one lesson they can be sent back to — L — and any rule that returns them to the entry
> *after* L throws away the rest of a lesson they never finished, with nothing in
> `STATE.md` recording that it happened. Mid-lesson detours are ordinary: being blocked on
> an untaught prerequisite happens mid-lesson by definition, and a learner may ask for a
> side lesson at any moment (`runner-protocol.md` section 7.1).

### 8.4 Completing a generated lesson

A detour completes like any other lesson, and then hands the learner back:

1. **Check the completion conditions you wrote**, individually and with evidence, per
   `runner-protocol.md` section 6. They bind because they are completion conditions, not
   because of who wrote them.
2. **Persist what the lesson's *On completion, persist* section names** into the
   instance's `DESIGN.md`, under an anchor that exists.
3. **Record the lesson complete** in `STATE.md`, per section 8.5. This is what lets a
   cold session answer "is this generated lesson incomplete?" without reading every file.
4. **Return to the main path.** Set `active_lesson` to `resume_at` and remove the
   `resume_at` field. One exception: when another incomplete generated lesson shares
   this detour's `after:` value, that one becomes `active_lesson` instead — oldest
   `generated_at` first — and `resume_at` carries over unchanged. The learner has not
   moved, so the place they come back to has not changed either.
5. **Set the body for wherever the learner lands.** *Concepts demonstrated* accumulates as
   usual either way; what the detour taught stays recorded.
   - **Returning into an interrupted lesson** — `resume_at` names the lesson that was
     active when the detour began. Do not reset the body. The learner has unfinished work
     in that lesson, and *Next task* is the task the detour interrupted, restated with
     whatever the detour changed about it.
   - **Returning to a lesson not yet started** — reset the body for a new lesson, per
     section 5 step 4.
6. **`updated`** — set to today.

**Never delete a generated lesson when it completes.** It stays in the instance as both
the record of what this learner needed and the evidence a bundle author acts on —
`bundle-format.md` section 8.

### 8.5 What `STATE.md` records

One extra body section, present only in an instance that has generated lessons. A fresh
instance does not have it, and `STATE.template.md` never does:

```markdown
## Generated lessons

- `lessons.generated/lifetimes-and-borrows.md` — side-lesson, after
  `lessons/03-first-refactor.md` — complete
- `lessons.generated/wal-recovery-draft.md` — main-path-draft, after
  `lessons/07-storage-engine.md` — pending
```

Each entry carries the path, the `kind`, the `after:` value, and `complete` or `pending`.
Nothing else: the reason lives in the lesson's own frontmatter, and a second copy here
would be a second thing to keep true.

This section exists because the advancement rule turns on the word *incomplete*
(`runner-protocol.md` section 7.3), and the lesson files deliberately carry no progress —
progress belongs in `STATE.md`, in one place, and a lesson that carries progress cannot be
promoted into a bundle.

### 8.6 The manifest's `lessons` list is NEVER mutated

When you write a generated lesson, do not add it to `lessons` in the instance's
`tutorial.yaml`. Do not reorder the list, do not remove an entry, and do not "fix" a path
in it. The temptation is real, and the damage arrives later, when nobody remembers.

`lessons` is the authored course. It stays identical for every learner who takes the
bundle, and that buys three things:

- **a later bundle revision stays reconcilable.** The instance's list and the bundle's
  list can be compared directly. Once a learner's list holds a private entry, nothing can
  tell an author's change from a tutor's;
- **two learners' courses do not diverge structurally.** They can take different detours
  and still be provably on the same course, because the overlay carries the difference and
  the list does not;
- **the overlay stays legible as an overlay.** A generated lesson merged into `lessons` is
  indistinguishable from an authored one within a session, and then nobody can tell what
  the course contains from what one tutor improvised.

The same holds for the rest of what the bundle wrote. In an instance, `COURSE.md` and
everything under `lessons/` are read-only. `DESIGN.md` is the one exception the format
already grants, and the tutor appends to it rather than rewriting it.

"Never mutated" includes the bundle source. Materialization copies once and teaching never
reaches back (section 3). Moving a generated lesson into a bundle is a separate,
deliberate authoring act with its own procedure — `bundle-format.md` section 8 — and
nothing in the teaching loop performs it.

---

## 9. Optional lessons

A bundle may ship **optional lessons**: authored lessons that live in `lessons/` with every
other lesson, are listed in the manifest's `optional_lessons` map rather than in `lessons`,
and are offered rather than sequenced (`bundle-format.md` section 2).

This section is the mechanics — what `STATE.md` records and what the frontmatter does.
Whether to offer, when to re-offer, and when to refuse are judgement, and they are in
`runner-protocol.md` section 8. Settle those there, exactly as section 8 above settles its
half in `runner-protocol.md` section 7.

### 9.1 What `STATE.md` records

One extra body section, present only once an optional lesson has been offered in this
instance. A fresh instance does not have it, and `STATE.template.md` never does:

```markdown
## Optional lessons

- `lessons/event-time-and-watermarks.md` — deferred — offered at
  `lessons/04-window-execution.md` on 2026-09-12
- `lessons/what-is-a-character.md` — complete — taken at
  `lessons/02-errors-and-tests.md` on 2026-09-14
```

Each entry carries the path, the state, and one clause saying where and when the last
decision happened and what prompted it. **Nothing else.** The risk the lesson addresses is
`offer_because`, the failures it anticipates are `anticipates`, and the lesson whose work
it repairs is `repair_in` — all three are in `tutorial.yaml`, which you load every turn. A
second copy here is a second thing to keep true, and it is the same argument section 8.5
makes about `reason:`.

When the last decision was a re-offer, the clause names the failure mode that prompted it:

```markdown
- `lessons/event-time-and-watermarks.md` — deferred — re-offered after
  `late-event-wrong-window` at `lessons/06-correctness-under-delay.md` on 2026-09-15
```

### 9.2 The five states

**Not yet offered is the absence of an entry.** Do not write a `not-offered` line: a course
carrying twelve optional lessons would then open this section with twelve lines saying that
nothing has happened, and the one question the section answers — *what has this learner been
offered?* — would be answered in noise.

The four that are written:

- **`offered`** — you asked and have no answer yet. It normally lives for part of one turn.
  Record it when the turn ends before the learner answers, so a cold session knows a
  question is outstanding rather than asking it a second time.
- **`deferred`** — the learner said not now. The clause MUST name the lesson the offer was
  made at and the date. Both the anti-nag rule and the re-offer depend on knowing that the
  offer happened and where (`runner-protocol.md` sections 8.3 and 8.5); an entry that omits
  either records a decision nobody can act on.
- **`in-progress`** — `active_lesson` names the lesson and `resume_at` is set. Both facts
  are in the frontmatter already. The record exists so that a cold session answers "what
  has this learner been offered" from one section, rather than by reasoning about which of
  three kinds of path `active_lesson` currently holds.
- **`complete`** — the lesson is finished. This is the state that stops it ever being
  offered again (`runner-protocol.md` section 8.8), so it MUST be written the moment the
  lesson completes, in the same step that records the completion.

**Re-offering a `deferred` lesson updates the entry in place.** It never adds a second one.
This section records the current state of each offer, not a history of offers, and one
lesson has one entry for the life of the instance.

### 9.3 Accepting an offer

1. `active_lesson` becomes the optional lesson's path.
2. `resume_at` becomes the lesson the learner is standing in. That is section 8.3's rule
   and not a second one: the way back is recorded at the moment the detour starts, from
   where the learner actually is. Never derive it from `repair_in`, and never from
   `offer_at`.
3. the *Optional lessons* entry becomes `in-progress`.
4. **`updated`** — set to today.

Do not reset the body. The learner has unfinished work in the lesson they were standing in,
and section 8.4 step 5 is the same situation with the same instruction.

An accepted offer and the generated-lesson advancement in section 8.4 cannot collide. An
accepted offer takes effect in the turn the learner accepts; generated-lesson advancement
applies when a lesson completes and no detour is active. Nor can the two name each other: a
generated lesson's `after:` MUST be an entry in `lessons`, and an optional lesson is never
in that list.

### 9.4 Completing one

Exactly section 8.4, with the *Optional lessons* entry in place of the *Generated lessons*
one:

1. **Check the completion conditions**, individually and with evidence, per
   `runner-protocol.md` section 6. The author wrote them; *optional* describes how the
   learner arrived, not how the lesson is left.
2. **Persist what the lesson's *On completion, persist* section names** into the instance's
   `DESIGN.md`, under an anchor that exists.
3. **Record the entry `complete`** (9.2).
4. **Return to the main path.** `active_lesson` becomes `resume_at`, and the `resume_at`
   field is removed.
5. **Do not reset the body.** `resume_at` always names the lesson the learner was standing
   in, and that lesson's body was set when they arrived in it — whether or not they had
   begun a task there. *Next task* becomes the repair `repair_in` names, stated in terms of
   the lesson that built the work (`runner-protocol.md` section 8.6); where there is nothing
   to repair, it is the task the detour interrupted. *Concepts demonstrated* accumulates as
   usual, and what the optional lesson taught stays recorded.
6. **`updated`** — set to today.

Step 4 carries no exception here. Section 8.4's exception is for a second generated lesson
sharing one `after:` value, and an optional lesson has no `after:`.

### 9.5 What this section does not hold

`repair_in` is in the manifest and is **never** copied into `STATE.md`. It is the same for
every learner, it does not change while a course is taken, and it is read at one moment —
when the detour completes and you state the first task on landing. The same holds for
`offer_because`, `anticipates` and `required_for`. `STATE.md` records what happened to this
learner; the manifest records what the course offers.
