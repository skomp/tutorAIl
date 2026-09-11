#!/usr/bin/env python3
"""Structural validator for tutorAIl bundles and instances.

Authoring-time only. Running a tutorial never invokes this script.

Usage:
    validate_bundle.py <path>              check a bundle
    validate_bundle.py --instance <path>   check an instance
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


class YamlError(Exception):
    """The document uses something the restricted reader will not guess at."""


_UNSUPPORTED_INDICATORS = {
    "&": "anchors (&name)",
    "*": "aliases (*name)",
    "!": "tags (!name)",
    "%": "directives (%YAML)",
    "`": "the reserved indicator '`'",
    "@": "the reserved indicator '@'",
}

_NULLS = {"", "null", "Null", "NULL", "~"}
_TRUE = {"true", "True", "TRUE"}
_FALSE = {"false", "False", "FALSE"}


def _plain_to_python(text: str) -> Any:
    if text in _NULLS:
        return None
    if text in _TRUE:
        return True
    if text in _FALSE:
        return False
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        pass
    return text


class _FlowParser:
    """Parses a single line's worth of YAML flow syntax.

    Supports: plain scalars, single- and double-quoted scalars, flow
    sequences [a, b], flow mappings {k: v}. Everything else raises.
    """

    def __init__(self, text: str, where: str, lineno: int) -> None:
        self.s = text
        self.i = 0
        self.where = where
        self.lineno = lineno

    def fail(self, msg: str) -> "YamlError":
        return YamlError(f"{self.where}: line {self.lineno}: {msg}")

    def parse(self) -> Any:
        value = self.value(in_flow=False)
        self.ws()
        if self.i < len(self.s):
            raise self.fail(
                f"unexpected text after the value: {self.s[self.i:]!r}"
            )
        return value

    def ws(self) -> None:
        while self.i < len(self.s) and self.s[self.i] in " \t":
            self.i += 1

    def peek(self) -> str:
        return self.s[self.i] if self.i < len(self.s) else ""

    def value(self, in_flow: bool) -> Any:
        self.ws()
        c = self.peek()
        if c == "[":
            return self.sequence()
        if c == "{":
            return self.mapping()
        if c in ('"', "'"):
            return self.quoted()
        if c in _UNSUPPORTED_INDICATORS:
            raise self.fail(
                f"{_UNSUPPORTED_INDICATORS[c]} are not supported by the "
                f"restricted YAML reader; rewrite the value literally"
            )
        return self.plain(in_flow)

    def plain(self, in_flow: bool) -> Any:
        start = self.i
        while self.i < len(self.s):
            c = self.s[self.i]
            if in_flow and c in ",]}":
                break
            self.i += 1
        text = self.s[start : self.i].strip()
        if in_flow and text == "":
            raise self.fail("empty value in a flow collection")
        return _plain_to_python(text)

    def quoted(self) -> str:
        quote = self.s[self.i]
        self.i += 1
        out: list[str] = []
        while True:
            if self.i >= len(self.s):
                raise self.fail(f"unterminated {quote}-quoted string")
            c = self.s[self.i]
            if quote == "'":
                if c == "'":
                    if self.s[self.i + 1 : self.i + 2] == "'":
                        out.append("'")
                        self.i += 2
                        continue
                    self.i += 1
                    return "".join(out)
                out.append(c)
                self.i += 1
                continue
            # double quoted
            if c == "\\":
                esc = self.s[self.i + 1 : self.i + 2]
                simple = {
                    "n": "\n",
                    "t": "\t",
                    "r": "\r",
                    '"': '"',
                    "\\": "\\",
                    "/": "/",
                    "0": "\0",
                    " ": " ",
                }
                if esc not in simple:
                    raise self.fail(
                        f"escape sequence '\\{esc}' is not supported by the "
                        f"restricted YAML reader"
                    )
                out.append(simple[esc])
                self.i += 2
                continue
            if c == '"':
                self.i += 1
                return "".join(out)
            out.append(c)
            self.i += 1

    def sequence(self) -> list:
        self.i += 1  # consume '['
        out: list = []
        self.ws()
        if self.peek() == "]":
            self.i += 1
            return out
        while True:
            out.append(self.value(in_flow=True))
            self.ws()
            c = self.peek()
            if c == ",":
                self.i += 1
                self.ws()
                if self.peek() == "]":
                    self.i += 1
                    return out
                continue
            if c == "]":
                self.i += 1
                return out
            raise self.fail(
                f"expected ',' or ']' in a flow sequence, found {c!r}"
                if c
                else "unterminated flow sequence '['"
            )

    def mapping(self) -> dict:
        self.i += 1  # consume '{'
        out: dict = {}
        self.ws()
        if self.peek() == "}":
            self.i += 1
            return out
        while True:
            self.ws()
            key = self.flow_key()
            self.ws()
            if self.peek() != ":":
                raise self.fail(
                    f"expected ':' after the key {key!r} in a flow mapping"
                )
            self.i += 1
            value = self.value(in_flow=True)
            if key in out:
                raise self.fail(f"duplicate key {key!r} in a flow mapping")
            out[key] = value
            self.ws()
            c = self.peek()
            if c == ",":
                self.i += 1
                self.ws()
                if self.peek() == "}":
                    self.i += 1
                    return out
                continue
            if c == "}":
                self.i += 1
                return out
            raise self.fail(
                f"expected ',' or '}}' in a flow mapping, found {c!r}"
                if c
                else "unterminated flow mapping '{'"
            )

    def flow_key(self) -> Any:
        if self.peek() in ('"', "'"):
            return self.quoted()
        start = self.i
        while self.i < len(self.s) and self.s[self.i] not in ":,]}":
            self.i += 1
        text = self.s[start : self.i].strip()
        if text == "":
            raise self.fail("empty key in a flow mapping")
        if text[0] in _UNSUPPORTED_INDICATORS:
            raise self.fail(
                f"{_UNSUPPORTED_INDICATORS[text[0]]} are not supported by the "
                f"restricted YAML reader"
            )
        return _plain_to_python(text)


def _strip_comment(line: str) -> str:
    """Remove a trailing '# ...' comment, respecting quotes.

    A '#' only starts a comment at the start of the line or after a space.
    """
    out: list[str] = []
    quote = ""
    for idx, c in enumerate(line):
        if quote:
            out.append(c)
            if c == quote:
                quote = ""
            continue
        if c in ('"', "'"):
            quote = c
            out.append(c)
            continue
        if c == "#" and (idx == 0 or line[idx - 1] in " \t"):
            break
        out.append(c)
    return "".join(out)


_KEY_RE = re.compile(
    r"""^(?P<key>"[^"]*"|'[^']*'|[^:#]+?)\s*:(?:[ \t]+(?P<val>.*))?$"""
)
_SEQ_KEY_RE = re.compile(r"""^("[^"]*"|'[^']*'|[^:#\[\]{},]+?)\s*:([ \t]|$)""")


