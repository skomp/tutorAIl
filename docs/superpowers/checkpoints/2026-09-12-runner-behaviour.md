# Checkpoint — Runner half of bundle relationships

**Date:** 2026-09-12
**Branch:** `main`, branched from `origin/main` at **79a2625**
**Spec:** `docs/superpowers/specs/2026-09-12-bundle-relationships-design.md`, sections 5, 6, 7, 11
**Status:** **COMPLETE as specified, and uncommitted.** Nothing is staged. The human reviews
and commits. Section 8 below is honest about what is written but not proven.

---

## 0. What this task was

Build the **runner** half of bundle relationships. The discovery half (catalogue index,
`catalogs.py covers|follow-ups|prepare`, `catalogue-format.md` section 12, validator checks
1-25, the `tests/fixtures/catalog-relationships/` fixtures) was already built and committed
at 79a2625 and was **not** reimplemented.

Files owned by this task, and nothing outside this list was created, edited, staged or
deleted:

| File | State at this checkpoint |
|---|---|
| `skills/tutorail/SKILL.md` | edited — one new section, two reference-table rows |
| `skills/tutorail/references/runner-protocol.md` | edited — new sections 11 and 12, plus four wiring edits |
| `skills/tutorail/references/state-lifecycle.md` | edited — new section 10, new frontmatter field, materialization step 9, plus wiring |
| `docs/superpowers/checkpoints/2026-09-12-runner-behaviour.md` | this file |

`git status --short` shows exactly those four and nothing else.

---

## 1. Baseline and final test results, verbatim

Baseline, before any edit:

```
$ git log --oneline -1
79a2625 Add covers, assumes and bundle recommendations to the format and validator

$ python3 tests/test_validate_bundle.py   -> OK - 359 assertions passed.
$ python3 tests/test_catalogs.py          -> OK - 267 assertions passed.
```

After all edits (only documents were changed, so these must be identical, and are):

```
$ python3 tests/test_validate_bundle.py   -> OK - 359 assertions passed.
$ python3 tests/test_catalogs.py          -> OK - 267 assertions passed.
```

---

## 2. What was written, file by file

### `skills/tutorail/references/runner-protocol.md`

Sections were **appended**, never renumbered. Five files cross-reference this document by
section number (`SKILL.md`, `state-lifecycle.md`, `bundle-format.md`, and itself), so
inserting a section anywhere but the end would have silently broken 23 references. The
existing numbering 1-10 is untouched.

- **New section 11, "Assumed concepts, before the first task"** — 11.1 when the review is
  due, 11.2 what it looks like, 11.3 the three answers and the way back, 11.4 recording the
  acknowledgement, 11.5 failure modes to refuse.
- **New section 12, "Follow-ups — at completion, and whenever they are asked for"** — 12.1
  when, 12.2 what to offer and in what order, 12.3 the curated list and the separate "find
  more", 12.4 nothing here can fail a finished course, 12.5 starting one is starting any
  other course, 12.6 failure modes to refuse.
- Header **Status** line: added "when a course finishes or the learner asks what comes after
  it".
- Section 1, the "load every turn" manifest bullet: added `assumes` where the bundle
  declares it.
- Section 6, the paragraph that ends a course: added a pointer to section 12 and the clause
  that the offer never implies the learner has to take one.
- Section 9, the consolidated refusal list: six new bullets pointing at 11.1, 11.2, 11.4,
  12.3, 12.4, 12.5.

### `skills/tutorail/references/state-lifecycle.md`

- **New section 10, "The assumed-concept acknowledgement"** — 10.1 the field, 10.2 what it
  asserts and what it does not (with the table of rejected alternatives), 10.3 writing it,
  10.4 offering follow-ups records nothing, 10.5 two inconsistencies to report.
- Section 2: `assumes_reviewed` added to the frontmatter field table and shown in the shape
  block as a comment.
