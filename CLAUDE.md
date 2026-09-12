# tutorAIl

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
