# Generic Tutorial Runner + Portable Tutorial Bundles — Design

**Date:** 2026-09-11
**Status:** Approved design, pending implementation plan
**Project:** `tutorAIl` (generic runner) — first consumer: AutomatonDB

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
| **Bundle** | distributable course package | no | **no** |
| **Instance** | `<workspace>/tutorial/` | yes | **yes, exactly one** |
| **Workspace** | the learner's own repository/directory | yes | learner-owned |

The runner contains no subject knowledge. The test applied to every proposed runner
feature: *would this still be needed if the tutorial taught Kubernetes, linear
programming, or compiler construction?* If no, it belongs in the bundle.

---

## 3. Bundle vs instance — the mechanical rule

Prose failed to convey this distinction to at least one bundle author. It is therefore
expressed as mutually exclusive **files**, which a script can check.

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
| `lessons/*.md` | required | read-only except progress notes | author |
| learner source | n/a | **learner-owned** | learner |

### The corollary authors get wrong

`COURSE.md` and `lessons/` describe the course for **every learner who will ever take
it**. They therefore contain no progress markers — no `Status: Complete`, no
`In progress`, no `Next`, no "current lesson".

All progress lives in `STATE.md`, in one place. The AutomatonDB source playbook
violates this in three places simultaneously (a "Current tutorial state" section,
per-lesson status markers inside the curriculum, and a "Current resume marker"
section), all of which must agree or the course misleads. Those three collapse into
`STATE.md`. This is check #5 of the validator (§9).

---

## 4. `tutorial.yaml`

Deliberately shallow — at most one level of nesting — because the author is more
likely to err than the parser is.

```yaml
bundle_format: 1
id: rust-automaton-db
title: Learn Rust by Building AutomatonDB
subjects: [rust, databases, distributed-systems]
level: intermediate-to-advanced
lessons:
  - lessons/00-foundations.md
  - lessons/01-rows-cells-temporal.md
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

**Stable vs mutable split.** `tutorial.yaml` declares validator *definitions*. Which
warnings are currently tolerated is progress, not configuration, and lives in
`STATE.md` with an expiry:

```yaml
accepted_warnings:
  - pattern: "never used"
    reason: "Table/Partition unreachable while main() is empty"
    until_lesson: lessons/02-first-refactor.md
```

The `until_lesson` expiry prevents "expected warnings" becoming permanent cover, which
would otherwise make the no-dead-code rule unenforceable.

---

## 5. `STATE.md`

Frontmatter is machine-checkable; the body is what the tutor reads.

```yaml
---
tutorial_id: rust-automaton-db
active_lesson: lessons/02-first-refactor.md
status: in-progress
updated: 2026-09-11
---
```

Body sections: last completed task; concepts demonstrated; decisions made in
discussion; known intentional/incomplete state; accepted warnings; next task;
explicitly deferred items.

**`active_lesson` is a path, not a description.** "Chapter 1, lesson 10" would require
reading `COURSE.md` to resolve, which defeats cold resume. This is the single field
that makes a fresh agent session work.

`STATE.md` never duplicates learner source code. Source is authoritative for
implementation state; `STATE.md` is authoritative for progress.

### The instance stamp

Materialization appends one block to the instance's copy of `tutorial.yaml`, recording
where the instance came from. It is absent from every bundle:

```yaml
instance:
  materialized_from: local:~/tutorials/rust-automaton-db
  materialized_at: 2026-09-11
  runner_version: 1
