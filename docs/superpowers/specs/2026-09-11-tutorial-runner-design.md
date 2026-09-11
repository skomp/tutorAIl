# Generic Tutorial Runner + Portable Tutorial Bundles — Design

**Date:** 2026-09-11
**Status:** Design approved. Formats and first bundle implemented; runner in progress.
**Repositories:** `tutorAIl` (runner), `tutorail-bundles` (courses), `automaton-db` (a learner)

---

## 1. Purpose

Build a tutorial system whose runtime is an existing coding agent (Claude Code, Codex).
The agent supplies the model and the conversational loop. This project supplies the
protocol, the portable course format, and the state lifecycle.

No standalone application. No model API integration. No hosted service.

The design goal that justifies the whole system: **a tutor should hold one lesson in
context, not a whole course.** Every structural decision below serves that.

---

## 2. Four concepts, deliberately separate

| Concept | Lives | Mutable | Contains a learner? |
|---|---|---|---|
| **Runner** | installed plugin, outside learner repos | no | no |
| **Bundle** | a subfolder of `tutorail-bundles` (or any source) | no | **no** |
| **Instance** | `<workspace>/tutorial/` | yes | **yes, exactly one** |
| **Workspace** | the learner's own repository/directory | yes | learner-owned |

The runner contains no subject knowledge. The test applied to every proposed runner
feature: *would this still be needed if the tutorial taught Kubernetes, linear
programming, or compiler construction?* If no, it belongs in the bundle.

---

## 3. Bundle vs instance — the mechanical rule

Prose failed to convey this distinction to a bundle author. It is therefore expressed as
mutually exclusive **files**, which a script can check.

```
BUNDLE (distributable)            INSTANCE (<workspace>/tutorial/)
├── tutorial.yaml                 ├── tutorial.yaml      + instance stamp
├── COURSE.md                     ├── COURSE.md
├── DESIGN.md                     ├── DESIGN.md          (tutor appends)
├── STATE.template.md  ◄── only   ├── STATE.md      ◄── only here
└── lessons/                      └── lessons/
```

> A bundle **must** contain `STATE.template.md` and **must not** contain `STATE.md`.
> An instance **must** contain `STATE.md` and **must not** contain `STATE.template.md`.

### Ownership

| File | In bundle | In instance | Written by |
|---|---|---|---|
| `tutorial.yaml` | required | copied + `instance:` stamp | author; runner stamps |
| `COURSE.md` | required | read-only | author |
| `DESIGN.md` | required (seed) | tutor appends durable decisions | author seeds, tutor grows |
| `STATE.template.md` | **required** | **must be absent** | author |
| `STATE.md` | **must be absent** | **required** | runner creates, tutor updates |
| `lessons/**` | required | **read-only** | author |
| learner source | n/a | **learner-owned** | learner |

### The corollary authors get wrong

`COURSE.md` and `lessons/` describe the course for **every learner who will ever take
it**. They therefore contain no progress markers — no `Status: Complete`, no
`In progress`, no `Next`, no "current lesson".

All progress lives in `STATE.md`, in one place. The AutomatonDB source playbook violated
this in three places at once (a "Current tutorial state" section, per-lesson status
markers inside the curriculum, and a "Current resume marker" section), all of which had
to agree or the course misled. Those three collapsed into `STATE.md`. The validator
enforces it (§9, check 5).

---

## 4. `tutorial.yaml`

Deliberately shallow — at most one level of nesting — because the author is more likely
to err than the parser is.

```yaml
bundle_format: 1
id: rust-automaton-db
title: Learn Rust by Building AutomatonDB
subjects: [rust, databases, distributed-systems]
level: intermediate-to-advanced

lessons:
  - lessons/00-foundations.md
  - lessons/01-rows-cells-temporal.md
  - lessons/08-automaton-machinery/LESSON.md   # foldered form
  # ... ordered; lessons[0] is the entry lesson

workspace_kind: existing-or-new-repository   # | new-repository | none
tutor_owned:    [tutorial/STATE.md, tutorial/DESIGN.md]
learner_owned:  [src/**, tests/**, Cargo.toml]
ownership_policy: tutor-must-not-edit-learner-owned   # | on-request | unrestricted

validators:
  cargo-check: { kind: command, command: [cargo, check] }
  cargo-test:  { kind: command, command: [cargo, test] }
  has-lib:     { kind: file-exists, path: src/lib.rs }

one_task_at_a_time: true
solution_code: on-request-only
advance_on: validated-evidence-only
```

