#!/usr/bin/env python3
"""Test suite for skills/tutorail/scripts/catalogs.py.

Run it with:  python3 tests/test_catalogs.py

No pytest, no PyYAML, and NO NETWORK. Nothing here contacts a host.

The point of this suite is not to show the script working. Every failure kind
gets a fixture that makes it fire, with a message a learner could act on, and
the meta-test at the end fails if any kind in catalogs.FAILURE_KINDS has no
fixture behind it. A kind that can only be shown passing is a false oracle,
and this script's whole job is to tell three failures apart.

How the git failures are produced, and why two ways:

  * REAL git, against a local repository over a file:// URL. That covers
    success, a missing catalogue file inside a real clone, and a ref that is
    really not there. It exercises clone, fetch, checkout and rev-parse for
    real, with no network.

  * A FAKE git on PATH, printing the stderr real git prints, exiting 128.
    That covers the failures a local repository cannot produce: an
    unreachable host, a refused credential, and a message the classifier has
    never seen. Each canned message is copied from what git actually prints,
    and the test asserts git's own words reach the report, so a fake that was
    never invoked cannot pass.

The trap this suite is built around: an SSH failure prints BOTH the transport
error AND "Could not read from remote repository. Please make sure you have
the correct access rights" - the same words a refused key prints. A
classifier that tests access first calls every unreachable host an access
problem. That case has its own test.
"""

from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import traceback
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
SCRIPTS = REPO / "skills" / "tutorail" / "scripts"

sys.path.insert(0, str(SCRIPTS))
import catalogs as cat  # noqa: E402
import validate_bundle as vb  # noqa: E402

# --------------------------------------------------------------------------
# Harness
# --------------------------------------------------------------------------

_failures: list[str] = []
_notes: list[str] = []
_passed = 0
_fired_kinds: set[str] = set()
_fired_catalog_checks: set[int] = set()


def record(ok: bool, label: str, detail: str = "") -> None:
    global _passed
    if ok:
        _passed += 1
        print(f"  ok   {label}")
    else:
        _failures.append(f"{label}\n       {detail}")
        print(f"  FAIL {label}")
        if detail:
            print(f"       {detail}")


def note(text: str) -> None:
    _notes.append(text)


FAKE_GIT = """#!/usr/bin/env python3
import os
import sys

sys.stderr.write(os.environ.get("TUTORAIL_FAKE_GIT_STDERR", ""))
sys.exit(128)
"""


class Env:
    """A throwaway config directory, cache and remote repository."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.config_dir = root / "config"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.cache = root / "cache"
        self.bin = root / "bin"
        self.bin.mkdir(parents=True, exist_ok=True)
        fake = self.bin / "git"
        fake.write_text(FAKE_GIT, encoding="utf-8")
        fake.chmod(0o755)
        self.empty_bin = root / "emptybin"
        self.empty_bin.mkdir(parents=True, exist_ok=True)

    @property
    def config(self) -> Path:
        return self.config_dir / "catalogs.yaml"

    def write_config(self, text: str) -> None:
        self.config.write_text(text, encoding="utf-8")

    def write_catalog(self, relative: str, text: str) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def make_bundle(self, relative: str) -> Path:
        path = self.root / relative
        path.mkdir(parents=True, exist_ok=True)
        (path / "tutorial.yaml").write_text("id: x\n", encoding="utf-8")
        (path / "STATE.template.md").write_text(
            "---\nstatus: not-started\n---\n", encoding="utf-8"
        )
        return path

    def run(self, *argv: str) -> tuple[int, str]:
        out = io.StringIO()
        err = io.StringIO()
        full = [
            "--config",
            str(self.config),
            "--cache-dir",
            str(self.cache),
            "--timeout",
            "20",
            *argv,
        ]
        with redirect_stderr(err):
            code = cat.main(full, stream=out)
        return code, out.getvalue() + err.getvalue()

    def run_json(self, *argv: str) -> tuple[int, dict]:
        code, text = self.run("--json", *argv)
        try:
            return code, json.loads(text)
        except ValueError:
            return code, {"_unparsed": text}


@contextmanager
def temp_env():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Env(Path(tmpdir))


@contextmanager
def path_prefixed(directory: Path, stderr: str = ""):
    """Put `directory` first on PATH for the duration."""
    old_path = os.environ.get("PATH", "")
    old_stderr = os.environ.get("TUTORAIL_FAKE_GIT_STDERR")
    os.environ["PATH"] = f"{directory}{os.pathsep}{old_path}"
    os.environ["TUTORAIL_FAKE_GIT_STDERR"] = stderr
    try:
        yield
    finally:
        os.environ["PATH"] = old_path
        if old_stderr is None:
            os.environ.pop("TUTORAIL_FAKE_GIT_STDERR", None)
        else:
            os.environ["TUTORAIL_FAKE_GIT_STDERR"] = old_stderr


@contextmanager
def path_only(directory: Path):
    """Replace PATH entirely, so `git` cannot be found at all."""
    old_path = os.environ.get("PATH", "")
    os.environ["PATH"] = str(directory)
    try:
        yield
    finally:
        os.environ["PATH"] = old_path


def make_repo(root: Path, files: dict[str, str], branch: str = "main") -> str:
    """A real git repository on disk, reachable by a file:// URL."""
    root.mkdir(parents=True, exist_ok=True)
    for relative, text in files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    def git(*args: str) -> None:
        subprocess.run(
            ["git", "-C", str(root), *args],
            check=True,
            capture_output=True,
            text=True,
        )
    git("init", "--quiet", "-b", branch)
    git("add", "-A")
    git(
        "-c",
        "user.email=suite@example.invalid",
        "-c",
        "user.name=suite",
        "commit",
        "--quiet",
        "-m",
        "fixture",
    )
    return f"file://{root}"


# --------------------------------------------------------------------------
# Catalogue documents
# --------------------------------------------------------------------------


def catalog_doc(*entries: tuple[str, str]) -> str:
    lines = ["catalog_version: 1", "tutorials:"]
    for identifier, path in entries:
        lines += [
            f"  - id: {identifier}",
            f"    title: The {identifier} course",
            f"    description: A course about {identifier}.",
            "    subjects: [testing]",
            "    level: beginner",
            "    workspace_kind: new-repository",
            "    source:",
            "      type: local",
            f"      path: {path}",
        ]
    return "\n".join(lines) + "\n"


