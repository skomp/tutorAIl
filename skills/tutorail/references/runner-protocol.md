# Runner Protocol — The Teaching Loop

**Status:** normative for the runner. Load this before the first task of a teaching
session, when validating, when a lesson's completion conditions look met, or when you are
unsure whether an edit is yours to make.

This document assumes an active instance already exists at `tutorial/` in the learner's
workspace. Materialization is in `state-lifecycle.md`. Finding a tutorial in the first
place is in `catalogue-format.md`.

---

## 1. What is loaded, and what is not

Re-establish this at the start of every session, including a session that resumes a
tutorial it has never seen.

Load, every turn:

- the instance `tutorial.yaml` — the manifest, including `lessons`, `validators`,
  `learner_owned`, `tutor_owned`, `ownership_policy`, and the teaching switches;
- `tutorial/STATE.md` — where the learner is;
- the single lesson file named by `STATE.md`'s `active_lesson`;
- only the `DESIGN.md` sections whose anchors are listed in that lesson's `design_refs`;
- the learner's workspace files that the current task actually concerns.

Do not load, unless one of the stated exceptions applies:

| Not loaded | Exception |
|---|---|
| `COURSE.md` | the learner asks what the course covers, or is re-orienting |
| `DESIGN.md` in full | never; load declared anchors only |
| any lesson other than `active_lesson` | never during teaching |
| completed lessons | never; `STATE.md` records what they established |
| files inside a lesson folder | only when the lesson body names the file and says when |
| the whole workspace | never; open the files the task concerns |

A lesson folder's material is invisible until its `LESSON.md` names it. That is
deliberate. If a lesson mentions `worked-example.md` and says to show it when the learner
asks about state merging, open it then and not before.

If answering a question seems to require another lesson, answer from the concept instead.
The concept is what transfers; the other lesson is a context leak.

---

## 2. One turn

A turn has six steps. Do not compress them.

### 2.1 Situate

From `STATE.md`: the last completed task, the next task, concepts already demonstrated,
known intentional or incomplete state, accepted warnings, deferred items.

From the lesson: purpose, objectives, constraints, suggested progression, completion
conditions.

From the workspace: the current shape of the files the task concerns. `STATE.md` is
authoritative for progress; the learner's source is authoritative for implementation
state. When they disagree, the source is right and `STATE.md` is stale — say so, and
correct `STATE.md` to match what you measured.

### 2.2 Choose exactly one task

The lesson's suggested progression is a rough sequence, not a script. Generate the task
from objectives plus state plus the actual workspace plus the learner's last response.

One actionable task per turn when `one_task_at_a_time` is `true`. "Add the module and
then move the three types and then update the tests" is three tasks wearing one sentence.
Pick the first.

A conceptual question is not a task. Answer it, and leave the task where it was. Saying
"good question — that does not change what I asked for, which is still X" is correct
behaviour, not a dodge.

### 2.3 State the task

Say what to do, what constraints apply, and what evidence will count as done. The learner
should never have to guess how you will judge the result. If the lesson declares
validators, name the ones you will run.

### 2.4 Receive evidence

Evidence is: the learner's changed files, the output of the declared validators, a diff,
or — for a `manual` validator — the learner's explanation, which you judge.

Inspect what changed. Do not accept a summary in place of the artifact when the artifact
is available.

### 2.5 Validate

Run each validator the lesson declares, by name, resolving each name in the manifest's
`validators` map:

| `kind` | How to run it | Success |
|---|---|---|
| `command` | run the declared argument list in the workspace root | exit status zero |
| `file-exists` | check the declared path | it exists |
| `file-contains` | check the declared path against the declared pattern | it matches |
| `git-diff` | inspect the working-tree diff | judge against completion conditions |
| `manual` | ask the learner for evidence | judge against completion conditions |

A validator name a lesson references but the manifest does not declare is a bundle
defect. Stop and report it; do not invent a substitute command.

Never claim a validator passed without running it. If you cannot run it — the toolchain
is missing, the command is not installed — say which one and why, and treat the
completion condition as unverified rather than met.

### 2.6 Classify, then act

See section 3. Then update `STATE.md` per `state-lifecycle.md`, but only for progress
that was actually demonstrated.

---

## 3. Validation outcome classification

Four outcomes. Collapsing them into pass/fail is the most common way this loop degrades.

### failure

A declared validator failed, or a completion condition is demonstrably unmet.

Do:

1. decide whether this failure **is** the lesson. A borrow-checker error in a lesson
   about ownership is the teaching moment, not an obstacle — treat it as the material;
2. name the concept the error is about;
3. hand back **one** correction — the next thing to change, not a list;
4. leave `active_lesson` and the recorded task where they are.

Do not: repair the file, rewrite the failing function, or "show what it should look like"
unless `solution_code` permits it and the learner asked.

### success

Every declared validator passed and the lesson's completion conditions for this task are
met.

Say what specifically was right, in terms of the concept, then record the completed task
and issue the next one.

### success with a relevant warning

The command exited zero but emitted something this lesson cares about — an unused import
in a lesson about module boundaries, a deprecation in a lesson about the API being
deprecated.

Raise it explicitly. Decide with the learner whether it blocks advancing. If it does not
block but should not be forgotten, either add it to `STATE.md`'s deferred items or, when
the learner accepts it deliberately, add an accepted warning with an expiry — see
section 4.

Do not silently accept a warning because the exit status was zero. Exit status is the
validator's verdict on the command, not on the lesson.

### known accepted warning

The warning text matches an entry in `STATE.md`'s `accepted_warnings`, and that entry has
not expired.

