# Catalogue Format — Finding a Tutorial to Offer

**Status:** normative for the runner. Load this when no active instance was found and you
must find a tutorial to offer, or when the learner asks what tutorials are available.

A catalogue is a list of tutorials the runner can offer. It holds **metadata only**. It
is not a course, and reading it must never require reading a course.

A learner configures **many** catalogues, and any of them may live in a Git repository.
The `scripts/catalogs.py` script fetches, caches and merges them, and you act on what it
prints. Fetching, precedence, staleness and failure classification are deterministic and
easy to get subtly wrong, so they are in code and not in your judgement.

---

## 1. The rule that makes catalogues cheap

> **Discovery loads metadata only. Do not open anything under a candidate's bundle path
> until the learner has chosen.**

Not the bundle's `tutorial.yaml`, not `COURSE.md`, not the lesson list, not a lesson
file. Everything needed to present a choice is already in the catalogue entry.

This is not merely a context saving. It is what makes a remote catalogue work: a
catalogue fetched from a repository returns the same entry shape, and its bundles may not
even be on the machine yet. A runner that peeks into the bundle to enrich a choice works
only for local sources and silently breaks the provider boundary.

`catalogs.py discover` keeps the rule mechanically: it never opens, lists or stats
anything under a bundle path. `catalogs.py resolve <id>`, which runs **after** the learner
has chosen, is the step that is allowed to look.

---

## 2. Where catalogues live

| File | Ships | Holds |
|---|---|---|
| `~/.config/tutorail/catalogs.yaml` | no | the list of catalogues, in priority order |
| `catalog/builtin.yaml`, relative to this skill | yes | only tutorials shipped with the plugin |
| `~/.config/tutorail/catalog.yaml` | no — created on first registration | the user's own registrations |
| `~/.cache/tutorail/catalogs/<id>/` | no | the last successful copy of each catalogue, and any clone |

**When `catalogs.yaml` is absent**, the runner behaves as though it listed
`~/.config/tutorail/catalog.yaml` first and the bundled catalogue second. That is exactly
the two-file model this replaced, so an existing user catalogue keeps working with no
migration and no action from you. A missing user catalogue is the normal state on a first
run: it is left out rather than reported as a failure.

`catalogs.py status` prints the configuration that the default implies. Use that text when
you write a real `catalogs.yaml`, so nothing already in use is dropped.

---

## 3. `catalogs.yaml` — the catalogue of catalogues

```yaml
catalogs_version: 1
catalogs:
  - id: mine
    source: { type: file, path: ~/tutorials/catalog.yaml }
  - id: skomp
    source:
      type: git
      url: git@github.com:skomp/tutorail-bundles.git
      ref: main
      path: catalog.yaml          # repository root, or any subfolder
  - id: builtin
    source: { type: bundled }
```

| Field | Required | Meaning |
|---|---|---|
| `catalogs_version` | SHOULD | `1` for this document. A version the runner does not know is an error, not a guess. |
| `id` | MUST | `[a-z0-9-]+`, unique. It names a cache directory and it is how failures are reported. |
| `source.type` | MUST | `bundled`, `file` or `git`. |

| `source.type` | Extra fields | Where the catalogue comes from |
|---|---|---|
| `bundled` | none | `catalog/builtin.yaml`, which ships with the plugin |
| `file` | `path` | a path on this machine; `~` is expanded |
| `git` | `url`, `ref` (optional), `path` (optional, default `catalog.yaml`) | a clone of that repository |

**The order is the priority order.** Put the user's own sources before `builtin`, so a
user can override a shipped tutorial. Section 6 covers what that obliges you to say.

**Authentication.** A `git` catalogue uses the Git credentials the user already has — an
SSH key, a credential helper, `gh`. The runner manages no tokens, stores no secrets and
never prompts for credentials; a request for one is turned into a reported failure rather
than a process that waits for a human who is not there. A private repository installs by
exactly the same mechanism as a public one. If a repository the user can clone by hand
fails here, the failure is real and worth reporting, not worth working around.

---

## 4. The script, and the three things it does

Run it at `scripts/catalogs.py`, relative to this skill's directory. It needs Python 3 and
the `git` command, and nothing else.

| Command | When | What it does |
|---|---|---|
| `catalogs.py discover` | a discovery request starts | refreshes every catalogue, then prints the merged catalogue and the status of each source |
| `catalogs.py status` | the learner asks what is configured, or a failure needs explaining | prints each catalogue's state from disk; fetches nothing |
| `catalogs.py resolve <id>` | the learner has chosen | prints that entry and the bundle directory it resolves to, and checks the bundle is really there |

