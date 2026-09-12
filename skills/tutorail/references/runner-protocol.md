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
- the single lesson file named by `STATE.md`'s `active_lesson` — which is normally an
  entry in `lessons`, and may be a file under `tutorial/lessons.generated/` (section 7);
- only the `DESIGN.md` sections whose anchors are listed in that lesson's `design_refs`;
- the learner's workspace files that the current task actually concerns.

Do not load, unless one of the stated exceptions applies:

| Not loaded | Exception |
|---|---|
| `COURSE.md` | the learner asks what the course covers, is re-orienting, or you are deciding whether to write a lesson (section 7.2) |
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

### A resume reads no catalogue

The learner's catalogues are refreshed **once, when a discovery request starts**, and at
no other moment. A session that resumes an instance reads no catalogue at all: the
instance already names its bundle, and `STATE.md` already holds the learner's place.

So a teaching turn never fetches anything, never contacts a host, and costs nothing
beyond the files listed above. Do not run `scripts/catalogs.py` during a teaching
session, and do not run it per turn during discovery either. `catalogue-format.md`
section 4 has the timing; this section exists so that a session which never loads that
document still knows not to.

The one exception is a learner who, mid-course, asks what else is available. That is a
discovery request inside a teaching session: refresh once, answer, and go back to the
lesson.

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

`tutor_owned` — typically `tutorial/STATE.md` and `tutorial/DESIGN.md` — is yours.
Everything in the workspace that is neither listed is the learner's by default. When in
doubt, treat a path as learner-owned.

Two paths are settled by the runner rather than by the manifest, because a bundle cannot
describe an instance that does not exist yet:

- `tutorial/lessons.generated/**` is **tutor-owned in every instance**, whether or not
  `tutor_owned` lists it. It holds only lessons you wrote (section 7);
- `tutorial/lessons/**` is **read-only in every instance**, whether or not `tutor_owned`
  lists it. Those are the author's lessons, copied in at materialization. Correct a
  defective one by reporting it, never by editing the copy.

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

Step 3 often settles a second question on its way past. If naming the concept reveals that
the learner has never met it, this may be a prerequisite gap rather than a hard exercise,
and section 7.2 has the test that decides. Run that test before you conclude that more
coaching is the answer — the ladder above is the right response to difficulty and the
wrong response to a concept nobody taught.

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
   take the next entry. The list is the order; filename sort is not. When the instance has
   a `lessons.generated/` directory, apply section 7.3 first: an incomplete generated
   lesson whose `after:` is the lesson just finished takes precedence over the next entry.
   Update `STATE.md` per `state-lifecycle.md`.
5. **Load the new lesson and nothing else.** Discard the previous lesson from working
   context. Do not summarise it into `STATE.md` beyond the concepts it demonstrated.

If `active_lesson` is the last entry in `lessons` and no incomplete generated lesson
claims it, the course is finished. Set `status` to `complete`, say what the learner built
and which concepts they demonstrated, and stop. Do not invent a further lesson — writing
one here would be exactly the improvisation section 7.2 refuses.

---

## 7. Generated lessons

A course can be entirely sound and still not carry what this learner needs next. Two
situations produce the same artifact:

- **A side lesson.** The learner meets a concept the main path never reaches — lifetimes,
  trait objects, interior mutability — and cannot continue without it. A compact detour,
  then back to the main path.
- **A main-path draft.** `COURSE.md` maps a chapter that has no lesson file yet, so
  `lessons` does not list one. Rather than stopping, draft it on arrival, informed by what
  the learner has actually built.

Both live in `tutorial/lessons.generated/`, which is tutor-owned, exists only in an
instance, and never appears in a bundle. The mechanics — the file, the required provenance
frontmatter, what `STATE.md` records — are in `state-lifecycle.md` section 8. Load it
before creating anything.

### 7.1 When generation is warranted

Generating a lesson is legitimate when the **course is working as intended** and the
learner needs something it does not cover. All of these must hold:

- every `lessons` entry resolves, every validator a lesson names is declared in the
  manifest, and every `design_refs` anchor exists. The bundle does what it says it does;