def file_config(*pairs: tuple[str, Path]) -> str:
    lines = ["catalogs_version: 1", "catalogs:"]
    for identifier, path in pairs:
        lines += [
            f"  - id: {identifier}",
            f"    source: {{ type: file, path: {path} }}",
        ]
    return "\n".join(lines) + "\n"


def git_config(
    identifier: str, url: str, ref: str = "main", path: str = "catalog.yaml"
) -> str:
    return (
        "catalogs_version: 1\n"
        "catalogs:\n"
        f"  - id: {identifier}\n"
        "    source:\n"
        "      type: git\n"
        f"      url: {url}\n"
        f"      ref: {ref}\n"
        f"      path: {path}\n"
    )


# --------------------------------------------------------------------------
# The canned git failures, copied from what real git prints
# --------------------------------------------------------------------------

GIT_MESSAGES: list[tuple[str, str, str]] = [
    (
        "ssh cannot resolve the host name",
        "unreachable",
        "ssh: Could not resolve hostname github.invalid: nodename nor "
        "servname provided, or not known\r\n"
        "fatal: Could not read from remote repository.\n"
        "\n"
        "Please make sure you have the correct access rights\n"
        "and the repository exists.\n",
    ),
    (
        "https cannot resolve the host name",
        "unreachable",
        "fatal: unable to access 'https://git.invalid/bundles.git/': "
        "Could not resolve host: git.invalid\n",
    ),
    (
        "ssh connects to nothing and times out",
        "unreachable",
        "ssh: connect to host github.com port 22: Operation timed out\r\n"
        "fatal: Could not read from remote repository.\n"
        "\n"
        "Please make sure you have the correct access rights\n"
        "and the repository exists.\n",
    ),
    (
        "the ssh key is refused",
        "no-access",
        "git@github.com: Permission denied (publickey).\r\n"
        "fatal: Could not read from remote repository.\n"
        "\n"
        "Please make sure you have the correct access rights\n"
        "and the repository exists.\n",
    ),
    (
        "the repository is private, or is not there",
        "no-access",
        "ERROR: Repository not found.\r\n"
        "fatal: Could not read from remote repository.\n",
    ),
    (
        "https authentication is refused",
        "no-access",
        "fatal: Authentication failed for "
        "'https://github.com/skomp/private.git/'\n",
    ),
    (
        "git wants to prompt for a password and may not",
        "no-access",
        "fatal: could not read Username for 'https://github.com': "
        "terminal prompts disabled\n",
    ),
    (
        "the branch is not in the repository",
        "no-ref",
        "fatal: Remote branch nope not found in upstream origin\n",
    ),
    (
        "a transfer broke in a way this script has never seen",
        "unclassified",
        "remote: aborting due to possible repository corruption on the "
        "remote side.\nfatal: early EOF\nfatal: index-pack failed\n",
    ),
]


def test_classifier() -> None:
    """The classifier, on its own, against messages real git prints."""
    print("\nthe git-error classifier, on real git messages:")
    for label, expected, message in GIT_MESSAGES:
        got = cat.classify_git_error(message)
        record(
            got == expected,
            f"{label!r} classifies as {expected}",
            f"got {got!r}; the message was:\n       "
            + message.replace("\n", "\n       "),
        )

    # The order test. This message contains the ACCESS wording verbatim and
    # is still a transport failure. If the access patterns were tried first,
    # every unreachable host would be reported as a permissions problem and
    # the learner would be sent to fix credentials that are already correct.
    timeout = GIT_MESSAGES[2][2]
    record(
        "correct access rights" in timeout
        and cat.classify_git_error(timeout) == "unreachable",
        "an ssh timeout that ALSO says 'correct access rights' is still "
        "unreachable, not no-access",
        f"got {cat.classify_git_error(timeout)!r}",
    )

    # And the classifier must be able to say it does not know. A classifier
    # that matched everything would pass every case above and be worthless.
    record(
        cat.classify_git_error("fatal: something nobody has ever seen")
        == "unclassified",
        "an unrecognised message is reported as unclassified, not guessed",
        f"got {cat.classify_git_error('fatal: something nobody has ever seen')!r}",
    )

    # Every kind must send the reader somewhere different. Two kinds with one
    # repair are one kind wearing two names.
    repairs = {kind: repair for kind, (_, repair) in cat.FAILURE_KINDS.items()}
    record(
        len(set(repairs.values())) == len(repairs),
        "every failure kind has a repair no other kind has",
        f"{len(set(repairs.values()))} distinct repairs for {len(repairs)} kinds",
    )
    summaries = {kind: summary for kind, (summary, _) in cat.FAILURE_KINDS.items()}
    record(
        len(set(summaries.values())) == len(summaries),
        "every failure kind has a summary no other kind has",
        repr(sorted(summaries.values())),
    )


# --------------------------------------------------------------------------
# The failure kinds, end to end
# --------------------------------------------------------------------------


def kind_of(payload: dict, identifier: str) -> str | None:
    for entry in payload.get("catalogs", []):
        if entry["id"] == identifier:
            failure = entry.get("failure")
            return failure["kind"] if failure else None
    return "(no such catalogue in the report)"


def state_of(payload: dict, identifier: str) -> str:
    for entry in payload.get("catalogs", []):
        if entry["id"] == identifier:
            return entry["state"]
    return "(no such catalogue in the report)"


def expect_kind(
    label: str, payload: dict, identifier: str, expected: str, text: str = ""
) -> None:
    got = kind_of(payload, identifier)
    if got == expected:
        _fired_kinds.add(expected)
        record(True, label)
    else:
        record(
            False,
            label,
            f"expected kind {expected!r}, got {got!r}. Report:\n"
            + json.dumps(payload.get("catalogs", []), indent=2)[:1800]
            + (f"\n{text[:800]}" if text else ""),
        )


