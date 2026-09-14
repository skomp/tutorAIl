# tutorAIl

## Scope — one session per repository

Three sessions run in parallel, one per repository. **This repository is the runner.**

| Repository | Session owns | Holds |
|---|---|---|
| `skomp/tutorAIl` | **this one** | the runner plugin, the bundle format contract, the validator, the catalogue and discovery |
| `skomp/tutorail-authoring` | the authoring-tools session | the authoring skill, the toolkit, the course-quality checker, the dry-run harness |
| `skomp/tutorail-bundles` | the bundles session | the courses themselves, and the repository catalogue |

Work that belongs to another repository goes to that repository as an issue. Do not build
it here because it is adjacent.

Between sessions, a signal is fine — which files are held, a branch has landed, an issue
has moved. A **question about another session's work is not**: it belongs in that session's
own chat. A peer session is not a channel to Robert, and not a second opinion to consult
when you dislike an answer you were given. See `~/.claude/CLAUDE.md`.

## Tracking

This project tracks work as **GitHub issues**, not in `TODO.md`. Label every issue Claude
files with `created-by-claude`.

`TODO.md` holds only settled decisions and measured facts, and is usually empty. A design
decision belongs in `docs/superpowers/specs/2026-09-11-tutorial-runner-design.md` instead.

## Two rules this repository keeps learning the hard way

**A spent checkpoint or a superseded document does not get to stay.** This project has
three times found a document that was accurate when written and wrong afterwards: a resume
marker naming a task finished several lessons earlier, a material-naming rule that outlived
the `supplies` exemption, and a runner instruction telling the tutor to work around a defect
that had been fixed. Guidance describing a fixed bug teaches a reader to distrust correct
output. Delete it, or correct it in place, in the same change that makes it stale.

**A check that cannot report a positive is worse than no check.** Prove a probe can see the
thing it looks for before you trust its silence. This repository has caught it in a
validator that could not fail, a test harness that matched a message from the wrong file, a
grep whose zero came from an untested pattern, and a merge watch that errored on every
iteration while reporting itself healthy.

## Releasing

An installed copy receives a change only when the **version number** moves. Claude Code
compares manifest versions, not commit shas: refreshing the marketplace pulls the new
commits and then reports the plugin as already current. Thirty commits sat unreachable
behind 0.4.0 this way, and nothing reported a problem.

The version lives in three files and they move together:

| File | Read by |
|---|---|
| `.claude-plugin/marketplace.json` (`plugins[0].version`) | Claude Code, resolving the marketplace entry |
| `.claude-plugin/plugin.json` | Claude Code, after install |
| `.codex-plugin/plugin.json` | Codex |

`claude plugin validate .` checks the first two agree. **Nothing checks the third** — the
Codex manifest is the one to remember.

Releasing is: bump all three, run both suites (`python3 tests/test_validate_bundle.py` and
`python3 tests/test_catalogs.py` — there is no pytest here), commit, **push**, then
`claude plugin marketplace update tutorail && claude plugin update tutorail@tutorail`.
The push is not optional: the marketplace source is the GitHub repository, so an unpushed
bump is invisible to it.

Run the validator suite once more with `TUTORAIL_SWEEP_SIBLING_REPOS=1` before you push a
release. The plain run validates only this commit, by design (tutorAIl#37); that run also
validates the published bundles in `skomp/tutorail-bundles`, which is the only place a
format change is seen against real courses. It reports what it added on its own line and
never folds it into the total.

Minor for added format surface, patch for a fix. Verify by diffing the installed cache
under `~/.claude/plugins/cache/tutorail/tutorail/<version>/` against the working tree —
and probe for something the previous version lacks, so a silent no-op cannot pass as a
success.