Validator `kind`s, all subject-neutral: `command`, `file-exists`, `file-contains`,
`git-diff`, `manual`. `cargo check` is a value, never a runner concept.

**`lessons` is the authoritative sequence.** It defines which lesson is first
(`lessons[0]` — there is no separate `entry_lesson` field) and what "the next lesson"
means on completion. It lives in the manifest rather than in `COURSE.md` frontmatter
because `COURSE.md` is deliberately not loaded in the steady state, and the runner needs
the sequence every time it advances. Filename sort is not the order; the list is.

**Stable vs mutable split.** `tutorial.yaml` declares validator *definitions*. Which
warnings are currently tolerated is progress, not configuration, and lives in `STATE.md`
with an expiry:

```yaml
accepted_warnings:
  - pattern: "is never used"
    reason: "Engine unreachable from the binary while main() is empty"
    until_lesson: lessons/03-first-refactor.md
```

The `until_lesson` expiry prevents "expected warnings" becoming permanent cover, which
would otherwise make the no-dead-code rule unenforceable.

**The expiry is exclusive**: acceptance is void once `active_lesson` reaches
`until_lesson`, not after it completes. The AutomatonDB case shows why — its dead-code
warnings expire at `lessons/03-first-refactor.md`, the lesson whose entire purpose is to
remove their cause. Holding acceptance *through* that lesson would suppress the warnings
exactly when they are the lesson's subject.

---

## 5. `STATE.md`

Frontmatter is machine-checkable; the body is what the tutor reads.

```yaml
---
tutorial_id: rust-automaton-db
active_lesson: lessons/03-first-refactor.md
status: in-progress
updated: 2026-09-11
---
```

Body sections: last completed task; concepts demonstrated; decisions made in discussion;
known intentional/incomplete state; accepted warnings; next task; explicitly deferred
items.

**`active_lesson` is a path, not a description.** "Chapter 1, lesson 10" would require
reading `COURSE.md` to resolve, which defeats cold resume. This is the single field that
makes a fresh agent session work.

`STATE.md` never duplicates learner source code. Source is authoritative for
implementation state; `STATE.md` is authoritative for progress.

### The instance stamp

Materialization appends one block to the instance's copy of `tutorial.yaml`, recording
where the instance came from. It is absent from every bundle:

```yaml
instance:
  materialized_from: local:../tutorail-bundles/rust-automaton-db
  materialized_at: 2026-09-11
  runner_version: 1
```

Provenance only. Nothing in the teaching loop reads it; it exists so a learner, or a
future update mechanism, can tell which bundle an instance came from.

---

## 6. Lessons

```yaml
---
id: 03-first-refactor
title: The first deliberate refactor
design_refs: [table-model, row-cell-model]
validators: [cargo-check, cargo-test, has-lib]
---
```

A lesson is **either** `lessons/<slug>.md` **or** `lessons/<slug>/LESSON.md` — a folder
when it ships material (diagrams, data, worked examples). Entries in `lessons` always
name the Markdown file, so every entry is directly readable, `active_lesson` keeps
meaning "the file to read", and the runner never branches on file-vs-directory. The `id`
equals the slug: the file stem, or the folder name.

**Foldered lessons are budget-positive, not a new risk.** The alternative to a folder is
material inlined in the lesson body, and the body is always loaded — so a long worked
example would cost its full length every turn of that lesson. As a sibling file it costs
nothing until the lesson asks for it. What makes this hold is a hard rule: **material
loads only when `LESSON.md` names it**, the same progressive-disclosure discipline skills
use. Two consequences the validator enforces rather than leaves to judgement:

- material a `LESSON.md` never mentions is **unreachable** — the tutor cannot know it
  exists — so it is dead weight shipped to every learner;
- a folder directly under `lessons/` with no `LESSON.md` hides its whole contents.

`LESSON.md` must match that name in **exact case**. macOS and Windows resolve `lesson.md`
case-insensitively, so a mis-cased body passes locally and fails on Linux; the validator
therefore compares directory entries by exact name rather than testing existence.

A lesson defines purpose, prerequisites, objectives, theory, concepts to teach,
constraints, suggested progression, completion conditions, and what to persist on
completion. It is **not** a script of conversational turns — the tutor generates each
task from objectives + state + workspace + the learner's last response.

