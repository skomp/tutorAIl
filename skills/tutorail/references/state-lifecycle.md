# State Lifecycle — `STATE.md` From Materialization to Completion

**Status:** normative for the runner. Load this when materializing a new instance, the
first time in a session you are about to change `STATE.md`, when a task completes, when a
lesson completes, or when you need to advance `active_lesson`.

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
| `active_lesson` | the lesson file to load now | MUST be a path, and MUST appear in the manifest's `lessons` list |
| `status` | `not-started`, `in-progress`, `complete` | set by the runner |
| `updated` | date of the last change | update whenever you change the file |

**`active_lesson` is a path, never a description.** "Chapter 1, lesson 10" would force a
fresh session to read `COURSE.md` to resolve it, which defeats cold resume. A path is
directly openable. This single field is what makes a new conversation with no history
work.

### Body sections

All seven headings are always present, even when a section says "None".

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
7. **Report what was created** — the instance path, the course title, the first lesson —
   and only then start teaching.

### Workspace kinds

| `workspace_kind` | What the runner needs |
|---|---|
| `existing-or-new-repository` | use the learner's current repository, or create a directory if they prefer a fresh start. Ask which. |
| `new-repository` | a fresh, empty repository. Do not materialize into a workspace that already holds a project. |
| `none` | any plain directory. `learner_owned` is empty; there is no code to protect. |

Creating the workspace itself — initialising a repository, creating a project skeleton —
is the learner's action unless they ask you to do it. Materializing `tutorial/` is yours.

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
   than a rule.
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

- `active_lesson` names a path that is not in the manifest's `lessons` list;
- `tutorial_id` does not match the manifest's `id`;
- `STATE.template.md` is present in the instance;
- the manifest names a lesson file that does not exist.

These are structural defects, not stale progress. Guessing at the intent will lose the
learner's place. Say what is wrong and let the learner decide.
