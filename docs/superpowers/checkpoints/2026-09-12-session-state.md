# Session checkpoint — 2026-09-12

Written because the token budget is nearly exhausted. This is the orchestration view.
Neither working agent has it.

---

## What is being built

**Bundle relationships and concept-based prerequisites.** Specification:
`docs/superpowers/specs/2026-09-12-bundle-relationships-design.md` — approved, complete,
and normative. Read it first; it is the contract.

The rule the whole feature exists to preserve:

> Named bundles are recommendations. Concepts are the educational contract. Neither one
> gates access to a tutorial or requires proof that another bundle was completed.

---

## Base

Branched from `origin/main` at **4b698e3**, where:

- `python3 tests/test_validate_bundle.py` → **310 assertions**
- `python3 tests/test_catalogs.py` → **158 assertions**
- all four real targets validate at exit 0:
  `skills/tutorail/examples/rust-cli-basics`,
  `tutorail-bundles/rust-automaton-db`, `tutorail-bundles/webgl-typescript-scene`,
  `--instance automaton-db/tutorial`

Quote both numbers together in any dispatch: a count without a sha cannot be verified, and
a sha without a count gives an agent no reason to question what it sees.

---

## Work in flight

Two agents, dispatched, **not committed and not staged**. Both were told to write their own
checkpoint:

| Agent | Owns | Checkpoint |
|---|---|---|
| format + validation | `bundle-format.md`, `validate_bundle.py`, `tests/test_validate_bundle.py`, fixtures | `checkpoints/2026-09-12-format-and-validation.md` |
| catalogue + discovery | `catalogue-format.md`, `catalogs.py`, `tests/test_catalogs.py`, `catalog-*` fixtures | `checkpoints/2026-09-12-catalogue-and-discovery.md` |

**Read their checkpoints before touching anything they own.**

## Never dispatched — the third piece

**Runner behaviour**, owning `SKILL.md`, `runner-protocol.md`, `state-lifecycle.md`.
Specification sections 5, 6 and 7. Nothing has been written for it. It covers:

- presenting `assumes` before the first implementation task, grouped by level, as assumed
  concepts and never as proof requirements;
- letting the learner continue immediately, ask about one concept, or ask for bundles
  covering an assumed concept, then returning to the pending course start;
- recording the acknowledgement in instance state with the smallest compatible extension,
  so the review is not shown again;
- offering follow-ups at completion — explicit ones first in manifest order, then
  reverse-declared third-party ones, deduplicated with provenance kept, nothing auto-started;
- course completion succeeding when recommended targets are unavailable.

---

## Known defects, both flagged by the supplies session, one still open

1. **FIXED at 4b698e3** — the design spec stated the material-naming rule with no exception
   and said the validator enforces it. Check 6 no longer does, since `supplies:` exempts
   supplied files.
2. **OPEN, assigned to the format agent as its Task 0** — `run_case` in
   `tests/test_validate_bundle.py` matches an expected message against **any** finding of a
   check number and never checks `where`. A case that mutates file A passes when the check
   fires on file B. **Everything built on that harness is untrustworthy until this is
   fixed.** Check its checkpoint for whether it landed.

---

## Measured — do not pay for these twice

- The restricted YAML reader already parses all four new field shapes. Verified by loading a
  document with `covers` (per-concept `summary` + `aliases`), `assumes` (`level` + folded
  `summary`) and a `recommended_follow_ups` list of mappings. **No parser work is needed.**
- `optional_lessons` already nests map → map → list, so `bundle-format.md` line 87 — "Keep it
  shallow. One level of nesting at most." — is already false. The format agent owns that
  correction.
- Validator checks 1–22 exist; 22 is `supplies`. **This feature starts at 23.**
- This filesystem is **case-insensitive**. A fixture that renames `LESSON.md` to `lesson.md`
  is a no-op and tests nothing. Verify fixtures by listing the directory, never `exists()`.

---

## Parallel sessions

Another session (`authoring tools`) works in this repository from its own worktree at
`../tutorAIl-supplies`. Its `supplies` feature merged as `125d672` (PR tutorAIl#1) and its
branch has moved on since, so it is still active.

Rules that hold: stage explicit paths only, never `git add -A`; check `git status --short`
between `add` and `commit`, because `git commit` commits the whole index and a live agent
can stage into it in the seconds between; never revert a file that changed under you; and
**never ask questions about another session's work in this chat, or this session's work in
theirs.**

---

## Immediate next steps, in order

1. Read both agent checkpoints.
2. Confirm the `run_case` fix landed. If not, do it before trusting any new test.
3. Review and commit the two agents' work — explicit paths, checking the index first.
4. Dispatch the runner-behaviour agent (spec sections 5–7).
5. Run the full verification: both suites, all four real targets, and the field sweep
   required by spec section 12 — grep `covers`, `assumes`, `recommended_follow_ups`,
   `recommended_previous_bundles` and confirm where each is parsed, validated, indexed,
   documented and exercised by tests.

## Still outstanding across the project, unrelated to this feature

The dry-run harness (`TODO.md`); the authoring toolkit's optional-lessons pass; the
materialization check, still never wired up; Codex consistency. And the thing that has never
happened: **no lesson has ever actually been taught.**