Useful options: `--json` for an exact machine-readable form, `--offline` to serve what is
on disk without fetching, `--timeout SECONDS` for a slow host.

Exit codes: `0` every catalogue answered; `1` at least one was served from cache or could
not be served, and there is still something to offer; `2` the configuration is unusable and
nothing was fetched; `3` there is nothing to offer at all.

### When to refresh

**Refresh when a discovery request starts. Once.** Never once per turn, and never during
a resume — a resume reads no catalogue at all, so a learner continuing a course pays
nothing for any of this.

An exit code of `2` is the one case where you stop and ask: the catalogue of catalogues
decides every other step, so nothing was fetched. Say which line is wrong, and offer to
correct it or to remove the file and fall back to the implied default.

---

## 5. Entry schema

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
      path: rust-automaton-db
```

| Field | Required | Meaning |
|---|---|---|
| `catalog_version` | MUST | `1` for this document. A version you do not recognise is an error, not a guess. |
| `id` | MUST | Stable identity, `[a-z0-9-]+`. Matches the bundle's `id`. |
| `title` | MUST | Human-facing course name. |
| `description` | MUST | One or two sentences. This is what a learner reads when choosing. |
| `subjects` | MUST | Lowercase topic tags. The primary matching signal. |
| `aliases` | SHOULD | Terms a learner might say instead of a subject. |
| `level` | MUST | `beginner`, `intermediate`, `intermediate-to-advanced`, and so on. |
| `style` | SHOULD | `project-driven`, `exercise-based`, `interactive`, `long-form`. |
| `scope` | SHOULD | Honest size. "23 lessons; months of work" is a service to the learner. |
| `workspace_kind` | MUST | What the course needs of a workspace. Surfaced at choice time. |
| `source` | MUST | Where the bundle is. See section 5.1. |

The entry duplicates fields that also appear in the bundle's `tutorial.yaml`. That is
deliberate: the duplication is exactly what lets discovery run without opening the
bundle. When the two disagree, the bundle is authoritative — but you learn that only
after the learner has chosen, and a mismatch is worth mentioning then.

An entry missing a MUST field is malformed. The script skips it and names the entry and
the field. Pass that on rather than pretending the catalogue was complete.

### 5.1 `source`, and where a bundle path resolves from

`source` is the **entire** provider boundary for a bundle. Everything else in this
runner — matching, choice, materialization, state lifecycle, teaching — is written
against the entry and never against its origin.

| `type` | Extra fields | Status |
|---|---|---|
| `local` | `path` | implemented |
| `git` | `url`, `revision` | declared, **not implemented** |
| `archive` | `url` | declared, **not implemented** |

> **A bundle path resolves relative to its own catalogue's root: the directory that holds
> the catalogue file.**

That one rule is what lets a bundles repository ship a `catalog.yaml` at its root listing
its own bundles by relative path. A learner adds the repository with one entry in
`catalogs.yaml`, and the bundles arrive with it. For a `git` catalogue the root is inside
the local cache clone, so `catalogs.py resolve` prints an absolute path under
`~/.cache/tutorail/` — that is correct, and materialization copies from there.

An absolute path, or one starting with `~`, is used as written. A catalogue fetched from a
repository may **not** do that, and may not climb out of its own directory with `..`: such
an entry is skipped with a reason, because a remote catalogue that can name any directory
on the learner's machine is a different and much larger thing than a list of courses.

A `git` or `archive` **bundle** source is still unimplemented, and the script skips such an
entry with that reason. Say so; do not substitute a clone command and do not quietly drop
it. The repair is to add that repository as a **catalogue**, which is what the whole of
section 3 is for.

---

## 6. Precedence, and what you must say about it

> **First match wins, by tutorial `id`. The order in `catalogs.yaml` is the priority
> order.**

The generated default lists user sources before `builtin`, so a user can override a
shipped tutorial with their own.

**When an entry is overridden, say so.** Name the catalogue that supplied the tutorial you
are offering, and name the catalogues that were shadowed. `discover` prints an `OVERRIDES`
line for exactly this, and `resolve` repeats it. A silent substitution of a different
bundle is the same hidden choice the matching rules forbid everywhere else: the learner
believes they are getting the course they know by name, and the content is somebody
else's.

Two different `id`s that describe the same course are two entries, not an override.
Present both.

---

## 7. When a catalogue fails

**A failed refresh must not fail discovery.** Serve what answered. Name what did not.

The script does the mechanics; your job is to pass on three things without flattening
them: which catalogue failed, which of the failures it was, and whether what you are
showing is current.

| Kind | What it means | The repair |
|---|---|---|
| `unreachable` | the host could not be reached | the network, or a mis-spelt host name |
| `no-access` | no access to that repository, or it does not exist | credentials, or the repository name |
| `no-ref` | the repository has no such branch or tag | the `ref` field |
| `no-catalogue` | the repository was fetched and holds no catalogue file at that path | the `path` field |
| `missing-file` | a local catalogue file is not there | the `path` field, or create the file |
| `unreadable` | the file is not UTF-8 text | permissions, or the file itself |
| `malformed` | the file is not a usable catalogue | correct the file; check it with `validate_bundle.py --catalog <path>` |
| `no-git` | the `git` command is not installed | install git |
| `unclassified` | git failed in a way the script does not recognise | read git's own message, which is printed verbatim |

These are not one message. "Check your network" sent to someone whose SSH key is simply
not on that repository wastes their afternoon. Report the kind the script reported, and
the repair that goes with it.

**Never present stale results as current.** When a catalogue is served from cache, the
entries from it are marked `cached` and the report carries the timestamp of the last
successful refresh. Say both: that these results are cached, and how old they are. When a
catalogue could not be served at all, say that too — "nothing matched your subject" is a
false statement when a whole catalogue is missing from the list.

`unclassified` is a real answer and a useful one. It means the script declined to guess.
Show git's message as it stands rather than deciding for it.

---

## 8. Matching

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
  If any catalogue was cached or unavailable, say that before you say nothing matched.

---

## 9. Presenting the choice

For each candidate, show:

- `title`
- `description`
- `level`
- `scope`
- `workspace_kind` — in plain terms, because it is the field with a consequence: a course
  that needs a fresh repository is a different commitment from one that uses the current
  project
- the reason it matched
- **which catalogue it came from, when more than one is configured**, and whether that
  catalogue was current or cached
- **that it overrode a shipped or lower-priority entry**, when it did

Do **not** show:

- the lesson list — it is not in the entry, and fetching it means opening the bundle;
- the bundle path, unless the learner asks or two entries would otherwise be
  indistinguishable;
- a guess at content the entry does not state.

Then ask the learner to choose. Wait for an answer. When they have chosen, run
`catalogs.py resolve <id>` to get the bundle directory, then load `state-lifecycle.md` and
materialize; that is the first moment anything under a bundle path may be opened. When
`resolve` reports that the bundle is not there, report it and stop — a cached catalogue can
name a bundle the last successful fetch did not carry.

---

## 10. Adding a catalogue, and registering a tutorial

**To add a whole repository of courses** — the cheap case, and the one to prefer:

1. ask for the repository URL, the branch, and where the catalogue file sits inside it
   (`catalog.yaml` at the root is the convention);
2. if `~/.config/tutorail/catalogs.yaml` does not exist, run `catalogs.py status` first and
   write the configuration it prints, so the user's existing catalogue is not dropped;
3. add the entry **above** `builtin`, and below any catalogue the user said they prefer;
4. run `catalogs.py discover` and show what arrived, including any entry that was skipped.

**To register one local bundle:**

1. ask for the source — a directory path for `local`;
2. open the bundle's `tutorial.yaml` to fill in `id`, `title`, `description`, `subjects`,
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

A catalogue file can be checked before it is used: `validate_bundle.py --catalog <path>`,
and `--portable` as well for a `catalog.yaml` that ships inside a bundles repository,
where every bundle must travel with the catalogue.

---

## 11. Failure modes to refuse

- **Peeking into a bundle to improve a recommendation.** It breaks the provider boundary
  and is the change that makes a remote catalogue impossible.
- **Auto-starting a single match.** The learner chooses.
- **Refreshing per turn, or during a resume.** Once, when discovery starts.
- **Letting one failed catalogue fail the whole discovery.** Serve what answered.
- **Collapsing the failure kinds into one message.** Three problems, three repairs.
- **Presenting cached entries as current**, or saying "nothing matched" while a catalogue
  is missing from the list.
- **Substituting an overridden entry silently.** Say which catalogue supplied it.
- **Inventing a tutorial that is not in a catalogue.** If nothing matches, say nothing
  matches.
- **Editing `catalog/builtin.yaml` on a user's behalf.** User registrations go in the
  user catalogue.
- **Managing credentials.** No tokens, no secrets, no prompting. Git already has the
  user's access, or the user has a repair to make.
- **Materializing before the learner has chosen.** Presenting is free; copying is not.
