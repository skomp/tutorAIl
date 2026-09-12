#!/usr/bin/env python3
"""Structural validator for tutorAIl bundles and instances.

Two callers, one script. An author runs it over a bundle or a catalogue
before shipping. A runner runs it over the instance it has just materialized,
before the first task, and at the four further moments
references/runner-protocol.md section 13.1 names. It is never run on a
teaching turn, and a learner never invokes it by hand.

It is safe on a learner's machine because it is stdlib-only (below) and reads
without writing: no file in the bundle, the instance or the workspace is
created, modified or removed by a run.

Usage:
    validate_bundle.py <path>              check a bundle
    validate_bundle.py --instance <path>   check an instance
    validate_bundle.py --catalog <path>    check a catalogue file
    validate_bundle.py --catalog <path> --portable
                                           also check that the catalogue can
                                           be served from a repository
    validate_bundle.py --help

The mode is always explicit. It is never inferred from which state file is
present: inferring it would make check 7 (STATE.template.md present /
STATE.md absent) unable to fail, because a mis-shaped bundle would simply be
validated as the other kind.

Exit codes:
    0  every applicable check ran and found nothing
    1  findings
    2  usage or I/O error
    3  indeterminate - a check could not run, so a clean result cannot be certified

A run may also print WARNINGS. A warning never changes the exit code and
never makes a bundle invalid: it is for a rule that is real but whose only
available evidence is circumstantial, where reporting a finding would fail
bundles that are correct. Checks 23 and 25 are where they come from in bundle
mode. Catalogue check 3 warns for a different and stronger reason: a
catalogue is data a newer runner may extend, so an unrecognised entry field
is named and the catalogue still passes.

Stdlib only. Python 3.11. PyYAML is used when importable; otherwise a
restricted reader parses the deliberately shallow subset the format uses and
*rejects* anything outside it rather than guessing.

Green means "structurally well-formed and executable by a runner". It says
nothing about pedagogical quality, lesson ordering, whether DESIGN.md is
accurate, or anything about learner code.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# --------------------------------------------------------------------------
# Restricted YAML reader
# --------------------------------------------------------------------------
#
# The reader lives in yamlite.py, because catalogs.py needs the same one and
# two hand-written YAML parsers would drift apart. The names are re-exported
# here so that validate_bundle.YamlError, .load_yaml, .YAML_READER and
# ._RestrictedYaml keep resolving for anything that imports this module.

try:
    from yamlite import (
        YAML_READER,
        YamlError,
        _RestrictedYaml,
        _pyyaml,
        load_yaml,
    )
except ImportError:  # pragma: no cover - only when sys.path lacks this dir
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from yamlite import (
        YAML_READER,
        YamlError,
        _RestrictedYaml,
        _pyyaml,
        load_yaml,
    )


# --------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------

CHECKS: dict[int, str] = {
    1: "every design_refs entry resolves to a DESIGN.md anchor",
    2: "every lesson validators entry is declared in tutorial.yaml",
    3: "every lesson has id + title frontmatter, and id equals its slug",
    4: "lessons entries resolve; every lesson is listed exactly once, in "
    "'lessons' or 'optional_lessons'; every lesson folder has an exact-case "
    "LESSON.md",
    5: "no progress markers in structural positions in COURSE.md, lessons/ or "
    "lessons.generated/",
    6: "every file in a lesson folder is named by that folder's LESSON.md",
    7: "state-file shape: STATE.template.md / STATE.md, and the instance stamp",
    8: "tutorial.yaml parses; bundle_format known; required fields present",
    9: "COURSE.md and DESIGN.md exist; lessons is non-empty",
    10: "workspace_kind and ownership_policy are known; ownership globs non-empty",
    11: "[instance] STATE.md frontmatter well-formed and consistent with the manifest",
    12: "[bundle] STATE.template.md is consistent with the manifest",
    13: "[bundle] lessons.generated/ is absent - it exists only in an instance",
    14: "[instance] every generated lesson declares its provenance, with a known kind",
    15: "[instance] every generated lesson's 'after' names a lesson in the manifest list",
    16: "the manifest's lessons list names no generated lesson",
    17: "[instance] resume_at is present exactly while active_lesson is "
    "generated or optional, and names a manifest lesson",
    18: "optional_lessons is well-formed: every key is a lesson, every offer "
    "resolves, every gate has something to gate on",
    19: "failure_modes is well-formed, and every declared mode is anticipated",
    20: "'optional: true' frontmatter agrees with the optional_lessons list",
    21: "[instance] STATE.md's '## Optional lessons' record is well-formed and "
    "agrees with active_lesson",
    22: "supplies entries are well-formed, and every 'from' resolves where "
        "the runner will look for it",
    23: "covers and assumes are well-formed: concept ids, summaries, levels "
        "and aliases",
    24: "the recommendation lists are well-formed, and no entry recommends "
        "this bundle",
    25: "every covers concept is recognisable somewhere in COURSE.md",
    26: "[bundle] STATE.template.md does not carry assumes_reviewed",
}

BUNDLE_ONLY = {12, 13, 26}
INSTANCE_ONLY = {11, 14, 15, 17, 21}

# Checks that can only ever WARN, never produce a finding.
#
# Check 25's rule - a `covers` concept should be recognisable in COURSE.md -
# is real, but the only evidence available for it is textual. A bundle whose
# COURSE.md names a concept in words the manifest does not use is correct,
# and failing it would be exactly the cry-wolf behaviour checks 5 and 6 are
# shaped to avoid. The suite's coverage meta-test reads this set, so a check
# named here must be demonstrated WARNING and one not named here must be
# demonstrated FINDING; neither stands in for the other.
WARNING_ONLY = {25}

RAN = "ran"
NOT_APPLICABLE = "n/a"
BLOCKED = "blocked"

WORKSPACE_KINDS = ("existing-or-new-repository", "new-repository", "none")
OWNERSHIP_POLICIES = (
    "tutor-must-not-edit-learner-owned",
    "on-request",
    "unrestricted",
)
VALIDATOR_KINDS = {
    "command": ("command",),
    "file-exists": ("path",),
    "file-contains": ("path", "pattern"),
    "git-diff": (),
    "manual": (),
}

REQUIRED_MANIFEST_FIELDS = (
    "bundle_format",
    "id",
    "title",
    "description",
    "subjects",
    "level",
    "lessons",
    "workspace_kind",
    "tutor_owned",
    "learner_owned",
    "ownership_policy",
    "validators",
)

KNOWN_BUNDLE_FORMATS = (1,)

# Generated lessons (checks 13-17).
#
# A tutor may write a lesson during a course. It lands in this directory, which
# is tutor-owned and exists ONLY in an instance. The manifest's `lessons` list
# is never mutated to mention it: a generated lesson is a learner-specific
# overlay, discovered by listing the directory and placed by reading `after:`.
GENERATED_DIR = "lessons.generated"
GENERATED_KINDS = ("side-lesson", "main-path-draft")
# `generated_at` is deliberately not format-checked: PyYAML parses an unquoted
# 2026-09-11 into a datetime.date while the restricted reader returns a string,
# so a type or pattern assertion here would depend on which reader is installed.
GENERATED_REQUIRED_FIELDS = ("generated", "generated_at", "kind", "reason", "after")

# Optional lessons (checks 18-21).
#
# An optional lesson is an ordinary authored lesson under lessons/ that the
# tutor OFFERS rather than sequences. It is listed in `optional_lessons`
# instead of `lessons`, and it may ANTICIPATE named failure modes, so that a
# lesson the learner deferred can be offered again when the failure it warned
# about actually arrives.
#
# `optional_lessons` and `failure_modes` are both optional keys. Their ABSENCE
# is the normal case and is never reported - see LIMITATIONS.
OPTIONAL_KEY = "optional_lessons"
FAILURE_MODES_KEY = "failure_modes"
OPTIONAL_REQUIRED_FIELDS = ("offer_at", "offer_because")
# The states one learner's decision about one optional lesson can be in. There
# is deliberately NO "not-offered": not yet offered is the ABSENCE of a record,
# so a record claiming it is a contradiction and is reported.
OPTIONAL_STATES = ("offered", "deferred", "in-progress", "complete")
OPTIONAL_SECTION = "Optional lessons"
_FAILURE_MODE_ID_RE = re.compile(r"[a-z0-9-]+")
# `- `path` — state — anything else`. Strict about the path and the state,
# tolerant about the trailing clause, which is free text an author may wrap.
_OPTIONAL_RECORD_RE = re.compile(
    r"^[-*+][ \t]+`(?P<path>[^`]+)`[ \t]*[—–-][ \t]*"
    r"(?P<state>[A-Za-z][A-Za-z-]*)"
)

# Progress markers (check 5).
#
# The contract's self-check list names five strings: "Status: Complete",
# "In progress", "Next:", "current lesson", "resume marker". Searching for
# those strings as free text produces FALSE POSITIVES that reject valid
# bundles: case-insensitively, "In progress" matches the ordinary teaching
# sentence "while the refactor is in progress, the engine is unreachable".
# A validator that fails valid bundles gets ignored, or makes authors contort
# good prose, which is as harmful as one that passes invalid bundles.
#
# So every marker below is anchored to a STRUCTURAL position - the places a
# status marker actually occupies: a `Status:`-style label at the start of a
# line, a heading annotated with a status, a ticked checklist box, a status
# word standing alone as a list item or a table cell, a `Current lesson:`
# label, or a heading naming a resume marker. Prose that merely uses the same
# words is not a progress marker and is not reported.
#
# Where a word is being used as a label rather than as English, the match is
# case-sensitive on purpose: "In progress" is a label, "in progress" mid
# sentence is not.

_STATUS_WORDS = (
    r"complete|completed|done|finished|in[ \t_-]?progress|"
    r"not[ \t_-]?started|current|pending|skipped|blocked"
)
# A line may open with any mix of blockquote, list, heading and table-cell
# punctuation before the marker itself.
_LEAD = r"[ \t]*(?:(?:[-*+]|\d+\.)[ \t]+|\#{1,6}[ \t]+|>[ \t]*|\|[ \t]*)*"
_EMPH = r"(?:\*\*|__|\*|_)?"

PROGRESS_MARKERS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "a Status: label",
        re.compile(
            rf"^{_LEAD}{_EMPH}status{_EMPH}[ \t]*:[ \t]*{_EMPH}(?:{_STATUS_WORDS})\b",
            re.IGNORECASE,
        ),
    ),
    (
        "a heading annotated with a status",
        re.compile(
            rf"^[ \t]*\#{{1,6}}[ \t].*?[(\[]{_EMPH}(?:{_STATUS_WORDS}){_EMPH}[)\]]"
            rf"[ \t]*$",
            re.IGNORECASE,
        ),
    ),
    (
        "a heading ending in a status word",
        re.compile(
            rf"^[ \t]*\#{{1,6}}[ \t].*[-–—][ \t]*{_EMPH}"
            rf"(?:{_STATUS_WORDS}){_EMPH}[ \t]*$",
            re.IGNORECASE,
        ),
    ),
    (
        "a ticked checklist box",
        re.compile(r"^[ \t]*(?:[-*+]|\d+\.)[ \t]+\[[xX✓✔]\][ \t]"),
    ),
    (
        "a status word standing alone as a list item",
        # Case-sensitive: a capitalised word alone on a bullet is a label.
        re.compile(
            r"^[ \t]*(?:[-*+]|\d+\.)[ \t]+(?:\*\*|__)?"
            r"(?:Complete|Completed|Done|Finished|In progress|In Progress|"
            r"Not started|Not Started)(?:\*\*|__)?[ \t]*\.?[ \t]*$"
        ),
    ),
    (
        "a status word standing alone in a table cell",
        re.compile(
            r"\|[ \t]*(?:\*\*|__)?"
            r"(?:Complete|Completed|Done|Finished|In progress|In Progress|"
            r"Not started|Not Started)(?:\*\*|__)?[ \t]*\|"
        ),
    ),
    (
        "a current-position label",
        re.compile(
            rf"^{_LEAD}{_EMPH}current[ \t]"
            rf"(?:lesson|task|position|progress|tutorial state|state){_EMPH}"
            rf"[ \t]*[:|]",
            re.IGNORECASE,
        ),
    ),
    (
        "a heading naming the current position",
        re.compile(
            r"^[ \t]*\#{1,6}[ \t]+(?:\*\*|__)?current[ \t]"
            r"(?:lesson|task|position|progress|tutorial state|state)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "a resume marker",
        re.compile(
            rf"^(?:[ \t]*\#{{1,6}}[ \t].*\bresume marker\b"
            rf"|{_LEAD}{_EMPH}(?:current[ \t]+)?resume marker{_EMPH}[ \t]*:)",
            re.IGNORECASE,
        ),
    ),
    (
        "a Next: pointer heading or label",
        # Only as a heading or an emphasised label. A plain sentence that
        # begins "Next: open the worked example." is teaching, not progress.
        re.compile(
            # a heading:            ## Next:  /  ### Next lesson:
            r"^(?:[ \t]*\#{1,6}[ \t]+(?:\*\*|__)?Next"
            r"(?:[ \t]+(?:lesson|task|step|up))?(?:\*\*|__)?[ \t]*:"
            # a bold label, with the colon inside or outside the emphasis:
            #   **Next:**  /  **Next**:  /  __Next task:__
            r"|[ \t]*(?:(?:[-*+]|\d+\.)[ \t]+)?(?:\*\*|__)Next"
            r"(?:[ \t]+(?:lesson|task|step|up))?"
            r"(?:[ \t]*:[ \t]*(?:\*\*|__)|[ \t]*(?:\*\*|__)[ \t]*:))"
        ),
    ),
)

# The one frontmatter field a TEMPLATE may never carry (check 26). The runner
# writes it into an INSTANCE's STATE.md, where it is normal and expected.
ASSUMES_REVIEWED = "assumes_reviewed"

STATE_SECTIONS = (
    "Last completed task",
    "Concepts demonstrated",
    "Decisions made in discussion",
    "Known intentional or incomplete state",
    "Accepted warnings",
    "Next task",
    "Deferred items",
)

_FRONTMATTER_RE = re.compile(
    r"\A---[ \t]*\n(?P<fm>.*?)\n---[ \t]*(?:\n|\Z)", re.DOTALL
)
_ANCHOR_RE = re.compile(r"\{#([A-Za-z0-9][A-Za-z0-9._-]*)\}")


LIMITATIONS = """What a pass does and does not mean
  Green means "structurally well-formed and executable by a runner". It says
  nothing about teaching quality, lesson ordering, whether DESIGN.md is
  accurate, whether completion conditions are really checkable, or anything
  about learner code.

  Two checks are deliberately weaker than the rule they serve, because a
  validator that cries wolf gets ignored:
    check 5 reports progress markers only in structural positions - a
      `Status:`-style label, an annotated heading, a ticked checklist box, a
      status word alone on a bullet or in a table cell, a current-position
      label, a resume-marker heading, or a `Next:` heading or bold label.
      Ordinary prose that uses the same words ("while the refactor is in
      progress") is not reported, so a bundle can still hide progress in
      free text.
    check 6 proves that a lesson folder's material is NAMED by its
      LESSON.md. It does not prove the lesson says WHEN to use it, which the
      contract also asks for. A name in a code fence or a quoted example
      counts as named. The naming rule is NOT absolute: a file covered by a
      `supplies:` entry - from the manifest or from any lesson, not only the
      one that owns the folder - is exempt and is never reported, because
      the declaration already says what it is and where it goes. A green
      check 6 therefore does not prove every material file is mentioned in
      prose; it proves each one is either named or declared.

  There is deliberately no reverse material check ("LESSON.md names a file
  that does not exist"). It cannot tell a material reference from an
  ordinary prose mention of DESIGN.md, src/lib.rs or Cargo.toml.

  Generated lessons (lessons.generated/, instance only):
    the ABSENCE of the directory is normal and is never reported. Checks 14,
      15 and 17 report "n/a" when there is nothing to check, which is not the
      same as passing.
    check 14 does not check the FORMAT of generated_at, because PyYAML reads
      an unquoted date as a datetime.date and the restricted reader reads it
      as a string, so any pattern assertion would depend on which reader is
      installed.
    nothing checks whether `reason` is a real reason, whether a side-lesson
      was warranted, or whether a main-path-draft matches the chapter
      COURSE.md maps. Those are judgement, and this validator makes none.
    check 15 resolves `after` against the manifest's lessons list, not
      against the disk. That is the stronger test - the list is what the
      runner walks - but it means a generated lesson placed after a file
      that exists and is simply unlisted reads as the same error as one
      placed after a path that is not there at all.
    nothing checks `resume_at` against the active detour's `after:`. The two
      are independent by design: `after:` is where the lesson belongs in the
      course, `resume_at` is the lesson to make active when the detour ends,
      and a detour taken part-way through a lesson returns INTO that lesson.
      Check 17 asserts only that `resume_at` is a path naming an entry in
      `lessons`, and that it is present exactly while a detour is active.

  Optional lessons (optional_lessons / failure_modes):
    the ABSENCE of both keys is normal and is never reported. A bundle that
      declares neither is valid exactly as it was before the keys existed.
      Checks 18, 19 and 21 report "n/a" when there is nothing to check, which
      is not the same as passing.
    nothing checks whether a failure mode is REAL, whether its `signals` are
      the right evidence for it, whether `offer_because` tells the learner
      anything useful, or whether an optional lesson is worth taking. Those
      are judgement, and this validator makes none.
    NOTHING CAN CHECK THE INVARIANT THAT MATTERS MOST: that the course can be
      finished by a learner who declines every offer. Section 13 of
      bundle-format.md makes that an authoring obligation, and it is not
      mechanically decidable - a green run does not certify it. A
      `required_for` gate is not an exception to it: the gate holds on the
      failure, not on the lesson, so a learner who declines is coached through
      the repair rather than blocked. The validator cannot tell a gate you
      meant from a prerequisite you hid.
      same reason nothing checks `after:` against it. `repair_in` is in the
      manifest and answers "whose work is now wrong"; `resume_at` is in the
      instance and answers "where does the learner stand". They differ
      whenever a failure surfaces later than the code that caused it, which
      is the ordinary case for an anticipated failure.
    check 21 validates the SHAPE of STATE.md's `## Optional lessons` record,
      not its truth. It cannot tell whether the learner was really offered
      anything, really deferred it, or really finished it.

  Supplies (`supplies:`):
    an ABSENT key and a PRESENT-but-empty one (`supplies:` with nothing
      under it, or `supplies: []`) are both silent and both report "n/a" -
      a freshly scaffolded bundle, or a bundle mid-edit by the authoring
      toolkit, may carry an empty declaration before its first real entry.
      Check 22 cannot tell an author who meant to declare nothing from one
      who wrote an empty key by accident, and it does not try: an empty key
      is silent, a malformed one (a bare scalar, or a mapping instead of a
      list) is loud and is always a finding.
    check 22 proves the entries are well-formed and every declared 'from'
      exists where the runner will look for it. It says nothing about
      whether the supplied files are the RIGHT files, and nothing about
      whether a lesson still tells the learner to copy them by hand - that
      judgement is the course-quality audit's, not this validator's.
    check 22 applies the 'from' rule BY SCOPE, because placement time
      differs. A LESSON-scope 'from' must resolve under lessons/ and is
      reported in BOTH modes when it does not: that lesson's files are
      placed when it opens, from the instance, and materialization copies
      only lessons/. A MANIFEST-scope 'from' is checked for existence in
      BUNDLE MODE ONLY - it is placed during materialization while the
      bundle source is still in reach, and nothing copies it into the
      instance, so an instance that no longer carries it is correct. In
      instance mode, therefore, a manifest-scope 'from' is not proved to
      exist anywhere and its trailing-slash form is not proved either.
      Validate the BUNDLE to prove those.

  Relationships (covers / assumes / the two recommendation lists):
    an ABSENT key, a key with nothing under it, and an explicitly empty one
      are all silent and all report "n/a". Checks 23, 24 and 25 report
      "n/a" when there is nothing to check, which is not the same as
      passing.
    AN UNRESOLVED BUNDLE ID IS CORRECT AND IS NEVER REPORTED. Check 24
      proves a referenced id is WELL FORMED and stops there. A bundle is
      distributed independently, so it must not be invalidated because
      another bundle is missing, unpublished or not installed here - that
      is the whole point of the design. Whether a recommended bundle is
      AVAILABLE is a question about a catalogue, and this mode has no
      catalogue: nothing here reports an unavailable target, in either
      direction. Reciprocity is not required and is not reported either.
    a concept in BOTH covers and assumes is legal and is never reported. A
      course may assume a baseline and then teach it deeper.
    nothing checks whether the course really teaches what `covers` claims,
      whether an `assumes` summary is specific enough for a learner to
      self-assess against, or whether a level is honestly chosen. Those are
      judgement, and this validator makes none.
    check 25 is WARNINGS ONLY and is textual. It asks whether a `covers`
      concept is recognisable ANYWHERE in COURSE.md - as its id, as a
      plain-words spelling, or as one of its aliases - and warns when no
      spelling of it appears at all. It searches the whole file rather than
      the coverage list, because the coverage list has no fixed heading and
      a guess that missed it would warn about a concept that is listed. A
      course can name a concept once and never teach it, and this check
      would be satisfied: it is evidence of shared vocabulary, never of
      coverage.
    check 23's alias collisions are WARNINGS for the same reason. An alias
      that is also a concept id, or that two concepts share, makes one
      search result ambiguous; it does not make the bundle wrong. Aliases
      overlapping ACROSS bundles by different authors are expressly allowed
      and are not reported at all.
    check 26 is BUNDLE MODE ONLY and is about STATE.template.md alone. In an
      INSTANCE, `assumes_reviewed` in STATE.md is normal and expected - it is
      what the runner writes once the learner has seen the review - and
      nothing here reports it. Nothing here checks its VALUE either, in
      either mode: whether the date is a date, and whether a stamp exists on
      a course that declares no `assumes`, are the runner's to report at
      materialization (state-lifecycle.md section 10.5). Check 26 asks one
      question - does the template carry the field - because that is the one
      failure no runner and no learner can see."""


@dataclass(frozen=True)
class Finding:
    check: int
    where: str
    message: str

    def __str__(self) -> str:
        return f"[check {self.check:>2}] {self.where}: {self.message}"


@dataclass
class Report:
    mode: str
    target: Path
    findings: list[Finding] = field(default_factory=list)
    # Warnings are NOT findings and never change the exit code.
    #
    # They exist for the checks whose rule is real but whose evidence is
    # circumstantial: an alias that collides with a concept id, a `covers`
    # concept that no phrase in COURSE.md resembles. Reporting those as
    # findings would fail bundles that are correct, and a validator that
    # fails correct bundles gets ignored - which is the reasoning that
    # already shapes checks 5 and 6. Reporting them as nothing would hide a
    # real authoring mistake. So they are reported, loudly, and the run
    # still passes.
    #
    # A warning is never the right home for a rule the format actually
    # requires. If a bundle is wrong, say so with a finding.
    warnings: list[Finding] = field(default_factory=list)
    status: dict[int, tuple[str, str]] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    # Which check table this report is against. A catalogue is a different
    # kind of document from a bundle, so it has its own numbering rather
    # than sharing one table in which most numbers never apply.
    checks: dict[int, str] = field(default_factory=lambda: CHECKS)
    limitations: str = ""

    def add(self, check: int, where: str, message: str) -> None:
        self.findings.append(Finding(check, where, message))

    def warn(self, check: int, where: str, message: str) -> None:
        """Report something worth an author's attention that is NOT an error.

        Deliberately a separate list from `findings`: exit_code() never
        consults it, so a warning cannot fail a bundle by accident, however
        many of them a run produces.
        """
        self.warnings.append(Finding(check, where, message))

    def ran(self, check: int, detail: str = "") -> None:
        self.status[check] = (RAN, detail)

    def na(self, check: int, reason: str) -> None:
        self.status[check] = (NOT_APPLICABLE, reason)

    def blocked(self, check: int, reason: str) -> None:
        self.status[check] = (BLOCKED, reason)

    @property
    def blocked_checks(self) -> list[int]:
        return [c for c, (s, _) in self.status.items() if s == BLOCKED]

    def exit_code(self) -> int:
        if self.findings:
            return 1
        if self.blocked_checks:
            return 3
        return 0


# -- filesystem helpers -----------------------------------------------------


def list_dir(path: Path) -> list[str]:
    try:
        return sorted(os.listdir(path))
    except (FileNotFoundError, NotADirectoryError, PermissionError):
        return []


def resolve_exact(base: Path, rel: str) -> tuple[Path | None, str]:
    """Resolve `rel` under `base`, matching every component's case exactly.

    The local filesystem is case-insensitive, so Path.exists() would happily
    resolve `lessons/03-First-Refactor.md`. That passes here and fails on
    Linux. Comparing against os.listdir() entries is the only way to see it.

    Returns (path, "") on success, or (None, reason).
    """
    if "\\" in rel:
        return None, "path uses a backslash; use '/' in bundle paths"
    parts = rel.split("/")
    current = base
    for part in parts:
        if part in ("", ".", ".."):
            return None, f"path component {part!r} is not allowed"
        entries = list_dir(current)
        if not entries and not current.is_dir():
            return None, f"{current.name or current} is not a directory"
        if part not in entries:
            near = [e for e in entries if e.lower() == part.lower()]
            if near:
                return None, (
                    f"the directory entry is named {near[0]!r}, not {part!r}; "
                    f"the case differs, which resolves on macOS or Windows and "
                    f"fails on Linux"
                )
            return None, "no such file"
        current = current / part
    return current, ""


def read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def split_frontmatter(text: str) -> tuple[str | None, str]:
    """Return (frontmatter text or None, body)."""
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return None, text
    return match.group("fm"), text[match.end() :]


def as_list(value: Any) -> list | None:
    return value if isinstance(value, list) else None


def _is_text(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _is_text_list(value: Any) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(_is_text(item) for item in value)
    )


def _is_count(value: Any) -> bool:
    """A non-negative whole number, and not a bool.

    `isinstance(True, int)` is True in Python, so a bare `isinstance` check
    would accept `optional_lesson_count: true` and hand the runner a count of
    1. YAML also reads `true`, `yes` and `on` as booleans, which makes this
    an easy value to write by accident rather than a contrived one.
    """
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


# -- lesson discovery -------------------------------------------------------


@dataclass
class Lesson:
    rel: str  # path relative to the bundle root, e.g. lessons/00-x.md
    slug: str
    path: Path
    folder: Path | None  # the lesson folder, for foldered lessons
    generated: bool = False  # discovered under lessons.generated/


def discover_lessons(
    root: Path, report: Report, subdir: str = "lessons"
) -> tuple[list[Lesson], bool]:
    """Walk `subdir` and return the lessons it actually contains.

    `subdir` is "lessons" for the authored course and GENERATED_DIR for the
    tutor-written overlay. The two directories hold the same kind of file and
    obey the same shape rules, so one walk serves both.

    Also reports check-4 findings for folders without an exact-case LESSON.md.
    The second return value says whether `subdir` is a directory at all.
    """
    generated = subdir == GENERATED_DIR
    lessons_dir = root / subdir
    if not lessons_dir.is_dir():
        return [], False
    found: list[Lesson] = []
    for name in list_dir(lessons_dir):
        if name.startswith("."):
            continue
        child = lessons_dir / name
        if child.is_file():
            if name.endswith(".md"):
                found.append(
                    Lesson(f"{subdir}/{name}", name[:-3], child, None, generated)
                )
            continue
        if child.is_dir():
            entries = list_dir(child)
            if "LESSON.md" in entries:
                found.append(
                    Lesson(
                        f"{subdir}/{name}/LESSON.md",
                        name,
                        child / "LESSON.md",
                        child,
                        generated,
                    )
                )
                continue
            miscased = [e for e in entries if e.lower() == "lesson.md"]
            if miscased:
                report.add(
                    4,
                    f"{subdir}/{name}/{miscased[0]}",
                    f"a lesson folder's body must be named exactly 'LESSON.md'; "
                    f"this one is {miscased[0]!r}. The local filesystem is "
                    f"case-insensitive so it resolves here and fails on Linux. "
                    f"Rename it (via a temporary name, because a plain rename "
                    f"is a no-op on this filesystem).",
                )
            else:
                report.add(
                    4,
                    f"{subdir}/{name}/",
                    f"a folder directly under {subdir}/ has no LESSON.md, so it "
                    f"is not a lesson and everything in it is unreachable. Add a "
                    f"LESSON.md, or move the files into the lesson folder they "
                    f"belong to.",
                )
    return found, True


# -- the checks -------------------------------------------------------------


def check_state_files(root: Path, mode: str, manifest: Any, report: Report) -> None:
    """Check 7 - the mechanical bundle/instance distinction."""
    entries = list_dir(root)
    has_state = "STATE.md" in entries
    has_template = "STATE.template.md" in entries
    if mode == "bundle":
        if has_state:
            report.add(
                7,
                "STATE.md",
                "a bundle must not contain STATE.md - that file is one learner's "
                "progress, and the runner creates it. Delete it, and move anything "
                "in it that describes the course into COURSE.md, DESIGN.md or a "
                "lesson.",
            )
        if not has_template:
            report.add(
                7,
                "STATE.template.md",
                "a bundle must contain STATE.template.md, the shape a fresh "
                "instance starts in.",
            )
        if isinstance(manifest, dict) and "instance" in manifest:
            report.add(
                7,
                "tutorial.yaml",
                "the 'instance:' stamp is written by the runner when it "
                "materializes an instance. A bundle must not carry it.",
            )
    else:
        if not has_state:
            report.add(
                7,
                "STATE.md",
                "an instance must contain STATE.md. If this directory has "
                "STATE.template.md instead, it is a bundle, not an instance.",
            )
        if has_template:
            report.add(
                7,
                "STATE.template.md",
                "an instance must not contain STATE.template.md - the runner "
                "turns the template into STATE.md and removes it.",
            )
        if isinstance(manifest, dict) and "instance" not in manifest:
            report.add(
                7,
                "tutorial.yaml",
                "an instance's tutorial.yaml carries an 'instance:' stamp "
                "recording what it was materialized from. This one has none.",
            )
    report.ran(7, f"mode={mode}")


def check_manifest(manifest: Any, report: Report) -> None:
    """Check 8 - required fields and validator definitions."""
    if not isinstance(manifest, dict):
        report.blocked(8, "tutorial.yaml did not parse into a mapping")
        return
    for name in REQUIRED_MANIFEST_FIELDS:
        if name not in manifest:
            report.add(
                8, "tutorial.yaml", f"the required field '{name}' is missing"
            )
        elif manifest[name] is None and name != "validators":
            report.add(8, "tutorial.yaml", f"the required field '{name}' is empty")
    fmt = manifest.get("bundle_format")
    if fmt is not None and fmt not in KNOWN_BUNDLE_FORMATS:
        report.add(
            8,
            "tutorial.yaml",
            f"bundle_format is {fmt!r}; this validator knows "
            f"{', '.join(str(k) for k in KNOWN_BUNDLE_FORMATS)}",
        )
    bundle_id = manifest.get("id")
    if isinstance(bundle_id, str) and not re.fullmatch(r"[a-z0-9-]+", bundle_id):
        report.add(
            8,
            "tutorial.yaml",
            f"id {bundle_id!r} must match [a-z0-9-]+ - lowercase letters, "
            f"digits and hyphens only",
        )
    for name in ("subjects", "tutor_owned", "learner_owned"):
        if name in manifest and manifest[name] is not None:
            if as_list(manifest[name]) is None:
                report.add(
                    8,
                    "tutorial.yaml",
                    f"{name} must be a list, not {type(manifest[name]).__name__}",
                )
    validators = manifest.get("validators")
    if validators is not None and not isinstance(validators, dict):
        report.add(
            8,
            "tutorial.yaml",
            f"validators must be a mapping of name to definition, not "
            f"{type(validators).__name__}",
        )
    elif isinstance(validators, dict):
        for vname, vdef in validators.items():
            where = f"tutorial.yaml (validators.{vname})"
            if not isinstance(vdef, dict):
                report.add(
                    8, where, "a validator definition must be a mapping with a 'kind'"
                )
                continue
            kind = vdef.get("kind")
            if kind not in VALIDATOR_KINDS:
                report.add(
                    8,
                    where,
                    f"kind {kind!r} is not one of "
                    f"{', '.join(sorted(VALIDATOR_KINDS))}",
                )
                continue
            for extra in VALIDATOR_KINDS[kind]:
                if extra not in vdef:
                    report.add(
                        8,
                        where,
                        f"kind {kind!r} requires the field {extra!r}",
                    )
    report.ran(8, f"{len(REQUIRED_MANIFEST_FIELDS)} required fields")


def check_required_files(root: Path, manifest: Any, report: Report) -> None:
    """Check 9 - COURSE.md, DESIGN.md, a lessons/ directory, a non-empty list."""
    entries = list_dir(root)
    for name in ("COURSE.md", "DESIGN.md"):
        if name not in entries:
            near = [e for e in entries if e.lower() == name.lower()]
            if near:
                report.add(
                    9,
                    name,
                    f"the file is named {near[0]!r}; the name must match exactly "
                    f"(this filesystem is case-insensitive and hides the "
                    f"difference)",
                )
            else:
                report.add(9, name, "the file is required and is missing")
    if "lessons" not in entries or not (root / "lessons").is_dir():
        report.add(9, "lessons/", "the lessons/ directory is required and is missing")
    listed = as_list(manifest.get("lessons")) if isinstance(manifest, dict) else None
    if listed is not None and len(listed) == 0:
        report.add(
            9, "tutorial.yaml", "the lessons list is empty; a bundle needs at least one lesson"
        )
    report.ran(9)


def check_workspace_and_ownership(manifest: Any, report: Report) -> None:
    """Check 10."""
    if not isinstance(manifest, dict):
        report.blocked(10, "tutorial.yaml did not parse into a mapping")
        return
    kind = manifest.get("workspace_kind")
    if kind not in WORKSPACE_KINDS:
        report.add(
            10,
            "tutorial.yaml",
            f"workspace_kind is {kind!r}; it must be one of "
            f"{', '.join(WORKSPACE_KINDS)}",
        )
    policy = manifest.get("ownership_policy")
    if policy not in OWNERSHIP_POLICIES:
        report.add(
            10,
            "tutorial.yaml",
            f"ownership_policy is {policy!r}; it must be one of "
            f"{', '.join(OWNERSHIP_POLICIES)}",
        )
    tutor_owned = as_list(manifest.get("tutor_owned"))
    if tutor_owned is not None and len(tutor_owned) == 0:
        report.add(
            10,
            "tutorial.yaml",
            "tutor_owned is empty; the tutor must own at least STATE.md and "
            "DESIGN.md in the instance",
        )
    learner_owned = as_list(manifest.get("learner_owned"))
    # The contract says a course that builds no software uses
    # workspace_kind: none and leaves learner_owned as an empty list. So an
    # empty learner_owned is only a finding for the other two kinds.
    if learner_owned is not None and len(learner_owned) == 0 and kind != "none":
        report.add(
            10,
            "tutorial.yaml",
            f"learner_owned is empty but workspace_kind is {kind!r}. An empty "
            f"learner_owned is only correct for workspace_kind: none, where the "
            f"course builds no software.",
        )
    report.ran(10, f"workspace_kind={kind!r}")


def check_unique_slugs(lessons: list[Lesson], report: Report) -> None:
    """Check 4 - no two lessons may claim the same id.

    The id namespace is the whole instance, not one directory: a generated
    lesson that shadows an authored lesson's slug makes `after:` and
    `active_lesson` ambiguous to a reader even though the paths differ.
    """
    slugs: dict[str, list[str]] = {}
    for lesson in lessons:
        slugs.setdefault(lesson.slug, []).append(lesson.rel)
    for slug, paths in sorted(slugs.items()):
        if len(paths) > 1:
            dirs = sorted({path.split("/", 1)[0] + "/" for path in paths})
            report.add(
                4,
                ", ".join(dirs),
                f"the slug {slug!r} is used by more than one lesson "
                f"({', '.join(sorted(paths))}); a lesson id must be unique "
                f"across lessons/ and {GENERATED_DIR}/",
            )


def check_lesson_list(
    root: Path,
    manifest: Any,
    lessons_dir_exists: bool,
    discovered: list[Lesson],
    optional_keys: set[str],
    report: Report,
) -> list[Lesson]:
    """Check 4 - resolution, exactly-once listing. Returns the lessons to load.

    A lesson is reachable through EITHER list: `lessons` walks the main path in
    order, `optional_lessons` holds the ones the tutor offers. A lesson in
    neither is invisible to the runner, which is what this reports.

    A lesson in BOTH belongs to check 18, not here. Reporting it twice would
    describe one mistake as two, and the useful message - "nothing can be both
    walked and offered" - is the one check 18 gives.
    """
    listed_raw = as_list(manifest.get("lessons")) if isinstance(manifest, dict) else None
    if listed_raw is None:
        report.blocked(
            4,
            "tutorial.yaml has no usable 'lessons' list, so entries cannot be "
            "cross-checked against lessons/",
        )
        return discovered
    listed: list[str] = []
    for item in listed_raw:
        if not isinstance(item, str):
            report.add(
                4,
                "tutorial.yaml",
                f"the lessons entry {item!r} is not a path string",
            )
            continue
        listed.append(item)

    seen: dict[str, int] = {}
    for entry in listed:
        seen[entry] = seen.get(entry, 0) + 1
    for entry, count in seen.items():
        if count > 1:
            report.add(
                4,
                "tutorial.yaml",
                f"the lessons list names {entry!r} {count} times; every lesson "
                f"must appear exactly once",
            )

    by_rel = {lesson.rel: lesson for lesson in discovered}
    for entry in listed:
        if entry == GENERATED_DIR or entry.startswith(GENERATED_DIR + "/"):
            # Check 16 owns this. Reporting it here as well would describe a
            # generated lesson as "not a lesson", which is both wrong and
            # useless to the author.
            continue
        resolved, reason = resolve_exact(root, entry)
        if resolved is None:
            report.add(
                4,
                "tutorial.yaml",
                f"the lessons entry {entry!r} does not resolve: {reason}",
            )
            continue
        if entry not in by_rel:
            report.add(
                4,
                "tutorial.yaml",
                f"the lessons entry {entry!r} resolves to a file that is not a "
                f"lesson. A lesson is a top-level .md file in lessons/, or "
                f"<folder>/LESSON.md. Supporting files inside a lesson folder are "
                f"material and must not be listed.",
            )

    if lessons_dir_exists:
        reachable = set(listed) | optional_keys
        for lesson in discovered:
            if lesson.rel not in reachable:
                report.add(
                    4,
                    lesson.rel,
                    "this lesson is not listed in tutorial.yaml's 'lessons', and "
                    "not in 'optional_lessons' either. The runner reaches a "
                    "lesson only through one of those two lists - 'lessons' is "
                    "the main path it walks, 'optional_lessons' is what it "
                    "offers - so this file is invisible. Add it to whichever one "
                    "it belongs in, or delete it.",
                )

    report.ran(
        4,
        f"{len(listed)} listed / {len(optional_keys)} optional / "
        f"{len(discovered)} found",
    )
    # Load every lesson we can see, whether listed or not: a lesson with a
    # broken design_ref is worth reporting even while it is unlisted.
    return discovered


def check_lesson_frontmatter(
    lessons: list[Lesson],
    anchors: set[str] | None,
    declared_validators: set[str] | None,
    report: Report,
) -> None:
    """Checks 1, 2 and 3."""
    if not lessons:
        for number in (1, 2, 3):
            report.na(number, "no lessons were found under lessons/")
        return

    checked_refs = 0
    checked_validators = 0
    for lesson in lessons:
        text = read_text(lesson.path)
        if text is None:
            report.add(3, lesson.rel, "the file could not be read as UTF-8 text")
            continue
        fm_text, _ = split_frontmatter(text)
        if fm_text is None:
            report.add(
                3,
                lesson.rel,
                "there is no YAML frontmatter. A lesson must open with a '---' "
                "block declaring at least id and title.",
            )
            continue
        try:
            fm = load_yaml(fm_text, lesson.rel + " frontmatter")
        except YamlError as exc:
            report.add(3, lesson.rel, f"the frontmatter does not parse: {exc}")
            continue
        if not isinstance(fm, dict):
            report.add(
                3, lesson.rel, "the frontmatter is not a mapping of field to value"
            )
            continue

        lid = fm.get("id")
        if lid is None or (isinstance(lid, str) and lid.strip() == ""):
            report.add(3, lesson.rel, "the frontmatter has no 'id'")
        elif str(lid) != lesson.slug:
            report.add(
                3,
                lesson.rel,
                f"the frontmatter id is {str(lid)!r} but the lesson slug is "
                f"{lesson.slug!r}. The id must equal the file stem, or the "
                f"folder name for a foldered lesson.",
            )
        title = fm.get("title")
        if title is None or (isinstance(title, str) and title.strip() == ""):
            report.add(3, lesson.rel, "the frontmatter has no 'title'")

        refs = fm.get("design_refs")
        if refs is not None:
            if as_list(refs) is None:
                report.add(
                    1,
                    lesson.rel,
                    f"design_refs must be a list of DESIGN.md anchors, not "
                    f"{type(refs).__name__}",
                )
            elif anchors is not None:
                for ref in refs:
                    checked_refs += 1
                    name = str(ref).lstrip("#")
                    if name not in anchors:
                        report.add(
                            1,
                            lesson.rel,
                            f"design_refs names {name!r}, which is not an anchor "
                            f"in DESIGN.md. Add a '## Heading {{#{name}}}' section, "
                            f"or point the lesson at an existing anchor.",
                        )

        vals = fm.get("validators")
        if vals is not None:
            if as_list(vals) is None:
                report.add(
                    2,
                    lesson.rel,
                    f"validators must be a list of validator names, not "
                    f"{type(vals).__name__}",
                )
            elif declared_validators is not None:
                for val in vals:
                    checked_validators += 1
                    if str(val) not in declared_validators:
                        report.add(
                            2,
                            lesson.rel,
                            f"validators names {str(val)!r}, which is not declared "
                            f"in tutorial.yaml's 'validators' map.",
                        )

    n_generated = sum(1 for lesson in lessons if lesson.generated)
    report.ran(
        3,
        f"{len(lessons)} lessons"
        + (f", {n_generated} of them generated" if n_generated else ""),
    )
    if anchors is None:
        report.blocked(1, "DESIGN.md is missing or unreadable, so anchors are unknown")
    else:
        report.ran(1, f"{checked_refs} refs against {len(anchors)} anchors")
    if declared_validators is None:
        report.blocked(
            2, "tutorial.yaml has no usable 'validators' map to check names against"
        )
    else:
        report.ran(
            2,
            f"{checked_validators} references against "
            f"{len(declared_validators)} declared",
        )


def check_progress_markers(
    root: Path, report: Report, subdirs: tuple[str, ...] = ("lessons",)
) -> None:
    """Check 5."""
    targets: list[tuple[str, Path]] = []
    course = root / "COURSE.md"
    if course.is_file():
        targets.append(("COURSE.md", course))
    for subdir in subdirs:
        lessons_dir = root / subdir
        if not lessons_dir.is_dir():
            continue
        for path in sorted(lessons_dir.rglob("*")):
            if not path.is_file() or path.name.startswith("."):
                continue
            targets.append((str(path.relative_to(root)), path))
    if not targets:
        report.na(
            5,
            f"neither COURSE.md nor any file under "
            f"{', '.join(s + '/' for s in subdirs)} was found",
        )
        return
    scanned = 0
    for rel, path in targets:
        text = read_text(path)
        if text is None:
            continue  # binary material; there is no prose to scan
        scanned += 1
        for lineno, line in enumerate(text.splitlines(), 1):
            for label, pattern in PROGRESS_MARKERS:
                match = pattern.search(line)
                if not match:
                    continue
                if rel.startswith(GENERATED_DIR + "/"):
                    why = (
                        "a generated lesson is still a lesson: it teaches, and it "
                        "records no progress. Where the learner has got to lives "
                        "in STATE.md, so that one file is the only thing to read "
                        "to answer that question."
                    )
                else:
                    why = (
                        "COURSE.md and lessons/ describe the course for every "
                        "learner who will ever take it, so they carry no "
                        "progress; all progress lives in STATE.md."
                    )
                report.add(
                    5,
                    f"{rel}:{lineno}",
                    f"{label} appears here: {match.group(0).strip()!r}. {why}",
                )
                # One finding per line. Several patterns can describe the same
                # marker, and repeating it once per pattern buries the rest of
                # the report.
                break
    report.ran(5, f"{scanned} text files, structural positions only")


def names_file(text: str, rel_in_folder: str) -> bool:
    """True if `text` names the material file `rel_in_folder`.

    A plain substring search is too weak: it is satisfied by a filename that
    is only part of a longer word or path, such as `dafsa.svg` inside
    `https://example.invalid/assets/dafsa.svg.bak`. So the match must be a
    delimited token - not preceded by a path or word character, and not
    continuing into one.

    The relative path counts, and so does the bare basename for a nested
    file, because a lesson that says "show `dafsa.svg`" has named it.

    KNOWN LIMITATION, stated because a pass must not be over-read: this
    proves the material is NAMED, not that the lesson says WHEN to use it,
    which the contract also asks for. A name inside a code fence, a quoted
    example or a URL-free aside counts as named. Judging intent cannot be
    done mechanically without crying wolf, and a check that cries wolf gets
    ignored - which is worse than a check that is honestly weak.
    """
    candidates = [rel_in_folder]
    basename = rel_in_folder.rsplit("/", 1)[-1]
    if basename != rel_in_folder:
        candidates.append(basename)
    for candidate in candidates:
        pattern = (
            r"(?<![A-Za-z0-9_./\\-])"
            + re.escape(candidate)
            + r"(?![A-Za-z0-9_-])(?!\.[A-Za-z0-9])"
        )
        if re.search(pattern, text):
            return True
    return False


def check_material_reachable(
    root: Path, manifest: Any, lessons: list[Lesson], report: Report
) -> None:
    """Check 6 - forward direction only.

    The reverse check ("LESSON.md names a file that does not exist") was
    implemented and deleted: it cannot tell a material reference from an
    ordinary prose mention of DESIGN.md, src/lib.rs or Cargo.toml. Do not
    reintroduce it.

    A file is exempt from the "named in LESSON.md" rule when some declared
    `supplies:` entry - from the manifest OR from any lesson, not only the
    one that owns the folder - covers it. A supplies entry says more than a
    prose mention does: it states what the file is and where it goes, so a
    tutor already knows it exists without LESSON.md repeating that. This is
    an EXEMPTION, not a loosening - a file no supplies entry covers must
    still be named, exactly as before.
    """
    foldered = [lesson for lesson in lessons if lesson.folder is not None]
    if not foldered:
        report.na(6, "no foldered lessons")
        return
    supplies_entries = [entry for _, entry in collect_supplies(root, manifest, lessons)]
    checked = 0
    supplied = 0
    for lesson in foldered:
        text = read_text(lesson.path)
        if text is None:
            continue
        folder = lesson.folder
        assert folder is not None
        folder_rel = folder.relative_to(root).as_posix()
        for path in sorted(folder.rglob("*")):
            if not path.is_file():
                continue
            rel_in_folder = path.relative_to(folder).as_posix()
            if rel_in_folder == "LESSON.md":
                continue
            if any(part.startswith(".") for part in path.relative_to(folder).parts):
                continue
            checked += 1
            bundle_rel = f"{folder_rel}/{rel_in_folder}"
            if supplies_covers(supplies_entries, bundle_rel):
                supplied += 1
                continue
            if not names_file(text, rel_in_folder):
                report.add(
                    6,
                    f"{lesson.rel} -> {rel_in_folder}",
                    f"the material file {rel_in_folder!r} is never named by "
                    f"LESSON.md, so the tutor has no way to know it exists. "
                    f"Name it in the lesson and say when to use it, or delete it.",
                )
    report.ran(
        6,
        f"{checked} material files in {len(foldered)} lesson folders "
        f"({supplied} cleared by a supplies declaration); names only, not intent",
    )


def optional_lesson_keys(manifest: Any) -> set[str]:
    """The paths declared in `optional_lessons`, for the checks that need them.

    A malformed `optional_lessons` yields an empty set rather than raising.
    Check 18 reports the malformation; every other check then behaves exactly
    as it would for a bundle that declared none, which is the safe direction.
    """
    if not isinstance(manifest, dict):
        return set()
    raw = manifest.get(OPTIONAL_KEY)
    if not isinstance(raw, dict):
        return set()
    return {str(key) for key in raw}


def anticipated_failure_modes(manifest: Any) -> set[str]:
    """Every failure-mode id named by some optional lesson's `anticipates`."""
    if not isinstance(manifest, dict):
        return set()
    raw = manifest.get(OPTIONAL_KEY)
    if not isinstance(raw, dict):
        return set()
    named: set[str] = set()
    for entry in raw.values():
        if not isinstance(entry, dict):
            continue
        ids = as_list(entry.get("anticipates"))
        if ids is None:
            continue
        named.update(str(item) for item in ids)
    return named


def check_optional_lessons(
    root: Path, manifest: Any, discovered: list[Lesson], report: Report
) -> None:
    """Check 18 - both modes.

    The ABSENCE of `optional_lessons` is normal, not a finding: most bundles
    never declare one, and the key is additive to bundle_format 1.
    """
    if not isinstance(manifest, dict) or manifest.get(OPTIONAL_KEY) is None:
        report.na(
            18,
            f"the manifest declares no {OPTIONAL_KEY}, which is the normal case",
        )
        return
    raw = manifest[OPTIONAL_KEY]
    if not isinstance(raw, dict):
        report.add(
            18,
            "tutorial.yaml",
            f"{OPTIONAL_KEY} must be a mapping of lesson path to offer "
            f"metadata, not {type(raw).__name__}. It is a map and not a list "
            f"because the tutor looks a lesson up by path.",
        )
        report.ran(18, f"{OPTIONAL_KEY} is not a mapping")
        return

    listed_raw = as_list(manifest.get("lessons"))
    listed: list[str] | None = (
        [entry for entry in listed_raw if isinstance(entry, str)]
        if listed_raw is not None
        else None
    )
    modes = manifest.get(FAILURE_MODES_KEY)
    declared_modes = {str(k) for k in modes} if isinstance(modes, dict) else set()
    by_rel = {lesson.rel for lesson in discovered}

    def in_lessons(where: str, field: str, value: Any) -> None:
        """Report `value` unless it is a string naming a `lessons` entry."""
        if not isinstance(value, str):
            report.add(
                18,
                where,
                f"{field} names {value!r}, which is not a path string",
            )
            return
        if listed is None or value in listed:
            return
        report.add(
            18,
            where,
            f"{field} names {value!r}, which is not an entry in tutorial.yaml's "
            f"'lessons' list. Every offer point, repair site and gate is a "
            f"place on the MAIN PATH, so each one must name a lesson the "
            f"runner actually walks.",
        )

    for key, value in raw.items():
        name = str(key)
        where = f"tutorial.yaml ({OPTIONAL_KEY}.{name})"
        if not isinstance(key, str):
            report.add(
                18,
                "tutorial.yaml",
                f"the {OPTIONAL_KEY} key {key!r} is not a path string",
            )
            continue
        if name == GENERATED_DIR or name.startswith(GENERATED_DIR + "/"):
            report.add(
                18,
                where,
                f"an optional lesson is AUTHORED and ships in the bundle, so it "
                f"lives in lessons/. This key names a path under "
                f"{GENERATED_DIR}/, which holds lessons one tutor wrote for one "
                f"learner during one course. To offer it to everyone, promote it "
                f"into lessons/ first (see check 13).",
            )
            continue
        resolved, reason = resolve_exact(root, name)
        if resolved is None:
            report.add(
                18, where, f"the {OPTIONAL_KEY} key does not resolve: {reason}"
            )
        elif name not in by_rel:
            report.add(
                18,
                where,
                f"the {OPTIONAL_KEY} key resolves to a file that is not a "
                f"lesson. A lesson is a top-level .md file in lessons/, or "
                f"<folder>/LESSON.md. Supporting files inside a lesson folder "
                f"are material and cannot be offered.",
            )
        if listed is not None and name in listed:
            report.add(
                18,
                where,
                f"this lesson is also an entry in the 'lessons' list. Nothing "
                f"can be both: 'lessons' is the main path every learner walks "
                f"in order, and an optional lesson is one the tutor offers and "
                f"the learner may decline. Choose one list.",
            )

        if not isinstance(value, dict):
            report.add(
                18,
                where,
                f"the entry must be a mapping declaring at least "
                f"{' and '.join(OPTIONAL_REQUIRED_FIELDS)}, not "
                f"{type(value).__name__}",
            )
            continue

        offer_at = value.get("offer_at")
        if "offer_at" not in value or offer_at is None:
            report.add(
                18,
                where,
                "'offer_at' is required and is missing. It names the 'lessons' "
                "entries at which the tutor raises the offer, and it is what "
                "makes the lesson reachable at all.",
            )
        elif as_list(offer_at) is None:
            report.add(
                18,
                where,
                f"'offer_at' must be a list of 'lessons' entries, not "
                f"{type(offer_at).__name__}",
            )
        elif not offer_at:
            report.add(
                18,
                where,
                "'offer_at' is empty, so nothing ever offers this lesson and no "
                "learner can reach it. That is the same error as a lesson "
                "listed in neither list (check 4), not a way to say 'offer it "
                "whenever you like'. Name at least one 'lessons' entry.",
            )
        else:
            for entry in offer_at:
                in_lessons(where, "'offer_at'", entry)

        if not _is_text(value.get("offer_because")):
            report.add(
                18,
                where,
                f"'offer_because' is required and must be a non-empty string. "
                f"It is {value.get('offer_because')!r}. The tutor says this "
                f"sentence to the learner when it offers the lesson, and it "
                f"lives here rather than in the lesson so that offering costs "
                f"no file open.",
            )

        anticipates = value.get("anticipates")
        if anticipates is not None:
            if as_list(anticipates) is None:
                report.add(
                    18,
                    where,
                    f"'anticipates' must be a list of failure-mode ids, not "
                    f"{type(anticipates).__name__}",
                )
            else:
                for item in anticipates:
                    if not isinstance(item, str):
                        report.add(
                            18,
                            where,
                            f"'anticipates' names {item!r}, which is not a "
                            f"failure-mode id string",
                        )
                    elif item not in declared_modes:
                        report.add(
                            18,
                            where,
                            f"'anticipates' names {item!r}, which is not "
                            f"declared in '{FAILURE_MODES_KEY}'. The tutor "
                            f"re-offers this lesson by recognising a named "
                            f"failure, so the name has to exist and carry a "
                            f"summary it can say out loud.",
                        )

        if "repair_in" in value and value["repair_in"] is not None:
            in_lessons(where, "'repair_in'", value["repair_in"])

        required_for = value.get("required_for")
        if required_for is not None:
            if as_list(required_for) is None:
                report.add(
                    18,
                    where,
                    f"'required_for' must be a list of 'lessons' entries, not "
                    f"{type(required_for).__name__}",
                )
            else:
                for entry in required_for:
                    in_lessons(where, "'required_for'", entry)
            if not _is_text_list(as_list(anticipates) or []):
                report.add(
                    18,
                    where,
                    "'required_for' declares a gate, but 'anticipates' is "
                    "missing or empty. The gate closes when an anticipated "
                    "failure is observed and opens when the lesson is taken, so "
                    "with nothing to anticipate it can never do either. Declare "
                    "the failure mode it gates on, or remove 'required_for'.",
                )

    if listed is None:
        report.blocked(
            18,
            "tutorial.yaml has no usable 'lessons' list, so offer_at, repair_in "
            "and required_for could not be resolved",
        )
    else:
        report.ran(18, f"{len(raw)} optional lesson(s)")


def check_failure_modes(
    manifest: Any,
    declared_validators: set[str] | None,
    anticipated: set[str],
    report: Report,
) -> None:
    """Check 19 - both modes.

    The ABSENCE of `failure_modes` is normal, not a finding: it is needed only
    by an optional lesson that anticipates something.
    """
    if not isinstance(manifest, dict) or manifest.get(FAILURE_MODES_KEY) is None:
        report.na(
            19,
            f"the manifest declares no {FAILURE_MODES_KEY}, which is the "
            f"normal case",
        )
        return
    raw = manifest[FAILURE_MODES_KEY]
    if not isinstance(raw, dict):
        report.add(
            19,
            "tutorial.yaml",
            f"{FAILURE_MODES_KEY} must be a mapping of id to definition, not "
            f"{type(raw).__name__}. An optional lesson anticipates a failure "
            f"BY ID, so the ids are the keys.",
        )
        report.ran(19, f"{FAILURE_MODES_KEY} is not a mapping")
        return

    checked_signals = 0
    for key, value in raw.items():
        name = str(key)
        where = f"tutorial.yaml ({FAILURE_MODES_KEY}.{name})"
        if not _FAILURE_MODE_ID_RE.fullmatch(name):
            report.add(
                19,
                "tutorial.yaml",
                f"the failure-mode id {name!r} must match [a-z0-9-]+. It is a "
                f"stable name an optional lesson refers to, so it is spelled "
                f"like every other id in this format.",
            )
        if not isinstance(value, dict):
            report.add(
                19,
                where,
                f"a failure mode must be a mapping declaring at least "
                f"'summary', not {type(value).__name__}",
            )
            continue
        if not _is_text(value.get("summary")):
            report.add(
                19,
                where,
                f"'summary' is required and must be a non-empty string. It is "
                f"{value.get('summary')!r}. The tutor says this sentence when "
                f"it connects an observed failure to the lesson the learner "
                f"set aside, so a failure mode without one cannot be raised.",
            )
        signals = value.get("signals")
        if signals is not None:
            if as_list(signals) is None:
                report.add(
                    19,
                    where,
                    f"'signals' must be a list of evidence forms, not "
                    f"{type(signals).__name__}",
                )
            else:
                for item in signals:
                    if not isinstance(item, str) or not item.strip():
                        report.add(
                            19,
                            where,
                            f"the signal {item!r} is not a string. A signal is "
                            f"one of 'validator:<name>', 'token:<TOKEN>' or "
                            f"the bare word 'diagnosis'.",
                        )
                        continue
                    checked_signals += 1
                    text = item.strip()
                    if text == "diagnosis":
                        continue
                    if text.startswith("validator:"):
                        vname = text[len("validator:") :].strip()
                        if not vname:
                            report.add(
                                19,
                                where,
                                "the signal 'validator:' names no validator",
                            )
                        elif (
                            declared_validators is not None
                            and vname not in declared_validators
                        ):
                            report.add(
                                19,
                                where,
                                f"the signal names validator {vname!r}, which "
                                f"is not declared in tutorial.yaml's "
                                f"'validators' map. A signal the tutor cannot "
                                f"run is evidence it can never weigh.",
                            )
                        continue
                    if text.startswith("token:"):
                        if not text[len("token:") :].strip():
                            report.add(
                                19, where, "the signal 'token:' names no token"
                            )
                        continue
                    report.add(
                        19,
                        where,
                        f"the signal {text!r} is in none of the three permitted "
                        f"forms: 'validator:<name>' for a declared validator "
                        f"failing, 'token:<TOKEN>' for an identifier a check "
                        f"you control prints, or the bare word 'diagnosis' for "
                        f"something the tutor concluded by reading the code. "
                        f"Raw compiler or test output is deliberately not a "
                        f"form - it breaks the first time a toolchain rewords.",
                    )
        if name not in anticipated:
            report.add(
                19,
                where,
                f"no optional lesson anticipates {name!r}, so nothing can ever "
                f"be re-offered when it happens and this declaration is dead "
                f"weight - the same error as a lesson nothing lists. Name it in "
                f"some optional lesson's 'anticipates', or remove it.",
            )

    if declared_validators is None:
        report.blocked(
            19,
            "tutorial.yaml has no usable 'validators' map, so 'validator:' "
            "signals could not be resolved",
        )
    else:
        report.ran(19, f"{len(raw)} failure mode(s), {checked_signals} signal(s)")


def check_optional_frontmatter(
    lessons: list[Lesson],
    optional_keys: set[str],
    listed: list[str] | None,
    report: Report,
) -> None:
    """Check 20 - both modes.

    Deliberate redundancy, of the same class as "id must equal the slug". The
    manifest already knows which lessons are optional. The lesson file says it
    again because a lesson that does not say so reads as main path to anyone
    who opens it alone - including its author, six months later.

    A file whose frontmatter is missing or unparseable is skipped silently
    here: check 3 already reports it, and a second finding about the same
    unreadable block tells the author nothing new.
    """
    checked = 0
    for lesson in lessons:
        text = read_text(lesson.path)
        if text is None:
            continue
        fm_text, _ = split_frontmatter(text)
        if fm_text is None:
            continue
        try:
            fm = load_yaml(fm_text, lesson.rel + " frontmatter")
        except YamlError:
            continue
        if not isinstance(fm, dict):
            continue
        checked += 1
        if lesson.rel in optional_keys:
            if "optional" not in fm:
                report.add(
                    20,
                    lesson.rel,
                    f"tutorial.yaml lists this lesson in '{OPTIONAL_KEY}', but "
                    f"its frontmatter does not declare 'optional: true'. Say it "
                    f"in both places: a lesson file that does not say it is "
                    f"optional reads as main path to everyone who opens it "
                    f"alone.",
                )
            elif fm["optional"] is not True:
                report.add(
                    20,
                    lesson.rel,
                    f"optional is {fm['optional']!r}; a lesson listed in "
                    f"'{OPTIONAL_KEY}' must declare exactly 'optional: true'. "
                    f"There is no third state - a lesson is offered or it is "
                    f"walked.",
                )
        elif "optional" in fm:
            if lesson.generated:
                where = (
                    f"it belongs to {GENERATED_DIR}/, which is an overlay one "
                    f"tutor wrote for one learner"
                )
            elif listed is not None and lesson.rel in listed:
                where = (
                    "it is an entry in tutorial.yaml's 'lessons' list, which "
                    "every learner walks in order"
                )
            else:
                where = "it is in neither list at all - see check 4"
            report.add(
                20,
                lesson.rel,
                f"the frontmatter declares 'optional: {fm['optional']!r}', but "
                f"this lesson is not listed in '{OPTIONAL_KEY}': {where}. Only "
                f"a lesson the tutor OFFERS is optional. Either add it to "
                f"'{OPTIONAL_KEY}' with its offer metadata, or remove the "
                f"field.",
            )
    report.ran(20, f"{checked} lessons, {len(optional_keys)} of them optional")


def section_lines(body: str, heading: str) -> list[str] | None:
    """The lines under '## <heading>', or None when the section is absent."""
    pattern = re.compile(
        rf"^#+[ \t]+{re.escape(heading)}[ \t]*$", re.IGNORECASE
    )
    lines = body.splitlines()
    for index, line in enumerate(lines):
        if not pattern.match(line):
            continue
        collected: list[str] = []
        for rest in lines[index + 1 :]:
            if re.match(r"^#+[ \t]", rest):
                break
            collected.append(rest)
        return collected
    return None


def check_optional_state(
    root: Path, optional_keys: set[str], fm: dict | None, report: Report
) -> None:
    """Check 21 - instance mode.

    STATE.md records ONE learner's decision about each optional lesson they
    were offered. Not yet offered is the ABSENCE of a record, which is why
    there is no 'not-offered' state: a record saying so claims the tutor
    offered a lesson and then un-offered it.
    """
    if "STATE.md" not in list_dir(root):
        if optional_keys:
            report.blocked(21, "STATE.md is missing (see check 7)")
        else:
            report.na(
                21,
                "the manifest declares no optional lessons, and there is no "
                "STATE.md to record any",
            )
        return
    text = read_text(root / "STATE.md")
    if text is None:
        if optional_keys:
            report.blocked(21, "STATE.md could not be read (see check 11)")
        else:
            report.na(21, "the manifest declares no optional lessons")
        return
    _, body = split_frontmatter(text)
    lines = section_lines(body, OPTIONAL_SECTION)
    if lines is None:
        if not optional_keys:
            report.na(
                21,
                f"the manifest declares no optional lessons and STATE.md has "
                f"no '## {OPTIONAL_SECTION}' section",
            )
            return
        # The manifest offers lessons but this learner has no record yet. That
        # is the ordinary state of a fresh instance, so the section's absence
        # is not itself a finding - but active_lesson is still checked below.
        lines = []

    # Bullets may wrap: a continuation line belongs to the bullet above it.
    entries: list[tuple[int, str]] = []
    for offset, line in enumerate(lines):
        if re.match(r"^[-*+][ \t]", line):
            entries.append((offset, line.strip()))
        elif entries and line.strip():
            index, existing = entries[-1]
            entries[-1] = (index, existing + " " + line.strip())

    seen: dict[str, str] = {}
    for _, entry in entries:
        if re.fullmatch(r"[-*+][ \t]+[Nn]one\.?", entry):
            continue  # the conventional "nothing to record" bullet
        match = _OPTIONAL_RECORD_RE.match(entry)
        if match is None:
            report.add(
                21,
                f"STATE.md (## {OPTIONAL_SECTION})",
                f"the entry {entry[:70]!r} is not a record. Each one names the "
                f"lesson path in backticks, then a dash, then one of "
                f"{', '.join(OPTIONAL_STATES)} - for example: "
                f"- `lessons/pure-core-and-edges.md` — deferred — offered at "
                f"`lessons/01-subcommands/LESSON.md` on 2026-09-11",
            )
            continue
        path = match.group("path").strip()
        state = match.group("state")
        if path in seen:
            report.add(
                21,
                f"STATE.md (## {OPTIONAL_SECTION})",
                f"{path!r} is recorded twice, as {seen[path]!r} and {state!r}. "
                f"One lesson has one current state; replace the record rather "
                f"than appending to it.",
            )
        else:
            seen[path] = state
        if path not in optional_keys:
            report.add(
                21,
                f"STATE.md (## {OPTIONAL_SECTION})",
                f"{path!r} is not a key in tutorial.yaml's '{OPTIONAL_KEY}', so "
                f"there is no lesson for this record to be about. This section "
                f"records decisions about optional lessons only; a generated "
                f"lesson belongs under '## Generated lessons'.",
            )
        if state == "not-offered":
            report.add(
                21,
                f"STATE.md (## {OPTIONAL_SECTION})",
                f"{path!r} is recorded as 'not-offered', which is not a state. "
                f"Not yet offered is the ABSENCE of a record: delete the entry. "
                f"The states are {', '.join(OPTIONAL_STATES)}.",
            )
        elif state not in OPTIONAL_STATES:
            report.add(
                21,
                f"STATE.md (## {OPTIONAL_SECTION})",
                f"{path!r} is recorded as {state!r}, which is not one of "
                f"{', '.join(OPTIONAL_STATES)}.",
            )

    active = fm.get("active_lesson") if isinstance(fm, dict) else None
    if isinstance(active, str) and active in optional_keys:
        if active not in seen:
            report.add(
                21,
                f"STATE.md (## {OPTIONAL_SECTION})",
                f"active_lesson is the optional lesson {active!r}, but this "
                f"section records nothing about it. The learner is standing in "
                f"it, so it must be recorded as 'in-progress'.",
            )
        elif seen[active] != "in-progress":
            report.add(
                21,
                f"STATE.md (## {OPTIONAL_SECTION})",
                f"active_lesson is the optional lesson {active!r}, but its "
                f"record says {seen[active]!r}. A lesson the learner is "
                f"standing in is 'in-progress'.",
            )
    for path, state in seen.items():
        if state == "in-progress" and path != active:
            report.add(
                21,
                f"STATE.md (## {OPTIONAL_SECTION})",
                f"{path!r} is recorded as 'in-progress', but active_lesson is "
                f"{active!r}. One lesson is active at a time, so an optional "
                f"lesson in progress is the active one. Record it as 'offered', "
                f"'deferred' or 'complete', or make it active.",
            )
    report.ran(21, f"{len(seen)} record(s)")


def check_state_template(
    root: Path, manifest: Any, report: Report
) -> dict | None:
    """Check 12 - bundle mode.

    Returns the parsed STATE.template.md frontmatter, or None when it could
    not be read, so check 26 does not have to parse the file a second time.
    """
    path = root / "STATE.template.md"
    if "STATE.template.md" not in list_dir(root):
        report.blocked(12, "STATE.template.md is missing (see check 7)")
        return None
    text = read_text(path)
    if text is None:
        report.add(12, "STATE.template.md", "the file could not be read as UTF-8 text")
        report.blocked(12, "STATE.template.md could not be read")
        return None
    fm_text, body = split_frontmatter(text)
    if fm_text is None:
        report.add(
            12,
            "STATE.template.md",
            "there is no YAML frontmatter; it must declare tutorial_id, "
            "active_lesson, status and updated.",
        )
        report.ran(12)
        return None
    try:
        fm = load_yaml(fm_text, "STATE.template.md frontmatter")
    except YamlError as exc:
        report.add(12, "STATE.template.md", f"the frontmatter does not parse: {exc}")
        report.ran(12)
        return None
    if not isinstance(fm, dict):
        report.add(12, "STATE.template.md", "the frontmatter is not a mapping")
        report.ran(12)
        return None

    manifest_id = manifest.get("id") if isinstance(manifest, dict) else None
    listed = as_list(manifest.get("lessons")) if isinstance(manifest, dict) else None
    first = listed[0] if listed else None

    if manifest_id is not None and fm.get("tutorial_id") != manifest_id:
        report.add(
            12,
            "STATE.template.md",
            f"tutorial_id is {fm.get('tutorial_id')!r} but tutorial.yaml's id is "
            f"{manifest_id!r}; they must be equal.",
        )
    if first is not None and fm.get("active_lesson") != first:
        report.add(
            12,
            "STATE.template.md",
            f"active_lesson is {fm.get('active_lesson')!r} but the first entry of "
            f"'lessons' is {first!r}; a fresh instance must start at lessons[0].",
        )
    if fm.get("status") != "not-started":
        report.add(
            12,
            "STATE.template.md",
            f"status is {fm.get('status')!r}; a template describes a learner who "
            f"has not started, so it must be 'not-started'.",
        )
    for section in STATE_SECTIONS:
        if not re.search(
            rf"^#+\s+{re.escape(section)}\s*$", body, re.MULTILINE | re.IGNORECASE
        ):
            report.add(
                12,
                "STATE.template.md",
                f"the required section heading '## {section}' is missing.",
            )
    report.ran(12)
    return fm


def check_template_assumes_reviewed(fm: dict | None, report: Report) -> None:
    """Check 26 - bundle mode.

    `assumes_reviewed` is the runner's record that ONE learner saw the review
    of the concepts this course assumes and chose to continue
    (state-lifecycle.md section 10). Its presence is the whole of "already
    answered": the runner presents the review only while the field is absent
    (runner-protocol.md section 11.1), and never removes or rewrites it.

    A template describes a learner who has not started, so no review can have
    been shown to anyone. A bundle that ships the stamp in its template hands
    every instance it ever produces an answer nobody gave, and the review is
    suppressed for every learner of that course, forever - each one starts
    without ever being told what the course assumes they already know.

    That is why this is a FINDING rather than a warning. Nothing else can
    report it: the bundle is otherwise well-formed, the runner does exactly
    what the stamp tells it, and the learner cannot miss a review they were
    never shown. It is invisible from every vantage point except this one,
    and it is one line to fix.

    The rule is unconditional (section 10.1). A course that declares no
    `assumes` never gets the stamp either, so there is no shape of template
    in which the field is correct, and this check never consults the
    manifest.

    It is BUNDLE-ONLY, and deliberately so. In an INSTANCE the field is
    normal and expected - it is precisely what the runner writes - so this
    check is never called in instance mode and cannot reject a course a
    learner has already reviewed.
    """
    if fm is None:
        report.blocked(
            26, "STATE.template.md's frontmatter could not be read (see check 12)"
        )
        return
    if ASSUMES_REVIEWED in fm:
        report.add(
            26,
            "STATE.template.md",
            f"the frontmatter carries {ASSUMES_REVIEWED!r} "
            f"({fm[ASSUMES_REVIEWED]!r}). A template describes a learner who "
            f"has not started, so no assumed-concept review can have been "
            f"shown. The runner reads the field's presence as 'the review was "
            f"shown and the learner chose to continue', so shipping it here "
            f"suppresses that review for EVERY learner of this course: none of "
            f"them is ever told what the course assumes they already know, and "
            f"nothing reports it. Remove the field. Materialization is where it "
            f"can first appear, and only once a learner has answered. See "
            f"state-lifecycle.md section 10.1.",
        )
    report.ran(26)


def check_instance_state(
    root: Path,
    manifest: Any,
    generated: list[Lesson],
    optional_keys: set[str],
    report: Report,
) -> dict | None:
    """Check 11 - instance mode.

    Returns the parsed STATE.md frontmatter, or None when it could not be
    read, so check 17 does not have to parse the file a second time.
    """
    if "STATE.md" not in list_dir(root):
        report.blocked(11, "STATE.md is missing (see check 7)")
        return None
    text = read_text(root / "STATE.md")
    if text is None:
        report.add(11, "STATE.md", "the file could not be read as UTF-8 text")
        report.blocked(11, "STATE.md could not be read")
        return None
    fm_text, _ = split_frontmatter(text)
    if fm_text is None:
        report.add(
            11,
            "STATE.md",
            "there is no YAML frontmatter; it must declare tutorial_id, "
            "active_lesson, status and updated.",
        )
        report.ran(11)
        return None
    try:
        fm = load_yaml(fm_text, "STATE.md frontmatter")
    except YamlError as exc:
        report.add(11, "STATE.md", f"the frontmatter does not parse: {exc}")
        report.ran(11)
        return None
    if not isinstance(fm, dict):
        report.add(11, "STATE.md", "the frontmatter is not a mapping")
        report.ran(11)
        return None

    for name in ("tutorial_id", "active_lesson", "status", "updated"):
        if name not in fm:
            report.add(11, "STATE.md", f"the frontmatter field {name!r} is missing")

    manifest_id = manifest.get("id") if isinstance(manifest, dict) else None
    if manifest_id is not None and fm.get("tutorial_id") != manifest_id:
        report.add(
            11,
            "STATE.md",
            f"tutorial_id is {fm.get('tutorial_id')!r} but tutorial.yaml's id is "
            f"{manifest_id!r}; this instance does not belong to this manifest.",
        )
    active = fm.get("active_lesson")
    if active is None:
        pass  # already reported as missing
    elif not isinstance(active, str):
        report.add(
            11,
            "STATE.md",
            f"active_lesson must be a lesson path, not {type(active).__name__}. "
            f"A description such as 'chapter 1, lesson 10' would force the tutor "
            f"to read COURSE.md to resolve it.",
        )
    else:
        resolved, reason = resolve_exact(root, active)
        if resolved is None:
            report.add(
                11,
                "STATE.md",
                f"active_lesson {active!r} does not resolve: {reason}",
            )
        listed = as_list(manifest.get("lessons")) if isinstance(manifest, dict) else None
        # An instance may sit on a generated lesson or on an optional one, and
        # neither is in the manifest's `lessons` list - deliberately. So the
        # target may be any of the three, and nothing else. A path that
        # resolves to some other file (COURSE.md, a material file, an unlisted
        # lesson) is still a finding: it leaves the runner with no way to say
        # what comes next.
        generated_rels = {lesson.rel for lesson in generated}
        if (
            listed is not None
            and active not in listed
            and active not in generated_rels
            and active not in optional_keys
        ):
            report.add(
                11,
                "STATE.md",
                f"active_lesson {active!r} is none of: an entry in "
                f"tutorial.yaml's 'lessons' list, a key in its "
                f"'{OPTIONAL_KEY}' map, or a lesson in {GENERATED_DIR}/. So the "
                f"runner cannot tell which lesson comes next.",
            )
    report.ran(11)
    return fm


def generated_dir_state(root: Path) -> tuple[bool, list[str]]:
    """Return (an exact-case lessons.generated/ exists, near-miss entry names).

    The local filesystem is case-insensitive, so `Lessons.Generated/` would
    answer an exists() test while being a different name on Linux. Compare
    directory entries instead, and report the near miss rather than silently
    ignoring a directory the author plainly meant as the generated one.
    """
    entries = list_dir(root)
    exact = GENERATED_DIR in entries
    near = [
        name
        for name in entries
        if name != GENERATED_DIR and name.lower() == GENERATED_DIR.lower()
    ]
    return exact, near


def check_no_generated_dir(root: Path, report: Report) -> None:
    """Check 13 - bundle mode. lessons.generated/ belongs only to an instance."""
    exact, near = generated_dir_state(root)
    for name in ([GENERATED_DIR] if exact else []) + near:
        report.add(
            13,
            f"{name}/",
            f"a bundle must not contain {GENERATED_DIR}/. That directory holds "
            f"lessons one tutor wrote for one learner during one course, so a "
            f"bundle carrying it is an instance by mistake - the same error as "
            f"a bundle carrying STATE.md. Delete it, or, if a generated lesson "
            f"has proved worth keeping, promote it: move it into lessons/, "
            f"strip its generated/generated_at/kind/reason/after frontmatter, "
            f"and add it to the 'lessons' list.",
        )
    report.ran(13)


def check_generated_lessons(
    root: Path,
    manifest: Any,
    generated: list[Lesson],
    exact: bool,
    near: list[str],
    report: Report,
) -> None:
    """Checks 14 and 15 - instance mode.

    The ABSENCE of lessons.generated/ is normal, not a finding: most instances
    never need one.
    """
    for name in near:
        report.add(
            14,
            f"{name}/",
            f"the directory is named {name!r}, not {GENERATED_DIR!r}. The local "
            f"filesystem is case-insensitive so it resolves here and is invisible "
            f"to the runner on Linux. Rename it (via a temporary name, because a "
            f"plain rename is a no-op on this filesystem).",
        )
    if not exact:
        if near:
            report.ran(14, "the directory name is mis-cased")
        else:
            report.na(
                14,
                f"{GENERATED_DIR}/ does not exist, which is the normal case",
            )
        report.na(15, "there are no generated lessons")
        return

    if not (root / GENERATED_DIR).is_dir():
        # Without this the run is silently clean: the entry name matches, the
        # walk finds no lessons, and every generated check reports "0 of them".
        report.add(
            14,
            GENERATED_DIR,
            f"{GENERATED_DIR} is a file, not a directory. It holds the lessons "
            f"the tutor wrote during this course, so it must be a directory of "
            f"lesson files.",
        )
        report.ran(14, "the entry is not a directory")
        report.na(15, "there are no generated lessons")
        return

    listed = as_list(manifest.get("lessons")) if isinstance(manifest, dict) else None
    checked_after = 0

    for lesson in generated:
        text = read_text(lesson.path)
        fm: Any = None
        if text is not None:
            fm_text, _ = split_frontmatter(text)
            if fm_text is not None:
                try:
                    fm = load_yaml(fm_text, lesson.rel + " frontmatter")
                except YamlError:
                    fm = None
        if not isinstance(fm, dict):
            report.add(
                14,
                lesson.rel,
                f"the frontmatter is missing or does not parse, so the "
                f"provenance cannot be read. A generated lesson must declare "
                f"{', '.join(GENERATED_REQUIRED_FIELDS)} on top of the ordinary "
                f"lesson fields. See check 3 for the underlying error.",
            )
            continue

        for name in GENERATED_REQUIRED_FIELDS:
            if name not in fm:
                report.add(
                    14,
                    lesson.rel,
                    f"the provenance field {name!r} is missing. A lesson under "
                    f"{GENERATED_DIR}/ was written during a course, and the "
                    f"record of why, when and where it belongs is what makes it "
                    f"promotable later instead of unexplained.",
                )
            elif name != "generated" and (
                fm[name] is None
                or (isinstance(fm[name], str) and fm[name].strip() == "")
            ):
                report.add(
                    14, lesson.rel, f"the provenance field {name!r} is empty"
                )

        if "generated" in fm and fm["generated"] is not True:
            report.add(
                14,
                lesson.rel,
                f"generated is {fm['generated']!r}; a lesson in {GENERATED_DIR}/ "
                f"must declare 'generated: true'. Anything else says the file is "
                f"authored, and an authored lesson belongs in lessons/.",
            )

        kind = fm.get("kind")
        if "kind" in fm and kind not in GENERATED_KINDS:
            report.add(
                14,
                lesson.rel,
                f"kind is {kind!r}; it must be one of "
                f"{', '.join(GENERATED_KINDS)}. A side-lesson is a detour the "
                f"course never planned; a main-path-draft fills a chapter "
                f"COURSE.md maps and the bundle has no file for.",
            )

        after = fm.get("after")
        if after is None:
            continue  # already reported as missing or empty
        if not isinstance(after, str):
            report.add(
                15,
                lesson.rel,
                f"after must be the path of the lesson this one follows, not "
                f"{type(after).__name__}.",
            )
            continue
        if listed is None:
            continue
        checked_after += 1
        if after not in listed:
            report.add(
                15,
                lesson.rel,
                f"after names {after!r}, which is not an entry in tutorial.yaml's "
                f"'lessons' list. A generated lesson is placed by the main-path "
                f"lesson it follows, so 'after' must name an authored lesson - "
                f"not another generated one, and not a path that is merely on "
                f"disk.",
            )

    report.ran(14, f"{len(generated)} generated lessons")
    if listed is None:
        report.blocked(
            15, "tutorial.yaml has no usable 'lessons' list to resolve 'after' against"
        )
    else:
        report.ran(15, f"{checked_after} 'after' values against {len(listed)} lessons")


def check_manifest_lists_no_generated(manifest: Any, report: Report) -> None:
    """Check 16 - both modes.

    The manifest's `lessons` list is the authored course and is identical for
    every learner. Adding a generated lesson to it makes two learners' courses
    diverge structurally and stops a later bundle revision reconciling.
    """
    listed = as_list(manifest.get("lessons")) if isinstance(manifest, dict) else None
    if listed is None:
        report.blocked(16, "tutorial.yaml has no usable 'lessons' list")
        return
    for entry in listed:
        if not isinstance(entry, str):
            continue
        if entry == GENERATED_DIR or entry.startswith(GENERATED_DIR + "/"):
            report.add(
                16,
                "tutorial.yaml",
                f"the lessons entry {entry!r} names a generated lesson. The "
                f"'lessons' list is the authored course and is never mutated: a "
                f"generated lesson is a learner-specific overlay, found by "
                f"listing {GENERATED_DIR}/ and placed by its 'after' field. "
                f"Remove the entry. To make the lesson part of the course for "
                f"everyone, promote it into lessons/ first.",
            )
    report.ran(16, f"{len(listed)} entries")


def check_generated_resume(
    fm: dict | None,
    manifest: Any,
    generated: list[Lesson],
    optional_keys: set[str],
    report: Report,
) -> None:
    """Check 17 - instance mode.

    Only applies while the learner is OFF the main path: on a generated lesson,
    or on an optional one. Either way, a detour that does not record where it
    came from leaves the runner guessing which main-path lesson to resume, and
    guessing is what `resume_at` exists to prevent.

    `resume_at` names the lesson to MAKE ACTIVE when the detour finishes. It is
    deliberately NOT derived from, and NOT checked against, the generated
    lesson's `after:` field. The two answer different questions - `after:` is
    placement in the course, `resume_at` is the way back - and any assertion
    tying them together would reject the ordinary case: a detour taken
    part-way through a lesson places itself before that lesson and returns
    INTO it, so `resume_at` is then LATER in `lessons` than `after:`.

    The same is true of an optional lesson's `repair_in`, and for the same
    reason. `repair_in` is in the MANIFEST and is identical for every learner:
    it answers "whose work is now wrong". `resume_at` is in the INSTANCE and is
    written at the moment the detour starts: it answers "where does this
    learner stand". They differ whenever a failure surfaces later than the code
    that caused it - a learner who defers at lesson 04 and trips the failure
    while standing in lesson 06 returns to 06 and repairs what 04 built - which
    is the ordinary case for an anticipated failure, not an exotic one.
    """
    if fm is None:
        report.blocked(17, "STATE.md frontmatter is missing or did not parse")
        return
    active = fm.get("active_lesson")
    generated_rels = {lesson.rel for lesson in generated}
    listed = as_list(manifest.get("lessons")) if isinstance(manifest, dict) else None
    resume = fm.get("resume_at")
    off_path = isinstance(active, str) and (
        active in generated_rels or active in optional_keys
    )
    if not off_path:
        # `resume_at` is present EXACTLY while a detour is active. Left
        # behind after one finished, it points a cold session at a lesson the
        # learner has already been through, with nothing to say it is stale.
        if resume is not None:
            report.add(
                17,
                "STATE.md",
                f"resume_at is {resume!r}, but active_lesson "
                f"{active!r} is neither a lesson in {GENERATED_DIR}/ nor a key "
                f"in tutorial.yaml's '{OPTIONAL_KEY}' map. The field records "
                f"where an active detour returns to, so it belongs in STATE.md "
                f"only while the learner is off the main path. Remove it.",
            )
            report.ran(17, "active_lesson is a main-path lesson")
        else:
            report.na(17, "active_lesson is a main-path lesson")
        return
    kind = (
        "a generated lesson"
        if isinstance(active, str) and active in generated_rels
        else "an optional lesson"
    )
    if "resume_at" not in fm or resume is None:
        report.add(
            17,
            "STATE.md",
            f"active_lesson {active!r} is {kind}, so STATE.md must "
            f"also carry 'resume_at' naming the main-path lesson to make active "
            f"when the detour ends - the interrupted lesson when this detour "
            f"started part-way through one, otherwise the entry after the "
            f"lesson it followed.",
        )
    elif not isinstance(resume, str):
        report.add(
            17,
            "STATE.md",
            f"resume_at must be a lesson path, not {type(resume).__name__}.",
        )
    elif listed is not None and resume not in listed:
        report.add(
            17,
            "STATE.md",
            f"resume_at is {resume!r}, which is not an entry in "
            f"tutorial.yaml's 'lessons' list. The detour has to return to the "
            f"main path, so it must name an authored lesson.",
        )
    report.ran(17, f"active_lesson is {kind}")


# Supplies (check 22).
#
# `supplies:` is a bundle's way to hand the learner's workspace files it
# never assigns as a task: the runner places them and reports them. It is
# additive to bundle_format 1, declared either at the top of tutorial.yaml
# (placed after materialization) or in a lesson's frontmatter (placed when
# that lesson opens). `from` is always relative to the BUNDLE root, in both
# scopes - one rule, no scope-dependent resolution.
#
# TIMING is what makes the two scopes differ in what a `from` may REACH:
#
#   manifest scope is placed DURING materialization, while the bundle source
#     is still in reach, so its `from` may resolve anywhere in the bundle -
#     including a `supplies/` directory at the bundle root, which is where
#     both authoring references tell authors to put supplied files;
#   lesson scope is placed when that lesson OPENS, long after materialization,
#     from an instance that holds only tutorial.yaml, COURSE.md, DESIGN.md and
#     lessons/. A lesson-scope `from` outside lessons/ names a file that will
#     not exist when the tutor needs it, so it is a bundle defect in BOTH
#     modes.
#
# The same timing is why a manifest-scope `from` that does not resolve is a
# finding in BUNDLE mode only: the instance legitimately no longer carries it,
# because placement already happened.
SUPPLIES_KEYS = ("from", "to", "describe")
LESSONS_DIR = "lessons"


def _supplies_sites(
    root: Path, manifest: Any, lessons: list[Lesson]
) -> list[tuple[str, Any]]:
    """Every place a `supplies:` key is PRESENT, as (where, raw value).

    `where` is "tutorial.yaml" for the manifest, or a lesson's `rel`. The
    raw value is exactly what the manifest or frontmatter holds under
    `supplies` - a list when the author got the shape right, but possibly a
    bare string, a mapping or anything else a typo produces. It is
    deliberately NOT filtered to lists here: a key that is PRESENT but not a
    list is a malformed declaration, and a caller that only ever saw
    filtered-out sites would have no way to tell "nothing declared" from
    "declared badly" - which is exactly the defect check_supplies used to
    have (a `supplies:` typo silently validated as if there were no
    `supplies:` key at all). Only the ABSENCE of the key at every site means
    nothing was declared.

    Shared by collect_supplies (which keeps only the well-formed lists and
    mapping entries, for A2 and Part B) and check_supplies (which also has
    to report a site that is present but is not a list at all).

    `root` is accepted for interface symmetry with collect_supplies, whose
    exact signature A2 and Part B depend on; a lesson's own `path` is
    already absolute, so it is not needed to read lesson text.
    """
    del root
    sites: list[tuple[str, Any]] = []
    if isinstance(manifest, dict) and "supplies" in manifest:
        sites.append(("tutorial.yaml", manifest.get("supplies")))
    for lesson in lessons:
        text = read_text(lesson.path)
        if text is None:
            continue
        fm_text, _ = split_frontmatter(text)
        if fm_text is None:
            continue
        try:
            fm = load_yaml(fm_text, lesson.rel + " frontmatter")
        except YamlError:
            continue
        if not isinstance(fm, dict):
            continue
        if "supplies" in fm:
            sites.append((lesson.rel, fm.get("supplies")))
    return sites


def collect_supplies(
    root: Path, manifest: Any, lessons: list[Lesson]
) -> list[tuple[str, dict]]:
    """Every declared supplies entry, as (where, entry).

    `where` is "tutorial.yaml" for a manifest-scope entry, or the lesson's
    `rel` for a lesson-scope one. A site whose `supplies` value is not a
    list at all is skipped entirely here, and a mapping entry is the only
    kind returned; check_supplies is what reports either malformation - this
    function silently keeps only what is already well-formed enough to use.
    """
    out: list[tuple[str, dict]] = []
    for where, raw in _supplies_sites(root, manifest, lessons):
        if not isinstance(raw, list):
            continue
        out.extend((where, e) for e in raw if isinstance(e, dict))
    return out


def supplies_covers(entries: list[dict], bundle_rel: str) -> bool:
    """True when some entry's 'from' names `bundle_rel` or a directory
    holding it, matched on path boundaries rather than by substring: a
    `from` of 'model' does not cover 'model2/x.bin'."""
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        from_ = entry.get("from")
        if not isinstance(from_, str):
            continue
        stripped = from_.rstrip("/")
        if not stripped:
            continue
        if stripped == bundle_rel or bundle_rel.startswith(stripped + "/"):
            return True
    return False


def _supplies_to_error(to: Any) -> str | None:
    """Validate a supplies entry's 'to' as a PATH ONLY - never resolved.

    The learner's workspace does not exist at validation time, so calling
    resolve_exact() against it would be meaningless. This reuses
    resolve_exact's component rule (no '', '.', '..') without touching the
    filesystem.
    """
    if not isinstance(to, str) or to == "":
        return "a supplies entry's 'to' must be a non-empty path"
    if to == ".":
        return None  # '.' is the workspace root itself.
    if "\\" in to:
        return (
            f"the 'to' path {to!r} uses a backslash; use '/' in bundle paths"
        )
    if to.startswith("/"):
        return f"the 'to' path {to!r} must be relative to the workspace, not absolute"
    parts = to.split("/")
    for part in parts:
        if part in ("", ".", ".."):
            return f"path component {part!r} is not allowed"
    if parts[0].lower() == "tutorial":
        # Case-INSENSITIVE deliberately. macOS and Windows filesystems fold
        # case, so a `to` of 'Tutorial/x' lands inside the instance exactly as
        # 'tutorial/x' does; an exact-case test would pass the mis-cased form
        # and let a supplies entry write into the course. Check 4 takes exact
        # case seriously for the mirror-image reason.
        return (
            f"the 'to' path {to!r} begins with 'tutorial/'; 'tutorial/' is the "
            f"instance, not the learner's workspace, so a supplies entry must "
            f"not target it"
        )
    return None


def check_supplies(
    root: Path,
    manifest: Any,
    lessons: list[Lesson],
    listed_rels: set[str],
    report: Report,
) -> None:
    """Check 22 - both modes.

    Proves that declared supplies entries are well-formed and that every
    declared 'from' exists where the runner will look for it. It says
    nothing about whether the supplied files are the RIGHT files, and
    nothing about whether a lesson still tells the learner to copy them by
    hand - that judgement belongs to the course-quality audit, not this
    validator.

    The 'from' rule is scope-dependent because PLACEMENT TIME is:

      lesson scope  - the 'from' MUST resolve under lessons/, in BOTH modes.
        The lesson's entries are placed when the lesson opens, from the
        instance, and materialization copies only lessons/.
      manifest scope - the 'from' may resolve anywhere in the bundle, and a
        'from' that does not resolve is a finding in BUNDLE MODE ONLY.
        Placement happened during materialization, while the bundle source
        was still in reach; nothing copies the source into the instance, so
        an instance that no longer carries it is correct, not broken.

    A site's raw `supplies` value falls into three buckets, matching the
    precedent check 18 already sets for `optional_lessons`: nothing under
    the key (`None`) or an explicitly empty list is treated as "nothing
    declared here" and is silent, exactly like the key being absent
    altogether - a freshly scaffolded bundle, or the authoring toolkit
    rewriting `supplies: []` into block form on its first real entry, must
    not fail validation for carrying one. A value that is present and is
    NEITHER a list nor empty - a bare scalar, or the missing-'- ' mapping
    typo - is a finding: only a key that is absent or empty EVERYWHERE
    reports `n/a`.

    `lessons` is expected to include generated lessons (an instance's
    lessons.generated/ overlay): a generated lesson's supplies entries get
    every well-formedness check a listed lesson's do, and only the
    listed-in-'lessons'-or-'optional_lessons' rule is skipped for them,
    because a generated lesson is never listed there by design (check 16).
    """
    sites = _supplies_sites(root, manifest, lessons)

    malformed_sites: list[tuple[str, Any]] = []
    live_sites: list[tuple[str, list]] = []
    for where, raw in sites:
        if raw is None:
            continue  # 'supplies:' with nothing under it - nothing declared
        if isinstance(raw, list):
            if raw:
                live_sites.append((where, raw))
            # else: 'supplies: []' - present, valid, nothing declared
            continue
        malformed_sites.append((where, raw))

    if not malformed_sites and not live_sites:
        report.na(22, "no bundle declares supplies")
        return

    checked = 0
    for where, raw in malformed_sites:
        report.add(
            22,
            where,
            f"'supplies' must be a list of entries, not "
            f"{type(raw).__name__}. Each entry needs its own '- ' list "
            f"marker; a single mapping directly under 'supplies:' is "
            f"the common typo.",
        )
    for where, raw in live_sites:
        for entry in raw:
            checked += 1
            if not isinstance(entry, dict):
                report.add(
                    22,
                    where,
                    f"a supplies entry is not a mapping of 'from', 'to' and "
                    f"'describe', it is {type(entry).__name__}: {entry!r}",
                )
                continue

            extra = sorted(set(entry) - set(SUPPLIES_KEYS))
            for key in extra:
                report.add(
                    22,
                    where,
                    f"a supplies entry carries an unknown key {key!r}; only "
                    f"'from', 'to' and 'describe' are recognised",
                )

            missing = [k for k in SUPPLIES_KEYS if k not in entry]
            for key in missing:
                report.add(
                    22,
                    where,
                    f"a supplies entry is missing required key {key!r}",
                )

            if "describe" in entry:
                describe = entry.get("describe")
                if not _is_text(describe):
                    report.add(
                        22,
                        where,
                        "a supplies entry's 'describe' must be a non-empty "
                        "string naming what these files are, in the author's "
                        "words - it is the sentence the runner says to the "
                        "learner",
                    )
                elif "\n" in describe.strip() or "\r" in describe.strip():
                    # bundle-format.md puts "one non-empty LINE" in the MUST
                    # column, and the runner SPEAKS this string to the
                    # learner, so an embedded newline is a defect in
                    # learner-facing output, not a style preference.
                    #
                    # The test is on the STRIPPED value deliberately. A
                    # folded scalar ('describe: >') is the author writing one
                    # sentence across several source lines: yamlite folds it
                    # to a single line and leaves one trailing newline, which
                    # must NOT be a finding. A literal scalar ('describe: |')
                    # keeps its newlines INSIDE the value, which must.
                    report.add(
                        22,
                        where,
                        "a supplies entry's 'describe' must be ONE line: the "
                        "runner says it to the learner as a sentence, and an "
                        "embedded newline breaks that in the learner's "
                        "output. Use a folded scalar ('describe: >') to wrap "
                        "one sentence across source lines, or shorten it",
                    )

            if "from" in entry:
                from_ = entry.get("from")
                is_lesson_scope = where != "tutorial.yaml"
                if not isinstance(from_, str) or from_ == "":
                    report.add(
                        22,
                        where,
                        "a supplies entry's 'from' must be a non-empty path",
                    )
                elif from_.split("/", 1)[0] == GENERATED_DIR:
                    report.add(
                        22,
                        where,
                        f"the 'from' entry {from_!r} points inside "
                        f"'{GENERATED_DIR}/', which exists only in an "
                        f"instance and is never part of what a bundle ships",
                    )
                else:
                    has_trailing_slash = from_.endswith("/")
                    bare = from_.rstrip("/")
                    if not bare:
                        report.add(
                            22,
                            where,
                            f"the 'from' entry {from_!r} does not resolve: "
                            f"path component '' is not allowed",
                        )
                    elif (
                        is_lesson_scope
                        and bare.split("/", 1)[0] != LESSONS_DIR
                    ):
                        # A lesson's entries are placed when the lesson OPENS,
                        # from the instance - and materialization copies only
                        # tutorial.yaml, COURSE.md, DESIGN.md and lessons/. A
                        # lesson-scope 'from' outside lessons/ therefore names
                        # a file that will not be there at placement time, in
                        # both modes, whether or not the bundle still has it.
                        report.add(
                            22,
                            where,
                            f"the 'from' entry {from_!r} is declared by a "
                            f"lesson but does not resolve under "
                            f"'{LESSONS_DIR}/'. A lesson's supplies are placed "
                            f"when that lesson opens, from the instance, and "
                            f"materialization copies only '{LESSONS_DIR}/' - "
                            f"so this file will not exist when the tutor needs "
                            f"it. Move it anywhere under '{LESSONS_DIR}/', or declare "
                            f"it in tutorial.yaml, where placement happens "
                            f"while the bundle source is still in reach.",
                        )
                    else:
                        resolved, reason = resolve_exact(root, bare)
                        if resolved is None:
                            # A MANIFEST-scope 'from' is placed during
                            # materialization and nothing copies it into the
                            # instance, so an instance legitimately no longer
                            # carries it: reporting it there would call a
                            # correct bundle broken. In bundle mode the source
                            # is the thing being validated, so it must be
                            # there. A lesson-scope 'from' is under lessons/ by
                            # the branch above, which the instance does carry,
                            # so it must resolve in both modes.
                            if is_lesson_scope or report.mode != "instance":
                                report.add(
                                    22,
                                    where,
                                    f"the 'from' entry {from_!r} does not "
                                    f"resolve: {reason}",
                                )
                        else:
                            is_dir = resolved.is_dir()
                            if has_trailing_slash and not is_dir:
                                report.add(
                                    22,
                                    where,
                                    f"the 'from' entry {from_!r} names a "
                                    f"file, but a trailing '/' means a "
                                    f"directory; remove the '/', or declare "
                                    f"the entry as the directory it "
                                    f"actually is",
                                )
                            elif not has_trailing_slash and is_dir:
                                report.add(
                                    22,
                                    where,
                                    f"the 'from' entry {from_!r} names a "
                                    f"directory; a directory's 'from' must "
                                    f"end in '/'",
                                )

            if "to" in entry:
                to_error = _supplies_to_error(entry.get("to"))
                if to_error is not None:
                    report.add(22, where, to_error)

            is_generated = where.startswith(GENERATED_DIR + "/")
            if (
                where != "tutorial.yaml"
                and not is_generated
                and where not in listed_rels
            ):
                report.add(
                    22,
                    where,
                    f"{where} declares supplies, but this lesson is not "
                    f"listed in tutorial.yaml's 'lessons' or "
                    f"'optional_lessons', so it is not listed and is "
                    f"invisible to the runner",
                )

    total_sites = len(live_sites) + len(malformed_sites)
    entry_word = "entry" if checked == 1 else "entries"
    site_word = "site" if total_sites == 1 else "sites"
    detail = f"{checked} supplies {entry_word} across {total_sites} declaration {site_word}"
    if malformed_sites:
        malformed_word = "site" if len(malformed_sites) == 1 else "sites"
        detail += f" ({len(malformed_sites)} malformed {malformed_word})"
    report.ran(22, detail)


# Bundle relationships (checks 23, 24, 25).
#
# Four optional manifest keys let a bundle say what it TEACHES, what it
# ASSUMES, and which other bundles it recommends before and after itself.
# They are additive to bundle_format 1: a manifest declaring none of them is
# valid exactly as it stands.
#
# ONE RULE SHAPES EVERY DECISION BELOW:
#
#   Named bundles are recommendations. Concepts are the educational
#   contract. Neither one gates access to a tutorial or requires proof that
#   another bundle was completed.
#
# Two consequences are easy to get backwards, and both are deliberate:
#
#   A concept in BOTH `covers` and `assumes` is LEGAL. A course may assume a
#     baseline and then teach it deeper, and saying so is more honest than
#     picking one key.
#   An UNRESOLVED bundle id is LEGAL. A bundle is distributed independently
#     and must never be invalidated because another bundle is missing,
#     unpublished or simply not installed here - that is the whole point.
#     This validator sees one bundle and no catalogue, so it checks that a
#     referenced id is WELL FORMED and says nothing whatever about whether
#     it resolves. See LIMITATIONS.
CONCEPT_KEYS: dict[str, tuple[str, ...]] = {
    # key -> the keys one concept's body may carry
    "covers": ("summary", "aliases"),
    "assumes": ("level", "summary", "aliases"),
}
CONCEPT_REQUIRED: dict[str, tuple[str, ...]] = {
    "covers": ("summary",),
    "assumes": ("level", "summary"),
}
ASSUMES_LEVELS = ("awareness", "conceptual", "working", "advanced")
RECOMMENDATION_KEYS = ("recommended_follow_ups", "recommended_previous_bundles")
RECOMMENDATION_ENTRY_KEYS = ("bundle", "because")
_CONCEPT_ID_RE = re.compile(r"[a-z0-9-]+")
# Alias normalisation. Every run of non-alphanumeric text is one separator and
# case never distinguishes two aliases, so `append-only-log`, `append_only_log`
# and `Append Only Log` are one alias written three ways, and declaring two of
# them is a duplicate rather than a pair.
#
# THIS MUST STAY IDENTICAL TO catalogs.normalise(). That function is what a
# RUNTIME concept query folds a learner's words with, and this one is what
# tells an author at authoring time what the runtime will do; two definitions
# of "the same alias" would make the validator pass a pair the index then
# silently merges. The agreement is pinned by a test, because a comment
# cannot notice when one of them changes.
#
# Folding punctuation to a separator is the right rule rather than merely the
# compatible one: a concept id is [a-z0-9-]+, so punctuation cannot appear in
# one at all, and an alias exists to be matched against an id. It also makes
# `node.js` and `nodejs` one alias, which is what a learner typing either
# means.
_ALIAS_WORD_RE = re.compile(r"[a-z0-9]+")
# Prose normalisation, for check 25 only. EVERY run of non-alphanumeric text
# becomes one separator, so a concept id can be matched against a sentence
# that ends in a comma or a full stop.
_PROSE_SEPARATOR_RE = re.compile(r"[^a-z0-9]+")


def normalise_alias(text: str) -> str:
    """The comparable form of one alias or concept id.

    Returns "" for a string with no alphanumeric content at all, which is an
    alias that cannot match anything and is reported rather than compared.
    """
    return "-".join(_ALIAS_WORD_RE.findall(str(text).lower()))


def concept_aliases(body: Any) -> list[str]:
    """The well-formed alias strings of one concept body, as written.

    Anything malformed - a non-list `aliases`, a non-string entry, an entry
    with no content - is skipped here and reported by check 23. Callers that
    only need the aliases that can actually match something use this;
    check 23 walks the raw list itself, because it has to report what this
    one drops.
    """
    if not isinstance(body, dict):
        return []
    raw = body.get("aliases")
    if not isinstance(raw, list):
        return []
    return [a for a in raw if isinstance(a, str) and normalise_alias(a)]


def concept_declarations(manifest: Any) -> dict[str, dict[str, Any]]:
    """The concept mappings under `covers` and `assumes`, ids stringified.

    A key whose value is not a mapping contributes nothing: it is malformed,
    check 23 reports it, and every other caller would only propagate the
    malformation. Concept BODIES are returned raw, because check 23 has to
    report a body that is not a mapping and check 25 has to skip one.
    """
    out: dict[str, dict[str, Any]] = {}
    if not isinstance(manifest, dict):
        return out
    for key in CONCEPT_KEYS:
        raw = manifest.get(key)
        if isinstance(raw, dict) and raw:
            out[key] = {str(k): v for k, v in raw.items()}
    return out


def check_concepts(manifest: Any, report: Report) -> None:
    """Check 23 - both modes.

    Proves that `covers` and `assumes` are well-formed: every concept id
    matches [a-z0-9-]+, every concept carries a non-empty summary, every
    assumed concept declares one of the four known levels, and every alias
    list is a list of distinct non-empty strings.

    It says NOTHING about whether the bundle really teaches what `covers`
    claims, whether a summary is specific enough for a learner to
    self-assess against, or whether a level is honestly chosen. Those are
    judgement, and this validator makes none. Check 25 is the one
    conservative textual test available, and it only ever warns.

    An ABSENT key, a key with nothing under it, and an explicitly empty
    mapping are all silent and all report n/a - the same treatment
    `optional_lessons` and `supplies` already get, for the same reason: a
    scaffolded bundle, or one an authoring tool is part-way through editing,
    carries an empty declaration legitimately. A key that is PRESENT and is
    neither a mapping nor empty is always a finding.
    """
    live: dict[str, dict[str, Any]] = {}
    malformed: list[tuple[str, Any]] = []
    for key in CONCEPT_KEYS:
        if not isinstance(manifest, dict) or key not in manifest:
            continue
        raw = manifest.get(key)
        if raw is None:
            continue  # 'covers:' with nothing under it - nothing declared
        if isinstance(raw, dict):
            if raw:
                live[key] = {str(k): v for k, v in raw.items()}
            # else: 'covers: {}' - present, valid, nothing declared
            continue
        malformed.append((key, raw))

    if not live and not malformed:
        report.na(23, "the bundle declares no covers or assumes concepts")
        return

    for key, raw in malformed:
        report.add(
            23,
            f"tutorial.yaml ({key})",
            f"'{key}' must be a mapping of concept id to its definition, not "
            f"{type(raw).__name__}. Each concept is a key with its own "
            f"'summary' underneath; a bare list of concept ids is the "
            f"common mistake, and it loses the summaries that make a "
            f"concept mean something to a learner.",
        )

    counted = 0
    for key in CONCEPT_KEYS:
        for cid, body in live.get(key, {}).items():
            counted += 1
            where = f"tutorial.yaml ({key}.{cid})"

            if not _CONCEPT_ID_RE.fullmatch(cid):
                report.add(
                    23,
                    where,
                    f"concept id {cid!r} must match [a-z0-9-]+ - lowercase "
                    f"letters, digits and hyphens only. A concept id names a "
                    f"technical concept and is quoted by other authors' "
                    f"bundles, so it is spelled the way an id is, not the "
                    f"way a heading is.",
                )

            if not isinstance(body, dict):
                report.add(
                    23,
                    where,
                    f"a concept must be a mapping of "
                    f"{', '.join(repr(k) for k in CONCEPT_KEYS[key])}, not "
                    f"{type(body).__name__}: {body!r}. A concept id on its "
                    f"own says nothing a learner or another bundle can use.",
                )
                continue

            for extra in sorted(set(body) - set(CONCEPT_KEYS[key])):
                if key == "covers" and extra == "level":
                    detail = (
                        "'level' says how well a learner must ALREADY know a "
                        "concept, which is an 'assumes' question. A course "
                        "teaches what it covers; there is no level to declare."
                    )
                else:
                    detail = (
                        f"only "
                        f"{', '.join(repr(k) for k in CONCEPT_KEYS[key])} "
                        f"are recognised here"
                    )
                report.add(
                    23,
                    where,
                    f"the concept carries an unknown key {extra!r}; {detail}",
                )

            for missing in CONCEPT_REQUIRED[key]:
                if missing not in body:
                    report.add(
                        23,
                        where,
                        f"the concept is missing required key {missing!r}",
                    )

            if "summary" in body and not _is_text(body.get("summary")):
                report.add(
                    23,
                    where,
                    f"'summary' must be a non-empty description of the "
                    f"concept, not {body.get('summary')!r}. It is written "
                    f"for a prospective learner deciding whether this course "
                    f"is for them, so the concept id alone is not enough.",
                )

            if key == "assumes" and "level" in body:
                level = body.get("level")
                if level not in ASSUMES_LEVELS:
                    report.add(
                        23,
                        where,
                        f"level {level!r} is not one of "
                        f"{', '.join(ASSUMES_LEVELS)}",
                    )

            _check_alias_list(key, cid, body, report)

    _warn_about_alias_collisions(live, report)

    word = "concept" if counted == 1 else "concepts"
    parts = [f"{len(live.get(k, {}))} {k}" for k in CONCEPT_KEYS if k in live]
    detail = f"{counted} {word}"
    if parts:
        detail += " (" + ", ".join(parts) + ")"
    if malformed:
        malformed_word = "key" if len(malformed) == 1 else "keys"
        detail += f", {len(malformed)} malformed {malformed_word}"
    report.ran(23, detail)


def _check_alias_list(key: str, cid: str, body: dict, report: Report) -> None:
    """The `aliases` half of check 23, for one concept."""
    if "aliases" not in body:
        return
    where = f"tutorial.yaml ({key}.{cid})"
    raw = body.get("aliases")
    if raw is None or raw == []:
        # 'aliases:' with nothing under it, and 'aliases: []', both declare
        # nothing and mean what the absent key means.
        return
    if not isinstance(raw, list):
        report.add(
            23,
            where,
            f"'aliases' must be a list of the other terms a learner might "
            f"say for this concept, not {type(raw).__name__}. One alias is "
            f"still a list: 'aliases: [replayable-log]'.",
        )
        return
    seen: dict[str, str] = {}
    for alias in raw:
        if not isinstance(alias, str):
            report.add(
                23,
                where,
                f"alias {alias!r} is {type(alias).__name__}, not a string",
            )
            continue
        normalised = normalise_alias(alias)
        if not normalised:
            report.add(
                23,
                where,
                f"alias {alias!r} has no searchable content, so nothing a "
                f"learner types can ever match it",
            )
            continue
        if normalised in seen:
            report.add(
                23,
                where,
                f"aliases {seen[normalised]!r} and {alias!r} are the same "
                f"alias written twice: case, spaces, underscores and hyphens "
                f"do not distinguish two aliases, and both normalise to "
                f"{normalised!r}",
            )
            continue
        seen[normalised] = alias


def _warn_about_alias_collisions(
    live: dict[str, dict[str, Any]], report: Report
) -> None:
    """The two alias-ambiguity WARNINGS of check 23.

    Neither is an error. An alias is discovery metadata: a collision makes a
    search result ambiguous, it does not make the bundle wrong, and two
    bundles by different authors are expressly allowed to share aliases.
    Within ONE bundle, though, both shapes below make an exact-alias match
    point at two different concepts, which is worth telling the author.
    """
    ids: dict[str, str] = {}
    for key in CONCEPT_KEYS:
        for cid in live.get(key, {}):
            ids.setdefault(normalise_alias(cid), cid)

    owners: dict[str, list[tuple[str, str, str]]] = {}
    for key in CONCEPT_KEYS:
        for cid, body in live.get(key, {}).items():
            for alias in concept_aliases(body):
                owners.setdefault(normalise_alias(alias), []).append(
                    (key, cid, alias)
                )

    for normalised, holders in sorted(owners.items()):
        # An alias that is ALSO a concept id in this bundle. Its own id does
        # not count: `covers` and `assumes` may legally name one concept, so
        # the comparison is by concept id, never by which key declared it.
        other = ids.get(normalised)
        for key, cid, alias in holders:
            if other is not None and other != cid:
                report.warn(
                    23,
                    f"tutorial.yaml ({key}.{cid})",
                    f"alias {alias!r} is also the concept id {other!r} "
                    f"declared by this bundle, so an exact search for it "
                    f"matches two different concepts. This is legal and the "
                    f"bundle is valid; rename the alias if the two are not "
                    f"the same idea.",
                )

        distinct = sorted({cid for _, cid, _ in holders})
        if len(distinct) > 1:
            # Once per HOLDER, not once for the alias. An author reading the
            # report is looking at one concept's declaration and needs the
            # note there; a single warning attached to whichever concept
            # happened to be declared first sends them to the wrong place.
            for key, cid, alias in holders:
                report.warn(
                    23,
                    f"tutorial.yaml ({key}.{cid})",
                    f"alias {alias!r} is declared by more than one concept "
                    f"in this bundle ({', '.join(distinct)}), so an exact "
                    f"search for it cannot choose between them. This is "
                    f"legal and the bundle is valid; give each concept an "
                    f"alias only it uses.",
                )


def check_recommendations(manifest: Any, report: Report) -> None:
    """Check 24 - both modes.

    Proves that `recommended_follow_ups` and `recommended_previous_bundles`
    are well-formed: a list of mappings, each naming one well-formed bundle
    id and saying why, with no duplicate and no entry naming this bundle.

    It deliberately says NOTHING about whether a referenced bundle exists.
    A recommendation is advisory, a bundle is distributed independently, and
    failing one because another is missing, unpublished, or simply not
    installed on this machine would defeat the whole design. An unresolved
    id is CORRECT, not tolerated. Availability is a question for a catalogue,
    which this mode does not have - see LIMITATIONS.

    Reciprocity is neither required nor reported: a third-party bundle
    naming an established one under `recommended_previous_bundles` is how it
    attaches itself to that course WITHOUT the other author changing
    anything, and one-way is the ordinary case.
    """
    live: list[tuple[str, list]] = []
    malformed: list[tuple[str, Any]] = []
    for key in RECOMMENDATION_KEYS:
        if not isinstance(manifest, dict) or key not in manifest:
            continue
        raw = manifest.get(key)
        if raw is None:
            continue  # the key with nothing under it - nothing declared
        if isinstance(raw, list):
            if raw:
                live.append((key, raw))
            continue
        malformed.append((key, raw))

    if not live and not malformed:
        report.na(24, "the bundle recommends no other bundles")
        return

    for key, raw in malformed:
        report.add(
            24,
            f"tutorial.yaml ({key})",
            f"'{key}' must be a list of entries, not {type(raw).__name__}. "
            f"Each entry needs its own '- ' list marker; a single mapping "
            f"written directly under the key is the common typo.",
        )

    bundle_id = manifest.get("id") if isinstance(manifest, dict) else None
    counted = 0
    named: dict[str, list[str]] = {}
    for key, raw in live:
        seen: dict[str, int] = {}
        for index, entry in enumerate(raw):
            counted += 1
            where = f"tutorial.yaml ({key}[{index}])"
            if not isinstance(entry, dict):
                report.add(
                    24,
                    where,
                    f"a recommendation is not a mapping of 'bundle' and "
                    f"'because', it is {type(entry).__name__}: {entry!r}. A "
                    f"bare bundle id is the common mistake, and it drops the "
                    f"one sentence the learner actually reads.",
                )
                continue

            for extra in sorted(set(entry) - set(RECOMMENDATION_ENTRY_KEYS)):
                report.add(
                    24,
                    where,
                    f"a recommendation carries an unknown key {extra!r}; only "
                    f"'bundle' and 'because' are recognised. This format has "
                    f"no field that requires, installs, orders or gates "
                    f"another bundle, by any spelling.",
                )

            for missing in RECOMMENDATION_ENTRY_KEYS:
                if missing not in entry:
                    report.add(
                        24,
                        where,
                        f"a recommendation is missing required key {missing!r}",
                    )

            if "because" in entry and not _is_text(entry.get("because")):
                report.add(
                    24,
                    where,
                    f"'because' must be a non-empty sentence saying what the "
                    f"other bundle gives this learner, not "
                    f"{entry.get('because')!r}. The runner shows it beside "
                    f"the recommendation, and a learner choosing what to do "
                    f"next has nothing else to go on.",
                )

            if "bundle" not in entry:
                continue
            other = entry.get("bundle")
            if not _is_text(other):
                report.add(
                    24,
                    where,
                    f"'bundle' must be a non-empty bundle id, not {other!r}",
                )
                continue
            if not _CONCEPT_ID_RE.fullmatch(other):
                report.add(
                    24,
                    where,
                    f"bundle id {other!r} must match [a-z0-9-]+ - lowercase "
                    f"letters, digits and hyphens only, exactly as that "
                    f"bundle's own 'id' field is spelled. A title, a path or "
                    f"a URL is not a bundle id.",
                )
                continue
            if isinstance(bundle_id, str) and other == bundle_id:
                report.add(
                    24,
                    where,
                    f"the bundle recommends itself ({other!r}). A "
                    f"recommendation points a learner at a DIFFERENT course, "
                    f"before or after this one.",
                )
                continue
            if other in seen:
                report.add(
                    24,
                    where,
                    f"bundle {other!r} is listed twice in '{key}' (also at "
                    f"index {seen[other]}). Author order is display order, so "
                    f"a duplicate shows the learner one course twice; give "
                    f"the better reason once.",
                )
                continue
            seen[other] = index
            named.setdefault(other, []).append(key)

    # A WARNING, not a finding: naming one bundle as both a follow-up and a
    # previous bundle is contradictory, but it is a contradiction about
    # DISPLAY ORDER rather than about correctness, and nothing a runner does
    # with it is unsafe. The learner sees one course recommended twice, in
    # two places, for two reasons.
    for other, keys in sorted(named.items()):
        if len(set(keys)) > 1:
            report.warn(
                24,
                "tutorial.yaml",
                f"bundle {other!r} is recommended both as a follow-up and as "
                f"a previous bundle. Both are advisory and the bundle is "
                f"valid, but a learner is being told to take one course both "
                f"before and after this one; keep the recommendation that is "
                f"true.",
            )

    word = "recommendation" if counted == 1 else "recommendations"
    detail = f"{counted} {word} across {len(live)} list"
    if len(live) != 1:
        detail += "s"
    if malformed:
        malformed_word = "key" if len(malformed) == 1 else "keys"
        detail += f", {len(malformed)} malformed {malformed_word}"
    report.ran(24, detail)


def concept_spellings(cid: str, aliases: list[str]) -> list[str]:
    """Every normalised spelling check 25 will accept for one concept.

    The id, each alias, and a singular/plural variant of each - `-s` added
    to the last word and, where it ends in one, removed. That last pair is
    what stops a coverage list reading "partition offset" from being
    reported for a concept id of `partition-offsets`.

    Deliberately generous. A false warning about a course whose COURSE.md is
    perfectly good is worse than a missed one: the author learns to skip the
    warnings, and then misses the real case.
    """
    out: list[str] = []
    for term in [cid, *aliases]:
        base = normalise_alias(term)
        if not base:
            continue
        for variant in (base, base + "s", base[:-1] if base.endswith("s") else base):
            if variant and variant not in out:
                out.append(variant)
    return out


def check_course_coverage(root: Path, manifest: Any, report: Report) -> None:
    """Check 25 - both modes. WARNINGS ONLY; it never produces a finding.

    A `covers` concept should also be recognisable in COURSE.md, which is
    where a learner reads what the course teaches and where the coverage
    list tells a tutor what the course owes them. A concept claimed in the
    manifest and named nowhere in COURSE.md is usually one of two ordinary
    authoring mistakes: a coverage list that was never updated, or a concept
    id spelled in a vocabulary the course itself does not use.

    THE TEST IS TEXTUAL AND CONSERVATIVE ON PURPOSE, and its limits are the
    point of it:

      It searches the WHOLE of COURSE.md, not the coverage list alone. The
        coverage list has no fixed heading - the format asks only for a
        heading that says what it is - so locating it would mean guessing,
        and a guess that missed would warn about a concept that is listed.
      It accepts the concept id, any alias, and a singular/plural variant of
        each, compared with punctuation and case removed. A course that says
        "retained event logs" satisfies a concept id of
        `retained-event-logs`.
      It proves NOTHING about teaching. A course can name a concept in one
        sentence and never teach it; this check would be satisfied and the
        course would be wrong. It is evidence that the author has used the
        same vocabulary in both places, and nothing more.

    That is why it warns rather than rejects. Semantic proof of coverage is
    not available to a structural validator, the spec forbids attempting it,
    and a check that failed a correct bundle on a vocabulary difference
    would be ignored within a week.
    """
    covers = {
        cid: body
        for cid, body in concept_declarations(manifest).get("covers", {}).items()
        if isinstance(body, dict)
    }
    if not covers:
        report.na(25, "the bundle declares no covers concepts")
        return
    resolved, _ = resolve_exact(root, "COURSE.md")
    text = read_text(resolved) if resolved is not None else None
    if text is None:
        report.na(
            25, "COURSE.md is missing or unreadable; check 9 reports that"
        )
        return

    haystack = "-" + _PROSE_SEPARATOR_RE.sub("-", text.casefold()).strip("-") + "-"
    unmatched = 0
    for cid, body in sorted(covers.items()):
        spellings = concept_spellings(cid, concept_aliases(body))
        if any(f"-{spelling}-" in haystack for spelling in spellings):
            continue
        unmatched += 1
        report.warn(
            25,
            "COURSE.md",
            f"the covers concept {cid!r} appears nowhere in COURSE.md - not "
            f"as its id, not as a plain-words spelling of it, and not as any "
            f"of its aliases. The bundle is valid. Either name it in the "
            f"coverage list, or add the words COURSE.md already uses for it "
            f"to that concept's 'aliases', so a learner searching either "
            f"vocabulary finds this course.",
        )

    word = "concept" if len(covers) == 1 else "concepts"
    detail = f"{len(covers)} covers {word}"
    if unmatched:
        detail += f", {unmatched} not found in COURSE.md"
    report.ran(25, detail)


# --------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------


def validate(target: Path, mode: str) -> Report:
    report = Report(mode=mode, target=target)

    manifest: Any = None
    manifest_error: str | None = None
    entries = list_dir(target)
    if "tutorial.yaml" not in entries:
        near = [e for e in entries if e.lower() == "tutorial.yaml"]
        manifest_error = (
            f"the file is named {near[0]!r}; the name must match exactly"
            if near
            else "the file is required and is missing"
        )
        report.add(8, "tutorial.yaml", manifest_error)
    else:
        raw = read_text(target / "tutorial.yaml")
        if raw is None:
            manifest_error = "the file could not be read as UTF-8 text"
            report.add(8, "tutorial.yaml", manifest_error)
        else:
            try:
                manifest = load_yaml(raw, "tutorial.yaml")
            except YamlError as exc:
                manifest = None
                manifest_error = str(exc)
                report.add(8, "tutorial.yaml", f"the file does not parse: {exc}")
            else:
                if not isinstance(manifest, dict):
                    report.add(
                        8,
                        "tutorial.yaml",
                        f"the manifest must be a mapping of field to value, not "
                        f"{type(manifest).__name__}",
                    )
                    manifest_error = "the manifest is not a mapping"
                    manifest = None

    manifest_dict: dict = manifest if isinstance(manifest, dict) else {}

    # DESIGN.md anchors (check 1 input)
    anchors: set[str] | None = None
    if "DESIGN.md" in entries:
        design_text = read_text(target / "DESIGN.md")
        if design_text is not None:
            anchors = set(_ANCHOR_RE.findall(design_text))

    # declared validators (check 2 input)
    declared: set[str] | None = None
    raw_validators = manifest_dict.get("validators", "\0missing")
    if isinstance(raw_validators, dict):
        declared = {str(k) for k in raw_validators}
    elif raw_validators is None:
        declared = set()  # 'validators:' with nothing under it is an empty map

    lessons, lessons_dir_exists = discover_lessons(target, report)

    # Generated lessons. They exist only in an instance; in bundle mode check
    # 13 reports the directory instead of walking it, so that a bundle carrying
    # one produces ONE clear finding rather than a shower of derived ones.
    generated_exact, generated_near = generated_dir_state(target)
    generated: list[Lesson] = []
    if mode == "instance" and generated_exact:
        generated, _ = discover_lessons(target, report, GENERATED_DIR)

    check_state_files(target, mode, manifest, report)
    if manifest_error is not None and manifest is None:
        report.blocked(8, f"tutorial.yaml is unusable: {manifest_error}")
    else:
        check_manifest(manifest, report)
    check_required_files(target, manifest_dict, report)
    check_workspace_and_ownership(manifest if manifest is not None else None, report)
    # Optional lessons are reachable through `optional_lessons` rather than
    # through `lessons`, so check 4 needs the keys before it can decide what is
    # unlisted. A malformed map yields an empty set here and is reported by
    # check 18 alone.
    optional_keys = optional_lesson_keys(manifest_dict)
    lessons = check_lesson_list(
        target, manifest_dict, lessons_dir_exists, lessons, optional_keys, report
    )
    check_optional_lessons(target, manifest_dict, lessons, report)
    check_failure_modes(
        manifest_dict, declared, anticipated_failure_modes(manifest_dict), report
    )
    # Checks 1, 2, 3 and 6 apply to a generated lesson exactly as they do to an
    # authored one: it is an ordinary lesson with extra frontmatter.
    all_lessons = lessons + generated
    check_optional_frontmatter(
        all_lessons, optional_keys, as_list(manifest_dict.get("lessons")), report
    )
    check_unique_slugs(all_lessons, report)
    check_lesson_frontmatter(all_lessons, anchors, declared, report)
    check_progress_markers(
        target,
        report,
        ("lessons", GENERATED_DIR) if mode == "instance" else ("lessons",),
    )
    check_material_reachable(target, manifest_dict, all_lessons, report)
    check_manifest_lists_no_generated(manifest_dict, report)
    # A lesson-scope supplies entry is legible only if its lesson is
    # reachable at all - through 'lessons' or 'optional_lessons', the same
    # two lists check 4 accepts. check_supplies runs over all_lessons (so a
    # generated lesson's own supplies entries get every well-formedness
    # check too) and skips the listed-ness rule ITSELF for a generated
    # lesson, since one is reachable by neither list by design (check 16).
    listed_raw = as_list(manifest_dict.get("lessons"))
    listed_rels = (
        {entry for entry in listed_raw if isinstance(entry, str)}
        if listed_raw is not None
        else set()
    ) | optional_keys
    check_supplies(target, manifest_dict, all_lessons, listed_rels, report)
    # Relationship metadata. All three run in BOTH modes: the four keys are
    # copied into the instance with the rest of tutorial.yaml, and a runner
    # reads `assumes` before the first task and the recommendation lists at
    # completion, so an instance carrying a malformed one is as broken as a
    # bundle carrying it.
    check_concepts(manifest_dict, report)
    check_recommendations(manifest_dict, report)
    check_course_coverage(target, manifest_dict, report)
    if mode == "bundle":
        check_no_generated_dir(target, report)
        template_fm = check_state_template(target, manifest_dict, report)
        check_template_assumes_reviewed(template_fm, report)
    else:
        check_generated_lessons(
            target, manifest_dict, generated, generated_exact, generated_near, report
        )
        state_fm = check_instance_state(
            target, manifest_dict, generated, optional_keys, report
        )
        check_generated_resume(
            state_fm, manifest_dict, generated, optional_keys, report
        )
        check_optional_state(target, optional_keys, state_fm, report)

    return report


# --------------------------------------------------------------------------
# Catalogue mode
# --------------------------------------------------------------------------
#
# A catalogue is not a bundle, so it gets its own numbering rather than a
# shared table in which most numbers never apply. The mode is explicit on the
# command line for the same reason bundle and instance are: a validator that
# guesses which kind of document it was handed cannot fail on a document of
# the wrong kind.

CATALOG_CHECKS: dict[int, str] = {
    1: "the file parses, is a mapping, and catalog_version is known",
    2: "tutorials is a non-empty list of mappings",
    3: "every entry carries the required fields, with the right shapes; "
    "an unrecognised field WARNS",
    4: "every id is unique in the file and matches [a-z0-9-]+",
    5: "every source names a known, implemented type with its required fields",
    6: "every bundle path resolves to a directory holding tutorial.yaml and "
    "STATE.template.md",
    7: "[--portable] no bundle path leaves the catalogue's own directory",
}

CATALOG_REQUIRED_FIELDS = (
    "id",
    "title",
    "description",
    "subjects",
    "level",
    "workspace_kind",
    "source",
)
CATALOG_LIST_FIELDS = ("subjects", "aliases", "style")
CATALOG_TEXT_FIELDS = ("title", "description", "level", "scope", "workspace_kind")
# Optional, and a whole number. `scope` counts the main path only, so this is
# the entry's only way to say that a course carries lessons beside it. The
# runner may not count them: discovery reads metadata and never opens a
# bundle. Named for the count it holds, and NOT `optional_lessons`, which is
# a mapping of lesson path to offer metadata in a bundle's tutorial.yaml.
CATALOG_COUNT_FIELDS = ("optional_lesson_count",)
# Every entry field catalogue-format.md section 5 defines, required and
# optional together. Check 3 WARNS about a key that is not in here.
#
# This is a list of FIELD NAMES, and it is matched against the keys of the
# PARSED entry mapping. It never searches the catalogue's text, and that is
# not a style preference - see the docstring on unknown_entry_fields().
CATALOG_KNOWN_ENTRY_FIELDS = (
    "aliases",
    "assumes",
    "covers",
    "description",
    "id",
    "level",
    "optional_lesson_count",
    "recommended_follow_ups",
    "recommended_previous_bundles",
    "scope",
    "source",
    "style",
    "subjects",
    "title",
    "workspace_kind",
)
# How far from a known field a key may be and still be called a near miss.
#
# Two, because plain Levenshtein scores a transposed pair of characters as
# two edits and a transposition is the commonest typo there is. A shorter
# field gets one: at two edits from `id` sits most of the two-character
# strings there are, and a suggestion that fits everything says nothing.
CATALOG_NEAR_MISS_DISTANCE = 2
CATALOG_NEAR_MISS_SHORT_FIELD = 5

CATALOG_ENTRY_SOURCE_TYPES = ("local", "git", "archive")
CATALOG_ENTRY_SOURCE_IMPLEMENTED = ("local",)
KNOWN_CATALOG_VERSIONS = (1,)

CATALOG_LIMITATIONS = """What a pass does and does not mean
  Green means "a runner can read this catalogue and act on every entry". It
  says nothing about whether the metadata is TRUE: a description that
  misrepresents the course, subjects that do not match what the bundle
  teaches, a `scope` that under-states the work, or an
  `optional_lesson_count` that disagrees with the bundle's own
  `optional_lessons` all pass. The count is checked for shape only; nothing
  here opens a bundle to recount it.

  Check 6 opens each bundle's directory, which discovery deliberately never
  does. That is why this is an authoring-time tool: it is allowed to look,
  and the runner is not.

  Check 6 proves only that the directory holds tutorial.yaml and
  STATE.template.md. Run validate_bundle.py <path> on the bundle itself to
  learn whether the bundle is well-formed.

  Check 7 runs only with --portable, because a user's own catalogue
  legitimately names bundles anywhere on their machine. Use --portable for a
  catalog.yaml that ships inside a bundles repository, where every bundle
  must travel with the catalogue.

  Check 3 reports an unrecognised entry field as a WARNING and never as a
  finding, so the catalogue still passes with one. That is deliberate: a
  catalogue is data a newer runner may extend, and an older reader must
  degrade rather than refuse - bundle-format.md section 13, applied to the
  catalogue. So the warning is the only report you will get about a
  misspelled field, and it is worth reading: a runner ignores a field name
  it does not know, so a misspelling costs the entry that field silently and
  the course then advertises nothing by it.

  That part of check 3 reads the KEYS of each parsed entry. A field name
  written in a comment, or inside a description, is not a key and is never
  reported - a generated catalogue names `optional_lesson_count` in its
  header comment, and that comment is not a field.

  Nothing here checks a catalogue entry against the bundle's own
  tutorial.yaml. The two are allowed to differ - the bundle is authoritative
  once resolved - and reporting every difference would reject valid
  catalogues whose entries are deliberately shorter."""


def _edit_distance(left: str, right: str) -> int:
    """Levenshtein distance, iterative, two rows.

    Plain Levenshtein and not Damerau-Levenshtein: a transposition costs two
    here, which CATALOG_NEAR_MISS_DISTANCE is set to accept. Adding the
    transposition case would let the threshold drop to one, and one edit
    from a five-character field is a large neighbourhood - `level` would
    then suggest itself for `levels`, `lever` and `bevel` alike.
    """
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)
    previous = list(range(len(right) + 1))
    for i, a in enumerate(left, start=1):
        current = [i]
        for j, b in enumerate(right, start=1):
            current.append(
                min(
                    previous[j] + 1,  # delete
                    current[j - 1] + 1,  # insert
                    previous[j - 1] + (a != b),  # substitute
                )
            )
        previous = current
    return previous[-1]


def near_misses(name: str, known: tuple[str, ...]) -> list[str]:
    """The known fields `name` is closest to, or [] when it is close to none.

    Returns every field at the SMALLEST qualifying distance rather than one
    arbitrary winner: a tie means the evidence does not pick between them,
    and naming one would be a guess presented as a suggestion.
    """
    best: list[str] = []
    best_distance = CATALOG_NEAR_MISS_DISTANCE + 1
    for candidate in known:
        budget = (
            1
            if len(candidate) < CATALOG_NEAR_MISS_SHORT_FIELD
            else CATALOG_NEAR_MISS_DISTANCE
        )
        distance = _edit_distance(name, candidate)
        if distance > budget:
            continue
        if distance < best_distance:
            best_distance, best = distance, [candidate]
        elif distance == best_distance:
            best.append(candidate)
    return sorted(best)


def unknown_entry_fields(entry: dict) -> list[str]:
    """The keys of one parsed catalogue entry that section 5 does not define.

    READ THE KEYS OF THE PARSED MAPPING. Never search the catalogue's text
    for a field name, and this is the constraint the whole check is built
    around rather than an implementation detail.

    A catalogue carries comments, and this project's own generator writes a
    header comment that NAMES `optional_lesson_count` into every catalogue
    it produces. A text search therefore counts that comment as though it
    were a field. The arithmetic is worse than one miscount: the loose
    count is (entries carrying the field) + 1 for the comment, so it equals
    the entry count EXACTLY when precisely one entry is missing the field -
    the single case such a check exists to catch is the single case it
    passes. Measured on the real catalogue in skomp/tutorail-bundles,
    which has 5 entries and a header comment naming the field:

                                                   as it   with one field
                                                   ships   removed
        entries                                        5         5
        loose    grep -c optional_lesson_count          6         5  <- reads
                                                                        complete
        anchored grep -c '^    optional_lesson_count: ' 5         4  <- reports
                                                                        the gap

    A key has a position in the parsed structure. A comment and a
    description string do not, so neither can reach this function.
    """
    known = set(CATALOG_KNOWN_ENTRY_FIELDS)
    return sorted((str(key) for key in entry if str(key) not in known), key=str)


def catalog_root(target: Path) -> Path:
    """The directory that holds `target`, as an absolute, normalised path.

    Every path question this file asks about a catalogue - check 6's
    resolution and check 7's containment - is asked relative to this
    directory, so it has to mean the same thing however the caller spelled
    the catalogue on the command line.

    `target.parent` does not. `Path("catalog.yaml").parent` is `Path(".")`,
    and `catalogs.escapes()` USED to decide containment by comparing
    strings: it asked whether `normpath(root + os.sep + relative)` was
    `str(root)`, or started with `str(root) + os.sep`. With a root of `"."`
    the join collapsed - `normpath("./durable-event-broker")` is
    `"durable-event-broker"` - so EVERY contained path looked like an
    escape and check 7 reported every entry in a valid catalogue. The two
    spellings that carry a directory component took the other branch and
    passed, which is how one file both passed and failed (issue #14).

    That predicate is gone (issue #16). `escapes()` is now STRUCTURAL: a
    path escapes when it is absolute, when it starts with `~`, or when it
    keeps a `..` component after normalisation. The verdict no longer
    depends on the root at all, so check 7 can no longer be broken by how
    the root is spelled.

    `catalog_root()` stays because CHECK 6 still resolves every bundle
    directory against it, and that question is unchanged: a relative
    bundle path must name one directory however the caller spelled the
    catalogue. `os.path.abspath` normalises and anchors without touching
    the filesystem, so `catalog.yaml`, `./catalog.yaml`,
    `../dir/catalog.yaml` and an absolute path all reduce to one root.
    Symlinks are deliberately NOT resolved: discovery must not stat
    anything under a bundle path, so the runtime decides on the strings,
    and an authoring-time root that resolved them would ask check 6 about
    a directory the runner never looks in.
    """
    return Path(os.path.abspath(target)).parent


def validate_catalog(target: Path, portable: bool) -> Report:
    report = Report(
        mode="catalog" + (" --portable" if portable else ""),
        target=target,
        checks=CATALOG_CHECKS,
        limitations=CATALOG_LIMITATIONS,
    )
    root = catalog_root(target)

    raw = read_text(target)
    if raw is None:
        report.add(1, target.name, "the file could not be read as UTF-8 text")
        for number in CATALOG_CHECKS:
            if number != 1:
                report.blocked(number, "the catalogue could not be read")
        report.ran(1)
        return report
    try:
        document = load_yaml(raw, target.name)
    except YamlError as exc:
        report.add(1, target.name, f"the file does not parse: {exc}")
        for number in CATALOG_CHECKS:
            if number != 1:
                report.blocked(number, "the catalogue does not parse")
        report.ran(1)
        return report

    if not isinstance(document, dict):
        report.add(
            1,
            target.name,
            f"a catalogue must be a mapping with 'catalog_version' and "
            f"'tutorials', not {type(document).__name__}",
        )
        for number in CATALOG_CHECKS:
            if number != 1:
                report.blocked(number, "the catalogue is not a mapping")
        report.ran(1)
        return report

    version = document.get("catalog_version")
    if version is None:
        report.add(1, target.name, "'catalog_version' is missing")
    elif version not in KNOWN_CATALOG_VERSIONS:
        report.add(
            1,
            target.name,
            f"catalog_version is {version!r}; this document defines "
            f"{', '.join(str(v) for v in KNOWN_CATALOG_VERSIONS)}. A version "
            f"you do not recognise is an error, not a guess",
        )
    unknown_top = sorted(set(document) - {"catalog_version", "tutorials"})
    if unknown_top:
        report.add(
            1,
            target.name,
            f"unknown top-level field(s) {', '.join(unknown_top)}; a "
            f"catalogue holds 'catalog_version' and 'tutorials'",
        )
    report.ran(1, f"catalog_version {version!r}")

    listed = document.get("tutorials")
    if listed is None:
        report.add(2, target.name, "'tutorials' is missing")
    elif not isinstance(listed, list):
        report.add(
            2,
            target.name,
            f"'tutorials' must be a list of entries, not "
            f"{type(listed).__name__}",
        )
        listed = None
    elif not listed:
        report.add(
            2,
            target.name,
            "the tutorials list is empty; a catalogue with no entry offers "
            "nothing and is almost certainly an accident",
        )
    if listed is None:
        for number in (2, 3, 4, 5, 6, 7):
            if number == 2:
                report.ran(2)
            else:
                report.blocked(number, "there is no usable tutorials list")
        return report

    entries: list[tuple[str, dict]] = []
    for index, item in enumerate(listed):
        where = f"tutorials[{index}]"
        if not isinstance(item, dict):
            report.add(
                2,
                where,
                f"the entry must be a mapping of field to value, not "
                f"{type(item).__name__}",
            )
            continue
        if _is_text(item.get("id")):
            where = f"{where} ({item['id']})"
        entries.append((where, item))
    report.ran(2, f"{len(listed)} entr{'y' if len(listed) == 1 else 'ies'}")

    # -- check 3: required fields, and their shapes
    for where, item in entries:
        missing = [f for f in CATALOG_REQUIRED_FIELDS if f not in item]
        for name in missing:
            report.add(3, where, f"the required field {name!r} is missing")
        for name in CATALOG_TEXT_FIELDS:
            if name in item and not _is_text(item[name]):
                report.add(
                    3,
                    where,
                    f"{name!r} must be a non-empty string; it is "
                    f"{item[name]!r}",
                )
        for name in CATALOG_LIST_FIELDS:
            if name in item and not _is_text_list(item[name]):
                report.add(
                    3,
                    where,
                    f"{name!r} must be a non-empty list of strings; it is "
                    f"{item[name]!r}",
                )
        for name in CATALOG_COUNT_FIELDS:
            if name in item and not _is_count(item[name]):
                report.add(
                    3,
                    where,
                    f"{name!r} must be a whole number that is zero or more; "
                    f"it is {item[name]!r}. It counts the lessons the bundle "
                    f"lists under 'optional_lessons', which 'scope' does not "
                    f"count. Omit the field when the course has none",
                )
        kind = item.get("workspace_kind")
        if _is_text(kind) and kind not in WORKSPACE_KINDS:
            report.add(
                3,
                where,
                f"workspace_kind is {kind!r}, which is not one of "
                f"{', '.join(WORKSPACE_KINDS)}",
            )
    # -- still check 3: a field this document does not define.
    #
    # A WARNING and never a finding, and that is the whole design. A
    # catalogue is data a NEWER runner may extend, and bundle-format.md
    # section 13 settled what an older reader does with a key it has never
    # heard of: it degrades, it does not refuse. A validator that rejected
    # an unrecognised key would turn a valid catalogue into an unusable one
    # the day the format grows - the one failure the additive-key policy
    # exists to prevent. So the key is named, loudly, and the catalogue
    # still passes: `exit_code()` never consults `warnings`, so this can
    # never stop a course.
    #
    # It is part of check 3 rather than a check of its own because check 3
    # IS the question about an entry's fields, and because a catalogue
    # check that can only ever warn would be a number in the table that can
    # never change the verdict. Bundle check 23 is the precedent: it
    # reports shape errors as findings and alias collisions as warnings.
    unknown_fields = 0
    for where, item in entries:
        for name in unknown_entry_fields(item):
            unknown_fields += 1
            suggestions = near_misses(name, CATALOG_KNOWN_ENTRY_FIELDS)
            if suggestions:
                report.warn(
                    3,
                    where,
                    f"unknown field {name!r}, which is a near miss for "
                    f"{' or '.join(repr(s) for s in suggestions)}. A runner "
                    f"reads an entry by field name and ignores a name it "
                    f"does not know, so a misspelling is silently absent "
                    f"rather than reported: the entry advertises nothing by "
                    f"it. Correct the spelling. This is a WARNING and the "
                    f"catalogue is still usable",
                )
            else:
                report.warn(
                    3,
                    where,
                    f"unknown field {name!r}. A runner ignores a field name "
                    f"it does not know, so this entry advertises nothing by "
                    f"it. That is correct for a field a newer catalogue "
                    f"adds, which is why this is a WARNING and the "
                    f"catalogue is still usable. The fields this document "
                    f"defines are "
                    f"{', '.join(CATALOG_KNOWN_ENTRY_FIELDS)}",
                )
    report.ran(
        3,
        f"{len(entries)} entr{'y' if len(entries) == 1 else 'ies'}, "
        f"{unknown_fields} unknown field(s)",
    )

    # -- check 4: identity
    seen: dict[str, str] = {}
    for where, item in entries:
        identifier = item.get("id")
        if not _is_text(identifier):
            continue
        if not re.fullmatch(r"[a-z0-9-]+", identifier):
            report.add(
                4,
                where,
                f"the id {identifier!r} must match [a-z0-9-]+; it is the "
                f"name a learner and a bundle both answer to",
            )
        if identifier in seen:
            report.add(
                4,
                where,
                f"the id {identifier!r} is already used by {seen[identifier]}; "
                f"two entries answering to one id make precedence undecidable",
            )
        else:
            seen[identifier] = where
    report.ran(4, f"{len(seen)} distinct id(s)")

    # -- check 5: the provider boundary
    resolvable: list[tuple[str, str]] = []
    for where, item in entries:
        source = item.get("source")
        if source is None:
            continue
        if not isinstance(source, dict):
            report.add(
                5,
                where,
                f"'source' must be a mapping, not {type(source).__name__}",
            )
            continue
        kind = source.get("type")
        if not _is_text(kind):
            report.add(5, where, "'source' has no 'type'")
            continue
        if kind not in CATALOG_ENTRY_SOURCE_TYPES:
            report.add(
                5,
                where,
                f"source type {kind!r} is not one of "
                f"{', '.join(CATALOG_ENTRY_SOURCE_TYPES)}",
            )
            continue
        if kind not in CATALOG_ENTRY_SOURCE_IMPLEMENTED:
            report.add(
                5,
                where,
                f"source type {kind!r} is declared but not implemented. A "
                f"bundle that lives in a repository is reached by adding "
                f"that repository as a CATALOGUE; a catalogue entry names a "
                f"path inside its own catalogue's directory",
            )
            continue
        path = source.get("path")
        if not _is_text(path):
            report.add(5, where, "a local source requires a non-empty 'path'")
            continue
        resolvable.append((where, path))
    report.ran(5, f"{len(resolvable)} resolvable source(s)")

    # -- check 6: the bundle is really there
    for where, path in resolvable:
        candidate = Path(os.path.expanduser(path))
        absolute = (
            candidate if candidate.is_absolute() else Path(os.path.normpath(root / candidate))
        )
        if not absolute.is_dir():
            report.add(
                6,
                where,
                f"the bundle path {path!r} resolves to {absolute}, which is "
                f"not a directory. Relative paths resolve from {root}, the "
                f"directory that holds this catalogue",
            )
            continue
        if absolute.name not in list_dir(absolute.parent):
            report.add(
                6,
                where,
                f"the directory is named "
                f"{[e for e in list_dir(absolute.parent) if e.lower() == absolute.name.lower()][0]!r}, "
                f"not {absolute.name!r}; the case differs, which resolves on "
                f"macOS or Windows and fails on Linux",
            )
            continue
        present = list_dir(absolute)
        for required in ("tutorial.yaml", "STATE.template.md"):
            if required not in present:
                near = [e for e in present if e.lower() == required.lower()]
                report.add(
                    6,
                    where,
                    f"{absolute}/{required} is missing"
                    + (f"; the entry is named {near[0]!r}" if near else "")
                    + ". A catalogue entry must name a bundle",
                )
    report.ran(6, f"{len(resolvable)} bundle path(s)")

    # -- check 7: portability
    if not portable:
        report.na(
            7,
            "pass --portable for a catalogue that ships inside a repository",
        )
        return report
    from catalogs import escapes  # authoring-time tool, runtime predicate

    for where, path in resolvable:
        if escapes(root, path):
            report.add(
                7,
                where,
                f"the bundle path {path!r} leaves {root}, the directory that "
                f"holds this catalogue. A catalogue served from a repository "
                f"may only name bundles that travel with it, so the path must "
                f"be relative and must stay inside",
            )
    report.ran(7, f"{len(resolvable)} bundle path(s)")
    return report


def render(report: Report, stream=sys.stdout) -> None:
    if report.checks is CHECKS:
        applicable = sorted(
            number
            for number in CHECKS
            if not (
                (number in BUNDLE_ONLY and report.mode != "bundle")
                or (number in INSTANCE_ONLY and report.mode != "instance")
            )
        )
    else:
        applicable = sorted(report.checks)
    print(f"tutorAIl validator - mode: {report.mode}", file=stream)
    print(f"target:      {report.target}", file=stream)
    print(f"yaml reader: {YAML_READER}", file=stream)
    print("", file=stream)
    print("checks:", file=stream)
    for number in applicable:
        state, detail = report.status.get(
            number, (BLOCKED, "the validator never reached this check")
        )
        label = {RAN: "ran", NOT_APPLICABLE: "n/a", BLOCKED: "NOT RUN"}[state]
        suffix = f"  ({detail})" if detail else ""
        print(
            f"  [{number:>2}] {label:<7} {report.checks[number]}{suffix}",
            file=stream,
        )
    print("", file=stream)

    if report.findings:
        print(f"FAIL - {len(report.findings)} finding(s):", file=stream)
        for finding in sorted(report.findings, key=lambda f: (f.check, f.where)):
            print(f"  {finding}", file=stream)
    if report.warnings:
        # Printed whether or not there are findings, and never counted with
        # them. A warning does not change the exit code and does not make a
        # bundle invalid; it is something worth an author's eye.
        if report.findings:
            print("", file=stream)
        print(
            f"{len(report.warnings)} warning(s) - these do not make the "
            f"bundle invalid:",
            file=stream,
        )
        for warning in sorted(report.warnings, key=lambda f: (f.check, f.where)):
            print(f"  {warning}", file=stream)
        print("", file=stream)
    blocked = report.blocked_checks
    if blocked:
        print("", file=stream)
        print(
            f"WARNING - {len(blocked)} check(s) did not run: "
            f"{', '.join(str(b) for b in sorted(blocked))}. "
            f"This result does not certify them.",
            file=stream,
        )
    if not report.findings:
        if blocked:
            print(
                "INDETERMINATE - no findings, but not every check ran.", file=stream
            )
        elif report.warnings:
            print(
                f"PASS - every applicable check ran and found nothing that "
                f"makes this bundle invalid. {len(report.warnings)} "
                f"warning(s) above are worth a look.",
                file=stream,
            )
        else:
            print(
                "PASS - every applicable check ran and found nothing.", file=stream
            )
    print("", file=stream)
    print(report.limitations or LIMITATIONS, file=stream)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="validate_bundle.py",
        description="Structurally validate a tutorAIl bundle or instance.",
    )
    parser.add_argument("path", help="the bundle, instance or catalogue path")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--instance",
        action="store_true",
        help="check the path as an instance instead of a bundle",
    )
    group.add_argument(
        "--catalog",
        action="store_true",
        help="check the path as a catalogue file instead of a bundle",
    )
    parser.add_argument(
        "--portable",
        action="store_true",
        help="with --catalog, also check that every bundle path stays inside "
        "the catalogue's own directory",
    )
    args = parser.parse_args(argv)

    target = Path(args.path)
    if args.portable and not args.catalog:
        print("error: --portable applies only with --catalog", file=sys.stderr)
        return 2
    if args.catalog:
        if not target.is_file():
            print(f"error: {target} is not a file", file=sys.stderr)
            return 2
        report = validate_catalog(target, args.portable)
        render(report)
        return report.exit_code()
    if not target.is_dir():
        print(f"error: {target} is not a directory", file=sys.stderr)
        return 2
    mode = "instance" if args.instance else "bundle"
    report = validate(target, mode)
    render(report)
    return report.exit_code()


if __name__ == "__main__":
    sys.exit(main())