- Section 3 (materialization): **new step 9**, "Show the assumed-concept review, if there is
  one", after the `supplies` placement and before teaching. The existing step 8 is unchanged
  and the one in-document reference to "step 8" still points at `supplies`.
- Section 5, *Reaching the end*: pointer to `runner-protocol.md` section 12 plus the rule
  that the offer writes nothing here.
- Section 7: one pointer line to 10.5 rather than a second copy of the two bullets.
- Header **Status** line: added the acknowledgement trigger.
- **Pre-existing host-neutrality violation fixed.** Line 153 read
  "**Read each `from` from the bundle source…**" — sentence-initial `Read`, which the grep
  bans. Changed to "**Take each `from` from the bundle source…**". This was present at
  79a2625 and is the only pre-existing hit in the three owned files.

### `skills/tutorail/SKILL.md`

- **New section "Assumed concepts, and what comes next"**, placed after *Optional lessons*
  and before *Reference files*. It opens with the central rule quoted verbatim and gives the
  control-plane summary of both behaviours, ending with the exact reference sections.
- The *Reference files* table: `references/runner-protocol.md` gains "when a course declares
  `assumes`; when a course finishes or the learner asks what comes after it";
  `references/state-lifecycle.md` gains "the learner acknowledges the assumed-concept
  review".
- **Frontmatter is byte-identical to 79a2625** — `name` + `description` only, and the
  description is unchanged. Proven by comparing the frontmatter block against
  `git show 79a2625:skills/tutorail/SKILL.md`; the comparison returns `True`.

---

## 3. The state extension, and why it is the smallest compatible one

**One optional frontmatter field on `STATE.md`: `assumes_reviewed`, holding a date.**

It is written once, in the turn the learner chooses to continue. Absence means the review
has not been shown; presence means it has. There is no third value, nothing to expire and
nothing to update later.

Why this rather than the alternatives, all of which were considered:

| Alternative | Rejected because |
|---|---|
| a line in *Decisions made in discussion* | that section is defined as "choices the learner made that later lessons depend on", and no lesson depends on this one. Worse, deciding whether to re-show the review would mean matching a **sentence** — a prose oracle for a yes/no question, which is neither unambiguous nor testable |
| a line in *Concepts demonstrated* | the learner demonstrated nothing. Section 1 of `state-lifecycle.md` forbids it directly |
| a new body section | a whole heading in every instance of every course that declares `assumes`, to hold one date. Section 9.2 of that document makes the same argument against writing `not-offered` lines |
| `prerequisites_met` / `assumes_confirmed` | both name a claim nobody made. The learner confirmed nothing about themselves |
| a boolean `true` | a date costs the same and records when. It matches `updated`'s existing shape |

Frontmatter is the right home because that document says so: "Frontmatter is
machine-checkable. The body is what the tutor reads." This fact is consumed by a machine
decision taken every session, and `resume_at` is the existing precedent for an optional
frontmatter field present only under a stated condition.

**Proven not to break the validator.** An instance built from
`skills/tutorail/examples/rust-cli-basics/` with `assumes_reviewed: 2026-09-12` added to
`STATE.md` produced **exactly the same single finding** as the same instance without the
field (`[check 7] tutorial.yaml: an instance's tutorial.yaml carries an 'instance:'
stamp… This one has none.` — an artefact of the hand-built instance, unrelated). Checks 11
and 12 validate required keys and do not whitelist, so the extra key adds zero findings.

---

## 4. How the learner returns to the pending course start after a digression

**Nothing moves, so there is nothing to restore.**

The review happens before the first task. A concept question is answered from the concept,
and a `covers`/`prepare` query reads catalogue metadata only. Neither opens a lesson file,
neither states a task, neither materialises anything, and neither writes to `STATE.md`. So
`active_lesson` still names `lessons[0]`, `status` is whatever materialization set, and the
pending start is *already* recorded by the field that always records it.