`design_refs` is the mechanism for partial `DESIGN.md` loading. `DESIGN.md` uses stable
section anchors; a lesson declares only the anchors it needs; the tutor reads only those.
A `lib.rs` refactor lesson structurally cannot pull in WAL recovery or quorum design.

### Generated lessons

A tutor may write a lesson **during** a course. Two situations call for it, and they
produce the same artifact:

- **A side lesson.** The learner hits a concept the main path does not reach — lifetimes,
  trait objects, interior mutability — and needs a compact detour before continuing. The
  AutomatonDB course rules explicitly ask for this.
- **A main-path draft.** `COURSE.md` maps a chapter that has no lesson file yet. Rather
  than stopping, the tutor drafts it on arrival, informed by what the learner actually
  built.

Generated lessons live in **`tutorial/lessons.generated/`**, which is tutor-owned and
**exists only in an instance — never in a bundle.** They follow the ordinary lesson format
and add required provenance frontmatter:

```yaml
---
id: lifetimes-and-borrows
title: Lifetimes, just enough to unblock the borrow
generated: true
generated_at: 2026-09-11
kind: side-lesson            # | main-path-draft
reason: "The borrow in Table::get_cell_at cannot be explained without lifetimes"
after: lessons/03-first-refactor.md
---
```

**The manifest's `lessons` list is never mutated.** It is the authored course, identical
for every learner; a generated lesson is a learner-specific overlay discovered by listing
`lessons.generated/` and reading `after:` to place it. This keeps a later bundle revision
reconcilable, and stops two learners' courses diverging structurally.

`STATE.md`'s `active_lesson` may point into `lessons.generated/`. When it does, a
`resume_after:` field records where to return, so completing a detour resumes the main
path rather than guessing.

**Ownership is a runner rule, not a manifest field.** `tutorial/lessons.generated/` is
tutor-owned in **every** instance, whatever the manifest says. It cannot be a `tutor_owned`
entry: every bundle authored before this feature existed omits it, and under
`tutor-must-not-edit-learner-owned` the default for an unlisted path is learner-owned — so
the tutor would be unable to write the directory the feature requires. `tutorial/lessons/`
is correspondingly read-only in every instance regardless of the manifest.

**Completion is tracked in `STATE.md`, not in the lesson file.** The provenance frontmatter
records where a generated lesson came from, never how far the learner got — progress never
lives in a lesson. An instance that has generated at least one lesson therefore gains an
eighth `STATE.md` body section:

```markdown
## Generated lessons

```yaml
- path: lessons.generated/lifetimes-and-borrows.md
  kind: side-lesson
  after: lessons/03-first-refactor.md
  status: pending        # | complete
```
```

The section is absent until an instance has one, which is why `STATE.template.md` does not
carry it.

**Advancement** on completing a lesson: if a generated lesson is `pending` and declares
`after:` equal to the lesson just finished, it becomes active next; otherwise the next entry
in `lessons`.

**`active_lesson` may name a generated lesson** — it resolves either to an entry in
`lessons` or to a file under `lessons.generated/`. It must resolve to one of the two; a path
resolving to neither is a finding.

**A detour off the final lesson** sets `resume_after` to that final entry. Completing the
detour returns there, finds it already complete, and completes the course. `resume_after` is
therefore always present and always names an authored lesson, which keeps the rule uniform
rather than adding an optional-field case.

**`after:` names an authored lesson, never another generated one.** Detours do not nest.

**Promotion is a deliberate authoring act, not automatic.** Nothing flows from an instance
back into a bundle on its own. Promoting one means:

1. copy the file into the bundle's `lessons/`, renaming it to the numbered slug convention
   of its neighbours;
2. **reset `id` to the new slug** — generated slugs carry no number prefix, and `id` must
   equal the slug, so promotion without a rename silently breaks that check;
3. strip **all five** provenance fields: `generated`, `generated_at`, `kind`, `reason`,
   `after`;
4. add it to `lessons` at the right position;
5. **re-check `design_refs`.** This is the step authoring alone never needs: an instance's
   `DESIGN.md` grows during a course, so a generated lesson may cite an anchor that exists
   in that learner's instance and has never existed in the bundle.

Promotion leaves the originating instance holding its draft, so the two share a slug. This
surfaces only when that learner takes a bundle revision: at re-materialization the draft is
a duplicate of an authored lesson and is reported, and the tutor deletes it then. Until
then the learner works from their copy and nothing breaks.