class _RestrictedYaml:
    """Block-structure reader for the shallow YAML the bundle format uses.

    Supported: block mappings, block sequences, sequences of mappings, flow
    sequences and mappings, quoted and plain scalars, '>' and '|' block
    scalars with '-'/'+' chomping, comments, one leading '---'.

    Rejected with an explicit message: anchors, aliases, tags, directives,
    multiple documents, tabs in indentation, duplicate keys, explicit
    indentation indicators on block scalars, plain multi-line scalars, and
    any line that is not 'key: value' or '- item'.
    """

    def __init__(self, text: str, where: str) -> None:
        self.lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        self.n = 0
        self.where = where
        self.seen_doc_start = False

    def fail(self, lineno: int, msg: str) -> YamlError:
        return YamlError(f"{self.where}: line {lineno}: {msg}")

    # -- line scanning -----------------------------------------------------

    def peek(self) -> tuple[int, int, str] | None:
        """Return (index, indent, stripped text) of the next significant line."""
        while self.n < len(self.lines):
            raw = self.lines[self.n]
            # Measure the leading whitespace run over BOTH spaces and tabs, so
            # a tab-indented line is caught here rather than being read as an
            # un-indented one and reported as some unrelated syntax error.
            indent = len(raw) - len(raw.lstrip(" \t"))
            if "\t" in raw[:indent]:
                raise self.fail(
                    self.n + 1,
                    "a tab is used for indentation; YAML forbids this, use spaces",
                )
            content = _strip_comment(raw).strip()
            if content == "":
                self.n += 1
                continue
            if content == "...":
                raise self.fail(
                    self.n + 1,
                    "the document-end marker '...' is not supported",
                )
            if content == "---":
                if self.seen_doc_start or any(
                    _strip_comment(x).strip() for x in self.lines[: self.n]
                ):
                    raise self.fail(
                        self.n + 1,
                        "multiple YAML documents in one file are not supported",
                    )
                self.seen_doc_start = True
                self.n += 1
                continue
            return self.n, indent, content
        return None

    # -- entry point -------------------------------------------------------

    def parse(self) -> Any:
        first = self.peek()
        if first is None:
            return None
        _, indent, _ = first
        if indent != 0:
            raise self.fail(first[0] + 1, "the document starts with an indented line")
        value = self.parse_block(0)
        trailing = self.peek()
        if trailing is not None:
            raise self.fail(trailing[0] + 1, f"unexpected line {trailing[2]!r}")
        return value

    def parse_block(self, indent: int) -> Any:
        peeked = self.peek()
        if peeked is None:
            return None
        _, _, text = peeked
        if text == "-" or text.startswith("- "):
            return self.parse_sequence(indent)
        return self.parse_mapping(indent)

    # -- structures --------------------------------------------------------

    def parse_mapping(self, indent: int) -> dict:
        out: dict = {}
        while True:
            peeked = self.peek()
            if peeked is None:
                break
            idx, ind, text = peeked
            if ind < indent:
                break
            if ind > indent:
                raise self.fail(
                    idx + 1,
                    f"unexpected indentation (expected {indent} spaces, found {ind}); "
                    f"a plain scalar cannot continue onto the next line - use '>' "
                    f"or quote the value",
                )
            if text == "-" or text.startswith("- "):
                raise self.fail(
                    idx + 1, "expected 'key: value' but found a sequence item"
                )
            match = _KEY_RE.match(text)
            if not match:
                raise self.fail(
                    idx + 1,
                    f"expected 'key: value' (with a space after the colon); "
                    f"found {text!r}",
                )
            raw_key = match.group("key").strip()
            if raw_key[:1] in _UNSUPPORTED_INDICATORS:
                raise self.fail(
                    idx + 1,
                    f"{_UNSUPPORTED_INDICATORS[raw_key[0]]} are not supported "
                    f"by the restricted YAML reader",
                )
            if raw_key == "<<":
                raise self.fail(idx + 1, "merge keys ('<<') are not supported")
            if raw_key[:1] in ('"', "'"):
                key = raw_key[1:-1]
            else:
                key = raw_key
            if key in out:
                raise self.fail(idx + 1, f"duplicate key {key!r}")
            rest = (match.group("val") or "").strip()
            self.n = idx + 1
            if rest == "":
                nxt = self.peek()
                if nxt is not None and nxt[1] > indent:
                    out[key] = self.parse_block(nxt[1])
                else:
                    out[key] = None
            elif rest[0] in "|>":
                out[key] = self.block_scalar(rest, indent, idx + 1)
            else:
                out[key] = _FlowParser(rest, self.where, idx + 1).parse()
        return out

    def parse_sequence(self, indent: int) -> list:
        out: list = []
        while True:
            peeked = self.peek()
            if peeked is None:
                break
            idx, ind, text = peeked
            if ind < indent:
                break
            if ind > indent:
                raise self.fail(
                    idx + 1,
                    f"unexpected indentation in a sequence "
                    f"(expected {indent} spaces, found {ind})",
                )
            if not (text == "-" or text.startswith("- ")):
                raise self.fail(
                    idx + 1,
                    f"expected a sequence item starting with '- '; found {text!r}",
                )
            rest = text[1:].strip()
            self.n = idx + 1
            if rest == "":
                nxt = self.peek()
                if nxt is not None and nxt[1] > indent:
                    out.append(self.parse_block(nxt[1]))
                else:
                    out.append(None)
                continue
            if _SEQ_KEY_RE.match(rest):
                # A mapping that starts on the '-' line. Rewrite the line so
                # the mapping's own column is its indentation, then reparse.
                gap = len(text) - 1 - len(text[1:].lstrip(" "))
                col = ind + 1 + gap
                self.lines[idx] = " " * col + rest
                self.n = idx
                out.append(self.parse_mapping(col))
                continue
            if rest[0] in "|>":
                out.append(self.block_scalar(rest, indent, idx + 1))
                continue
            out.append(_FlowParser(rest, self.where, idx + 1).parse())
        return out

    def block_scalar(self, header: str, parent_indent: int, lineno: int) -> str:
        style = header[0]
        modifiers = header[1:].strip()
        chomp = ""
        if modifiers in ("-", "+"):
            chomp = modifiers
        elif modifiers != "":
            raise self.fail(
                lineno,
                f"block scalar header {header!r} is not supported; only "
                f"'{style}', '{style}-' and '{style}+' are",
            )
        body: list[str] = []
        while self.n < len(self.lines):
            raw = self.lines[self.n]
            if raw.strip() == "":
                body.append("")
                self.n += 1
                continue
            indent = len(raw) - len(raw.lstrip(" \t"))
            if "\t" in raw[:indent]:
                raise self.fail(
                    self.n + 1, "a tab is used for indentation inside a block scalar"
                )
            if indent <= parent_indent:
                break
            body.append(raw)
            self.n += 1
        while body and body[-1] == "":
            body.pop()
        if not body:
            return ""
        block_indent = min(
            len(line) - len(line.lstrip(" ")) for line in body if line.strip()
        )
        stripped = [line[block_indent:] if line.strip() else "" for line in body]
        if style == "|":
            text = "\n".join(stripped)
        else:
            parts: list[str] = []
            for line in stripped:
                if line == "":
                    parts.append("\n")
                elif parts and parts[-1] not in ("\n",):
                    parts.append(" " + line)
                else:
                    parts.append(line)
            text = "".join(parts)
        if chomp == "-":
            return text
        return text + "\n"