This is the deliberate contrast with an optional-lesson detour, which **does** move
`active_lesson` and therefore **must** record `resume_at` (`state-lifecycle.md` section 9.3).
Stated in both documents so neither can be read as the other's rule:
`runner-protocol.md` 11.3 and `state-lifecycle.md` 10.3.

The learner may take several digressions, in any order; the review is not re-shown between
them. If the digression ends with them wanting the preparatory course instead, that is
`SKILL.md` step 2's existing "named a different subject" branch — `tutorial/` is singular,
the tutor states what is active and lets them choose, and never replaces an instance on its
own judgement.

---

## 5. Decisions the spec did not settle

| Decision | Chosen | Why, and what the alternative was |
|---|---|---|
| **Trigger for the review** | exactly one condition: non-empty `assumes` **and** no `assumes_reviewed` stamp | The alternative — also requiring "the course has not started" — is a compound condition, harder to test, and would mean an instance materialized before the field existed never sees the review at all. The chosen rule shows it once, mid-course, on such an instance; that is stated in 11.1 as intended rather than left to be discovered as a bug. It can never loop |
| **Grouping order of the `assumes` review** | by level, **most demanding first**: `advanced`, `working`, `conceptual`, `awareness`; manifest order inside each group | Spec says "grouped by level" and not which way. Ascending would match the level table in `catalogue-format.md`. Descending was chosen because the demanding group is the one a learner who is not ready recognises themselves in, and the one they would skim past. Reversible in one sentence of 11.2 if the reviewer disagrees |
| **Which script answers a digression** | `prepare <tutorial_id>` for the whole list, `covers <concept>` for one named concept | `prepare` answers the list in one run and names assumed concepts nothing available covers. `covers` was the obvious choice and is worse for the common case |
| **A course that is in the author-curated section but also carries an inferred reason line** | keep the course where the script put it, and keep the inferred line with its tag | The script's own sectioning is per-course; the tagging is per-line. Dropping the inferred line to tidy the entry loses provenance, which is the one thing the feature refuses to lose. Stated in 12.3 |
| **Whether offering follow-ups records anything** | nothing at all | Same argument section 3 gives for supplied files whose targets already exist: re-running is idempotent and the answer is derivable, so a record would be a second thing to keep true. Stated in 10.4 |
| **Whether `STATE.template.md` may carry the field** | never | A template describes a learner who has not started. A stamped template would suppress the review for every learner of that course. Stated in 10.1 — as documentation only; see section 7 |

---

## 6. Measured — do not re-derive

Reproducible from the repository, using the committed fixture catalogue
`tests/fixtures/catalog-relationships/catalog.yaml` through a one-entry `catalogs.yaml`
pointed at it by absolute path.

| Fact | Value |
|---|---|
| `catalogs.py` subcommands | `discover`, `status`, `resolve`, `covers <query>`, `follow-ups <id>`, `prepare <id>`; the last three take `--refresh` and otherwise read what `discover` left on disk |
| `follow-ups durable-event-broker` ordering | the course's own `recommended_follow_ups` in **author order** first, then reverse-index hits. `streaming-query-engine` (author) before `log-replay-forensics` (third party, reverse index) |
| Deduplication | one course, one block, **every** provenance line kept — `streaming-query-engine` returned five `why:` lines |
| Provenance tagging | every `why:` line ends `[author recommendation]` or `[not an author recommendation]` |
| Section split | `recommended by an author (N), in author order:` then `related, found by matching metadata (N) - these are NOT author recommendations:` |
| Unavailable follow-up | `unresolved: durable-event-broker recommends 'distributed-log-broker' … and no configured catalogue carries it`, **exit 0** |
| `follow-ups` on a leaf course | `(no bundle matched)`, **exit 3** |
| `follow-ups` on an unknown id | `error: no catalogue supplies '<id>'. Available: …`, **exit 3** |
| `covers ""` | refused — "the query holds no letters or digits", **exit 2** |
| `prepare streaming-query-engine` | two `note:` lines naming `go-programming` and `consumer-offsets` as assumed concepts nothing available covers, exit 0 |