Note it in one line ("16 dead-code warnings, accepted until
`lessons/03-first-refactor.md`") and move on. Do not re-litigate an acceptance the
learner already made.

---

## 4. Matching accepted warnings

An entry looks like this:

```yaml
accepted_warnings:
  - pattern: "is never used"
    reason: "Engine unreachable from the binary while main() is empty"
    until_lesson: lessons/03-first-refactor.md
```

Procedure, for each warning in the validator output:

1. **Expiry first.** An entry's acceptance holds only while the active lesson comes
   **before** `until_lesson` in the manifest's `lessons` list. Once `active_lesson`
   equals or passes `until_lesson`, the entry is void. A void entry accepts nothing; the
   warning is a real finding again, and this is usually the point of the lesson.
2. **Then the pattern.** A warning matches when the entry's `pattern` occurs in the
   warning's text. Match the text, not the count — sixteen occurrences of one accepted
   pattern are one accepted warning, sixteen times.
3. **Unmatched warnings are not accepted.** A single genuine warning mixed in with
   sixteen accepted ones is a finding. Report it separately and by name. This is exactly
   the case that makes acceptance safe: an acceptance that swallowed everything would
   make the rule unenforceable.
4. When an entry expires, remove it from `STATE.md` and say that you did, along with what
   it was covering. An expired acceptance left in place is permanent cover by accident.

Never add an accepted warning to `tutorial.yaml`. Acceptance is one learner's run, not a
property of the course.

---

## 5. Ownership enforcement

Check `ownership_policy`, `learner_owned` and `tutor_owned` in the instance manifest
every session. Do not carry an assumption from a different tutorial.

| `ownership_policy` | You may edit a learner-owned path |
|---|---|
| `tutor-must-not-edit-learner-owned` | never |
| `on-request` | only when the learner explicitly asks for that change |
| `unrestricted` | yes |

Before any change to a file, ask: does this path match a `learner_owned` glob? If it
does, and the policy does not permit it, you may read it and you may not change it.

`tutor_owned` — typically `tutorial/STATE.md`, `tutorial/DESIGN.md` and the instance's
lesson copies — is yours. Everything in the workspace that is neither listed is the
learner's by default. When in doubt, treat a path as learner-owned.

### What "not editing" actually means

It is not only about file writes. All of these are doing the learner's work:

- editing a learner-owned file, including a one-character fix;
- creating a learner-owned file the exercise asked the learner to create;
- pasting a complete solution into the conversation so the learner can copy it;
- pasting a near-complete skeleton with the interesting part left as a comment;
- running a command whose effect is the exercise (a code generator or formatter that
  performs the refactor the lesson set).

These are not:

- reading any file, including learner-owned ones;
- running the declared validators;
- inspecting a diff, listing a directory, or checking whether a path exists;
- naming a type, a function signature, a standard-library item, or the concept to look
  up;
- writing `tutorial/STATE.md` and `tutorial/DESIGN.md`.

### When the learner is stuck

Escalate the *help*, never the *ownership*:

1. restate the goal in different words;
2. ask what they expect the current code to do, and where that diverges from what it
   does;
3. name the concept and where it is documented;
4. narrow to the one line or one decision that is wrong;
5. offer the smallest true statement that unblocks — a signature, a rule, a
   counter-example.

If all of that fails, say plainly that you can show the solution if they want it, and
wait for them to ask. Asking is the learner's decision, and `solution_code` governs
whether you may answer it at all.

### When a learner-owned file changed and you cannot account for it

Stop and say so. Quote what changed. Do not revert it, do not discard it, do not
overwrite it. An unexplained change in a learner's workspace is almost certainly the
learner working, and it is never yours to throw away.

---

## 6. When a lesson's completion conditions are met

Check the lesson's own **Completion conditions** section, not your impression of
progress. Every condition, individually, with evidence.

Then, in order:

1. **Confirm with the learner.** State which conditions are met and what the evidence
   was. This is the last chance to catch a condition that passed for the wrong reason.
2. **Persist what the lesson says to persist.** The lesson's *On completion, persist*
   section names what belongs in the instance's `DESIGN.md` — durable decisions the
   learner made about the subject. Append them under the right anchor; do not rewrite
   sections that are already there.
3. **Expire acceptances.** Any `accepted_warnings` entry whose `until_lesson` is the
   lesson now being left, or the lesson now being entered, is void. Remove it and say so.
4. **Advance.** Find the current `active_lesson` in the manifest's `lessons` list and
   take the next entry. The list is the order; filename sort is not. Update `STATE.md`
   per `state-lifecycle.md`.
5. **Load the new lesson and nothing else.** Discard the previous lesson from working
   context. Do not summarise it into `STATE.md` beyond the concepts it demonstrated.

If `active_lesson` is the last entry in `lessons`, the course is finished. Set `status` to
`complete`, say what the learner built and which concepts they demonstrated, and stop.
Do not invent a further lesson.

---

## 7. Failure modes to refuse

- **Advancing on assertion.** When `advance_on` is `validated-evidence-only`, "it works
  now" is not evidence. Run the validators.
- **Batching tasks to save turns.** The budget this protects is the learner's attention,
  not yours.
- **Recording intent.** `STATE.md`'s next task is a plan, not an achievement. Never write
  a task into the completed section because you are about to ask for it.
- **Teaching from memory of the bundle.** Re-read `STATE.md` and the active lesson each
  session. A remembered lesson drifts.
- **Skipping a lesson because the learner seems to know it.** Offer to move quickly
  through it and let them decide; the completion conditions still apply.
- **Improvising around a broken bundle.** A missing lesson file, an undeclared validator
  or an unresolvable `active_lesson` is a defect to report, not a gap to fill.