def test_unreachable_and_no_access() -> None:
    print("\nthe git failures a local repository cannot produce:")
    for label, expected, message in GIT_MESSAGES:
        if expected == "no-ref":
            continue  # produced for real, below
        with temp_env() as env:
            env.write_config(git_config("remote", "git@github.com:skomp/x.git"))
            with path_prefixed(env.bin, message):
                code, payload = env.run_json("discover")
            expect_kind(
                f"{label!r} reaches the report as {expected}", payload, "remote", expected
            )
            # The fake git must really have been invoked: git's own words are
            # in the detail. Without this, a run in which git was never called
            # at all would pass.
            detail = ""
            for entry in payload.get("catalogs", []):
                if entry["id"] == "remote" and entry.get("failure"):
                    detail = entry["failure"]["detail"]
            first_line = message.splitlines()[0].strip()
            record(
                first_line in detail,
                f"  git's own first line reaches the report: {first_line[:54]!r}",
                f"detail was {detail!r}",
            )
            record(
                code == 3,
                "  a catalogue that fails with no cache leaves nothing to serve "
                "(exit 3)",
                f"exit was {code}",
            )


def test_no_git_binary() -> None:
    print("\ngit is not installed:")
    with temp_env() as env:
        env.write_config(git_config("remote", "git@github.com:skomp/x.git"))
        with path_only(env.empty_bin):
            record(
                shutil.which("git") is None,
                "the fixture really hides git from PATH",
                f"which('git') = {shutil.which('git')!r}",
            )
            code, payload = env.run_json("discover")
        expect_kind("a missing git binary is its own kind", payload, "remote", "no-git")


def test_real_git_success_and_failures() -> None:
    print("\nreal git, against a local repository over file://:")
    with temp_env() as env:
        url = make_repo(
            env.root / "remote",
            {
                "catalog.yaml": catalog_doc(("demo-course", "demo-bundle")),
                "demo-bundle/tutorial.yaml": "id: demo-course\n",
                "demo-bundle/STATE.template.md": "---\nstatus: not-started\n---\n",
            },
        )

        # -- success
        env.write_config(git_config("demo", url))
        code, payload = env.run_json("discover")
        record(
            code == 0 and state_of(payload, "demo") == "current",
            "a real clone answers, and the catalogue is current",
            f"exit {code}, state {state_of(payload, 'demo')!r}, "
            f"failure {kind_of(payload, 'demo')!r}",
        )
        ids = [e["id"] for e in payload.get("tutorials", [])]
        record(
            ids == ["demo-course"],
            "the repository's own catalogue supplies its own bundle",
            f"tutorials = {ids}",
        )
        entry = payload["tutorials"][0]
        record(
            entry["resolved_path"].endswith("/repo/demo-bundle")
            and str(env.cache) in entry["resolved_path"],
            "the bundle path resolves inside the cached clone, relative to "
            "the catalogue's own root",
            f"resolved_path = {entry['resolved_path']!r}",
        )
        record(
            bool(payload["catalogs"][0]["commit"]),
            "the report names the commit that was fetched",
            repr(payload["catalogs"][0]),
        )

        # -- a second run updates the clone rather than re-cloning
        code, payload = env.run_json("discover")
        record(
            code == 0 and state_of(payload, "demo") == "current",
            "a second refresh of an existing clone succeeds",
            f"exit {code}, failure {kind_of(payload, 'demo')!r}",
        )

        # -- the ref is not in the repository. REAL git says so.
        env.write_config(git_config("demo2", url, ref="no-such-branch"))
        code, payload = env.run_json("discover")
        expect_kind(
            "a branch that is not in the repository is its own kind",
            payload,
            "demo2",
            "no-ref",
        )

        # -- the repository is fine; the catalogue file is not at that path
        env.write_config(git_config("demo3", url, path="somewhere/catalog.yaml"))
        code, payload = env.run_json("discover")
        expect_kind(
            "a repository with no catalogue file at that path is its own kind",
            payload,
            "demo3",
            "no-catalogue",
        )
        detail = payload["catalogs"][0]["failure"]["detail"]
        record(
            "demo-bundle" in detail and "catalog.yaml" in detail,
            "  and the message lists what the repository DOES hold, so the "
            "path can be corrected",
            f"detail = {detail!r}",
        )


def test_file_catalogue_failures() -> None:
    print("\nthe failures of a local catalogue file:")
    with temp_env() as env:
        env.write_config(file_config(("mine", env.root / "nowhere.yaml")))
        code, payload = env.run_json("discover")
        expect_kind(
            "a catalogue file that is not there is its own kind",
            payload,
            "mine",
            "missing-file",
        )

    with temp_env() as env:
        broken = env.root / "broken.yaml"
        broken.write_bytes(b"catalog_version: 1\ntutorials: []\n\xff\xfe not text\n")
        env.write_config(file_config(("mine", broken)))
        code, payload = env.run_json("discover")
        expect_kind(
            "a catalogue that is not UTF-8 text is its own kind",
            payload,
            "mine",
            "unreadable",
        )

    with temp_env() as env:
        env.write_catalog("mine.yaml", "catalog_version: 2\ntutorials: []\n")
        env.write_config(file_config(("mine", env.root / "mine.yaml")))
        code, payload = env.run_json("discover")
        expect_kind(
            "a catalog_version this runner does not know is malformed, not a "
            "guess",
            payload,
            "mine",
            "malformed",
        )
        record(
            "catalog_version" in payload["catalogs"][0]["failure"]["detail"],
            "  and the message names the field",
            repr(payload["catalogs"][0]["failure"]["detail"]),
        )

    with temp_env() as env:
        env.write_catalog("mine.yaml", "catalog_version: 1\ntutorials:\n\t- id: x\n")
        env.write_config(file_config(("mine", env.root / "mine.yaml")))
        code, payload = env.run_json("discover")
        expect_kind(
            "a catalogue that does not parse is malformed",
            payload,
            "mine",
            "malformed",
        )