**Exit 3 is ambiguous and the runner must disambiguate it by the message.** "no bundle
matched" (a finished course with nothing after it — normal) and "no catalogue supplies
`<id>`" (the instance's `tutorial_id` is in no configured catalogue) share the code. Neither
may fail course completion. This is the table in `runner-protocol.md` 12.4.

### Host-neutrality grep, with the positive control watched firing

```
PAT='\b(Read|Bash|Task|Grep|Edit|Write|apply_patch|AskUserQuestion)\b'
FILES=skills/tutorail/SKILL.md
      skills/tutorail/references/runner-protocol.md
      skills/tutorail/references/state-lifecycle.md
```

- **Positive control A** — each of the eight tokens planted alone in a file: the grep
  matched 1 line for every one of the eight.
- **Positive control B** — `Read the manifest, then Write the state file.` appended to a
  **copy of each of the three real files**: 1 hit in each. This rules out a path, encoding
  or file-size reason for a zero.
- **Negative control** — `Open the file. Check the path. Record the stamp. Take each entry.`
  → 0 hits, so the replacements used in the prose do not trip it.
- **Real run** — `grep exit=1`, no matches, on all three files.
- Widened sweep for `Glob|TodoWrite|WebFetch|WebSearch|NotebookEdit|MultiEdit|BashOutput|KillShell|SlashCommand` → no matches.
- `grep -nE '\$\{|CLAUDE_PLUGIN_ROOT'` → control fires on a planted `${CLAUDE_PLUGIN_ROOT}/x`; real run has no matches.
- No absolute paths: `grep -nE '(^|[ (`])/(Users|home|private|tmp)/'` → no matches.

### `SKILL.md` size — the brief's figure does not match the file

| Method | At 79a2625 | Now | Delta |
|---|---|---|---|
| `wc -w`, whole file | 2542 | 2783 | +241 |
| body after frontmatter | 2412 | 2653 | +241 |
| body minus markdown table rows | **2084** | **2302** | +218 |

**The brief's "roughly 1900 words, do not inflate past ~2100" matches no measurement of the
file as it stood before this task.** The closest method already read 2084 at baseline, and
`wc -w` read 2542. The constraint was therefore treated as "add as little as possible":
the new section is 3 paragraphs, one of which is the mandated 26-word quotation, and the two
per-reference triggers went into existing table rows. **This is over the stated ceiling and
is flagged rather than hidden** — if the reviewer wants it back under 2100, the section can
lose its closing pointer (the reference table now carries both triggers) and each paragraph
can lose roughly a third, at the cost of the explicit "never inspect a licence or a
completion record" and "inferred matches are nobody's recommendation" clauses.

---

## 7. Design problems found — evidence attached

### 7.1 `covers <concept>` returns a course that does not cover the concept, and may assume it

**Reproduced on the committed fixture, not on a synthetic case.**

```
$ catalogs.py --config <fixture> covers go-programming
recommended by an author (1), in author order:
  durable-event-broker  [current]  from the rel catalogue
      why:  Recommended by streaming-query-engine as a previous bundle;
            streaming-query-engine assumes go-programming  [author recommendation]
EXIT=0
```

`durable-event-broker` does **not** list `go-programming` under `covers`. It lists it under
`assumes`, at level `working` (`tests/fixtures/catalog-relationships/catalog.yaml` line 54).
So a learner asking who teaches Go is answered with a course that itself requires working
Go — which is verbatim the first entry of `catalogue-format.md` section 12.8's own refusal
list: *"Answering 'who teaches X' from `assumes`. It sends the learner to the course that
begins where they are stuck."*

The same fact gets the opposite answer from the sibling command:

```
$ catalogs.py --config <fixture> prepare streaming-query-engine
note: no available bundle covers go-programming, which streaming-query-engine assumes at level working: ...
```

Spec section 4 defines rank 4 as "explicit recommended previous bundle **that covers the
concept**". The implementation's rank 4, and `catalogue-format.md` 12.2's restatement of it
("an author names this bundle as the way into a concept **they** assume"), drop that
qualifier. The result is also placed under the heading *recommended by an author*, so the
heading alone reads as an endorsement that the course teaches the concept.

**Not fixed here** — `catalogs.py` and `catalogue-format.md` are not this task's files.
Mitigated in `runner-protocol.md` 11.3, which now tells the runner to read the reason line
rather than the section heading, to pass it on as written, and to check with the learner
before offering such a course as the answer. The real repair is one of: filter rank 4 to
courses that also `cover` the concept; or keep the route and stop tagging it
`[author recommendation]` for this query.

### 7.2 Nothing enforces that `STATE.template.md` has no `assumes_reviewed`

Section 10.1 states the rule. Check 12 validates required keys only and does not whitelist,
so a bundle shipping a stamped template would pass and would silently suppress the review
for every learner of that course. That is a candidate **check 26** for the validator, which
is not this task's file. Filed here rather than fixed.

### 7.3 The format cannot say "start from where the previous course ended"

Spec section 7 asks for this to be reported separately rather than solved with recommendation
metadata. `workspace_kind: existing-or-new-repository` lets a learner point a follow-up at
any repository, including the one they just finished in, but no field lets an author say
*this course continues that course's code*. That is **correct** under sections 7 and 11 —
solving it through relationship metadata is explicitly out of scope. The consequence for the
runner is behavioural and is written into 12.5: **ask the learner which workspace, never
infer it**, and never copy a finished workspace because the metadata connects the two.

---

## 8. Honest incompleteness

- **Everything in this task is documentation. It is written, and it is not proven by a
  test.** No test exercises the runner's behaviour, because there is no runner test harness
  — the runner is prose executed by a model. The two suites pass unchanged (359 / 267)
  because no code was touched, which is evidence of *no regression* and is not evidence that
  the new sections are correct.
- **What was proven, and how:** the `assumes_reviewed` field does not change the validator's
  output (measured, before/after, identical); the host-neutrality greps return clean and can
  fire (controls watched); every fact in section 6 was measured against the committed
  fixture; the frontmatter is byte-identical to 79a2625 (compared programmatically).
- **What was not proven:** that a model following sections 11 and 12 produces the intended
  behaviour. Nothing here has been run against a real instance of a course declaring
  `assumes`, because no shipped bundle declares one — `catalog/builtin.yaml` and
  `examples/rust-cli-basics/` carry no relationship metadata. The fixtures under `tests/`
  are catalogue entries, not materialisable bundles, by design (spec section 10).
- **Nothing is half-written.** Both new sections are complete, all cross-references resolve,
  and no placeholder or TODO was left in any owned file.

---

## 9. If you are resuming this work

There is no next step inside this task; it is finished and awaiting review. The open items
it produced, all outside this task's file ownership:

1. **`catalogs.py` rank 4** — decide between filtering it to courses that also `cover` the
   concept, or keeping the route and dropping the `[author recommendation]` tag for a
   `covers` query. Section 7.1 has the reproduction.
2. **Validator check 26** — reject `assumes_reviewed` in `STATE.template.md`. Section 7.2.
3. **`SKILL.md` word budget** — over the brief's stated ceiling, and the ceiling did not
   match the file at baseline either. Section 6 says exactly what to cut if the reviewer
   wants it under 2100.
4. **No shipped bundle declares `assumes`**, so none of this behaviour is reachable by a
   learner yet. Adding relationship metadata to `catalog/builtin.yaml` or to
   `examples/rust-cli-basics/` would make it so; both are outside this task's ownership.