- the gap is real and it is now — the learner is blocked on a concept the course never
  teaches, or has arrived at a chapter `COURSE.md` maps and no lesson file covers;
- an answer in conversation is not enough. The material needs objectives, constraints and
  completion conditions of its own;
- you can state `reason:` in one sentence that a bundle author who was not here can act
  on.

Generation is a recorded, provenanced act, not an improvisation. If you cannot write the
reason down, you do not have one.

Two routes reach a warranted lesson. Either you judge that the gap is real — which needs
the test in section 7.2, because one symptom is produced by two opposite situations — or
the learner asks for one.

#### When the learner asks for one

A learner may ask for a side lesson directly: "give me a side lesson on lifetimes", "I
want a detour on trait objects before we carry on". Treat that request as first-class. It
settles the judgement in section 7.2 without you having to make it, because the person who
knows what they do not know has said so.

One guard, and only one. **A learner may not request a side lesson on the active lesson's
own learning objectives.** "Teach me lifetimes" during a lesson whose declared objectives
are lifetimes is a request for the answer with extra steps: the lesson exists to make them
work that concept out, and handing it over in lesson form hands over the exercise. Say so
plainly, name what the current lesson is asking them to arrive at, and offer the
escalation in section 5 instead.

Everything outside the active lesson's declared objectives is fair game — a concept the
course reaches later, a concept the coverage list never mentions, a concept you would not
have judged blocking. Test the request against the objectives the lesson declares, not
against your impression of what the lesson is about.

A requested lesson is an ordinary generated lesson in every other respect: the same
structure, the same provenance frontmatter, the same completion conditions, the same
placement by `after:`. Record in `reason:` that the learner asked for it, and what they
asked for.

**The request usually arrives part-way through a lesson**, because that is when the
learner notices what they are missing. Take the detour from where they are and send them
back to the same place: section 7.3 is the mechanic, and it is the same one that covers
being blocked on an untaught prerequisite. Do not make the learner finish the lesson first
so the detour fits at a boundary. A bundle author reading these files later must be able to tell a detour the
tutor judged necessary from one the learner chose, because only the first is evidence
about the course (`bundle-format.md` section 8).

### 7.2 When generation is NOT warranted

**Improvising around a broken bundle remains forbidden, and this is not a way around it.**
The distinction carries the whole feature:

| What you found | What it is | What to do |
|---|---|---|
| `lessons` names a lesson file that is not there | a defect | stop; report the path |
| a lesson names a validator the manifest does not declare | a defect | stop; report the name |
| a lesson's `design_refs` names an anchor `DESIGN.md` does not have | a defect | stop; report the anchor |
| `active_lesson` names a path in neither `lessons` nor `lessons.generated/` | a defect | stop; report it |
| a lesson folder has no `LESSON.md`, or names material that is not there | a defect | stop; report it |
| `COURSE.md` maps a chapter, `lessons` claims no lesson for it | a gap | a main-path draft is warranted |
| the learner is blocked on a concept the course never teaches | a gap | a side lesson is warranted |

A **defect** is the bundle contradicting itself: it promises something it does not
contain. Drafting a lesson over a defect hides the contradiction from the only person who
can fix it, and quietly gives this learner a different course from every other learner.
Report it and let the learner decide.

A **gap** is the bundle being honest about its own edge. Nothing is broken; the course
simply does not reach where this learner now is.

These are also not reasons to generate:

- **the learner is stuck on a concept the course already taught.** That is a teaching
  problem. Escalate the help, per section 5. Being stuck is not one situation, though, and
  the test that tells the two apart is at the end of this section;
- the lesson turned out harder than you expected, or you would rather teach something
  else;
- a topic seems missing to you while nothing is blocked — record it as a deferred item in
  `STATE.md` instead, and say it is a suggestion for the course author;
- to move past a lesson quickly, or to cover a lesson you have not opened.

**Never generate a lesson that replaces one the bundle has.** A generated lesson adds to
the course for one learner. It never overrides an authored lesson, and it never edits one:
the instance's `lessons/` copies stay read-only.

A generated lesson is held to the same rules as an authored one. It may name only
validators the manifest declares and only `DESIGN.md` anchors that exist — inventing
either would manufacture the very defect this section tells you to report.