```

It is provenance only. Nothing in the teaching loop reads it; it exists so a learner
(or a future update mechanism) can tell which bundle and revision an instance came
from.

---

## 6. Lessons

```yaml
---
id: 02-first-refactor
title: The first deliberate refactor
design_refs: [key-ordering, temporal-semantics]
validators: [cargo-check, cargo-test]
---
```

A lesson is **either** `lessons/<slug>.md` or `lessons/<slug>/LESSON.md` — a folder when
it ships material (diagrams, data, worked examples). Entries in `lessons` always name the
Markdown file, so every entry is directly readable and `active_lesson` keeps meaning "the
file to read"; the runner never branches on file-vs-directory.

Material in a lesson folder loads **only when `LESSON.md` names it**, the same
progressive-disclosure rule skills use. Without that constraint a folder lesson would
quietly reload a whole course's worth of material and defeat the context budget in §8.
A folder directly under `lessons/` with no `LESSON.md` is an error rather than an
ignored directory, so misfiled material cannot go silently unreachable.

A lesson defines purpose, prerequisites, objectives, theory, concepts to teach,
constraints, suggested progression, completion conditions, and what to persist on
completion. It is **not** a script of conversational turns — the tutor generates each
task from objectives + state + workspace + the learner's last response.

**Lesson order is `tutorial.yaml`'s `lessons` list, not filename sort.** The list is the
single source of truth for both which lesson is first (`lessons[0]`, replacing a separate
`entry_lesson` field) and what "the next lesson" means on completion. It lives in the
manifest rather than in `COURSE.md` frontmatter because `COURSE.md` is deliberately not
loaded in the steady state, and the runner needs the sequence every time it advances.

An earlier draft cross-referenced `COURSE.md` against `lessons/` by scanning its prose
for lesson paths. That check was **inert** on a real bundle — the course map names
lessons as prose headings, so the scan matched nothing and reported clean without
examining anything. An explicit list removes the need to parse prose at all.

`design_refs` is the mechanism for partial `DESIGN.md` loading. `DESIGN.md` uses stable
section anchors; a lesson declares only the anchors it needs; the tutor reads only
those. A `lib.rs` refactor lesson structurally cannot pull in WAL recovery or quorum
design.

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
      Project-driven Rust taught by building a masterless, partitioned,
      automaton-indexed database from scratch.
    subjects: [rust, databases, distributed-systems]
    aliases: [cassandra-like, storage-engine, lsm]
    level: intermediate-to-advanced
    style: [project-driven, interactive, long-form]
    scope: "22 chapters; months of work"
    workspace_kind: existing-or-new-repository
    source:
      type: local            # | git | archive
      path: ~/tutorials/rust-automaton-db
```

**`source` is the entire provider boundary.** An online catalogue later returns the
same entry shape and differs only inside `source` (`type: git`, `url`, `revision`).
Matching, choice, materialization, state lifecycle and teaching are written against the
entry and never against its origin. Adding `OnlineCatalogProvider` means implementing
one new `source.type` in the resolve step and touching nothing else. `git` and
`archive` are declared but unimplemented in v1, and fail explicitly rather than
silently.

### Matching

Agent judgement against `subjects`/`aliases`/`title`/`description`/`level`/`style` —
not a scoring function. Rules:

- Never silently choose when more than one entry plausibly matches.
- A single match is offered, never auto-started.
- State **why** each candidate matched, so ranking is inspectable.
- Show title, description, level, scope, `workspace_kind` — not the lesson list.
- Do not discard weak-but-valid alternatives; rank them lower.

**Discovery loads metadata only.** The runner must not read anything under
`source.path` until the learner has chosen. This is what makes a remote catalogue
viable later.

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
| **one** lesson file | any completed lesson |
| learner files relevant to the task | course history |

### Teaching contract (bundle-overridable defaults)

- Exactly one actionable task per turn. A conceptual question is answered and does
  **not** advance the task.
- The learner writes the code. No solution code unless explicitly requested.
- Validate against declared completion conditions before advancing. "Looks plausible"
  is not evidence.
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
reading the bundle into context.** For a 22-chapter course, verifying every lesson's
`design_refs` by agent means loading 22 lesson files plus `DESIGN.md`. A script answers
it with zero context.

**Checks that need a script** (cross-file, all-lessons):

1. every `design_refs` entry resolves to a real `DESIGN.md` anchor
2. every lesson `validators` entry is declared in `tutorial.yaml`
3. every lesson has `id` + `title` frontmatter
4. every `lessons` entry resolves; every lesson in `lessons/` (top-level `.md` plus
   folders with `LESSON.md`) is listed exactly once; every lesson folder has a `LESSON.md`
5. no progress markers anywhere in `COURSE.md` or `lessons/`

**Cheap checks** (free once the script exists):

6. `STATE.template.md` present / `STATE.md` absent — reversed in instance mode
7. `tutorial.yaml` parses; `bundle_format` known; required fields present
8. `COURSE.md`, `DESIGN.md` exist; `lessons` is non-empty
9. `workspace_kind` is a known value; ownership globs non-empty

Mode is explicit, never inferred: `validate_bundle.py <path>` checks a bundle,
`validate_bundle.py --instance <path>` checks an instance. Inferring the mode from
which state file is present would make check #6 unable to fail, since a mis-shaped
bundle would simply be validated as the other kind.

Instance mode adds: `STATE.md` frontmatter well-formed, `active_lesson` resolves,
`tutorial_id` matches the manifest.

**Explicitly out of scope**, stated in the docs so a green run is not over-read:
pedagogical quality, lesson ordering, whether `DESIGN.md` is *accurate*, whether
completion conditions are checkable, anything about learner code. Green means
"structurally well-formed and executable by a runner", not "good course".

### Test strategy

Every check gets a deliberately broken fixture, and the suite asserts **that specific
error fires**. A validator that can only be shown passing is a false oracle. The suite
must demonstrate each check reporting a positive before any bundle is called clean.
The parser reports which checks ran; it never silently skips a check and prints green.

