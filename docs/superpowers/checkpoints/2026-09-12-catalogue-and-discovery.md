# Checkpoint — concept discovery and the relationship index (catalogue side)

**Date:** 2026-09-12
**Branch:** `main`, branched from `origin/main` at `4b698e3`
**Spec:** `docs/superpowers/specs/2026-09-12-bundle-relationships-design.md`, sections 3, 4, 11, 13
**Author of this checkpoint:** the catalogue-side agent

> **Status: the assigned work is COMPLETE and green.** 267 assertions pass, up from the
> 158 at `4b698e3`. Nothing is half-written. Nothing is left non-importable. The sections
> below say what was built, what is proven, and by which test, so the next session can
> verify rather than trust.

---

## 1. State of every file this agent owns

| File | State |
|---|---|
| `skills/tutorail/scripts/catalogs.py` | **finished.** 1544 → ~2530 lines. Imports cleanly. |
| `tests/test_catalogs.py` | **finished.** 18 new test functions plus one meta-test. 267 assertions, all green. |
| `skills/tutorail/references/catalogue-format.md` | **finished.** New section 12 (12.1–12.8), plus edits to sections 4, 5 and 8. |
| `tests/fixtures/catalog-relationships/catalog.yaml` | **finished.** The spec's section 10 example, as a catalogue. |

Nothing else was created, edited, staged or committed. **Nothing is staged; nothing is
committed.** The human reviews and commits.

### `catalogs.py` — what changed

Additions only; no existing function's behaviour was changed except `render_entries`,
which gained one call.

1. **Module docstring** — three new usage lines, and a fourth bullet in the "rules this
   script exists to keep" list: *"Covering is not assuming."*
2. **New section `# Relationships: concepts, recommendations, and the reverse index`**,
   inserted between `merge()` and `# Rendering`. Everything new lives there:
   `SEMANTIC_MATCHING_AVAILABLE`, `CONCEPT_ID_RE`, `ASSUMES_LEVELS`, `PROVENANCE_KINDS`,
   `QUESTION_WORDS`, `normalise`, `tokenise`, `QueryError`, `Concept`, `Recommendation`,
   `IndexedBundle`, `read_concepts`, `read_recommendations`, `Provenance`, `Match`,
   `Collector`, `QueryResult`, `RelationshipIndex`.
3. **Rendering** — `render_entry_relationships`, `render_match`, `render_query`; and
   `render_entries` now calls `render_entry_relationships(entry, stream)` just before the
   `OVERRIDES` loop, so `discover` lists each entry's concepts.
4. **Commands** — `query_exit_code`, `run_query`, `command_covers`, `command_follow_ups`,
   `command_prepare`, and three subparsers (`covers`, `follow-ups`, `prepare`), each with
   `--refresh`.

### The fixture

`tests/fixtures/catalog-relationships/catalog.yaml` — the `catalog-` prefix is deliberate,
so it cannot collide with the fixtures the bundle-side agent is adding under
`tests/fixtures/durable-event-broker/`, `streaming-query-engine/` and
`event-stream-recipes/`. **Those three are NOT this agent's and were not touched.**

Three entries, from spec section 10:

- `durable-event-broker` — covers `retained-event-logs` (aliases `append-only-log`,
  `replayable-log`), `partition-offsets` (aliases `stream-offsets`, `consumer-position`),
  `topic-partitions`, `group-commit`. Assumes `go-programming` (working). Recommends
  `distributed-log-broker` (**deliberately absent from every catalogue**) then
  `streaming-query-engine`, in that order.
- `streaming-query-engine` — covers four query concepts. **Assumes** `retained-event-logs`,
  `partition-offsets`, `topic-partitions`, `consumer-offsets`, `go-programming`, and
  covers none of them. Names `durable-event-broker` as a previous bundle.
- `log-replay-forensics` — the fictional third party. Names `durable-event-broker` as a
  previous bundle; **the broker never names it**. Both covers *and* assumes
  `retained-event-logs`, which exercises the legal overlap from spec section 3.

**The three bundle directories are deliberately absent from disk.** That is what proves a
concept query never opens a bundle path, and the test asserts their absence first.