#### Being stuck is two situations wearing one symptom

"The learner is stuck" is a symptom, and two opposite situations produce it. Stuck because
a concept they needed was never taught is precisely what a side lesson is for. Stuck
because the exercise is hard is the learning itself, and a lesson written to relieve it
takes the lesson away. Guessing which one you are looking at is how this feature turns
into a way of finishing exercises for people.

So do not judge it. Name the **blocking concept** — the single thing that, if they had it,
would unblock them — and test that concept against the course's own **coverage list**: the
section of `COURSE.md` naming the topics the course must eventually cover
(`bundle-format.md` section 3). This is one of the stated exceptions in section 1, so open
`COURSE.md` for it.

| The blocking concept | What it is | What to do |
|---|---|---|
| is in the coverage list, and no completed lesson taught it | a genuine prerequisite gap | a side lesson is warranted |
| is in the coverage list, and was already taught | ordinary difficulty | do not generate; coach, per section 5 |
| is nowhere in the coverage list | outside what this course undertakes | say so to the learner; do not widen the course silently |

Answer "no completed lesson taught it" from `STATE.md` — the *Concepts demonstrated*
section and the *Generated lessons* record — never by opening completed lesson files.
Section 1 still holds; a concept worth teaching twice is not worth a context leak. When
`STATE.md` does not settle it, ask the learner whether they have met the concept before.
One question is cheaper than a lesson, and they are a better witness to their own history
than your reconstruction of it.

The third row is a conversation, not a refusal. Say that the concept sits outside what
this course covers, say what it would take to learn it properly, and offer the smallest
true statement that unblocks the task in front of them. What the row forbids is the
*silent* version: drafting the lesson anyway grows the course by one tutor's judgement,
for one learner, with nothing recorded that says the course was widened. If the learner
hears that and asks for the detour regardless, it is now a request, and section 7.1
governs it.

**When the bundle declares no coverage list**, this test has no oracle and cannot be run.
Fall back to your own judgement of whether the concept is a prerequisite the course
assumes or a difficulty the exercise intends — and say which you concluded, and why, so
the learner can disagree. A course that declares a coverage list takes that judgement out
of your hands, which is the whole point of declaring one.

### 7.3 Moving between lessons when generated lessons exist

The manifest's `lessons` list is **never** modified — not to add a generated lesson, not
for any other reason. `state-lifecycle.md` section 8 says why. Generated lessons are an
overlay, positioned by their `after:` field and discovered by listing the directory.

A generated lesson's `after:` always names an **authored** lesson — an entry in `lessons`,
never another generated lesson. Two fields carry the overlay, and they are independent:

- **`after:`**, in the generated lesson's own frontmatter, is **placement** — where this
  lesson belongs in the course;
- **`resume_at`**, in `STATE.md`, is **the way back** — the `lessons` entry that becomes
  active when the detour finishes.

**Never compute one from the other.** `state-lifecycle.md` section 8.3 has the rule and
the reason: a detour can start part-way through a lesson, and deriving the way back from
the placement sends the learner past the rest of the lesson they were in the middle of.

There are three moments, and the first two both write `resume_at`.

**A detour starts part-way through a lesson L**

This is the ordinary case for a side lesson. Being blocked on a concept the course never
taught happens inside a lesson, not at its edge, and a learner may ask for a detour at any
moment (section 7.1). Nothing about lesson L completes here — it is interrupted.

1. `active_lesson` becomes the generated lesson;
2. `resume_at` becomes **L**, the interrupted lesson;
3. record the lesson in the *Generated lessons* section as pending
   (`state-lifecycle.md` section 8.5).

The detour's own `after:` is placement and is chosen separately —
`state-lifecycle.md` section 8.2. Do not advance `active_lesson` past L, do not record
L complete, and do not reset the `STATE.md` body: L is interrupted, not finished.

**A detour starts at a boundary, on completing an authored lesson L**

After the steps in section 6:

1. list `tutorial/lessons.generated/`. If it does not exist, there is no overlay and
   nothing changes;
