# Checkpoint — bundle relationships, manifest format and validation half

**Date:** 2026-09-12
**Branch:** `main`. Work started from 4b698e3; `main` has since moved to a187a27 (the
catalogue half's commits), which touched **none** of my files — verified with
`git diff --name-only 4b698e3..HEAD`.
**Nothing is staged or committed.** Every change below is in the working tree only.

---

## 0. Status: COMPLETE and GREEN

`python3 tests/test_validate_bundle.py` → **OK — 359 assertions passed** (baseline was 310).
`python3 tests/test_catalogs.py` → **OK — 267 assertions passed** (the other agent's suite,
unaffected).
All four real targets exit 0. The live learner instance was read only and is untouched
(`git status --short tutorial` in that repo is empty).

Task 0 (the `run_case` false oracle) is **DONE and PROVED** — section 2.

Everything in the original task is done: the harness fix, checks 23–25 with a firing or
warning fixture each, the three normative fixtures, and the documentation.

---

---

## 1. State of every file I own

### `skills/tutorail/scripts/validate_bundle.py` — COMPLETE, compiles, all checks written

| Change | State |
|---|---|
| Module docstring: exit codes now explain that warnings never change the exit code | done |
| `Report.warnings: list[Finding]` + `Report.warn(check, where, message)` | done |
| `exit_code()` deliberately does NOT consult warnings | done |
| `CHECKS` entries 23, 24, 25 | done |
| `WARNING_ONLY = {25}` | done |
| Constants: `CONCEPT_KEYS`, `CONCEPT_REQUIRED`, `ASSUMES_LEVELS`, `RECOMMENDATION_KEYS`, `RECOMMENDATION_ENTRY_KEYS`, `_CONCEPT_ID_RE`, `_ALIAS_SEPARATOR_RE`, `_PROSE_SEPARATOR_RE` | done |
| `normalise_alias`, `concept_aliases`, `concept_declarations`, `concept_spellings` | done |
| `check_concepts` (23), `_check_alias_list`, `_warn_about_alias_collisions` | done |
| `check_recommendations` (24) | done |
| `check_course_coverage` (25) | done |
| Wired into `validate()` — all three run in BOTH modes | done |
| `render()` prints a separate warnings block; PASS line mentions warning count | done |
| `LIMITATIONS` gained a "Relationships" section | done |

Nothing in this file is half-written. It imports and runs.

### `tests/test_validate_bundle.py` — COMPLETE except the three failures in section 7

| Change | State |
|---|---|
| `Case.where` field + doc comment | done |
| `Case.kind` gained `"warns"` | done |
| `_message_matches`, `_one_matching`, `_mismatch_detail` helpers | done |
| `run_case`: `"warns"` branch; `"fires"` branch uses `_one_matching` | done |
| `_warned_checks` global | done |
| `m_bad_design_ref_in_05` probe mutator | done |
| `test_run_case_checks_where()` — the Task 0 proof, wired into `main()` | done, PASSING |
| Three new BASELINES: `broker`, `engine`, `recipes` | done |
| ~25 relationship mutators | done, 3 defective — section 7 |
| 30 new Cases for checks 23/24/25 | done, 3 failing — section 7 |
| `test_check_coverage()` meta-test, now `WARNING_ONLY`-aware | done |
| `test_alias_normalisation_matches_the_runtime()` | done — see section 8, finding 7 |

### `tests/fixtures/` — three NEW fixtures, all validate clean

- `tests/fixtures/durable-event-broker/` — 5 files. 4 `covers`, 2 `assumes`, 2 `recommended_follow_ups`.
- `tests/fixtures/streaming-query-engine/` — 5 files. 4 `covers`, 6 `assumes`, 1 `recommended_previous_bundles`. **Both assumes AND covers `windowed-aggregation`** — the legal overlap, shipped as a positive control.
- `tests/fixtures/event-stream-recipes/` — 5 files. The fictional third party: names `durable-event-broker` under `recommended_previous_bundles` while the broker says nothing about it.

All three: `PASS - every applicable check ran and found nothing`, zero warnings, all 25 checks reporting a status.

### `skills/tutorail/references/bundle-format.md` — COMPLETE

- **Line 87 corrected.** "Keep it shallow. One level of nesting at most." was already false
  (`optional_lessons` nests map→map→list today). It now describes which fields nest and why,
  and says that deeper than that means the field wants to be a list of mappings.
- Four new rows in the **field reference** table, all `MAY`.
- New section **"Concepts and relationships"**, placed after **Supplied files — `supplies`**
  and before `## 3. COURSE.md`. It carries the central rule verbatim, the concept-identifier
  rule, `covers`, `assumes` with the level table, aliases, the recommendation rules table,
  the normative three-bundle example as **manifest excerpts** pointing at the fixtures, the
  empty-vs-malformed rule, and what the validator will not do.
- **The coverage list** section now ties `covers` to it and explains check 25's warning.
- **Common mistakes** gained 6 entries (numbers 23–28); the old 23 is renumbered 29.
- **Self-check** gained 6 checklist items.
- **Section 13** now names all four new keys as additive, and states what an older runner
  does with them — nothing, and the learner is never blocked, which is the whole design.

---

## 2. Task 0 — the `run_case` false oracle. DONE.

**The defect.** `run_case` collected `hits = [f for f in report.findings if f.check == case.check]`
and then asserted only that *some* hit's message contained `case.expect`. `where` was never
checked, so a case that mutated file A passed when the check fired on file B with a similar
message.

**The fix.** `Case` gained an optional `where: str = ""`. When set, `_one_matching()` requires
**exactly one** reported finding to satisfy BOTH the message and `h.where == case.where`.
Exactly one, not at least one: two findings about one mutated file mean the case is no longer
pinning down which it asserts.

**The proof** is `test_run_case_checks_where()` near the bottom of the test file. It builds the
false pass deliberately, using `m_bad_design_ref_in_05` (typo'd `design_refs` anchor in
`lessons/05-canonical-ordered-keys.md`) with a Case claiming `where="lessons/03-first-refactor.md"`,
and asserts five things on that one broken tree:

1. the probe is a genuine false pass — check 1 fires, about a file the case never touched
2. **the OLD message-only rule ACCEPTED it** (the defect, demonstrated not asserted)
3. the NEW rule REJECTS it
4. the control — the NEW rule ACCEPTS the same case aimed at lesson 05 (so it discriminates rather than merely being strict)
5. the failure message names both the expected and the actual place

All five pass. Every new Case that targets one identifiable place sets `where`.

**Retrofitting existing cases: NOT DONE.** The ~100 pre-existing cases still have `where`
unset and still use the old weak rule. That is a remaining task, not a regression.

---

## 3. Checks added

| # | Rejects / reports | Firing fixture? |
|---|---|---|
| 23 | `covers`/`assumes` well-formedness: bad concept id; missing/blank summary; unknown `assumes.level`; missing `level`; non-list `aliases`; blank alias; duplicate aliases after normalisation; `covers`/`assumes` not a mapping; concept body not a mapping; unknown key in a concept body | **YES — 11 firing cases, all green** |
| 23 (warn) | an alias that is also another concept's id; two concepts sharing one alias | **YES — 2 warning cases, green** |
| 24 | recommendation list not a list; entry not a mapping; missing `bundle`; missing/blank `because`; bundle id not `[a-z0-9-]+`; self-recommendation; duplicate id within one list; unknown key | **YES — 9 firing cases, all green** |
| 24 (warn) | one bundle named in both lists | green |
| 25 | WARNINGS ONLY. A `covers` concept recognisable nowhere in `COURSE.md` | **YES — 1 warning case, green** |

**Allowances proved silent (all green):** a concept in both `covers` and `assumes`;
`covers: {}`; `aliases: []`; `recommended_follow_ups: []`; COURSE.md naming a concept only
by an alias; COURSE.md naming it in the singular.

**Unresolved bundle ids** are proved legal by the three shipped fixtures: every recommended
id in them (`distributed-log-broker`, `streaming-query-engine` from the broker,
`durable-event-broker` from the recipes) resolves to nothing, and all three still pass.

---

## 4. Decisions the spec did not settle

These are the expensive ones to lose. Each is a real choice, with the reasoning.

1. **A warning mechanism had to be invented.** The validator had none — `Report.notes`
   existed but was dead code, never written by any check. Spec §8 requires "warn, never
   reject", so `Report.warnings` + `Report.warn()` were added, deliberately in a separate
   list from `findings` so `exit_code()` cannot consult them by accident.

2. **"Empty aliases" in spec §8's reject list was read as an empty alias ENTRY, not an
   empty alias LIST.** `aliases: []` and `aliases:` (nothing under it) are silent, exactly
   as `supplies: []` and `optional_lessons:` already are in this codebase. An alias entry
   that is blank or has no alphanumeric content is a finding. Rationale: the "empty
   declaration is silent, malformed one is loud" pattern is already the format's precedent
   in two places, and rejecting `aliases: []` would fail bundles a scaffolding tool wrote.

3. **`aliases` is allowed under `assumes` as well as `covers`.** Spec §3 documents it only
   under `covers`, but §8's reject list speaks of aliases generically and §4 indexes
   "per-concept aliases" without restricting to `covers`. Resolved permissively — the spec's
   whole spirit is that nothing invalidates a bundle unnecessarily. `streaming-query-engine`
   uses it (`retained-event-logs` has `aliases: [append-only-log]`). **If the catalogue half
   only indexes `covers` aliases, this becomes a silent no-op field and should be revisited.**

4. **Alias normalisation is defined as: lowercase, then join every run of `[a-z0-9]+` with
   a hyphen.** So `append-only-log`, `append_only_log`, `Append Only Log` and `node.js` /
   `nodejs` each fold together. The spec says "after normalisation" without defining it.
   Exposed as `validate_bundle.normalise_alias()`.
   **CORRECTION:** this was first implemented collapsing only whitespace, underscores and
   hyphens, which DISAGREED with the committed `catalogs.normalise()` on punctuation. That
   was a real interop defect and is fixed — see section 8, finding 7. The two are now
   identical and a test pins them.

5. **Availability of a recommended bundle is NOT checked, and no check for it was added.**
   The validator sees one bundle and no catalogue, so every reference is unresolved and
   warning about all of them would put noise on every bundle that uses the feature. Spec §8's
   last paragraph assigns this to *cross-catalogue* validation. **A check that cannot fire is
   exactly the false oracle this repo exists to avoid, so none was written.** This is a real
   boundary finding for the coordinator: the "unavailable recommended target" warning needs
   catalogue context and belongs with the catalogue half of the feature.

6. **Two warnings were added that spec §8 does not list**, both harmless because a warning
   never rejects:
   - two concepts in one bundle sharing one alias (makes ranking rule 2, "exact per-concept
     alias match", unable to choose between them)
   - one bundle named in both recommendation lists (tells a learner to take one course both
     before and after this one)

7. **Check 25 searches the WHOLE of `COURSE.md`, not the coverage list.** The coverage list
   has no fixed heading — `bundle-format.md` asks only for "a heading that says what it is" —
   so locating it means guessing, and a guess that missed would warn about a concept that IS
   listed. Searching everything is strictly more conservative.

8. **Check 25 accepts the id, any alias, and a singular/plural variant of each**, compared
   with case and punctuation removed. Generous on purpose: a false warning about a good
   COURSE.md teaches the author to ignore warnings.

9. **Findings use a `where` of `tutorial.yaml (covers.<id>)` / `tutorial.yaml
   (recommended_follow_ups[<index>])`**, following the existing `tutorial.yaml
   (validators.<name>)` precedent. Without this every relationship finding would share one
   location and Task 0's location assertion would pin nothing.

10. **All three checks run in BOTH bundle and instance mode**, because the four keys are
    copied into the instance with the rest of `tutorial.yaml` and a runner reads them there.

11. **No unknown-key rejection exists at manifest top level**, so adding four keys needed no
    change to `check_manifest`.

---

## 5. Measured facts — do not pay for these twice

- **Baseline confirmed at 4b698e3:** `test_validate_bundle.py` = 310 assertions,
  `test_catalogs.py` = 158. Exactly as the dispatch said.
- **`yamlite` parses all four field shapes correctly.** Verified directly. Nested
  map→map→list, folded scalars, list-of-mappings all return the expected structures.
- **A folded scalar (`summary: >`) keeps ONE TRAILING NEWLINE** in its value. Any "must be
  one line" rule must test the *stripped* value. Check 23 imposes no one-line rule on
  summaries (unlike `supplies.describe`, which does).
- **The restricted YAML reader rejects `*.go` in a flow list** as a YAML alias
  (`aliases (*name) are not supported`). This bit the first fixture; `learner_owned` now
  uses `[cmd/**, internal/**, go.mod]`. Any future fixture must avoid a leading `*`.
- **The restricted reader rejects a plain scalar continuing onto the next line** with
  "unexpected indentation (expected 2 spaces, found 4)". This is what breaks the check-24
  mutator in section 7.
- **`Report.notes` was dead code** before this work — declared, never written.
- **Checks 1–22 existed; 23–25 are new**, exactly as the dispatch said.
- **The filesystem is case-insensitive** (the suite's own note confirms it every run).
- **There is no section 13 in the design spec.** The dispatch says "spec section 13's
  parsing and validation lists". `docs/superpowers/specs/2026-09-12-bundle-relationships-design.md`
  ends at **section 12 (Deliverables)**. The lists actually meant are in **section 8**
  (Reject / Allow / Warn), and that is what the tests were written against. See section 8.

---

## 6. What is left

Nothing required by the task. Two optional follow-ups:

1. **Retrofit `where` onto the ~100 pre-existing cases.** New cases all set it; older ones
   still use the weaker message-only rule. Mechanical, and each one should be eyeballed
   against its mutator rather than derived from a run, or a check that currently fires on
   the wrong file would be locked in.
2. **`Report.notes` is still dead code** — declared, never written by any check. Delete it
   or use it, in a separate change.

## 7. Current test results — verbatim

```
$ python3 tests/test_validate_bundle.py
OK - 359 assertions passed.

$ python3 tests/test_catalogs.py
OK - 267 assertions passed.
```

The four real targets, all exit 0, with checks 23, 24 and 25 all reporting `n/a`
("the bundle declares no covers or assumes concepts" / "recommends no other bundles"),
which is the backward-compatibility result the spec §9 asks for:

```
skills/tutorail/examples/rust-cli-basics                           exit=0  PASS
tutorail-bundles/rust-automaton-db                                 exit=0  PASS
tutorail-bundles/webgl-typescript-scene                            exit=0  PASS
automaton-db/tutorial  --instance                                  exit=0  PASS
```

The last is a real learner's live instance in a repo we do not own. It was **read only**;
`git status --short tutorial` in that repo is empty.

The three new fixtures also pass clean in both bundle and instance mode, with zero warnings.

## 8. Found wrong, not yet acted on

1. **The dispatch cites "spec section 13", which does not exist.** The spec ends at section
   12. The reject/allow/warn lists are in **section 8**. Tests were written against section 8.

2. **`bundle-format.md` line 87 is false today**, independently of this work:
   "Keep it shallow. One level of nesting at most." `optional_lessons` already nests
   map→map→list. Correcting it is part of this task and is **not yet done**.

3. **`Report.notes` was dead code.** Still is — the warning mechanism uses a new list rather
   than repurposing it. Worth deleting or using, in a separate change.

4. **Spec §8's "empty aliases" is ambiguous** — see decision 2 in section 4.

5. **Spec §3 documents `aliases` only under `covers`** while §8 and §4 speak of aliases
   generically — see decision 3 in section 4.

6. **The "unavailable recommended target" warning from spec §8 has no home in this half of
   the feature** — see decision 5 in section 4. It needs catalogue context. This is the one
   piece of spec §8 that is deliberately unimplemented here, and the coordinator should
   decide where it lands. **Still open.**

7. **FOUND AND FIXED: the validator and the catalogue disagreed on "the same alias".**
   `catalogs.normalise()` (committed in a187a27) folds every run of non-alphanumeric text to
   a separator; my `normalise_alias()` originally folded only whitespace, underscores and
   hyphens. So `node.js` and `nodejs` were **two** aliases to the validator and **one** to
   the runtime index: an author could declare both, be told the bundle was fine, and have
   the index silently merge them. Fixed by adopting the catalogue's rule, which is also the
   better one — a concept id is `[a-z0-9-]+`, so punctuation cannot survive into one anyway.
   `test_alias_normalisation_matches_the_runtime()` now fails if either side drifts, and it
   carries a control proving the function really folds, so agreement cannot pass trivially.
   The two halves had **independently** agreed on the other integration question (aliases are
   read under `assumes` as well as `covers`), so decision 3 in section 4 is confirmed by
   their implementation rather than merely compatible with it.

8. **The three new fixtures live under `tests/fixtures/`**, alongside the catalogue half's
   `tests/fixtures/catalog-relationships/`. No collision; different directories.