---

## 2. The index shape

Built per query from `run.entries` (the merged `MergedEntry` list) — cheap, and it inherits
merge precedence, shadowing and freshness for free. There is no persisted index and no
cache of one.

```
RelationshipIndex(entries: list[MergedEntry])
  .bundles: dict[bundle_id -> IndexedBundle]
  .order:   list[bundle_id]            # merged catalogue order; the stable tie-break
  .notes:   list[str]                  # malformed metadata, never silently dropped
  .declared_previous:  dict[target_id -> list[(declaring_id, Recommendation)]]   # REVERSE
  .declared_follow_up: dict[target_id -> list[(declaring_id, Recommendation)]]   # REVERSE

IndexedBundle
  .merged: MergedEntry     .position: int      # index in .order
  .covers:  dict[concept_id -> Concept]
  .assumes: dict[concept_id -> Concept]
  .follow_ups: list[Recommendation]   # AUTHOR ORDER, .order = position in the list
  .previous:   list[Recommendation]   # AUTHOR ORDER
  # title / subjects / aliases are properties reading merged.entry, not copies

Concept(id, summary, aliases: tuple, level: str|None)
  level is populated for `assumes` only.
  .alias_slugs / .id_tokens() / .alias_tokens() / .summary_tokens()  -- all derived, no store
```

`covers` and `assumes` are **two separate dicts on the same object**. They are never
unioned anywhere in the file. That is the structural reason behaviour (a) below cannot be
broken by accident: there is no combined "concepts" map to reach for.

The reverse index is the two `declared_*` dicts, keyed by the **target** bundle id — the
bundle that was named — with the naming bundle as the value. That inversion is the whole
mechanism of spec section 10's third case.

### Where provenance lives

```
Provenance(kind, detail, concept=None, bundle=None, because=None, order=0)
  .rank            -> PROVENANCE_KINDS[kind][0]
  .recommendation  -> PROVENANCE_KINDS[kind][1]   # True ONLY if a human author wrote it
  .key()           -> (kind, concept, bundle)      # the dedup key

Match(bundle: IndexedBundle, provenance: list[Provenance])
  .add(p)   appends unless an identical .key() is already present
  .rank     min rank across provenance
  .order    min .order among provenance at that best rank
  .author_recommended  any(p.recommendation)
  .sort_key()  (rank, order, bundle.position)

Collector  dict[bundle_id -> Match]; .add() merges into the existing Match.
QueryResult(kind, query, matches, notes, unresolved, subject_of)
  .recommended / .inferred split the list for rendering.
```

**Deduplication happens at the `Match` level and never at the provenance level.** A bundle
appears once; its list of reasons grows. This is the answer to "merged without losing
provenance".

`PROVENANCE_KINDS` is the single registry: `kind -> (rank, is_recommendation, description)`.
Eleven kinds, five for concept queries and three for each relationship direction.

---

## 3. The four easy-to-get-wrong behaviours

### (a) A `covers` query never returns a bundle that merely `assumes` the concept

**Implemented: yes. Proven: yes.**

`RelationshipIndex._covering_pass` tiers 1–3 iterate `bundle.covers.values()` and nothing
else. Tier 4 reads `assumes`, but the assuming bundle is **not** added — only the bundle
its author names in `recommended_previous_bundles`.

Test `test_a_bundle_that_only_assumes_a_concept_does_not_teach_it`:
- asserts `streaming-query-engine` is absent from `covers retained-event-logs`;
- **positive control in the same assertion block**: the same query does return
  `["durable-event-broker", "log-replay-forensics"]`, so the absence is not an empty result
  wearing a pass;
- asserts from `discover --json` that the fixture really does carry
  `retained-event-logs` in that bundle's `assumes` and really does not carry it in its
  `covers` — so the test cannot pass because the metadata is missing;
- asserts the overlap case: `log-replay-forensics` both assumes and covers it, and **is**
  returned, because `covers` is what decides.

Also proven by `test_a_recommended_previous_bundle_answers_a_concept_query`: in a
two-bundle catalogue where only `engine` assumes `group-commit`, the result is
`["thin-broker"]` and `engine` is absent.