def test_bundled_catalogue() -> None:
    print("\nthe catalogue that ships with the plugin:")
    with temp_env() as env:
        env.write_config(
            "catalogs_version: 1\ncatalogs:\n  - id: builtin\n"
            "    source: { type: bundled }\n"
        )
        code, payload = env.run_json("discover")
        record(
            code == 0 and state_of(payload, "builtin") == "current",
            "the bundled catalogue is served",
            f"exit {code}, {payload.get('catalogs')}",
        )
        ids = [e["id"] for e in payload["tutorials"]]
        record(
            "rust-cli-basics" in ids,
            "and it carries the example bundle",
            f"tutorials = {ids}",
        )
        entry = payload["tutorials"][0]
        expected = str(
            (REPO / "skills" / "tutorail" / "examples" / "rust-cli-basics").resolve()
        )
        record(
            entry["resolved_path"] == expected,
            "its bundle path resolves from the directory that holds the "
            "catalogue file",
            f"resolved_path = {entry['resolved_path']!r}, expected {expected!r}",
        )


# --------------------------------------------------------------------------
# The cache, and staleness
# --------------------------------------------------------------------------


def test_stale_fallback() -> None:
    print("\na failed refresh falls back to the cache, and says so:")
    with temp_env() as env:
        url = make_repo(
            env.root / "remote",
            {
                "catalog.yaml": catalog_doc(("demo-course", "demo-bundle")),
                "demo-bundle/tutorial.yaml": "id: demo-course\n",
                "demo-bundle/STATE.template.md": "---\nstatus: not-started\n---\n",
            },
        )
        env.write_config(git_config("demo", url))

        code, first = env.run_json("discover")
        record(
            code == 0 and state_of(first, "demo") == "current",
            "the first refresh succeeds and is current",
            f"exit {code}, state {state_of(first, 'demo')!r}",
        )
        fetched_at = first["catalogs"][0]["fetched_at"]

        # Now the host is unreachable. The catalogue must still be served.
        message = GIT_MESSAGES[0][2]
        with path_prefixed(env.bin, message):
            code, second = env.run_json("discover")
            _, text = env.run("discover")

        record(
            state_of(second, "demo") == "cached",
            "the failed refresh serves the last successful copy, marked cached",
            f"state {state_of(second, 'demo')!r}",
        )
        expect_kind(
            "  and the failure that caused it is still reported by kind",
            second,
            "demo",
            "unreachable",
        )
        ids = [e["id"] for e in second["tutorials"]]
        record(
            ids == ["demo-course"],
            "  the entries are still offered - discovery did not fail",
            f"tutorials = {ids}",
        )
        record(
            all(e["freshness"] == "cached" for e in second["tutorials"]),
            "  every entry from it is marked cached, never current",
            repr([(e["id"], e["freshness"]) for e in second["tutorials"]]),
        )
        record(
            second["catalogs"][0]["fetched_at"] == fetched_at,
            "  and the report carries the timestamp of the last SUCCESSFUL "
            "refresh, not of the failed attempt",
            f"{second['catalogs'][0]['fetched_at']!r} vs {fetched_at!r}",
        )
        record(code == 1, "  exit 1 says the result is partial", f"exit {code}")
        record(
            "SERVED FROM CACHE" in text
            and "demo" in text
            and "not current" in text,
            "  the human report names the catalogue and says the entries are "
            "not current",
            text[:1200],
        )

        # A later run that fetches nothing must NOT forget that the last
        # attempt failed. This is the quiet way "never present stale results
        # as current" gets broken: the success timestamp is still there.
        code, third = env.run_json("status")
        record(
            state_of(third, "demo") == "cached",
            "a later status, which fetches nothing, still reports it cached",
            f"state {state_of(third, 'demo')!r}",
        )

        # And a successful refresh clears the mark again.
        code, fourth = env.run_json("discover")
        record(
            code == 0 and state_of(fourth, "demo") == "current",
            "a refresh that succeeds again clears the cached marking",
            f"exit {code}, state {state_of(fourth, 'demo')!r}",
        )


def test_cache_is_not_reused_across_sources() -> None:
    print("\nthe cache belongs to a source, not to an id:")
    with temp_env() as env:
        url = make_repo(
            env.root / "remote",
            {"catalog.yaml": catalog_doc(("demo-course", "demo-bundle"))},
        )
        env.write_config(git_config("demo", url))
        code, _ = env.run_json("discover")
        record(code == 0, "the first source is cached", f"exit {code}")

        # Same id, different url. The cached copy answers for the OLD source,
        # so serving it would silently present one repository's courses as
        # another's.
        env.write_config(git_config("demo", "git@github.com:someone/else.git"))
        with path_prefixed(env.bin, GIT_MESSAGES[0][2]):
            code, payload = env.run_json("discover")
        record(
            state_of(payload, "demo") == "unavailable"
            and not payload["tutorials"],
            "a cached copy from a DIFFERENT source is not served",
            f"state {state_of(payload, 'demo')!r}, "
            f"tutorials {[e['id'] for e in payload['tutorials']]}",
        )
        detail = payload["catalogs"][0]["failure"]["detail"]
        record(
            "different source" in detail,
            "  and the report says why the cache was not used",
            repr(detail),
        )
        record(code == 3, "  exit 3 says nothing could be served", f"exit {code}")


def test_unavailable_is_reported() -> None:
    print("\na catalogue with nothing to fall back on:")
    with temp_env() as env:
        good = env.write_catalog("mine.yaml", catalog_doc(("mine-course", "b")))
        env.make_bundle("b")
        env.write_config(
            "catalogs_version: 1\ncatalogs:\n"
            f"  - id: mine\n    source: {{ type: file, path: {good} }}\n"
            "  - id: remote\n    source:\n      type: git\n"
            "      url: git@github.com:skomp/x.git\n      ref: main\n"
        )
        with path_prefixed(env.bin, GIT_MESSAGES[4][2]):
            code, payload = env.run_json("discover")
            _, text = env.run("discover")
        record(
            [e["id"] for e in payload["tutorials"]] == ["mine-course"],
            "the catalogue that answered is still served",
            repr([e["id"] for e in payload["tutorials"]]),
        )
        record(
            state_of(payload, "remote") == "unavailable" and code == 1,
            "the one that did not is reported unavailable, and the exit code "
            "says the result is partial",
            f"state {state_of(payload, 'remote')!r}, exit {code}",
        )
        record(
            "remote" in text and "could not be served at all" in text,
            "the human report names it, so 'nothing matched' is never said "
            "when a catalogue is simply missing",
            text[:1200],
        )


# --------------------------------------------------------------------------
# Precedence
# --------------------------------------------------------------------------