try:  # pragma: no cover - depends on the environment
    import yaml as _pyyaml
except Exception:  # pragma: no cover
    _pyyaml = None

YAML_READER = "PyYAML" if _pyyaml is not None else "restricted (no PyYAML installed)"


def load_yaml(text: str, where: str) -> Any:
    """Parse YAML, preferring PyYAML, falling back to the restricted reader."""
    if _pyyaml is not None:  # pragma: no cover - depends on the environment
        try:
            return _pyyaml.safe_load(text)
        except _pyyaml.YAMLError as exc:
            raise YamlError(f"{where}: {exc}") from exc
    return _RestrictedYaml(text, where).parse()


# --------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------

CHECKS: dict[int, str] = {
    1: "every design_refs entry resolves to a DESIGN.md anchor",
    2: "every lesson validators entry is declared in tutorial.yaml",
    3: "every lesson has id + title frontmatter, and id equals its slug",
    4: "lessons entries resolve; every lesson is listed exactly once; "
    "every lesson folder has an exact-case LESSON.md",
    5: "no progress markers in structural positions in COURSE.md or lessons/",
    6: "every file in a lesson folder is named by that folder's LESSON.md",
    7: "state-file shape: STATE.template.md / STATE.md, and the instance stamp",
    8: "tutorial.yaml parses; bundle_format known; required fields present",
    9: "COURSE.md and DESIGN.md exist; lessons is non-empty",
    10: "workspace_kind and ownership_policy are known; ownership globs non-empty",
    11: "[instance] STATE.md frontmatter well-formed and consistent with the manifest",
    12: "[bundle] STATE.template.md is consistent with the manifest",
}