### (b) Provenance preserved, never flattened; duplicates merged without loss

**Implemented: yes. Proven: yes.**

Test `test_provenance_is_kept_when_a_bundle_arrives_by_several_routes`: on
`covers retained-event-logs`, `durable-event-broker` appears **once** and carries both an
`exact-concept` route and **two separate** `recommended-previous` routes, one per declaring
author, each with that author's own `because`. The match is `author_recommended: true`
while its `exact-concept` route still reports `author_recommendation: false` — the two
claims never merge.

Test `test_follow_ups_put_the_authors_own_list_first`: `streaming-query-engine` arrives by
three routes at once (`author-follow-up`, `declared-previous`, `assumes-covered`) and keeps
all three, with the inferred one still flagged inferred on a bundle the author did
recommend.

Test `test_broad_subject_is_the_last_tier_and_never_a_recommendation`: a pure subject query
prints no author-recommendation section at all, and every line is tagged
`[not an author recommendation]`.

The rendering carries the separation twice over: two sections, **and** a tag on every
single line. The section heading alone was judged too easy to lose in a paraphrase.

### (c) The reverse index finds a third-party follow-up the original never names

**Implemented: yes. Proven: yes.**

Test `test_follow_ups_read_the_reverse_index`: first asserts from `discover --json` that
`durable-event-broker`'s `recommended_follow_ups` does **not** contain
`log-replay-forensics` — so the fixture really is the open-ended case — then asserts
`follow-ups durable-event-broker` returns it anyway, with kind `declared-previous`, a
detail naming both bundles in that direction, and the third party's own `because`.

### (d) A concept query returns every suitable bundle, never collapsing to one

**Implemented: yes. Proven: yes.**

Test `test_more_than_one_bundle_covers_a_concept`: `covers "retained event logs"` returns
both bundles that cover it, `match_count == 2`, with the author-recommended one first and
the other still present. The bundle named in `recommended_previous_bundles` is the one that
ranks first, which is exactly the collapse the spec warns about, and it does not happen.

---

## 4. Ranking — how far the six tiers got

| Tier | Kind | Implemented | Tested by |
|---|---|---|---|
| 1 exact `covers` id | `exact-concept` | yes | `test_concept_query_exact_and_alias` (incl. spoken "Partition Offsets") |
| 2 exact per-concept alias | `concept-alias` | yes | same test, asserts the printed line names alias and concept |
| 3 normalised text on id / alias / summary | `concept-text` | yes | same test ("logical offsets" → summary of `retained-event-logs`); `test_concept_discovery_needs_no_service_and_no_bundle` covers the id-token route |
| 4 recommended previous bundle covering the concept | `recommended-previous` | yes | `test_a_recommended_previous_bundle_answers_a_concept_query`, asserts `rank == 4` |
| 5 broad `subjects` / bundle alias | `broad-subject` | yes | `test_broad_subject_is_the_last_tier_and_never_a_recommendation`, asserts `rank == 5` |
| 6 semantic | **absent by design** | n/a | `test_provenance_kind_coverage` asserts `SEMANTIC_MATCHING_AVAILABLE is False` **and** that no `"semantic"` key exists in `PROVENANCE_KINDS` |

**No tier is untested.** The meta-test `test_provenance_kind_coverage` fails if any of the
eleven kinds in `PROVENANCE_KINDS` has no fixture behind it — the same false-oracle
discipline the existing `test_kind_coverage` applies to failure kinds. Tier 6 is deliberately
*not* a declared-and-never-fired kind, because that would be exactly the false oracle the
suite exists to prevent.

The alias tier matching `stream-offsets` was verified to be tier 2 and not tier 3, and the
text tier was verified to report **which field** it matched in (`id`, `aliases`, `summary`).

---

## 5. Decisions the spec did not settle

These are the expensive ones to lose.