def test_precedence_and_override_reporting() -> None:
    print("\nprecedence: first match wins, and the override is announced:")
    with temp_env() as env:
        env.make_bundle("bundles/from-a")
        env.make_bundle("bundles/from-b")
        a = env.write_catalog(
            "a.yaml", catalog_doc(("shared", "bundles/from-a"), ("only-a", "bundles/from-a"))
        )
        b = env.write_catalog(
            "b.yaml", catalog_doc(("shared", "bundles/from-b"), ("only-b", "bundles/from-b"))
        )

        env.write_config(file_config(("alpha", a), ("beta", b)))
        code, payload = env.run_json("discover")
        _, text = env.run("discover")
        winner = next(e for e in payload["tutorials"] if e["id"] == "shared")
        record(
            winner["catalog"] == "alpha",
            "the catalogue listed first supplies a contested id",
            f"catalog = {winner['catalog']!r}",
        )
        record(
            winner["resolved_path"].endswith("from-a"),
            "  and the bundle really is the first catalogue's bundle, not "
            "just its name",
            f"resolved_path = {winner['resolved_path']!r}",
        )
        record(
            [s["catalog"] for s in winner["shadows"]] == ["beta"],
            "  the entry records which catalogue it shadowed",
            repr(winner["shadows"]),
        )
        record(
            len(payload["shadowed"]) == 1
            and payload["shadowed"][0]["id"] == "shared"
            and payload["shadowed"][0]["catalog"] == "beta",
            "  the shadowed entry is listed rather than dropped silently",
            repr(payload["shadowed"]),
        )
        record(
            "OVERRIDES" in text and "beta" in text and "alpha" in text,
            "  and the human report says which catalogue supplied it and "
            "which was shadowed",
            text[:1600],
        )
        record(
            sorted(e["id"] for e in payload["tutorials"])
            == ["only-a", "only-b", "shared"],
            "  uncontested entries from both catalogues are still offered",
            repr([e["id"] for e in payload["tutorials"]]),
        )

        # Reverse the order. Precedence must follow the FILE, not the ids.
        env.write_config(file_config(("beta", b), ("alpha", a)))
        code, payload = env.run_json("discover")
        winner = next(e for e in payload["tutorials"] if e["id"] == "shared")
        record(
            winner["catalog"] == "beta"
            and winner["resolved_path"].endswith("from-b"),
            "reversing the order in catalogs.yaml reverses which entry wins",
            f"catalog = {winner['catalog']!r}, path = {winner['resolved_path']!r}",
        )

        # The negative direction: with no contest there must be NO override
        # notice. A reporter that always announces one proves nothing.
        env.write_config(file_config(("alpha", a)))
        code, payload = env.run_json("discover")
        _, text = env.run("discover")
        winner = next(e for e in payload["tutorials"] if e["id"] == "shared")
        record(
            winner["shadows"] == [] and not payload["shadowed"],
            "an id only one catalogue carries records no override",
            repr(winner["shadows"]),
        )
        record(
            "OVERRIDES" not in text and "shadowed entries" not in text,
            "  and the human report does not announce one",
            text[:1200],
        )


def test_implied_default_keeps_the_old_two_file_model() -> None:
    print("\nno catalogs.yaml: the two-file model keeps working:")
    with temp_env() as env:
        env.make_bundle("bundles/mine")
        (env.config_dir / "catalog.yaml").write_text(
            catalog_doc(("mine-course", str(env.root / "bundles" / "mine")),
                        ("rust-cli-basics", str(env.root / "bundles" / "mine"))),
            encoding="utf-8",
        )
        record(
            not env.config.exists(),
            "the fixture really has no catalogs.yaml",
            f"{env.config} exists",
        )
        code, payload = env.run_json("discover")
        record(
            payload["implied_default"] and code == 0,
            "the implied default is used, and discovery succeeds",
            f"exit {code}, implied {payload.get('implied_default')!r}",
        )
        listed = [c["id"] for c in payload["catalogs"]]
        record(
            listed == ["user", "builtin"],
            "it is the user catalogue followed by the bundled one",
            f"catalogs = {listed}",
        )
        winner = next(e for e in payload["tutorials"] if e["id"] == "rust-cli-basics")
        record(
            winner["catalog"] == "user"
            and [s["catalog"] for s in winner["shadows"]] == ["builtin"],
            "the user's entry overrides the shipped one, and says so",
            f"catalog = {winner['catalog']!r}, shadows = {winner['shadows']!r}",
        )

        _, text = env.run("status")
        record(
            "catalogs_version: 1" in text and "type: bundled" in text,
            "status prints the configuration the default implies, so it can "
            "be written down before a catalogue is added",
            text[:1400],
        )

    # And with no user file either, only the bundled catalogue is listed. A
    # missing user catalogue is the normal first run, not a failure.
    with temp_env() as env:
        code, payload = env.run_json("discover")
        record(
            [c["id"] for c in payload["catalogs"]] == ["builtin"]
            and code == 0
            and not any(c["failure"] for c in payload["catalogs"]),
            "a first run with neither file reports no failure at all",
            f"exit {code}, catalogs = {payload.get('catalogs')}",
        )


# --------------------------------------------------------------------------
# The provider boundary
# --------------------------------------------------------------------------


def test_discovery_never_opens_a_bundle() -> None:
    print("\ndiscovery loads metadata only:")
    with temp_env() as env:
        # The bundle path does not exist at all. Discovery must not care.
        mine = env.write_catalog("mine.yaml", catalog_doc(("ghost", "bundles/ghost")))
        env.write_config(file_config(("mine", mine)))
        record(
            not (env.root / "bundles" / "ghost").exists(),
            "the fixture's bundle directory really is absent",
            "it exists",
        )
        code, payload = env.run_json("discover")
        record(
            code == 0 and [e["id"] for e in payload["tutorials"]] == ["ghost"],
            "discovery offers an entry whose bundle is not on disk - it never "
            "looked",
            f"exit {code}, tutorials {[e['id'] for e in payload['tutorials']]}",
        )

        # resolve is the step that IS allowed to look, and it reports the gap.
        code, payload = env.run_json("resolve", "ghost")
        record(
            code == 1
            and payload["found"]
            and not payload["bundle_present"]
            and payload["problems"],
            "resolve, which runs after the learner has chosen, reports the "
            "missing bundle",
            repr(payload),
        )

        code, payload = env.run_json("resolve", "no-such-course")
        record(
            code == 3 and payload["found"] is False,
            "resolve names what is available when the id is unknown",
            repr(payload),
        )

        env.make_bundle("bundles/ghost")
        code, payload = env.run_json("resolve", "ghost")
        record(
            code == 0 and payload["bundle_present"] and not payload["problems"],
            "and it passes once the bundle carries tutorial.yaml and "
            "STATE.template.md",
            repr(payload),
        )