BUNDLE_ONLY = {12}
INSTANCE_ONLY = {11}

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
      counts as named.

  There is deliberately no reverse material check ("LESSON.md names a file
  that does not exist"). It cannot tell a material reference from an
  ordinary prose mention of DESIGN.md, src/lib.rs or Cargo.toml."""


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
    status: dict[int, tuple[str, str]] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def add(self, check: int, where: str, message: str) -> None:
        self.findings.append(Finding(check, where, message))

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


# -- lesson discovery -------------------------------------------------------


@dataclass
class Lesson:
    rel: str  # path relative to the bundle root, e.g. lessons/00-x.md
    slug: str
    path: Path
    folder: Path | None  # the lesson folder, for foldered lessons


def discover_lessons(root: Path, report: Report) -> tuple[list[Lesson], bool]:
    """Walk lessons/ and return the lessons it actually contains.

    Also reports check-4 findings for folders without an exact-case LESSON.md.
    The second return value says whether lessons/ is a directory at all.
    """
    lessons_dir = root / "lessons"
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
                    Lesson(f"lessons/{name}", name[:-3], child, None)
                )
            continue
        if child.is_dir():
            entries = list_dir(child)
            if "LESSON.md" in entries:
                found.append(
                    Lesson(
                        f"lessons/{name}/LESSON.md",
                        name,
                        child / "LESSON.md",
                        child,
                    )
                )
                continue
            miscased = [e for e in entries if e.lower() == "lesson.md"]
            if miscased:
                report.add(
                    4,
                    f"lessons/{name}/{miscased[0]}",
                    f"a lesson folder's body must be named exactly 'LESSON.md'; "
                    f"this one is {miscased[0]!r}. The local filesystem is "
                    f"case-insensitive so it resolves here and fails on Linux. "
                    f"Rename it (via a temporary name, because a plain rename "
                    f"is a no-op on this filesystem).",
                )
            else:
                report.add(
                    4,
                    f"lessons/{name}/",
                    "a folder directly under lessons/ has no LESSON.md, so it is "
                    "not a lesson and everything in it is unreachable. Add a "
                    "LESSON.md, or move the files into the lesson folder they "
                    "belong to.",
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


def check_lesson_list(
    root: Path,
    manifest: Any,
    lessons_dir_exists: bool,
    discovered: list[Lesson],
    report: Report,
) -> list[Lesson]:
    """Check 4 - resolution, exactly-once listing. Returns the lessons to load."""
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
        listed_set = set(listed)
        for lesson in discovered:
            if lesson.rel not in listed_set:
                report.add(
                    4,
                    lesson.rel,
                    "this lesson is not listed in tutorial.yaml's 'lessons'. The "
                    "runner reaches lessons only through that list, so it is "
                    "invisible.",
                )

    slugs: dict[str, list[str]] = {}
    for lesson in discovered:
        slugs.setdefault(lesson.slug, []).append(lesson.rel)
    for slug, paths in slugs.items():
        if len(paths) > 1:
            report.add(
                4,
                "lessons/",
                f"the slug {slug!r} is used by more than one lesson "
                f"({', '.join(paths)}); a lesson id must be unique",
            )

    report.ran(4, f"{len(listed)} listed / {len(discovered)} found")
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

    report.ran(3, f"{len(lessons)} lessons")
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


def check_progress_markers(root: Path, report: Report) -> None:
    """Check 5."""
    targets: list[tuple[str, Path]] = []
    course = root / "COURSE.md"
    if course.is_file():
        targets.append(("COURSE.md", course))
    lessons_dir = root / "lessons"
    if lessons_dir.is_dir():
        for path in sorted(lessons_dir.rglob("*")):
            if not path.is_file() or path.name.startswith("."):
                continue
            targets.append((str(path.relative_to(root)), path))
    if not targets:
        report.na(5, "neither COURSE.md nor any file under lessons/ was found")
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
                report.add(
                    5,
                    f"{rel}:{lineno}",
                    f"{label} appears here: {match.group(0).strip()!r}. COURSE.md "
                    f"and lessons/ describe the course for every learner who will "
                    f"ever take it, so they carry no progress; all progress lives "
                    f"in STATE.md.",
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


def check_material_reachable(lessons: list[Lesson], report: Report) -> None:
    """Check 6 - forward direction only.

    The reverse check ("LESSON.md names a file that does not exist") was
    implemented and deleted: it cannot tell a material reference from an
    ordinary prose mention of DESIGN.md, src/lib.rs or Cargo.toml. Do not
    reintroduce it.
    """
    foldered = [lesson for lesson in lessons if lesson.folder is not None]
    if not foldered:
        report.na(6, "no foldered lessons")
        return
    checked = 0
    for lesson in foldered:
        text = read_text(lesson.path)
        if text is None:
            continue
        folder = lesson.folder
        assert folder is not None
        for path in sorted(folder.rglob("*")):
            if not path.is_file():
                continue
            rel_in_folder = path.relative_to(folder).as_posix()
            if rel_in_folder == "LESSON.md":
                continue
            if any(part.startswith(".") for part in path.relative_to(folder).parts):
                continue
            checked += 1
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
        f"{checked} material files in {len(foldered)} lesson folders; "
        f"names only, not intent",
    )


def check_state_template(
    root: Path, manifest: Any, report: Report
) -> None:
    """Check 12 - bundle mode."""
    path = root / "STATE.template.md"
    if "STATE.template.md" not in list_dir(root):
        report.blocked(12, "STATE.template.md is missing (see check 7)")
        return
    text = read_text(path)
    if text is None:
        report.add(12, "STATE.template.md", "the file could not be read as UTF-8 text")
        report.blocked(12, "STATE.template.md could not be read")
        return
    fm_text, body = split_frontmatter(text)
    if fm_text is None:
        report.add(
            12,
            "STATE.template.md",
            "there is no YAML frontmatter; it must declare tutorial_id, "
            "active_lesson, status and updated.",
        )
        report.ran(12)
        return
    try:
        fm = load_yaml(fm_text, "STATE.template.md frontmatter")
    except YamlError as exc:
        report.add(12, "STATE.template.md", f"the frontmatter does not parse: {exc}")
        report.ran(12)
        return
    if not isinstance(fm, dict):
        report.add(12, "STATE.template.md", "the frontmatter is not a mapping")
        report.ran(12)
        return

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


def check_instance_state(root: Path, manifest: Any, report: Report) -> None:
    """Check 11 - instance mode."""
    if "STATE.md" not in list_dir(root):
        report.blocked(11, "STATE.md is missing (see check 7)")
        return
    text = read_text(root / "STATE.md")
    if text is None:
        report.add(11, "STATE.md", "the file could not be read as UTF-8 text")
        report.blocked(11, "STATE.md could not be read")
        return
    fm_text, _ = split_frontmatter(text)
    if fm_text is None:
        report.add(
            11,
            "STATE.md",
            "there is no YAML frontmatter; it must declare tutorial_id, "
            "active_lesson, status and updated.",
        )
        report.ran(11)
        return
    try:
        fm = load_yaml(fm_text, "STATE.md frontmatter")
    except YamlError as exc:
        report.add(11, "STATE.md", f"the frontmatter does not parse: {exc}")
        report.ran(11)
        return
    if not isinstance(fm, dict):
        report.add(11, "STATE.md", "the frontmatter is not a mapping")
        report.ran(11)
        return

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
        if listed is not None and active not in listed:
            report.add(
                11,
                "STATE.md",
                f"active_lesson {active!r} is not in tutorial.yaml's 'lessons' "
                f"list, so the runner cannot tell which lesson comes next.",
            )
    report.ran(11)


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

    check_state_files(target, mode, manifest, report)
    if manifest_error is not None and manifest is None:
        report.blocked(8, f"tutorial.yaml is unusable: {manifest_error}")
    else:
        check_manifest(manifest, report)
    check_required_files(target, manifest_dict, report)
    check_workspace_and_ownership(manifest if manifest is not None else None, report)
    lessons = check_lesson_list(
        target, manifest_dict, lessons_dir_exists, lessons, report
    )
    check_lesson_frontmatter(lessons, anchors, declared, report)
    check_progress_markers(target, report)
    check_material_reachable(lessons, report)
    if mode == "bundle":
        check_state_template(target, manifest_dict, report)
    else:
        check_instance_state(target, manifest_dict, report)

    return report


def render(report: Report, stream=sys.stdout) -> None:
    applicable = sorted(
        number
        for number in CHECKS
        if not (
            (number in BUNDLE_ONLY and report.mode != "bundle")
            or (number in INSTANCE_ONLY and report.mode != "instance")
        )
    )
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
        print(f"  [{number:>2}] {label:<7} {CHECKS[number]}{suffix}", file=stream)
    print("", file=stream)

    if report.findings:
        print(f"FAIL - {len(report.findings)} finding(s):", file=stream)
        for finding in sorted(report.findings, key=lambda f: (f.check, f.where)):
            print(f"  {finding}", file=stream)
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
        else:
            print(
                "PASS - every applicable check ran and found nothing.", file=stream
            )
    print("", file=stream)
    print(LIMITATIONS, file=stream)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="validate_bundle.py",
        description="Structurally validate a tutorAIl bundle or instance.",
    )
    parser.add_argument("path", help="the bundle or instance directory")
    parser.add_argument(
        "--instance",
        action="store_true",
        help="check the path as an instance instead of a bundle",
    )
    args = parser.parse_args(argv)

    target = Path(args.path)
    if not target.is_dir():
        print(f"error: {target} is not a directory", file=sys.stderr)
        return 2
    mode = "instance" if args.instance else "bundle"
    report = validate(target, mode)
    render(report)
    return report.exit_code()


if __name__ == "__main__":
    sys.exit(main())