1. **The four fields live on the CATALOGUE ENTRY, not only in `tutorial.yaml`.** Forced by
   catalogue-format section 1: discovery loads metadata only, and a git catalogue's bundles
   may not be on the machine. The entry already duplicates `subjects`/`aliases` for exactly
   this reason. Verified safe: `validate_bundle.validate_catalog` restricts unknown fields
   only at the **document** top level (`unknown_top`), never per entry, so the new fields
   pass today's validator untouched. The bundle-side agent owns manifest-level validation.

2. **Three commands, not one.** `covers <query>`, `follow-ups <id>`, `prepare <id>`. A
   concept query and a relationship query take different arguments and rank on different
   ladders; one overloaded command would have had to guess which.

3. **They fetch nothing by default; `--refresh` opts in.** A concept question is asked
   mid-conversation, repeatedly. Refreshing per question is the per-turn refresh the
   document forbids. Same posture as `resolve`. `discover` remains the one refreshing
   command.

4. **The runtime reader is TOLERANT; the validator is strict.** `read_concepts` and
   `read_recommendations` drop a malformed concept or recommendation, record a note, and
   keep the tutorial discoverable. Rationale: relationship metadata is optional, so a typo
   in it must never remove a working course from the catalogue. Spec section 8's rejections
   belong in `validate_bundle.py`, where an author is asking to be told. Proven by
   `test_relationship_metadata_never_removes_a_tutorial`, which checks all five note kinds
   fire and that the sound concept next to them still matches.

5. **Normalisation is `lowercase → [a-z0-9]+ runs → joined with '-'`.** "Partition Offsets"
   and `partition-offsets` are one query. This is what lets tiers 1 and 2 be exact string
   equality with no fuzzy matcher and no service.

6. **Question words are a SECOND PASS, announced.** A query is tried verbatim first; only
   if that finds nothing is it retried with `QUESTION_WORDS` removed, and the result carries
   a note saying so. This cannot damage an exact id or alias, because the first pass would
   already have matched one. `QUESTION_WORDS` deliberately excludes anything that could be a
   real subject — `go` is **not** in it. Proven by
   `test_question_words_are_a_second_pass_and_are_announced`, including that a query which
   works as written is never re-run.

7. **The empty needle is refused, exit 2.** An empty or punctuation-only query would match
   every bundle. `QueryError` is raised before any matching. The test runs a **positive
   control first** (the same probe finding a real concept) so the refusal is not a probe
   that can never fire.

8. **Tier 4's reading.** "Explicit recommended previous bundle that covers the concept" is
   implemented as: bundle X **assumes** the concept, X names B under
   `recommended_previous_bundles`, therefore **B** is returned (not X), with provenance
   naming X. The literal alternative reading — "B covers it and is also recommended" — adds
   no route, because B would already have matched at tier 1. This reading is the only one
   that earns tier 4 a place on the ladder.

9. **Tier 4 IS an author recommendation; tiers 1, 2, 3 and 5 are not.** A human wrote the
   `because` in tier 4. An author writing `covers:` is stating a fact about their course,
   not recommending it to anyone — so an exact concept match is tagged
   `[not an author recommendation]`. This is the distinction the spec draws, and getting it
   backwards would be the exact failure spec section 4 warns about.

10. **`prepare` also reads the reverse of `recommended_follow_ups`** (kind
    `declared-follow-up`). Spec section 6 only specifies the reverse for follow-ups; the
    mirror is the same mechanism and is equally an author's written recommendation.

11. **An assumed concept that nothing available covers is stated in the notes.** Otherwise
    `prepare` prints a list that looks complete. It is a fact, not a blocker.