def test_remote_catalogue_cannot_reach_outside_itself() -> None:
    print("\na catalogue fetched from a repository may only name its own bundles:")
    with temp_env() as env:
        url = make_repo(
            env.root / "remote",
            {
                "catalog.yaml": catalog_doc(
                    ("escaping", "../../../../etc"),
                    ("absolute", "/etc"),
                    ("good", "demo-bundle"),
                ),
                "demo-bundle/tutorial.yaml": "id: good\n",
                "demo-bundle/STATE.template.md": "---\nstatus: not-started\n---\n",
            },
        )
        env.write_config(git_config("demo", url))
        code, payload = env.run_json("discover")
        _, text = env.run("discover")
        offered = [e["id"] for e in payload["tutorials"]]
        record(
            offered == ["good"],
            "an entry naming a path outside the clone is skipped; the rest "
            "of the catalogue is still served",
            f"tutorials = {offered}",
        )
        skipped = payload["catalogs"][0]["skipped"]
        record(
            len(skipped) == 2
            and all("leaves the catalogue" in s["reason"] for s in skipped),
            "  both the '..' path and the absolute path are skipped, with a "
            "reason",
            repr(skipped),
        )
        record(
            "skipped" in text and "escaping" in text,
            "  and the skip is visible in the human report, not silent",
            text[:1400],
        )

    # The negative direction: a LOCAL catalogue is the user's own file and may
    # legitimately name bundles anywhere on their machine. A guard that fired
    # here would break every existing user catalogue.
    with temp_env() as env:
        outside = env.make_bundle("elsewhere/course")
        mine = env.write_catalog(
            "cat/mine.yaml", catalog_doc(("outside", str(outside)))
        )
        env.write_config(file_config(("mine", mine)))
        code, payload = env.run_json("discover")
        record(
            code == 0 and [e["id"] for e in payload["tutorials"]] == ["outside"],
            "the user's own catalogue may name a bundle anywhere",
            f"exit {code}, skipped "
            f"{payload['catalogs'][0]['skipped'] if payload.get('catalogs') else '?'}",
        )


def test_malformed_entries_are_skipped_not_fatal() -> None:
    print("\none bad entry does not hide a catalogue:")
    with temp_env() as env:
        env.make_bundle("b")
        mine = env.write_catalog(
            "mine.yaml",
            "catalog_version: 1\n"
            "tutorials:\n"
            "  - id: no-title\n"
            "    description: It has no title.\n"
            "    subjects: [testing]\n"
            "    level: beginner\n"
            "    workspace_kind: new-repository\n"
            "    source: { type: local, path: b }\n"
            "  - id: remote-bundle\n"
            "    title: A bundle in a repository\n"
            "    description: Declared but not implemented.\n"
            "    subjects: [testing]\n"
            "    level: beginner\n"
            "    workspace_kind: new-repository\n"
            "    source: { type: git, url: git@example.invalid:x.git }\n"
            + catalog_doc(("fine", "b")).split("tutorials:\n", 1)[1],
        )
        env.write_config(file_config(("mine", mine)))
        code, payload = env.run_json("discover")
        _, text = env.run("discover")
        record(
            [e["id"] for e in payload["tutorials"]] == ["fine"],
            "the well-formed entry is served",
            repr([e["id"] for e in payload["tutorials"]]),
        )
        reasons = " ".join(s["reason"] for s in payload["catalogs"][0]["skipped"])
        record(
            "title" in reasons and "not implemented" in reasons,
            "the malformed entry and the unimplemented source type are each "
            "named, with their own reason",
            repr(payload["catalogs"][0]["skipped"]),
        )
        record(
            "no-title" in text and "remote-bundle" in text,
            "and both are visible in the human report",
            text[:1400],
        )


# --------------------------------------------------------------------------
# The catalogue of catalogues itself
# --------------------------------------------------------------------------


def test_configuration_errors() -> None:
    print("\nthe catalogue of catalogues decides everything, so it fails loudly:")
    cases = [
        (
            "a tab indents the file",
            "catalogs_version: 1\ncatalogs:\n\t- id: a\n",
            "tab",
        ),
        (
            "catalogs is empty",
            "catalogs_version: 1\ncatalogs: []\n",
            "non-empty list",
        ),
        (
            "two catalogues share an id",
            "catalogs_version: 1\ncatalogs:\n"
            "  - id: a\n    source: { type: bundled }\n"
            "  - id: a\n    source: { type: file, path: /tmp/x.yaml }\n",
            "used more than once",
        ),
        (
            "an id that would escape the cache directory",
            "catalogs_version: 1\ncatalogs:\n"
            "  - id: ../../evil\n    source: { type: bundled }\n",
            "names a cache directory",
        ),
        (
            "an unknown source type",
            "catalogs_version: 1\ncatalogs:\n"
            "  - id: a\n    source: { type: ftp, path: x }\n",
            "is not one of",
        ),
        (
            "a git source with no url",
            "catalogs_version: 1\ncatalogs:\n"
            "  - id: a\n    source: { type: git, ref: main }\n",
            "requires the field 'url'",
        ),
        (
            "a git path that climbs out of the repository",
            "catalogs_version: 1\ncatalogs:\n"
            "  - id: a\n    source:\n      type: git\n"
            "      url: git@example.invalid:x.git\n"
            "      path: ../../etc/passwd\n",
            "must stay inside the repository",
        ),
        (
            "a catalogs_version this runner does not know",
            "catalogs_version: 9\ncatalogs:\n"
            "  - id: a\n    source: { type: bundled }\n",
            "does not know",
        ),
        (
            "a catalogue with no source",
            "catalogs_version: 1\ncatalogs:\n  - id: a\n",
            "has no 'source'",
        ),
    ]
    for label, text, expected in cases:
        with temp_env() as env:
            env.write_config(text)
            code, output = env.run("discover")
            record(
                code == 2 and expected in output,
                f"{label} is refused (exit 2), naming the reason",
                f"exit {code}; output was:\n       "
                + output.replace("\n", "\n       ")[:900],
            )

    # The positive control: a configuration of the same shape, correct, is
    # accepted. Without it, every case above would also pass a parser that
    # rejected everything.
    with temp_env() as env:
        env.write_config(
            "catalogs_version: 1\ncatalogs:\n"
            "  - id: builtin\n    source: { type: bundled }\n"
        )
        code, _ = env.run("discover")
        record(code == 0, "a correct configuration of the same shape is accepted",
               f"exit {code}")