This is also the course's only quality signal from real use. Three learners all needing a
lifetimes detour after lesson 03 is not three side lessons; it is a missing lesson, and the
generated files are the evidence.

**Improvising around a broken bundle remains forbidden.** A missing lesson file that
`lessons` *does* list, an undeclared validator, a dangling `design_ref` — these are defects
to report, not to paper over. Generation is a recorded, provenanced act for a course that
is working as intended.

> **A rejected design, recorded so it is not retried.** An earlier draft made `COURSE.md`
> the lesson index and cross-referenced it against `lessons/` by scanning its prose for
> lesson paths. On a real bundle that check was **inert**: the course map names lessons as
> prose headings, so the scan matched nothing and reported clean without examining
> anything. An explicit list in the manifest removes the need to parse prose at all.

---

## 7. Catalogue and the provider boundary

| File | Ships | Contains |
|---|---|---|
| `skills/tutorail/catalog/builtin.yaml` | yes | only bundles shipped with the plugin |
| `~/.config/tutorail/catalog.yaml` | no — created on first run | the user's registrations |

```yaml
catalog_version: 1
tutorials:
  - id: rust-automaton-db
    title: Learn Rust by Building AutomatonDB
    description: >
      Project-driven Rust taught by building a serious automaton-native,
      partitioned database with storage-engine and distributed-systems depth.
    subjects: [rust, databases, distributed-systems, automata, storage-engines]
    aliases: [cassandra-like, key-value-store, database-internals]
    level: intermediate-to-advanced
    style: [project-driven, interactive, long-form]
    scope: "23 lessons; months of work"
    workspace_kind: existing-or-new-repository
    source:
      type: local            # | git | archive
      path: ~/src/github.com/skomp/tutorail-bundles/rust-automaton-db
```

**`source` is the entire provider boundary.** An online catalogue later returns the same
entry shape and differs only inside `source` (`type: git`, `url`, `revision`). Matching,
choice, materialization, state lifecycle and teaching are written against the entry and
never against its origin. Adding `OnlineCatalogProvider` means implementing one new
`source.type` in the resolve step and touching nothing else. `git` and `archive` are
declared but unimplemented in v1, and fail explicitly rather than silently.

### Matching

Agent judgement against `subjects`/`aliases`/`title`/`description`/`level`/`style` — not
a scoring function. Rules:

- Never silently choose when more than one entry plausibly matches.
- A single match is offered, never auto-started.
- State **why** each candidate matched, so ranking is inspectable.
- Show title, description, level, scope, `workspace_kind` — not the lesson list.
- Do not discard weak-but-valid alternatives; rank them lower.

**Discovery loads metadata only.** The runner must not read anything under `source.path`
until the learner has chosen. This is what makes a remote catalogue viable later.

Registration is the one deliberate exception: adding a course to a catalogue requires
reading its `tutorial.yaml` to build the entry. The learner is pointing at that specific
bundle, so no provider boundary is crossed.

### Precedence and authority

Both catalogue files are read and merged. **The user's file wins on an `id` collision**,
because the user controls their own file — but the runner must say that a shipped entry
was overridden, since silently substituting a different `source.path` is exactly the kind
of hidden choice the matching rules otherwise forbid.

Catalogue entries duplicate manifest metadata (`title`, `subjects`, `level`,
`workspace_kind`, …) by necessity, because discovery must not open the bundle. The copy
can therefore drift. **The bundle's `tutorial.yaml` is authoritative once resolved**; the
catalogue entry is a discovery-time hint. If they disagree after resolution, the runner
uses the manifest and should say so.

`scope` is the exception: it exists only in the catalogue, has no manifest field, and is
derived at registration time from the length of the `lessons` list.

---

## 8. Runner protocol

```
ORIENT
  ├─ <cwd>/tutorial/tutorial.yaml exists (walking up to repo root)?
  │    ├─ yes + "continue" / no subject named ──────────► RESUME
  │    └─ yes + different subject named ────────────────► ask
  └─ no ─────────────────────────────────────────────────► DISCOVER
                                          catalogue metadata → match → choice
                                                        ↓
                                                  MATERIALIZE
                                    resolve source → copy → STATE.template.md
                                    → STATE.md → stamp instance
                                                        ↓
                                  ┌───────────────► TEACH LOOP ◄──────┐
                                  │  read tutorial.yaml, STATE.md      │
                                  │  read ONE lesson file              │
                                  │  inspect learner workspace         │
                                  │  → exactly one task                │
                                  │  ← learner evidence                │
                                  │  validate                          │
                                  │  update STATE.md ──────────────────┘
```