12. **`catalogue-format.md` was NOT renumbered.** The new material is section 12, appended.
    `runner-protocol.md` (another agent's file) cites "catalogue-format.md section 9" twice,
    and renumbering would have broken a cross-file reference this agent may not fix.

---

## 6. Measured facts — do not re-derive

- **Baseline at `4b698e3`**: `tests/test_catalogs.py` → 158 assertions;
  `tests/test_validate_bundle.py` → 310. Both confirmed before any edit.
- **The restricted YAML reader** (`yamlite`, and PyYAML is **not** installed on this
  machine — `YAML_READER` reports `restricted`) parses all four field shapes, including
  nested map→map→list and folded `>` scalars. Verified directly.
- **`validate_bundle.validate_catalog` does not reject unknown ENTRY fields**, only unknown
  top-level document fields. `CATALOG_CHECKS` tops out at 7 for catalogue mode.
- **`parse_catalog` in `catalogs.py` copies the whole entry** (`entries.append(dict(raw))`),
  so new fields flow through to `MergedEntry.as_dict()` with no parser change.
- **The real `~/.config/tutorail/catalogs.yaml`** points at a private git catalogue
  (`skomp`) and the bundled one. `catalogs.py discover` against it **still exits 0** and
  lists 4 tutorials. It was not modified.
- **argparse quirk**: a query beginning with `-` is read as an option. `--` is needed before
  it. A test that used `"---"` as an empty-query fixture raised `SystemExit`, which the
  suite's `except Exception` does not catch, and killed the whole run silently. Documented
  in catalogue-format section 4; the fixture now uses `"!!"` and `"?? ..."`.
- **The existing suite's idiom** is that fixture bundle directories may be absent
  (`test_discovery_never_opens_a_bundle`), which is why the relationship fixture has none.

---

## 7. Current test results

```
$ python3 tests/test_catalogs.py
...
OK - 267 assertions passed.
                                        (exit 0)
```

158 at the baseline → 267 now; **+109 assertions**, none removed, none weakened.

```
$ python3 skills/tutorail/scripts/catalogs.py discover
                                        (exit 0, 4 tutorials, real config unmodified)
```

**`tests/test_validate_bundle.py` is currently RED — 3 of 318 failing — and that is not
this agent's work.** Another agent is live in the same checkout and has `validate_bundle.py`,
`tests/test_validate_bundle.py` and three `tests/fixtures/` directories modified in the
working tree. The failures name its in-progress check 25 (`every covers concept is
recognisable somewhere in COURSE.md`) as a kind with no fixture behind it. Nothing in this
agent's change can affect that suite: the two share only `yamlite.py`, which was not
touched. Do not "fix" it from this side.

---

## 8. The exact next step

**Nothing is outstanding on the catalogue side.** The assigned scope is finished and green.
The next step is not in these files — it is the bundle side, which another agent owns:
manifest parsing, spec section 8 validation (checks 23+), `bundle-format.md`,
`runner-protocol.md` and `state-lifecycle.md`.

If a session must pick something up here, in priority order:

1. **Review, then commit.** Four paths: `skills/tutorail/scripts/catalogs.py`,
   `tests/test_catalogs.py`, `skills/tutorail/references/catalogue-format.md`,
   `tests/fixtures/catalog-relationships/catalog.yaml`. Stage those **explicit paths only** —
   never `git add -A`, because another agent is live in this checkout.
2. **Optional, not required by the spec:** `RelationshipIndex` is rebuilt per invocation.
   If a runner ever calls `covers` in a loop over a large catalogue, memoise it in `gather`.
   Not a defect today; the merged catalogue is tens of entries.
3. **Optional:** `SKILL.md` does not yet mention the three new commands. That file is
   another agent's, so it was left alone — worth one line in its reference table once the
   branch settles.

---

## 9. Found wrong, not acted on

1. **Spec section 4's tier 4 is ambiguous.** "Explicit recommended previous bundle that
   covers the concept" reads two ways; the implemented reading is decision 9 in section 5
   above. Worth an editorial correction in the spec so the next reader does not have to
   re-derive it.
2. **Spec section 12's deliverable list says "examples"**, while section 10 says explicitly
   *not* to ship the three bundles under `examples/`. The two are in tension. This agent
   followed section 10 (fixtures under `tests/`, nothing in `examples/`), which is the more
   specific and better-argued instruction.
3. **Spec section 2 records that the runner spec's "deliberately shallow nesting" claim is
   outdated** and should be corrected. That correction belongs in
   `docs/superpowers/specs/2026-09-11-tutorial-runner-design.md`, which this agent does not
   own. **Not done. Still outstanding.**
4. **Nothing was found wrong in the existing `catalogs.py`.** Its merge, precedence,
   staleness and failure-classification code was read closely and is sound; the new section
   sits beside it without altering any of it.