**Parsing.** YAML, chosen for its two real readers — the author and the agent. The only
mechanical consumer is this script. It uses PyYAML when present and a restricted reader
when not; the restricted reader **rejects** constructs outside its subset rather than
guessing. (Verified on this machine: Python 3.11.9, no PyYAML, no `yq`.)

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
- **The skill body names no host-specific tool.** Describe actions ("read the file",
  "run the configured command"), never `Read`, `Bash`, `Task`, `apply_patch`. This one
  rule makes the body portable, and it is the same rule that keeps bundles portable.
- **No `${CLAUDE_PLUGIN_ROOT}`** — Claude-only. Both hosts resolve skill-body paths
  relative to the skill directory, so everything needed at runtime lives under
  `skills/tutorail/` and is referenced relatively.
- **Trigger words go at the front of `description`** — Codex truncates descriptions
  under a 2%-of-context / 8,000-char budget, shortest-first, and a truncated
  description stops triggering.
- **No file-backed slash command on Codex.** Invocation there is `$tutorail` or
  implicit description match. The runner must be discoverable by description, not by
  command name.

---

## 11. AutomatonDB scope

AutomatonDB is **not shipped** with the plugin. Its bundle is authored separately from
the full course history; this project delivers the contract that bundle must satisfy.

**Delivered here:** `automaton-db/tutorial/STATE.md` only.

Written from the actual repository source, not from the playbook's resume marker, which
is stale. The marker claims the next task is "introduce a provisional scalar `Key`" and
describes `Database { entries: BTreeMap<String, Row> }`. The real `src/main.rs` (362
lines) has moved well past that:

```
KeyValue{Utf8,Int64}  KeyType  KeyColumn  PartitionKey  ClusteringKey
Cell{value,valid_from,expires_at}  Row{cells,expires_at}
Partition{rows}  Table{partition_key_columns,clustering_key_columns,partitions}
TableError{InvalidPartitionKey,InvalidClusteringKey}
Table::put -> Result<Option<String>, TableError>   (validates count then type)
5 tests inline in `mod tests`; main() empty; Table::get commented out
```

So the learner has completed the provisional-key step, composite keys, and typed-schema
validation. The pending task is the **Chapter 2 refactor: `main.rs` → `lib.rs`**, which
is now overdue — real structural pressure has emerged. `STATE.md` records this as the
next task, undone.

**The tutor must not perform that refactor.** It is the learner's exercise.

Until the bundle is materialized around it, the instance is incomplete and
`validate_bundle.py --instance` will correctly fail on the missing `tutorial.yaml`.
`STATE.md` says so in a note, so a fresh session does not try to "fix" it.

---

## 12. Scenarios

- **A — discovery with choice.** `"I want to learn Rust"` → catalogue metadata read →
  candidates presented with match reasons → learner chooses. Out of the box exactly one
  tutorial ships, so two matches require the user's catalogue to register a second;
  documentation states this rather than implying the shipped state demonstrates it.
- **B — start.** Resolve definition → resolve/create workspace → materialize instance →
  `STATE.template.md` becomes `STATE.md` → load entry lesson → exactly one task.
- **C — resume.** Active instance detected; no selection; `STATE.md` read;
  `active_lesson` loaded; pending task presented.
- **D — validation.** Tutor inspects diff/source, runs configured commands, classifies
  the outcome, does not rewrite source; success advances state, failure is explained.
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
| Local toolchain | Python 3.11.9 (no PyYAML), `jq` 1.8.2, no `yq`, cargo/rustc 1.98.0 |

---

## 14. Non-goals (v1)

Standalone UI; web/desktop app; hosted backend; any model API client; accounts; cloud
state; marketplace; recommendation ML; embedding search; ratings; payments; a full
remote catalogue service; autonomous coding mode; a workflow engine; a custom DSL.

Remote trust, signing, bundle updates after a learner has started, offline caching and
catalogue mirrors are documented as future concerns, not solved.

---

## 15. Open decisions

1. **`automaton-db` has zero commits.** Adding `tutorial/STATE.md` and committing would
   create the repo's first commit, necessarily including `main.rs`, `Cargo.toml` and
   both `TUTORIAL*.md` files. Left uncommitted; the owner decides.
2. **Fate of `TUTORIAL.md` / `TUTORIAL.updated.md`** once the bundle exists — keep as
   historical source, or remove. Not decided.
3. **Bundle update after a learner has started.** A bundle revision while an instance is
   live has no reconciliation story. Deferred, documented.
4. **Multiple concurrent tutorials in one workspace.** Not supported; `tutorial/` is
   singular. Deferred.