def test_offline() -> None:
    print("\n--offline serves what is on disk and fetches nothing:")
    with temp_env() as env:
        url = make_repo(
            env.root / "remote",
            {"catalog.yaml": catalog_doc(("demo-course", "demo-bundle"))},
        )
        env.write_config(git_config("demo", url))
        code, _ = env.run_json("discover")
        record(code == 0, "seeded the cache", f"exit {code}")
        # No git at all. Offline must still answer from the clone.
        with path_only(env.empty_bin):
            code, payload = env.run_json("discover", "--offline")
        record(
            code == 0 and [e["id"] for e in payload["tutorials"]] == ["demo-course"],
            "with git removed entirely, --offline still serves the clone",
            f"exit {code}, {payload.get('catalogs')}",
        )


# --------------------------------------------------------------------------
# The validator's catalogue mode
# --------------------------------------------------------------------------

CATALOG_CASES: list[tuple[str, int, str, str, bool]] = [
    (
        "1: the catalogue does not parse",
        1,
        "catalog_version: 1\ntutorials:\n\t- id: a\n",
        "a tab is used for indentation",
        False,
    ),
    (
        "1: catalog_version is missing",
        1,
        "tutorials: []\n",
        "'catalog_version' is missing",
        False,
    ),
    (
        "1: catalog_version is unknown",
        1,
        "catalog_version: 7\ntutorials: []\n",
        "not a guess",
        False,
    ),
    (
        "1: an unknown top-level field",
        1,
        "catalog_version: 1\ncatalogs: []\ntutorials: []\n",
        "unknown top-level field(s) catalogs",
        False,
    ),
    (
        "2: tutorials is missing",
        2,
        "catalog_version: 1\n",
        "'tutorials' is missing",
        False,
    ),
    (
        "2: the tutorials list is empty",
        2,
        "catalog_version: 1\ntutorials: []\n",
        "offers nothing",
        False,
    ),
    (
        "2: an entry is not a mapping",
        2,
        "catalog_version: 1\ntutorials:\n  - just-a-string\n",
        "must be a mapping",
        False,
    ),
    (
        "3: a required field is missing",
        3,
        catalog_doc(("a", "bundle")).replace("    level: beginner\n", ""),
        "the required field 'level' is missing",
        False,
    ),
    (
        "3: subjects is a bare string, not a list",
        3,
        catalog_doc(("a", "bundle")).replace(
            "    subjects: [testing]", "    subjects: testing"
        ),
        "'subjects' must be a non-empty list of strings",
        False,
    ),
    (
        "3: an unknown workspace_kind",
        3,
        catalog_doc(("a", "bundle")).replace(
            "new-repository", "existing-repository"
        ),
        "not one of",
        False,
    ),
    (
        "4: two entries share an id",
        4,
        catalog_doc(("a", "bundle"), ("a", "bundle")),
        "precedence undecidable",
        False,
    ),
    (
        "4: an id that is not [a-z0-9-]+",
        4,
        catalog_doc(("A_Course", "bundle")),
        "must match [a-z0-9-]+",
        False,
    ),
    (
        "5: a source type the runner does not implement",
        5,
        catalog_doc(("a", "bundle")).replace(
            "      type: local", "      type: archive"
        ),
        "declared but not implemented",
        False,
    ),
    (
        "5: a local source with no path",
        5,
        catalog_doc(("a", "bundle")).replace("      path: bundle\n", ""),
        "requires a non-empty 'path'",
        False,
    ),
    (
        "6: the bundle directory is not there",
        6,
        catalog_doc(("a", "no-such-bundle")),
        "which is not a directory",
        False,
    ),
    (
        "6: the directory is not a bundle",
        6,
        catalog_doc(("a", "empty-dir")),
        "tutorial.yaml is missing",
        False,
    ),
    (
        "7: a bundle path leaves the catalogue's directory",
        7,
        catalog_doc(("a", "../outside-bundle")),
        "may only name bundles that travel with it",
        True,
    ),
]


