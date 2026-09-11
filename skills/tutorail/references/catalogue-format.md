# Catalogue Format — Finding a Tutorial to Offer

**Status:** normative for the runner. Load this when no active instance was found and you
must find a tutorial to offer, or when the learner asks what tutorials are available.

A catalogue is a list of tutorials the runner can offer. It holds **metadata only**. It
is not a course, and reading it must never require reading a course.

---

## 1. The rule that makes catalogues cheap

> **Discovery loads metadata only. Do not open anything under a candidate's `source.path`
> until the learner has chosen.**

Not the bundle's `tutorial.yaml`, not `COURSE.md`, not the lesson list, not a lesson
file. Everything needed to present a choice is already in the catalogue entry.

This is not merely a context saving. It is what keeps a remote catalogue possible later:
an online provider returns the same entry shape and has nothing local to open. A runner
that peeks into the bundle to enrich a choice works only for local sources and silently
breaks the provider boundary.

---

## 2. Where catalogues live

| File | Ships | Holds |
|---|---|---|
| `catalog/builtin.yaml`, relative to this skill | yes | only tutorials shipped with the plugin |
| `~/.config/tutorail/catalog.yaml` | no — created on first registration | the user's own registrations |

Both are optional at runtime. A missing user catalogue is the normal state on a first
run: create it only when the user asks to register a tutorial, and say that you did.
A missing or empty builtin catalogue is a packaging problem worth reporting, not a
runtime error.

**Precedence.** Load both and merge the entries. When the same `id` appears in both, the
user catalogue's entry wins — it is the one the user controls — and say that the shipped
entry was overridden, so a surprising source is visible rather than silent. Two different
`id`s that describe the same course are two entries; present both.

Reference the builtin catalogue by a path relative to this skill's directory. Do not use
a host-specific plugin-root variable; the two supported hosts resolve relative paths from
the skill directory and a variable form works on only one of them.

---

## 3. Entry schema

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
      type: local
      path: ~/src/github.com/skomp/tutorail-bundles/rust-automaton-db
```

| Field | Required | Meaning |
|---|---|---|
| `catalog_version` | MUST | `1` for this document. A version you do not recognise is an error, not a guess. |
| `id` | MUST | Stable identity. Matches the bundle's `id`. |
| `title` | MUST | Human-facing course name. |
| `description` | MUST | One or two sentences. This is what a learner reads when choosing. |
| `subjects` | MUST | Lowercase topic tags. The primary matching signal. |
| `aliases` | SHOULD | Terms a learner might say instead of a subject. |
| `level` | MUST | `beginner`, `intermediate`, `intermediate-to-advanced`, and so on. |
| `style` | SHOULD | `project-driven`, `exercise-based`, `interactive`, `long-form`. |
| `scope` | SHOULD | Honest size. "23 lessons; months of work" is a service to the learner. |
| `workspace_kind` | MUST | What the course needs of a workspace. Surfaced at choice time. |
| `source` | MUST | Where the bundle is. See section 4. |

The entry duplicates fields that also appear in the bundle's `tutorial.yaml`. That is
deliberate: the duplication is exactly what lets discovery run without opening the
bundle. When the two disagree, the bundle is authoritative — but you learn that only
after the learner has chosen, and a mismatch is worth mentioning then.

An entry missing a MUST field is malformed. Skip it, and say which entry and which field,
rather than dropping it silently.

---

## 4. `source` — the provider boundary

`source` is the **entire** provider boundary. Everything else in this runner — matching,
choice, materialization, state lifecycle, teaching — is written against the entry and
never against its origin.

| `type` | Extra fields | Status in v1 |
|---|---|---|
| `local` | `path` | implemented |
| `git` | `url`, `revision` | declared, **not implemented** |
| `archive` | `url` | declared, **not implemented** |

Resolving a `local` source: expand `~`, resolve the path, confirm the directory exists
and contains `tutorial.yaml` and `STATE.template.md`. That confirmation happens **after**
the learner has chosen, as the first step of materialization — it is not part of
discovery, and it is the only reason to look inside a bundle before copying it.

A `git` or `archive` source must **fail explicitly**: name the entry, name the
unimplemented `type`, and stop. Do not substitute a clone command, do not fall back to a
local path, and do not quietly skip the entry as if it were not there. A silent skip is
indistinguishable from "no such tutorial" and hides a registration the user made
deliberately.

Adding an online provider later means implementing one new `source.type` in the resolve
step. If a change needed for a new provider touches matching, choice, or the teaching
loop, the boundary has been broken and the change is wrong.

---

## 5. Matching

Matching is agent judgement against `subjects`, `aliases`, `title`, `description`,
`level` and `style`. It is not a scoring function, and there is no threshold to tune.

Rules, all of which matter more than ranking quality:

- **Never silently choose when more than one entry plausibly matches.** Present them.
- **A single match is offered, never auto-started.** One candidate is still a choice.
- **State why each candidate matched**, so the ranking is inspectable and the learner can
  correct it. "Matched on `rust` and `databases`; you said storage engines, which is in
  its aliases" is a reason. "Best match" is not.
- **Do not discard weak-but-valid alternatives.** Rank them lower and say why they are
  lower. A learner who said "Rust" may want the beginner course even though their
  phrasing sounded advanced.
- **Level mismatch is a note, not a filter.** Say that a course is advanced; let the
  learner decide.
- **When nothing matches**, say so plainly, list what is available by title and subject,
  and offer to register a tutorial. Do not stretch a poor match into a recommendation.

---

## 6. Presenting the choice

For each candidate, show:

- `title`
- `description`
- `level`
- `scope`
- `workspace_kind` — in plain terms, because it is the field with a consequence: a course
  that needs a fresh repository is a different commitment from one that uses the current
  project
- the reason it matched

Do **not** show:

- the lesson list — it is not in the entry, and fetching it means opening the bundle;
- the bundle path, unless the learner asks or two entries would otherwise be
  indistinguishable;
- a guess at content the entry does not state.

Then ask the learner to choose. Wait for an answer. When they have chosen, load
`state-lifecycle.md` and materialize; that is the first moment anything under
`source.path` may be opened.

---

## 7. Registering a tutorial

When the learner wants to add a course:

1. ask for the source — a directory path for `local`;
2. read the bundle's `tutorial.yaml` to fill in `id`, `title`, `description`, `subjects`,
   `aliases`, `level`, `style` and `workspace_kind`. Registration is the one operation
   that legitimately opens a bundle without a learner having chosen it, because the
   learner is pointing at that specific bundle;
3. write the entry into `~/.config/tutorail/catalog.yaml`, creating the file with
   `catalog_version: 1` and a `tutorials:` list if it does not exist;
4. do not add the entry to `catalog/builtin.yaml`. That file ships with the plugin and
   holds only what the plugin ships;
5. show the entry you wrote.

`scope` is not in a bundle's `tutorial.yaml`. Derive it from the length of the manifest's
`lessons` list, and say that you did.

---

## 8. Failure modes to refuse

- **Peeking into a bundle to improve a recommendation.** It breaks the provider boundary
  and is the change that makes a remote catalogue impossible.
- **Auto-starting a single match.** The learner chooses.
- **Silently skipping a `git` or `archive` entry.** Fail with the reason.
- **Inventing a tutorial that is not in a catalogue.** If nothing matches, say nothing
  matches.
- **Editing `catalog/builtin.yaml` on a user's behalf.** User registrations go in the
  user catalogue.
- **Materializing before the learner has chosen.** Presenting is free; copying is not.