### Context budget (the reason this project exists)

| Loaded every turn | Never loaded routinely |
|---|---|
| `SKILL.md` | `COURSE.md` |
| `tutorial.yaml` | `DESIGN.md` in full (only declared anchors) |
| `STATE.md` | any other lesson |
| **one** lesson body | any completed lesson |
| learner files relevant to the task | lesson-folder material not named by `LESSON.md` |

### Teaching contract (bundle-overridable defaults)

- Exactly one actionable task per turn. A conceptual question is answered and does
  **not** advance the task.
- The learner writes the code. No solution code unless explicitly requested.
- Validate against declared completion conditions before advancing. "Looks plausible" is
  not evidence.
- On failure: decide whether it is the intended lesson, explain the concept, hand back
  one correction. Do not repair the learner's work.
- **Update `STATE.md` only after demonstrated progress**, never to record intent.
- Do not edit learner-owned paths. Do not silently complete exercises.

Validation outcomes are distinguished: `failure` / `success` / `success with relevant
warning` / `known accepted warning` (matched against `STATE.md`'s `accepted_warnings`).

---

## 9. Validator script

`skills/tutorail/scripts/validate_bundle.py` — **authoring-time only.** Never in a
learner's path; running a tutorial does not invoke it.

Its justification is the same as the runner's: **checking a bundle must not require
reading the bundle into context.** For a 23-lesson course, verifying every lesson's
`design_refs` by agent means loading 23 lesson files plus `DESIGN.md`. A script answers
it with zero context.

**Checks that need a script** (cross-file, all-lessons):

1. every `design_refs` entry resolves to a real `DESIGN.md` anchor
2. every lesson `validators` entry is declared in `tutorial.yaml`
3. every lesson has `id` + `title` frontmatter, and `id` equals its slug
4. every `lessons` entry resolves; every lesson in `lessons/` (top-level `.md` plus
   folders with `LESSON.md`) is listed exactly once; every lesson folder has a
   `LESSON.md` named in exact case
5. no progress markers anywhere in `COURSE.md` or `lessons/`
6. every file in a lesson folder is mentioned by that folder's `LESSON.md`

**Cheap checks** (free once the script exists):

7. `STATE.template.md` present / `STATE.md` absent — reversed in instance mode
8. `tutorial.yaml` parses; `bundle_format` known; required fields present
9. `COURSE.md`, `DESIGN.md` exist; `lessons` is non-empty
10. `workspace_kind` and `ownership_policy` are known values; `tutor_owned` is non-empty;
    `learner_owned` is non-empty **unless** `workspace_kind: none`, since a course that
    builds no software owns none of the learner's files

Mode is explicit, never inferred: `validate_bundle.py <path>` checks a bundle,
`validate_bundle.py --instance <path>` checks an instance. Inferring the mode from which
state file is present would make check 7 unable to fail, since a mis-shaped bundle would
simply be validated as the other kind.

Two further checks follow from §3 and §5 rather than from the list above:

11. instance mode — `STATE.md` frontmatter well-formed, `tutorial_id` matches the
    manifest, and `active_lesson` resolves **either** to an entry in `lessons` **or** to a
    file under `lessons.generated/` (see "Generated lessons" in §6); a path resolving to
    neither is a finding
12. bundle mode — `STATE.template.md` agrees with the manifest (`tutorial_id` equals
    `id`, `active_lesson` equals `lessons[0]`, `status` is `not-started`)

The `instance:` stamp is asserted in both directions: absent from a bundle, present in an
instance.

Exit codes are `0` pass, `1` findings, `2` usage, and **`3` indeterminate** — no findings,
but some check could not run. A `DESIGN.md` that is not valid UTF-8 reaches this: check 1
cannot run while nothing else complains, and printing green there would be a false
oracle.

**Explicitly out of scope**, stated in the docs so a green run is not over-read:
pedagogical quality, lesson ordering, whether `DESIGN.md` is *accurate*, whether
completion conditions are checkable, anything about learner code. Green means
"structurally well-formed and executable by a runner", not "good course".

Two limits are narrower than the rules they serve, and the script says so on every run
rather than looking stronger than it is:

- **Check 6 verifies that a `LESSON.md` names its material, not that it says *when* to
  use it.** Intent cannot be distinguished from a filename inside a code fence without
  crying wolf.
- **"No learner source code in the bundle" is not checked at all.** It cannot be told
  apart from a legitimate code example. It stays an author-judgement item on the
  contract's self-check list.

Progress-marker detection (check 5) is anchored to **structural positions** — headings,
`Status:`-style labels, ticked checklist boxes, bold labels, table cells, lesson
frontmatter — and is case-sensitive where the word is a label. An earlier free-text,
case-insensitive match rejected valid bundles for ordinary prose such as "while the
refactor is in progress".

### A check that was removed, and why

A reverse material check — "`LESSON.md` references a file that does not exist" — was
implemented and then deleted. It cannot distinguish a material reference from an ordinary
prose mention: it immediately flagged `DESIGN.md` and `STATE.md` because a lesson says
"record those in `DESIGN.md`", and lesson 03 alone mentions `src/lib.rs`, `main.rs` and
`Cargo.toml`. The exclusion list is unbounded. **A validator that cries wolf gets
ignored, which is worse than not having the check.** The forward direction (check 6)
survives because it walks files that actually exist.

### Test strategy

Every check gets a deliberately broken fixture, and the suite asserts **that specific
error fires**. A validator that can only be shown passing is a false oracle. The suite
must demonstrate each check reporting a positive before any bundle is called clean. The
parser reports which checks ran; it never silently skips a check and prints green.

Fixtures must not rely on filesystem behaviour that differs by platform. A fixture that
renamed `LESSON.md` to `lesson.md` silently tested nothing on macOS, because the rename
was a no-op on a case-insensitive filesystem.

**Parsing.** YAML, chosen for its two real readers — the author and the agent. The only
mechanical consumer is this script. It uses PyYAML when present and a restricted reader
when not; the restricted reader **rejects** constructs outside its subset rather than
guessing. (Verified: Python 3.11.9, no PyYAML, no `yq`.)

---

## 10. Packaging

One shared `skills/` directory, sibling per-host manifests. Proven shape: superpowers
6.3.0 ships `.claude-plugin/`, `.codex-plugin/` and others over a single `skills/`.

```
tutorAIl/
├── .claude-plugin/{plugin.json,marketplace.json}
├── .codex-plugin/plugin.json          "skills": "./skills/", "hooks": {}
├── skills/tutorail/
│   ├── SKILL.md
│   ├── references/{bundle-format,catalogue-format,runner-protocol,state-lifecycle}.md
│   ├── scripts/validate_bundle.py
│   ├── catalog/builtin.yaml
│   └── examples/rust-cli-basics/
├── tests/{fixtures/,test_validate_bundle.py}
├── docs/superpowers/specs/
└── README.md
```

Install:

```
Claude Code:  /plugin marketplace add skomp/tutorAIl ; /plugin install tutorail@tutorail
Codex:        codex plugin marketplace add <repo> ; codex plugin add tutorail
```

### Host-neutrality rules (all verified, see §13)

- Frontmatter: `name` + `description` only. Both hosts accept this; anything more is
  host-specific enrichment.
- **The skill body names no host-specific tool.** Describe actions ("read the file", "run
  the configured command"), never `Read`, `Bash`, `Task`, `apply_patch`. This one rule
  makes the body portable, and it is the same rule that keeps bundles portable.
- **No `${CLAUDE_PLUGIN_ROOT}`** — Claude-only. Both hosts resolve skill-body paths
  relative to the skill directory, so everything needed at runtime lives under
  `skills/tutorail/` and is referenced relatively.
- **Trigger words go at the front of `description`** — Codex truncates descriptions under
  a 2%-of-context / 8,000-char budget, shortest-first, and a truncated description stops
  triggering.
- **No file-backed slash command on Codex.** Invocation there is `$tutorail` or implicit
  description match. The runner must be discoverable by description, not by command name.

---

## 11. Repositories and current state

Three repositories, deliberately separate.

### `tutorAIl` — the runner

The plugin. Contains no course content. Ships the skill, the reference documents, the
validator, and a small example bundle.

### `tutorail-bundles` — the courses

Each subfolder is one self-contained bundle. Not shipped with the plugin; registered in a
user's catalogue. Currently holds `rust-automaton-db/`.

That bundle was authored separately from the full course history and imported verbatim,
then corrected in three ways: an ordered `lessons` list replacing `entry_lesson`;
`workspace_kind` from `new-repository` to `existing-or-new-repository`, because the course
resumes in a repository that already exists; and `ownership_policy` from `on-request` to
`tutor-must-not-edit-learner-owned`, because the looser value would permit a tutor to
perform the pending refactor on the learner's behalf.

Its lesson numbering differs from the original playbook: what older notes call "Chapter 2,
the first refactor" is `lessons/03-first-refactor.md`, because the original Chapter 1 was
split into `01-rows-cells-temporal` and `02-typed-keys-table-hierarchy`.

### `automaton-db` — a learner workspace

Holds the Rust implementation and one instance at `tutorial/`, materialized from the
bundle. **Uncommitted** — the repository has no commits at all, and making its first one
would necessarily include `main.rs`, `Cargo.toml` and the two legacy `TUTORIAL*.md` files.
That is the owner's decision (§15).

Its `STATE.md` was written from `src/main.rs` and from measured build output, not from the
playbook's resume marker, which was stale: the marker named "introduce a provisional
scalar `Key`" as the next task and described `Database { entries: BTreeMap<String, Row> }`.
The actual source had moved well past that:

```
KeyValue{Utf8,Int64}  KeyType  KeyColumn  PartitionKey  ClusteringKey
Cell{value,valid_from,expires_at}  Row{cells,expires_at}
Partition{rows}  Table{partition_key_columns,clustering_key_columns,partitions}
TableError{InvalidPartitionKey,InvalidClusteringKey}
Table::put -> Result<Option<String>, TableError>   (validates count, then type)
5 tests inline in `mod tests`; main() empty; Table::get commented out
```

Measured 2026-09-11: `cargo test` passes 5/5; `cargo check` emits 17 warnings, of which
16 are dead-code consequences of `main()` being empty (accepted, expiring at
`lessons/03-first-refactor.md`) and one is a genuine unused-imports cleanup, explicitly
not accepted.

**The pending task is lesson `03-first-refactor`: `main.rs` → `lib.rs`. It has not been
started, and the tutor must not perform it.** `src/lib.rs` does not exist. This is the
single most important fact for any session picking the work up.

---

## 12. Scenarios

- **A — discovery with choice.** `"I want to learn Rust"` → catalogue metadata read →
  candidates presented with match reasons → learner chooses. Only one tutorial ships with
  the plugin, so two matches require the user's catalogue to register a second;
  documentation states this rather than implying the shipped state demonstrates it.
- **B — start.** Resolve definition → resolve/create workspace → materialize instance →
  `STATE.template.md` becomes `STATE.md` → load `lessons[0]` → exactly one task.
- **C — resume.** Active instance detected; no selection; `STATE.md` read; `active_lesson`
  loaded; pending task presented.
- **D — validation.** Tutor inspects diff/source, runs configured commands, classifies the
  outcome, does not rewrite source; success advances state, failure is explained.
- **E — cold thread.** New conversation, no chat history: `tutorial.yaml` + `STATE.md` +
  one lesson is sufficient. This is what `active_lesson`-as-path buys.

---

## 13. Verified host facts

Measured 2026-09-11 against installed versions and source, not recalled. Implementers
should not re-derive these.

| Fact | Value |
|---|---|
| Codex version probed | `codex-cli 0.136.0` |
| Codex canonical skills dir | `~/.agents/skills/` (user), `<repo>/.agents/skills/` |
| `~/.codex/skills` | works, non-canonical, characterised as deprecated |
| Codex skill frontmatter | requires `name` + `description`; runtime ignores unknown keys |
| Codex authoring linter | allows only `{name, description, license, allowed-tools, metadata}` |
| Claude Code frontmatter | **all** fields optional; `name` ≤64 `[a-z0-9-]`, `description` ≤1024 |
| Shared `SKILL.md` on both hosts | **verified working** — a Claude-flavoured skill loaded normally on Codex |
| Codex skills context budget | 2% of window, or 8,000 chars; descriptions truncated first |
| Codex file-backed slash commands | **do not exist**; `~/.codex/prompts/*.md` is inert |
| Codex skill invocation | `$name` popup, or implicit description match; `/skills` is management only |
| Codex implicit-invocation opt-out | `agents/openai.yaml` → `policy.allow_implicit_invocation: false` |
| Codex plugin manifest | `.codex-plugin/plugin.json`; needs `"hooks": {}` to suppress hook discovery |
| Claude Code plugin manifest | `.claude-plugin/plugin.json`; `skills/` auto-discovered |
| Path resolution in skill body | relative to skill directory, **both hosts** |
| `project_doc_fallback_filenames` | real, but ambient-instructions only — **not** a skills mechanism |
| Local filesystem | case-insensitive; `lesson.md` resolves as `LESSON.md` |
| Local toolchain | Python 3.11.9 (no PyYAML), `jq` 1.8.2, no `yq`, cargo/rustc 1.98.0 |

---

## 14. Non-goals (v1)

Standalone UI; web/desktop app; hosted backend; any model API client; accounts; cloud
state; marketplace; recommendation ML; embedding search; ratings; payments; a full remote
catalogue service; autonomous coding mode; a workflow engine; a custom DSL.

Remote trust, signing, bundle updates after a learner has started, offline caching and
catalogue mirrors are documented as future concerns, not solved.

---

## 15. Open decisions

1. **`automaton-db` has zero commits.** Adding `tutorial/` and committing would create the
   repository's first commit, necessarily including `main.rs`, `Cargo.toml` and both
   `TUTORIAL*.md` files. Left uncommitted; the owner decides.
2. **Fate of `TUTORIAL.md` / `TUTORIAL.updated.md`** now that the bundle exists — keep as
   historical source, or remove. Not decided.
3. **Bundle update after a learner has started.** A bundle revision while an instance is
   live has no reconciliation story. Deferred, documented.
4. **Multiple concurrent tutorials in one workspace.** Not supported; `tutorial/` is
   singular. Deferred.
5. **Remote repositories.** Both `tutorAIl` and `tutorail-bundles` are local-only. Nothing
   has been created on GitHub.

---

## 16. Deferred: telemetry feedback

Generated lessons are the course's only quality signal from real use. A later version
should be able to emit them, **optionally and opt-in**, to a webhook so a course author
sees where learners actually stall.

Not built, and no backend exists. Recorded because one decision has to be made now and is
expensive to retrofit.

**Nothing needs to be built to start collecting.** Generated lessons are already files on
disk in each learner's workspace, with structured provenance. The signal accrues whether
or not anything transmits it, so a webhook added later works against accumulated history
rather than starting from zero. Collect locally, transmit later.

**The decision to make now: separate the signal from the content.** A generated lesson's
`reason` field, and its body, can contain the learner's code, their misunderstanding, and
the shape of the system they are building. Transmitting that is a disclosure, and a course
author usually does not need it. The two layers:

| Layer | Example | Sensitivity |
|---|---|---|
| **Signal** | `after: lessons/03-first-refactor.md`, `kind: side-lesson`, `id`, `generated_at` | low — no learner content |
| **Content** | `reason` prose, the lesson body, any material | high — learner code and context |

The provenance frontmatter already isolates the signal layer, which is what makes an
"anonymous signal only" opt-in cheap later. Keep it that way: **do not move learner context
into a frontmatter field**, and do not add frontmatter that quotes learner code. If
`reason` needs to stay human-readable, that is fine — it simply belongs to the content
layer and is not transmitted by default.

Other signals worth emitting eventually, all already present or derivable in `STATE.md`:
which lesson a learner stalls on, repeated validation failures per lesson, elapsed time
per lesson, and the lesson at which a course is abandoned. Abandonment is probably the
single most valuable number and nothing currently records it.

Open questions, none urgent: consent and its revocation; whether an instance carries a
stable anonymous id or is unlinkable between reports; whether a self-hosted receiver is
supported; and what happens when transmission fails (it must never block a lesson).

---

## 17. Implementation status

| Deliverable | State |
|---|---|
| Bundle format contract (`references/bundle-format.md`) | **done** |
| Design spec (this document) | **done** |
| `tutorail-bundles` repository | **done** — holds `rust-automaton-db` |
| `rust-automaton-db` bundle | **done** — imported, corrected, verified |
| `automaton-db/tutorial/` instance + `STATE.md` | **done** — uncommitted |
| Validator (`scripts/validate_bundle.py`) | **done** — 12 checks, restricted YAML reader |
| Validator test suite | **done** — 138 assertions; every check proven firing |
| `SKILL.md` (the runner control plane) | **done** |
| `references/catalogue-format.md` | **done** |
| `references/runner-protocol.md` | **done** |
| `references/state-lifecycle.md` | **done** |
| `catalog/builtin.yaml` | **done** |
| `examples/rust-cli-basics/` example bundle | **done** |
| `.claude-plugin/` + `.codex-plugin/` manifests | **done** |
| `README.md` | **done** |