2. if an **incomplete** generated lesson declares `after: L`, it becomes `active_lesson`,
   and `resume_at` becomes the entry that follows L in `lessons` — L is finished, so
   there is nothing to go back into. When L is the **last** entry, `resume_at` is L
   itself (`state-lifecycle.md` section 8.3);
3. otherwise take the next entry in `lessons`, exactly as section 6 step 4 says.

**A generated lesson completes**

1. if another incomplete generated lesson declares the same `after:` value, it becomes
   `active_lesson` and `resume_at` is left as it is. The learner has not moved, so the
   place they come back to has not changed;
2. otherwise `active_lesson` becomes `resume_at`, and the `resume_at` field is removed.
   When `resume_at` names the interrupted lesson, the learner lands back in unfinished
   work: do not reset the `STATE.md` body, and make *Next task* the task the detour
   interrupted (`state-lifecycle.md` section 8.4, step 5).

A generated lesson is incomplete until `STATE.md` records it as finished, in the
*Generated lessons* section (`state-lifecycle.md` section 8.5). The lesson files carry no
progress themselves, deliberately. When several incomplete generated lessons share one
`after:`, take them oldest `generated_at` first, and only then the main path.

A generated lesson's completion conditions bind exactly like an authored lesson's. You
wrote them; do not wave them through because you wrote them.

### 7.4 A main-path draft announces itself

**When a lesson with `kind: main-path-draft` becomes the active lesson, say so before you
teach anything from it.** One sentence, at the start, in your own voice: this chapter had
no lesson written for it, and you are drafting it from where the learner has actually got
to.

The learner cannot tell otherwise. A draft sits in the same place in the course, uses the
same structure, and reads in the same confident voice as a lesson someone wrote and
reviewed — and it carries none of the same warrant. Two things turn on their knowing:

- **it changes how to read a confident claim in that lesson.** An authored lesson was
  written before anyone took the course and was reviewed as a lesson. A draft was written
  today, by you, against one learner's code, and was reviewed by nobody. The learner is
  entitled to weigh it accordingly, and to push back harder on it than they would on a
  chapter the author wrote;
- **they will want to know which lessons were drafted.** A draft is the raw material an
  author later promotes into the course (`bundle-format.md` section 8), and the learner who
  took it is the one person who can say whether it was any good. That is a question they
  can only answer if they knew at the time.

Do not bury it — not in a closing note, not in a parenthesis halfway down, not only in
`STATE.md`. A learner who works out at the end of a chapter that you knew and did not lead
with it has learned something about you rather than about the subject.

A `side-lesson` does not need this. Its nature is already plain: either the learner asked
for it, or you announced the detour when you proposed it (`state-lifecycle.md` section 8.2,
step 7). Saying it a second time is noise, and noise is what makes the announcement that
matters easy to miss.

---

## 8. Failure modes to refuse

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
- **Generating a lesson over a defect.** Section 7 permits writing a lesson when the
  course works and the learner needs something it does not cover. It permits nothing when
  the course is broken: a drafted lesson there conceals the defect and gives this learner
  a course nobody else is taking. Section 7.2 is the test.
- **Generating a lesson because the learner is stuck.** Stuck on a concept the course
  already taught is a teaching problem, and a lesson written to relieve it is the exercise
  handed over in a longer form. Section 7.2 has the test.
- **Teaching a main-path draft as though someone wrote it.** The learner is owed one
  sentence saying the chapter was drafted on arrival. Section 7.4.
- **Editing the manifest's `lessons` list.** It is the authored course. A generated lesson
  is an overlay; the list stays byte-identical to the bundle's.
- **Refreshing a catalogue to teach a lesson.** A resume reads no catalogue. Section 1.
- **Reporting a catalogue that failed to refresh as though it simply held nothing.** A
  host that cannot be reached, a repository the learner has no access to, and a
  repository with no catalogue file at that path are three problems with three repairs,
  and none of them is "no tutorial matched". `catalogue-format.md` section 7 carries the
  kinds; report the one that happened.
- **Offering a cached entry as current.** When a catalogue was served from its last
  successful copy, say so and say how old it is, every time you present an entry from it.