def test_validator_catalog_mode() -> None:
    print("\nthe validator's catalogue mode, each check firing:")
    for label, check, text, expected, portable in CATALOG_CASES:
        with temp_env() as env:
            base = env.root / "cat"
            base.mkdir(parents=True, exist_ok=True)
            (base / "bundle").mkdir(exist_ok=True)
            (base / "bundle" / "tutorial.yaml").write_text("id: a\n")
            (base / "bundle" / "STATE.template.md").write_text("---\n---\n")
            (base / "empty-dir").mkdir(exist_ok=True)
            outside = env.root / "outside-bundle"
            outside.mkdir(exist_ok=True)
            (outside / "tutorial.yaml").write_text("id: a\n")
            (outside / "STATE.template.md").write_text("---\n---\n")
            target = base / "catalog.yaml"
            target.write_text(text, encoding="utf-8")
            report = vb.validate_catalog(target, portable)
            hits = [f for f in report.findings if f.check == check]
            if not hits:
                record(
                    False,
                    label,
                    f"check {check} did not fire. Findings: "
                    + ("; ".join(str(f) for f in report.findings) or "(none)"),
                )
                continue
            if not any(expected in h.message for h in hits):
                record(
                    False,
                    label,
                    f"check {check} fired but no message contained "
                    f"{expected!r}: " + " || ".join(h.message for h in hits),
                )
                continue
            _fired_catalog_checks.add(check)
            record(True, label)

    # The positive controls. Without them every case above would pass a
    # validator that rejected every catalogue.
    with temp_env() as env:
        base = env.root / "cat"
        base.mkdir(parents=True)
        env.make_bundle("cat/bundle")
        target = base / "catalog.yaml"
        target.write_text(catalog_doc(("a", "bundle")), encoding="utf-8")
        report = vb.validate_catalog(target, portable=False)
        record(
            report.exit_code() == 0,
            "a well-formed catalogue passes",
            "; ".join(str(f) for f in report.findings)
            or f"blocked = {report.blocked_checks}",
        )
        report = vb.validate_catalog(target, portable=True)
        record(
            report.exit_code() == 0,
            "and it passes --portable too, since its bundle travels with it",
            "; ".join(str(f) for f in report.findings),
        )
        record(
            report.status.get(7, ("", ""))[0] == vb.RAN,
            "check 7 actually RAN under --portable",
            repr(report.status.get(7)),
        )
        report = vb.validate_catalog(target, portable=False)
        record(
            report.status.get(7, ("", ""))[0] == vb.NOT_APPLICABLE,
            "and reports n/a without it, rather than quietly passing",
            repr(report.status.get(7)),
        )

    shipped = REPO / "skills" / "tutorail" / "catalog" / "builtin.yaml"
    report = vb.validate_catalog(shipped, portable=False)
    record(
        report.exit_code() == 0,
        "the shipped catalogue validates",
        "; ".join(str(f) for f in report.findings)
        or f"blocked = {report.blocked_checks}",
    )

    # The mode is never inferred: a bundle handed to catalogue mode fails,
    # and a catalogue handed to bundle mode fails.
    example = REPO / "skills" / "tutorail" / "examples" / "rust-cli-basics"
    quiet = io.StringIO()
    with redirect_stderr(quiet), redirect_stdout(quiet):
        as_bundle = vb.main([str(shipped)])
        bundle_as_catalog = vb.main(["--catalog", str(example)])
        portable_alone = vb.main(["--portable", str(example)])
    record(as_bundle != 0, "a catalogue checked as a BUNDLE fails", f"exit {as_bundle}")
    record(
        bundle_as_catalog == 2,
        "a bundle directory handed to --catalog is refused as a usage error",
        f"exit {bundle_as_catalog}",
    )
    record(
        portable_alone == 2,
        "--portable without --catalog is refused",
        f"exit {portable_alone}",
    )


# --------------------------------------------------------------------------
# The command-line surface
# --------------------------------------------------------------------------


def test_cli() -> None:
    print("\nthe command line:")
    with temp_env() as env:
        env.write_config(
            "catalogs_version: 1\ncatalogs:\n  - id: builtin\n"
            "    source: { type: bundled }\n"
        )
        code, text = env.run("discover")
        record(
            "Nothing under a bundle path was opened" in text,
            "discover states the rule it kept",
            text[:600],
        )
        code, text = env.run("status")
        record(
            "Nothing was fetched" in text and code == 0,
            "status says it fetched nothing",
            text[:600],
        )
    for argv in (["discover"], ["status"], ["resolve", "x"]):
        parser = cat.build_parser()
        args = parser.parse_args(argv)
        record(
            callable(getattr(args, "run", None)),
            f"the {argv[0]!r} subcommand is wired to a command",
            repr(args),
        )
    out = io.StringIO()
    err = io.StringIO()
    try:
        with redirect_stderr(err):
            cat.main([], stream=out)
        record(False, "a missing subcommand is refused", "it was accepted")
    except SystemExit as exc:
        record(exc.code == 2, "a missing subcommand is refused", f"exit {exc.code}")


# --------------------------------------------------------------------------
# Meta
# --------------------------------------------------------------------------


def test_kind_coverage() -> None:
    print("\nmeta: every failure kind has a fixture that makes it fire:")
    for kind in sorted(cat.FAILURE_KINDS):
        record(
            kind in _fired_kinds,
            f"kind {kind!r} was demonstrated firing",
            "NO fixture in this suite produces this kind, so it is a false "
            "oracle: it can only be shown not happening.",
        )


def test_catalog_check_coverage() -> None:
    print("\nmeta: every catalogue check has a fixture that makes it fire:")
    for number, description in sorted(vb.CATALOG_CHECKS.items()):
        record(
            number in _fired_catalog_checks,
            f"catalogue check {number} was demonstrated firing  "
            f"({description[:52]})",
            "NO fixture in this suite makes this check report a finding.",
        )


# --------------------------------------------------------------------------


def main() -> int:
    print("catalogs.py test suite")
    print(f"  script:      {SCRIPTS / 'catalogs.py'}")
    print(f"  yaml reader: {cat.YAML_READER}")
    print(f"  python:      {sys.version.split()[0]}")
    real_git = shutil.which("git")
    print(f"  git:         {real_git}")
    if real_git is None:
        print("\nFAILED - this suite needs a real git for its positive control.")
        return 1

    for test in (
        test_classifier,
        test_unreachable_and_no_access,
        test_no_git_binary,
        test_real_git_success_and_failures,
        test_file_catalogue_failures,
        test_bundled_catalogue,
        test_stale_fallback,
        test_cache_is_not_reused_across_sources,
        test_unavailable_is_reported,
        test_precedence_and_override_reporting,
        test_implied_default_keeps_the_old_two_file_model,
        test_discovery_never_opens_a_bundle,
        test_remote_catalogue_cannot_reach_outside_itself,
        test_malformed_entries_are_skipped_not_fatal,
        test_configuration_errors,
        test_offline,
        test_validator_catalog_mode,
        test_cli,
    ):
        try:
            test()
        except Exception:  # pragma: no cover
            record(False, test.__name__, "raised:\n" + traceback.format_exc())

    test_kind_coverage()
    test_catalog_check_coverage()

    if _notes:
        print("\nnotes:")
        for text in _notes:
            print(text)

    print()
    if _failures:
        print(f"FAILED - {len(_failures)} of {_passed + len(_failures)} assertions:")
        for text in _failures:
            print(f"  - {text}")
        return 1
    print(f"OK - {_passed} assertions passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
