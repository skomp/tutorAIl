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
| `lessons/**` | required | read-only except progress notes | author |
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
tutor_owned:    [tutorial/STATE.md, tutorial/DESIGN.md, tutorial/lessons/**]
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
10. `workspace_kind` is a known value; ownership globs non-empty

Mode is explicit, never inferred: `validate_bundle.py <path>` checks a bundle,
`validate_bundle.py --instance <path>` checks an instance. Inferring the mode from which
state file is present would make check 7 unable to fail, since a mis-shaped bundle would
simply be validated as the other kind.

Instance mode adds: `STATE.md` frontmatter well-formed, `active_lesson` resolves and is
listed in `lessons`, `tutorial_id` matches the manifest.

**Explicitly out of scope**, stated in the docs so a green run is not over-read:
pedagogical quality, lesson ordering, whether `DESIGN.md` is *accurate*, whether
completion conditions are checkable, anything about learner code. Green means
"structurally well-formed and executable by a runner", not "good course".

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

## 16. Implementation status

| Deliverable | State |
|---|---|
| Bundle format contract (`references/bundle-format.md`) | **done** |
| Design spec (this document) | **done** |
| `tutorail-bundles` repository | **done** — holds `rust-automaton-db` |
| `rust-automaton-db` bundle | **done** — imported, corrected, verified |
| `automaton-db/tutorial/` instance + `STATE.md` | **done** — uncommitted |
| Validator, as a proven prototype | **done** — 17 failure modes verified firing |
| Validator, promoted into the repo with fixtures + suite | pending |
| `SKILL.md` (the runner control plane) | pending |
| `references/catalogue-format.md` | pending |
| `references/runner-protocol.md` | pending |
| `references/state-lifecycle.md` | pending |
| `catalog/builtin.yaml` | pending |
| `examples/rust-cli-basics/` example bundle | pending |
| `.claude-plugin/` + `.codex-plugin/` manifests | pending |
| `README.md` | pending |
