#!/usr/bin/env python3
"""Test suite for skills/tutorail/scripts/validate_bundle.py.

Run it with:  python3 tests/test_validate_bundle.py

No pytest, no PyYAML - nothing is installed in this environment.

The point of this suite is NOT to show the validator passing. A validator that
can only be shown passing is a false oracle. Every check gets a deliberately
broken fixture and the suite asserts THAT SPECIFIC check fires with a message
the bundle's author could act on. The meta-test at the end fails if any check
in validate_bundle.CHECKS has no fixture that makes it fire.

Two traps this suite is built around:

  * The local filesystem is CASE-INSENSITIVE. Renaming LESSON.md to lesson.md
    is a no-op unless the old entry is removed first, so the mis-cased fixture
    verifies the directory listing rather than assuming the shell worked.

  * A reverse material check ("LESSON.md names a file that does not exist")
    was implemented and deleted upstream because it cannot tell a material
    reference from an ordinary prose mention. It must not come back, so there
    is no test for it.

Positive-fixture baselines are copies of real, known-good bundles. They are
never mutated in place: each case works on a fresh copy in a temp directory.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
SCRIPT = REPO / "skills" / "tutorail" / "scripts" / "validate_bundle.py"
FIXTURES = HERE / "fixtures"

sys.path.insert(0, str(SCRIPT.parent))
import validate_bundle as vb  # noqa: E402

# --------------------------------------------------------------------------
# Baselines
# --------------------------------------------------------------------------

BASELINES = {
    # 23 single-file lessons, 23 DESIGN.md anchors, 6 validators.
    "automaton": FIXTURES / "rust-automaton-db",
    # 3 lessons, one of them foldered with two material files.
    "cli": FIXTURES / "rust-cli-basics",
    # Hand-built: one single-file lesson, one foldered lesson with nested
    # material, workspace_kind: none with an empty learner_owned.
    "foldered": FIXTURES / "foldered-bundle",
}

# Baselines that are already INSTANCES and must not be run through
# to_instance(). lessons.generated/ cannot appear in a bundle at all (check
# 13), so the generated-lesson feature is only expressible here.
INSTANCE_BASELINES = {
    # An instance of rust-cli-basics carrying two generated lessons: a
    # single-file side-lesson, which STATE.md is sitting on, and a foldered
    # main-path-draft with one material file.
    "generated": FIXTURES / "generated-instance",
}

ALL_BASELINES = {**BASELINES, **INSTANCE_BASELINES}

# The backward-compatibility control. Neither of these declares
# `optional_lessons` or `failure_modes`, and both must keep validating exactly
# as they did before those keys existed - in bundle mode and in instance mode.
NO_OPTIONAL_BASELINES = ("automaton", "foldered")

Mutator = Callable[[Path], None]


def fresh(baseline: str, tmp: Path) -> Path:
    root = tmp / "target"
    shutil.copytree(ALL_BASELINES[baseline], root)
    return root


def to_instance(root: Path) -> None:
    """Turn a bundle copy into a well-formed instance."""
    template = root / "STATE.template.md"
    text = template.read_text()
    assert "status: not-started" in text
    text = text.replace("status: not-started", "status: in-progress").replace(
        "updated: null", "updated: 2026-09-11"
    )
    (root / "STATE.md").write_text(text)
    template.unlink()
    with (root / "tutorial.yaml").open("a", encoding="utf-8") as handle:
        handle.write(
            "\ninstance:\n"
            "  materialized_from: local:../tests/fixtures\n"
            "  materialized_at: 2026-09-11\n"
            "  runner_version: 1\n"
        )


def edit(path: Path, old: str, new: str, count: int = 1) -> None:
    """Replace `old` with `new`, asserting `old` was really there.

    The assertion is the fixture verification: a mutation that silently did
    nothing would otherwise produce a test that proves nothing.
    """
    text = path.read_text()
    assert old in text, f"{path.name}: expected to find {old!r} to mutate"
    path.write_text(text.replace(old, new, count))


def append(path: Path, extra: str) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(extra)


# --------------------------------------------------------------------------
# Mutators, grouped by the check they are meant to trip
# --------------------------------------------------------------------------


# -- check 1: design_refs -> DESIGN.md anchors


def m_bad_design_ref(root: Path) -> None:
    edit(
        root / "lessons" / "03-first-refactor.md",
        "design_refs: [table-model,",
        "design_refs: [tbale-model,",
    )


def m_anchor_renamed(root: Path) -> None:
    edit(root / "DESIGN.md", "{#row-cell-model}", "{#row-and-cell-model}")


def m_design_refs_not_a_list(root: Path) -> None:
    edit(
        root / "lessons" / "03-first-refactor.md",
        "design_refs: [table-model, row-cell-model, partition-key, clustering-key]",
        "design_refs: table-model",
    )


# -- check 2: lesson validators -> tutorial.yaml validators


def m_undeclared_validator(root: Path) -> None:
    edit(
        root / "lessons" / "03-first-refactor.md",
        "validators: [cargo-check,",
        "validators: [cargo-clippy,",
    )


def m_validator_removed_from_manifest(root: Path) -> None:
    edit(
        root / "tutorial.yaml",
        "  has-lib: { kind: file-exists, path: src/lib.rs }\n",
        "",
    )


# -- check 3: lesson frontmatter


def m_id_not_slug(root: Path) -> None:
    edit(
        root / "lessons" / "03-first-refactor.md",
        "id: 03-first-refactor",
        "id: first-refactor",
    )


def m_no_title(root: Path) -> None:
    edit(
        root / "lessons" / "03-first-refactor.md",
        "title: The first deliberate refactor\n",
        "",
    )


def m_no_frontmatter(root: Path) -> None:
    path = root / "lessons" / "03-first-refactor.md"
    text = path.read_text()
    assert text.startswith("---\n")
    _, _, rest = text[4:].partition("\n---\n")
    assert rest, "expected a closing frontmatter fence to strip"
    path.write_text(rest)


def m_foldered_id_is_file_stem(root: Path) -> None:
    # A classic foldered-lesson mistake: the id copies the body's filename
    # instead of the folder name.
    edit(
        root / "lessons" / "01-subcommands" / "LESSON.md",
        "id: 01-subcommands",
        "id: LESSON",
    )


# -- check 4: the lessons list and lesson discovery


def m_unlisted_lesson(root: Path) -> None:
    body = (root / "lessons" / "00-foundations.md").read_text()
    target = root / "lessons" / "99-orphan.md"
    target.write_text(body.replace("id: 00-foundations", "id: 99-orphan"))
    assert target.is_file()


def m_entry_does_not_resolve(root: Path) -> None:
    edit(
        root / "tutorial.yaml",
        "  - lessons/03-first-refactor.md\n",
        "  - lessons/03-the-first-refactor.md\n",
    )


def m_entry_listed_twice(root: Path) -> None:
    edit(
        root / "tutorial.yaml",
        "  - lessons/03-first-refactor.md\n",
        "  - lessons/03-first-refactor.md\n  - lessons/03-first-refactor.md\n",
    )


def m_entry_case_differs(root: Path) -> None:
    edit(
        root / "tutorial.yaml",
        "  - lessons/03-first-refactor.md\n",
        "  - lessons/03-First-Refactor.md\n",
    )


def m_folder_without_lesson_md(root: Path) -> None:
    folder = root / "lessons" / "shared-diagrams"
    folder.mkdir()
    (folder / "overview.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'/>\n")
    assert os.listdir(folder) == ["overview.svg"]


def m_miscased_lesson_body(root: Path) -> None:
    """Replace LESSON.md with lesson.md - the case-insensitivity trap.

    A plain rename is a NO-OP on this filesystem. The old entry must be
    removed before the new one is written, and the directory listing must be
    checked afterwards; see v_miscased_lesson_body.
    """
    folder = root / "lessons" / "01-subcommands"
    body = (folder / "LESSON.md").read_text()
    (folder / "LESSON.md").unlink()
    (folder / "lesson.md").write_text(body)
    edit(
        root / "tutorial.yaml",
        "  - lessons/01-subcommands/LESSON.md\n",
        "  - lessons/01-subcommands/lesson.md\n",
    )


def v_miscased_lesson_body(root: Path) -> None:
    folder = root / "lessons" / "01-subcommands"
    names = os.listdir(folder)
    assert "lesson.md" in names, f"fixture did not take effect: {names}"
    assert "LESSON.md" not in names, (
        f"the directory still has an exact-case LESSON.md, so this fixture "
        f"tests nothing: {names}"
    )
    if (folder / "LESSON.md").exists():
        note(
            "  (confirmed: this filesystem is case-insensitive - "
            "Path('LESSON.md').exists() is True while the real entry is "
            "'lesson.md'. That is exactly what check 4 has to see through.)"
        )


def m_material_listed_as_lesson(root: Path) -> None:
    edit(
        root / "tutorial.yaml",
        "  - lessons/01-subcommands/LESSON.md\n",
        "  - lessons/01-subcommands/LESSON.md\n  - lessons/01-subcommands/usage.txt\n",
    )


def m_duplicate_slug(root: Path) -> None:
    # lessons/01-subcommands.md alongside lessons/01-subcommands/LESSON.md:
    # two lessons, one slug, so two lessons claim the same id.
    body = (root / "lessons" / "00-hello-args.md").read_text()
    target = root / "lessons" / "01-subcommands.md"
    target.write_text(body.replace("id: 00-hello-args", "id: 01-subcommands"))
    edit(
        root / "tutorial.yaml",
        "  - lessons/01-subcommands/LESSON.md\n",
        "  - lessons/01-subcommands/LESSON.md\n  - lessons/01-subcommands.md\n",
    )


# -- check 5: progress markers, positive direction


def m_marker_heading_annotated(root: Path) -> None:
    append(
        root / "lessons" / "03-first-refactor.md",
        "\n### 03 — First refactor (Complete)\n\nNotes follow.\n",
    )


def m_marker_status_label(root: Path) -> None:
    append(
        root / "lessons" / "03-first-refactor.md",
        "\n## Progress\n\nStatus: Complete\n",
    )


def m_marker_ticked_box(root: Path) -> None:
    append(
        root / "lessons" / "03-first-refactor.md",
        "\n## Checklist\n\n- [x] In progress\n- [ ] Not yet reached\n",
    )


def m_marker_current_heading(root: Path) -> None:
    append(root / "COURSE.md", "\n## Current tutorial state\n\nLesson 3.\n")


def m_marker_table_cell(root: Path) -> None:
    append(
        root / "COURSE.md",
        "\n| Lesson | State |\n|---|---|\n"
        "| 02-typed-keys-table-hierarchy | Complete |\n",
    )


def m_marker_bold_next_label(root: Path) -> None:
    append(
        root / "lessons" / "03-first-refactor.md",
        "\n**Next:** lessons/04-richer-typed-schemas.md\n",
    )


def m_marker_current_lesson_label(root: Path) -> None:
    append(
        root / "COURSE.md",
        "\nCurrent lesson: lessons/03-first-refactor.md\n",
    )


def m_marker_frontmatter_status(root: Path) -> None:
    edit(
        root / "lessons" / "03-first-refactor.md",
        "id: 03-first-refactor\n",
        "id: 03-first-refactor\nstatus: in-progress\n",
    )


def m_marker_resume_heading(root: Path) -> None:
    append(root / "COURSE.md", "\n## Current resume marker\n\nLesson 3.\n")


def m_marker_lone_list_item(root: Path) -> None:
    append(
        root / "COURSE.md",
        "\n## Chapter one\n\n- 00-foundations\n- Complete\n",
    )


# -- check 5: progress markers, NEGATIVE direction (must NOT fire)

PROSE_THAT_MUST_NOT_FIRE = """
## Theory of partial work

While the refactor is in progress, the engine is unreachable from the binary.
The next lesson introduces modules, and this status is complete once the tests
pass. Mark the work done only when `cargo test` agrees.

Status is complete only in the sense the compiler means it.

- Do not treat a partially complete refactor as finished.
- In progress work is not evidence; a passing test is.
- Next, read the theory section again before answering.
- Current state of the art in automaton minimisation is out of scope.

A resume marker is the thing STATE.md replaces, so a lesson never carries one.

| Concept | Why it matters |
|---|---|
| Modules | They make the refactor possible |
| Visibility | It decides what the binary can still see |
"""


def m_prose_only(root: Path) -> None:
    append(root / "lessons" / "03-first-refactor.md", PROSE_THAT_MUST_NOT_FIRE)
    append(root / "COURSE.md", PROSE_THAT_MUST_NOT_FIRE)


# -- check 6: lesson-folder material


def m_unnamed_material(root: Path) -> None:
    target = root / "lessons" / "01-subcommands" / "orphan-notes.md"
    target.write_text("# Notes\n\nNothing in LESSON.md names this file.\n")
    assert target.is_file()


def m_unnamed_nested_material(root: Path) -> None:
    folder = root / "lessons" / "01-state-merging" / "assets"
    target = folder / "unused.svg"
    target.write_text("<svg xmlns='http://www.w3.org/2000/svg'/>\n")
    assert target.is_file()


def m_material_named_only_inside_a_longer_path(root: Path) -> None:
    """A plain substring search would call this 'mentioned'. It is not.

    The filename appears only as part of a longer URL-ish token, which is
    what the tightened, delimiter-aware match exists to reject.
    """
    folder = root / "lessons" / "01-subcommands"
    (folder / "notes.md").write_text("# Notes\n\nReal material.\n")
    append(
        folder / "LESSON.md",
        "\nBackground reading lives at "
        "https://example.invalid/archive/notes.md.bak and is optional.\n",
    )


def m_material_properly_named(root: Path) -> None:
    """Control for the case above: the same file, named as a reference."""
    folder = root / "lessons" / "01-subcommands"
    (folder / "notes.md").write_text("# Notes\n\nReal material.\n")
    append(
        folder / "LESSON.md",
        "\nIf the learner asks where dispatch tables came from, read "
        "`notes.md` with them.\n",
    )


# -- check 7: the bundle/instance distinction


def m_bundle_has_state_md(root: Path) -> None:
    shutil.copy(root / "STATE.template.md", root / "STATE.md")
    assert "STATE.md" in os.listdir(root)


def m_bundle_missing_template(root: Path) -> None:
    (root / "STATE.template.md").unlink()
    assert "STATE.template.md" not in os.listdir(root)


def m_bundle_has_instance_stamp(root: Path) -> None:
    append(
        root / "tutorial.yaml",
        "\ninstance:\n  materialized_from: local:../somewhere\n"
        "  materialized_at: 2026-09-11\n  runner_version: 1\n",
    )


def m_instance_missing_state(root: Path) -> None:
    to_instance(root)
    (root / "STATE.md").unlink()
    assert "STATE.md" not in os.listdir(root)


def m_instance_has_template(root: Path) -> None:
    to_instance(root)
    shutil.copy(root / "STATE.md", root / "STATE.template.md")
    edit(root / "STATE.template.md", "status: in-progress", "status: not-started")


def m_instance_missing_stamp(root: Path) -> None:
    to_instance(root)
    text = (root / "tutorial.yaml").read_text()
    head, sep, _ = text.partition("\ninstance:\n")
    assert sep, "expected to_instance to have written an instance stamp"
    (root / "tutorial.yaml").write_text(head + "\n")


# -- check 8: the manifest


def m_missing_required_field(root: Path) -> None:
    path = root / "tutorial.yaml"
    text = path.read_text()
    start = text.index("description: >")
    end = text.index("subjects:")
    assert start < end
    path.write_text(text[:start] + text[end:])


def m_unknown_bundle_format(root: Path) -> None:
    edit(root / "tutorial.yaml", "bundle_format: 1", "bundle_format: 2")


def m_manifest_tab_indent(root: Path) -> None:
    edit(
        root / "tutorial.yaml",
        "  - lessons/03-first-refactor.md\n",
        "\t- lessons/03-first-refactor.md\n",
    )


def m_manifest_yaml_anchor(root: Path) -> None:
    edit(root / "tutorial.yaml", "level: ", "level: &lvl ")


def m_validator_unknown_kind(root: Path) -> None:
    edit(
        root / "tutorial.yaml",
        "has-lib: { kind: file-exists, path: src/lib.rs }",
        "has-lib: { kind: file-exsits, path: src/lib.rs }",
    )


def m_validator_missing_field(root: Path) -> None:
    edit(
        root / "tutorial.yaml",
        "has-lib: { kind: file-exists, path: src/lib.rs }",
        "has-lib: { kind: file-exists }",
    )


def m_id_not_slug_shaped(root: Path) -> None:
    edit(root / "tutorial.yaml", "id: rust-automaton-db", "id: Rust_AutomatonDB")


def m_duplicate_manifest_key(root: Path) -> None:
    edit(
        root / "tutorial.yaml",
        "level: intermediate-to-advanced\n",
        "level: intermediate-to-advanced\nlevel: beginner\n",
    )


# -- check 9: required files


def m_no_design_md(root: Path) -> None:
    (root / "DESIGN.md").unlink()
    assert "DESIGN.md" not in os.listdir(root)


def m_course_md_miscased(root: Path) -> None:
    text = (root / "COURSE.md").read_text()
    (root / "COURSE.md").unlink()
    (root / "Course.md").write_text(text)
    names = os.listdir(root)
    assert "Course.md" in names and "COURSE.md" not in names, names


def m_empty_lessons_list(root: Path) -> None:
    path = root / "tutorial.yaml"
    text = path.read_text()
    start = text.index("lessons:\n")
    end = text.index("workspace_kind:")
    assert start < end
    path.write_text(text[:start] + "lessons: []\n\n" + text[end:])


# -- check 10: workspace_kind and ownership


def m_unknown_workspace_kind(root: Path) -> None:
    edit(
        root / "tutorial.yaml",
        "workspace_kind: existing-or-new-repository",
        "workspace_kind: existing-repository",
    )


def m_unknown_ownership_policy(root: Path) -> None:
    edit(
        root / "tutorial.yaml",
        "ownership_policy: tutor-must-not-edit-learner-owned",
        "ownership_policy: tutor-decides",
    )


def m_empty_learner_owned(root: Path) -> None:
    edit(
        root / "tutorial.yaml",
        "learner_owned: [src/**, tests/**, Cargo.toml, Cargo.lock]",
        "learner_owned: []",
    )


def m_empty_tutor_owned(root: Path) -> None:
    edit(
        root / "tutorial.yaml",
        "tutor_owned: [tutorial/STATE.md, tutorial/DESIGN.md, tutorial/lessons/**]",
        "tutor_owned: []",
    )


# -- check 11: instance STATE.md


def m_instance_id_mismatch(root: Path) -> None:
    to_instance(root)
    edit(
        root / "STATE.md",
        "tutorial_id: rust-automaton-db",
        "tutorial_id: rust-automaton-database",
    )


def m_instance_active_lesson_unlisted(root: Path) -> None:
    to_instance(root)
    body = (root / "lessons" / "00-foundations.md").read_text()
    (root / "lessons" / "90-side-quest.md").write_text(
        body.replace("id: 00-foundations", "id: 90-side-quest")
    )
    edit(
        root / "STATE.md",
        "active_lesson: lessons/00-foundations.md",
        "active_lesson: lessons/90-side-quest.md",
    )


def m_instance_active_lesson_unresolved(root: Path) -> None:
    to_instance(root)
    edit(
        root / "STATE.md",
        "active_lesson: lessons/00-foundations.md",
        "active_lesson: lessons/00-foundatoins.md",
    )


def m_instance_active_lesson_is_prose(root: Path) -> None:
    to_instance(root)
    edit(
        root / "STATE.md",
        "active_lesson: lessons/00-foundations.md",
        "active_lesson: 3",
    )


def m_instance_no_frontmatter(root: Path) -> None:
    to_instance(root)
    path = root / "STATE.md"
    text = path.read_text()
    _, _, rest = text[4:].partition("\n---\n")
    assert rest
    path.write_text(rest)


def m_instance_missing_status(root: Path) -> None:
    to_instance(root)
    edit(root / "STATE.md", "status: in-progress\n", "")


# -- check 12: STATE.template.md


def m_template_id_mismatch(root: Path) -> None:
    edit(
        root / "STATE.template.md",
        "tutorial_id: rust-automaton-db",
        "tutorial_id: rust-automaton",
    )


def m_template_wrong_entry_lesson(root: Path) -> None:
    edit(
        root / "STATE.template.md",
        "active_lesson: lessons/00-foundations.md",
        "active_lesson: lessons/03-first-refactor.md",
    )


def m_template_status_started(root: Path) -> None:
    edit(root / "STATE.template.md", "status: not-started", "status: in-progress")


def m_template_missing_section(root: Path) -> None:
    edit(
        root / "STATE.template.md",
        "## Accepted warnings\n\nNone.\n",
        "",
    )


def m_template_no_frontmatter(root: Path) -> None:
    path = root / "STATE.template.md"
    text = path.read_text()
    _, _, rest = text[4:].partition("\n---\n")
    assert rest
    path.write_text(rest)


# -- generated lessons: shared paths
#
# The "generated" baseline is an instance of rust-cli-basics carrying:
#   lessons.generated/lifetimes-and-borrows.md            side-lesson
#   lessons.generated/03-reading-files-draft/LESSON.md     main-path-draft
#   lessons.generated/03-reading-files-draft/worked-example.rs
# and a STATE.md whose active_lesson is the side-lesson.

SIDE = "lessons.generated/lifetimes-and-borrows.md"
DRAFT_DIR = "lessons.generated/03-reading-files-draft"
DRAFT = f"{DRAFT_DIR}/LESSON.md"


# -- check 13: a bundle must not carry lessons.generated/


def m_bundle_has_generated_dir(root: Path) -> None:
    folder = root / "lessons.generated"
    folder.mkdir()
    (folder / "lifetimes.md").write_text(
        "---\nid: lifetimes\ntitle: Lifetimes\ngenerated: true\n"
        "generated_at: 2026-09-11\nkind: side-lesson\n"
        'reason: "the learner asked"\nafter: lessons/00-hello-args.md\n---\n\n'
        "## Purpose\n\nA detour.\n"
    )
    assert "lessons.generated" in os.listdir(root)


def m_bundle_has_miscased_generated_dir(root: Path) -> None:
    """A bundle carrying `Lessons.Generated/` is the same error, spelt oddly.

    Without the case-folded comparison this is invisible: the entry name
    differs, so `"lessons.generated" in os.listdir(root)` is False.
    """
    folder = root / "Lessons.Generated"
    folder.mkdir()
    (folder / "notes.md").write_text("---\nid: notes\ntitle: Notes\n---\n\nx\n")
    names = os.listdir(root)
    assert "Lessons.Generated" in names and "lessons.generated" not in names, names


# -- check 14: provenance frontmatter


def m_generated_no_kind(root: Path) -> None:
    edit(root / SIDE, "kind: side-lesson\n", "")


def m_generated_unknown_kind(root: Path) -> None:
    edit(root / SIDE, "kind: side-lesson", "kind: side-quest")


def m_generated_not_marked_generated(root: Path) -> None:
    edit(root / DRAFT, "generated: true\n", "")


def m_generated_marked_false(root: Path) -> None:
    edit(root / DRAFT, "generated: true", "generated: false")


def m_generated_no_reason(root: Path) -> None:
    edit(
        root / SIDE,
        'reason: "The learner cannot explain why count_lines takes &str '
        'rather than String"\n',
        "",
    )


def m_generated_empty_generated_at(root: Path) -> None:
    edit(root / SIDE, "generated_at: 2026-09-11", 'generated_at: ""')


def m_generated_no_frontmatter(root: Path) -> None:
    path = root / SIDE
    text = path.read_text()
    assert text.startswith("---\n")
    _, _, rest = text[4:].partition("\n---\n")
    assert rest, "expected a closing frontmatter fence to strip"
    path.write_text(rest)


def m_generated_dir_miscased(root: Path) -> None:
    """Rename lessons.generated/ to lessons.Generated/ - a no-op rename trap.

    A plain rename does nothing on a case-insensitive filesystem, so this
    moves via a temporary name and then verifies the listing.
    """
    old = root / "lessons.generated"
    tmp = root / "lessons.generated.tmp"
    old.rename(tmp)
    tmp.rename(root / "lessons.Generated")


def m_generated_dir_is_a_file(root: Path) -> None:
    """`lessons.generated` present, but as a file.

    Without an explicit guard this is SILENTLY clean: the entry name matches
    exactly, the walk finds no lessons, and every generated check reports
    "0 of them" and passes.
    """
    folder = root / "lessons.generated"
    shutil.rmtree(folder)
    folder.write_text("I meant to make a directory.\n")
    assert "lessons.generated" in os.listdir(root) and folder.is_file()


def v_generated_dir_miscased(root: Path) -> None:
    names = os.listdir(root)
    assert "lessons.Generated" in names, f"fixture did not take effect: {names}"
    assert "lessons.generated" not in names, (
        f"the directory still has an exact-case lessons.generated, so this "
        f"fixture tests nothing: {names}"
    )


# -- check 15: 'after' resolution


def m_generated_after_not_a_lesson(root: Path) -> None:
    edit(root / SIDE, "after: lessons/00-hello-args.md", "after: lessons/99-nope.md")


def m_generated_after_names_a_generated_lesson(root: Path) -> None:
    """`after` must reach the MAIN path, not another generated lesson.

    The path exists on disk, so a bare existence test would pass this.
    """
    edit(root / DRAFT, "after: lessons/02-errors-and-tests.md", f"after: {SIDE}")
    assert (root / SIDE).is_file(), "the target of 'after' must really exist"


def m_generated_after_is_material(root: Path) -> None:
    """`after` points at a real file under lessons/ that is not a lesson."""
    edit(
        root / SIDE,
        "after: lessons/00-hello-args.md",
        "after: lessons/01-subcommands/usage.txt",
    )
    assert (root / "lessons/01-subcommands/usage.txt").is_file()


# -- check 16: the manifest must not list a generated lesson


def m_manifest_lists_generated_lesson(root: Path) -> None:
    edit(
        root / "tutorial.yaml",
        "  - lessons/02-errors-and-tests.md\n",
        f"  - lessons/02-errors-and-tests.md\n  - {SIDE}\n",
    )


def m_bundle_manifest_lists_generated_lesson(root: Path) -> None:
    """The same mistake in a bundle, where the directory does not even exist.

    Check 4 deliberately stays quiet about lessons.generated/ entries, so if
    check 16 did not run in bundle mode this would pass silently.
    """
    edit(
        root / "tutorial.yaml",
        "  - lessons/02-errors-and-tests.md\n",
        "  - lessons/02-errors-and-tests.md\n  - lessons.generated/detour.md\n",
    )
    assert "lessons.generated" not in os.listdir(root)


# -- check 17: resume_at


def m_generated_active_without_resume(root: Path) -> None:
    edit(root / "STATE.md", "resume_at: lessons/01-subcommands/LESSON.md\n", "")


def m_generated_resume_unlisted(root: Path) -> None:
    edit(
        root / "STATE.md",
        "resume_at: lessons/01-subcommands/LESSON.md",
        f"resume_at: {SIDE}",
    )


def m_generated_resume_not_a_path(root: Path) -> None:
    edit(
        root / "STATE.md",
        "resume_at: lessons/01-subcommands/LESSON.md",
        "resume_at: 2",
    )


# -- check 17, negative direction: the shapes a detour is allowed to take.
#
# `after:` is placement in the course; `resume_at` is the lesson to make
# active when the detour ends. They are independent fields, so no ordering
# relationship between them may be asserted. The baseline itself is already
# the mid-lesson PREREQUISITE shape - after: lessons/00-hello-args.md,
# resume_at: lessons/01-subcommands/LESSON.md - so these two cover the other
# two shapes.


def m_detour_at_a_boundary(root: Path) -> None:
    """Lesson 01 COMPLETED, then the detour. It returns to lesson 02.

    The old derived rule produced exactly this pair, so this is the shape
    that must keep working after the rule was removed.
    """
    edit(root / SIDE, "after: lessons/00-hello-args.md", "after: lessons/01-subcommands/LESSON.md")
    edit(
        root / "STATE.md",
        "resume_at: lessons/01-subcommands/LESSON.md",
        "resume_at: lessons/02-errors-and-tests.md",
    )


def m_detour_mid_lesson_placed_on_the_interrupted_lesson(root: Path) -> None:
    """Part-way through lesson 01, on a topic lesson 01 does not depend on.

    The learner asked for it, so it does not belong BEFORE 01; it belongs
    after it. The learner still has unfinished work in 01, so that is where
    they go back to. `after:` and `resume_at` therefore name the SAME entry,
    which the derived rule `resume = the entry after after:` could not
    produce: it would have returned lessons/02-errors-and-tests.md and thrown
    away the rest of lesson 01.
    """
    edit(root / SIDE, "after: lessons/00-hello-args.md", "after: lessons/01-subcommands/LESSON.md")
    text = (root / "STATE.md").read_text()
    assert "resume_at: lessons/01-subcommands/LESSON.md" in text
    side = (root / SIDE).read_text()
    assert "after: lessons/01-subcommands/LESSON.md" in side
    listed = _manifest_lessons(root)
    assert listed.index("lessons/01-subcommands/LESSON.md") < len(listed) - 1, (
        "the interrupted lesson must not be the last entry, or this fixture "
        "would be the final-lesson special case instead"
    )


def _manifest_lessons(root: Path) -> list[str]:
    parsed = vb._RestrictedYaml(
        (root / "tutorial.yaml").read_text(), "tutorial.yaml"
    ).parse()
    return [str(entry) for entry in parsed["lessons"]]


# -- check 11, in the presence of generated lessons


def m_active_lesson_resolves_to_neither(root: Path) -> None:
    """The relaxation must not become "anything that resolves is fine".

    COURSE.md exists and resolves. It is not a lesson of either kind.
    """
    edit(root / "STATE.md", f"active_lesson: {SIDE}", "active_lesson: COURSE.md")
    edit(root / "STATE.md", "resume_at: lessons/01-subcommands/LESSON.md\n", "")
    assert (root / "COURSE.md").is_file()


def m_active_lesson_generated_but_absent(root: Path) -> None:
    edit(
        root / "STATE.md",
        f"active_lesson: {SIDE}",
        "active_lesson: lessons.generated/never-written.md",
    )


# -- ordinary lesson rules still apply to a generated lesson


def m_generated_id_not_slug(root: Path) -> None:
    edit(root / DRAFT, "id: 03-reading-files-draft", "id: LESSON")


def m_generated_bad_design_ref(root: Path) -> None:
    edit(root / SIDE, "design_refs: [io-boundary,", "design_refs: [io-boundry,")


def m_generated_undeclared_validator(root: Path) -> None:
    edit(root / SIDE, "validators: [cargo-check,", "validators: [cargo-clippy,")


def m_generated_miscased_lesson_md(root: Path) -> None:
    folder = root / DRAFT_DIR
    body = (folder / "LESSON.md").read_text()
    (folder / "LESSON.md").unlink()
    (folder / "Lesson.md").write_text(body)


def v_generated_miscased_lesson_md(root: Path) -> None:
    names = os.listdir(root / DRAFT_DIR)
    assert "Lesson.md" in names, f"fixture did not take effect: {names}"
    assert "LESSON.md" not in names, (
        f"the directory still has an exact-case LESSON.md, so this fixture "
        f"tests nothing: {names}"
    )


def m_generated_unnamed_material(root: Path) -> None:
    target = root / DRAFT_DIR / "spare-notes.md"
    target.write_text("# Notes\n\nNothing in LESSON.md names this file.\n")
    assert target.is_file()


def m_generated_progress_marker(root: Path) -> None:
    append(root / SIDE, "\n## Where we are\n\nStatus: In progress\n")


def m_generated_duplicate_slug(root: Path) -> None:
    body = (root / SIDE).read_text()
    target = root / "lessons.generated" / "03-reading-files-draft.md"
    target.write_text(body.replace("id: lifetimes-and-borrows", "id: 03-reading-files-draft"))
    assert target.is_file()


def m_generated_shadows_an_authored_slug(root: Path) -> None:
    """A generated lesson claiming an AUTHORED lesson's slug.

    The paths differ, so a per-directory uniqueness check would miss it, but
    the two files then answer to the same id.
    """
    body = (root / SIDE).read_text()
    target = root / "lessons.generated" / "00-hello-args.md"
    target.write_text(body.replace("id: lifetimes-and-borrows", "id: 00-hello-args"))
    assert (root / "lessons" / "00-hello-args.md").is_file()
    assert target.is_file()


def m_stale_resume_at(root: Path) -> None:
    """The detour finished, active_lesson moved back, resume_at stayed."""
    edit(
        root / "STATE.md",
        f"active_lesson: {SIDE}",
        "active_lesson: lessons/02-errors-and-tests.md",
    )


# -- optional lessons: shared paths
#
# The "cli" baseline declares two optional lessons, one of each authored
# shape, and the two failure modes the first of them anticipates:
#
#   lessons/pure-core-and-edges.md   anticipation - anticipates, repair_in,
#                                    required_for
#   lessons/what-is-a-character.md   plain enrichment - offer_at and
#                                    offer_because and nothing else
#
# The "generated" instance is an instance of it, so it carries both, plus a
# STATE.md whose "## Optional lessons" section records one deferral.

OPT_PURE = "lessons/pure-core-and-edges.md"
OPT_CHARS = "lessons/what-is-a-character.md"
OPT_RECORD = (
    "- `lessons/pure-core-and-edges.md` — deferred — offered at\n"
    "  `lessons/01-subcommands/LESSON.md` on 2026-09-11"
)
# The whole `offer_because` block of the enrichment entry, as one string, so a
# mutator can delete exactly it.
CHARS_OFFER_BECAUSE = (
    "    offer_because: >\n"
    "      DESIGN.md leaves a chars command undecided because nobody agrees "
    "what a\n"
    "      character is. There is a short lesson on that argument whenever "
    "you want it.\n"
)


def add_optional_entry(root: Path, key: str, body: str) -> None:
    """Insert one optional_lessons entry, keeping the rest of the map intact.

    Editing an EXISTING entry would make its lesson file unlisted as well, so
    check 4 would fire alongside check 18 and the case would no longer say
    which one it is really about.
    """
    edit(
        root / "tutorial.yaml",
        "\nworkspace_kind: new-repository",
        f"  {key}:\n{body}\nworkspace_kind: new-repository",
    )


# -- check 18: optional_lessons is well-formed


def m_optional_key_unresolved(root: Path) -> None:
    add_optional_entry(
        root,
        "lessons/never-written.md",
        "    offer_at:      [lessons/00-hello-args.md]\n"
        "    offer_because: A lesson nobody wrote.\n",
    )


def m_optional_key_is_material(root: Path) -> None:
    """A real file under lessons/ that is material, not a lesson."""
    add_optional_entry(
        root,
        "lessons/01-subcommands/usage.txt",
        "    offer_at:      [lessons/00-hello-args.md]\n"
        "    offer_because: Material cannot be offered as a lesson.\n",
    )
    assert (root / "lessons/01-subcommands/usage.txt").is_file()


def m_optional_key_is_generated(root: Path) -> None:
    """An overlay one tutor wrote cannot be an authored optional lesson."""
    add_optional_entry(
        root,
        SIDE,
        "    offer_at:      [lessons/00-hello-args.md]\n"
        "    offer_because: An overlay is not authored material.\n",
    )


def m_optional_also_on_main_path(root: Path) -> None:
    """Listed in BOTH lists. Check 4 must stay quiet; this is check 18's."""
    edit(
        root / "tutorial.yaml",
        "  - lessons/02-errors-and-tests.md\n",
        f"  - lessons/02-errors-and-tests.md\n  - {OPT_CHARS}\n",
    )


def m_optional_no_offer_because(root: Path) -> None:
    edit(root / "tutorial.yaml", CHARS_OFFER_BECAUSE, "")


def m_optional_empty_offer_at(root: Path) -> None:
    """An empty offer_at makes the lesson unreachable, not 'offer it anywhere'."""
    edit(
        root / "tutorial.yaml",
        "    offer_at:      [lessons/02-errors-and-tests.md]",
        "    offer_at:      []",
    )


def m_optional_offer_at_unlisted(root: Path) -> None:
    """offer_at names a real lesson - but an OPTIONAL one, not a main-path entry."""
    edit(
        root / "tutorial.yaml",
        "    offer_at:      [lessons/02-errors-and-tests.md]",
        f"    offer_at:      [{OPT_PURE}]",
    )
    assert (root / OPT_PURE).is_file()


def m_optional_anticipates_undeclared(root: Path) -> None:
    edit(
        root / "tutorial.yaml",
        "    anticipates:   [counting-coupled-to-io, test-needs-a-fixture-file]",
        "    anticipates:   [counting-coupled-to-i-o, test-needs-a-fixture-file]",
    )


def m_optional_repair_in_unlisted(root: Path) -> None:
    edit(
        root / "tutorial.yaml",
        "    repair_in:     lessons/01-subcommands/LESSON.md",
        f"    repair_in:     {OPT_PURE}",
    )


def m_optional_gate_without_anticipates(root: Path) -> None:
    """A gate on the ENRICHMENT entry, which anticipates nothing.

    required_for closes when an anticipated failure is observed and opens when
    the lesson is taken. With no anticipates it can never do either.
    """
    edit(
        root / "tutorial.yaml",
        CHARS_OFFER_BECAUSE,
        CHARS_OFFER_BECAUSE
        + "    required_for:  [lessons/02-errors-and-tests.md]\n",
    )


def m_optional_lessons_is_a_list(root: Path) -> None:
    path = root / "tutorial.yaml"
    text = path.read_text()
    start = text.index("optional_lessons:\n")
    end = text.index("\nworkspace_kind: new-repository")
    path.write_text(
        text[:start]
        + f"optional_lessons: [{OPT_PURE}, {OPT_CHARS}]\n"
        + text[end:]
    )


def m_optional_entry_is_a_string(root: Path) -> None:
    """The offer metadata replaced by a sentence.

    The key stays valid, so checks 4 and 20 stay quiet and this case says
    exactly which check it is about.
    """
    path = root / "tutorial.yaml"
    text = path.read_text()
    start = text.index(f"  {OPT_CHARS}:\n")
    end = text.index("\nworkspace_kind: new-repository")
    path.write_text(
        text[:start] + f"  {OPT_CHARS}: offer it whenever you like\n" + text[end:]
    )


# -- check 19: failure_modes is well-formed


def m_failure_mode_no_summary(root: Path) -> None:
    edit(
        root / "tutorial.yaml",
        "    summary: >\n"
        "      A test of the counting rules fails unless a fixture file "
        "exists, so the\n"
        "      suite depends on files the course never creates.\n",
        "",
    )


def m_signal_names_undeclared_validator(root: Path) -> None:
    edit(
        root / "tutorial.yaml",
        "    signals: [validator:cargo-test, validator:explains-choice, diagnosis]",
        "    signals: [validator:cargo-tests, validator:explains-choice, diagnosis]",
    )


def m_signal_in_no_permitted_form(root: Path) -> None:
    """Raw compiler output is deliberately NOT a signal form."""
    edit(
        root / "tutorial.yaml",
        "    signals: [token:FIXTURE_FILE_REQUIRED, diagnosis]",
        '    signals: ["error[E0502]: cannot borrow", diagnosis]',
    )


def m_failure_mode_unanticipated(root: Path) -> None:
    """A declared failure mode no optional lesson names can never re-offer."""
    edit(
        root / "tutorial.yaml",
        "    anticipates:   [counting-coupled-to-io, test-needs-a-fixture-file]",
        "    anticipates:   [counting-coupled-to-io]",
    )


def m_failure_mode_id_not_slug_shaped(root: Path) -> None:
    edit(root / "tutorial.yaml", "  test-needs-a-fixture-file:\n",
         "  Test_Needs_A_Fixture_File:\n")
    edit(
        root / "tutorial.yaml",
        "    anticipates:   [counting-coupled-to-io, test-needs-a-fixture-file]",
        "    anticipates:   [counting-coupled-to-io, Test_Needs_A_Fixture_File]",
    )


# -- check 20: the 'optional:' frontmatter flag


def m_main_path_declares_optional(root: Path) -> None:
    edit(
        root / "lessons" / "00-hello-args.md",
        "title: Reading command-line arguments\n",
        "title: Reading command-line arguments\noptional: true\n",
    )


def m_optional_lesson_omits_the_flag(root: Path) -> None:
    edit(root / OPT_PURE, "optional: true\n", "")


def m_optional_flag_is_false(root: Path) -> None:
    edit(root / OPT_CHARS, "optional: true", "optional: false")


def m_generated_lesson_declares_optional(root: Path) -> None:
    """A generated lesson is an overlay, never an offer."""
    edit(
        root / SIDE,
        "title: Borrowing, just enough to unblock the dispatch\n",
        "title: Borrowing, just enough to unblock the dispatch\noptional: true\n",
    )


# -- check 21: STATE.md's "## Optional lessons" record


def m_record_names_a_main_path_lesson(root: Path) -> None:
    edit(
        root / "STATE.md",
        f"- `{OPT_PURE}` — deferred",
        "- `lessons/00-hello-args.md` — deferred",
    )


def m_record_unknown_state(root: Path) -> None:
    edit(root / "STATE.md", "` — deferred — offered at", "` — postponed — offered at")


def m_record_not_offered(root: Path) -> None:
    """'not-offered' is not a state: not yet offered is the ABSENCE of a record."""
    edit(
        root / "STATE.md", "` — deferred — offered at", "` — not-offered — offered at"
    )


def m_record_twice(root: Path) -> None:
    edit(
        root / "STATE.md",
        OPT_RECORD,
        OPT_RECORD + f"\n- `{OPT_PURE}` — complete — taken on 2026-09-12",
    )


def m_record_is_not_a_record(root: Path) -> None:
    """A bullet that names no path in backticks must not be skipped silently."""
    edit(
        root / "STATE.md",
        f"- `{OPT_PURE}` — deferred — offered at",
        "- the learner put the pure-core lesson off — offered at",
    )


def m_record_in_progress_but_not_active(root: Path) -> None:
    edit(
        root / "STATE.md", "` — deferred — offered at", "` — in-progress — offered at"
    )


def m_active_optional_without_a_record(root: Path) -> None:
    """active_lesson is the ENRICHMENT lesson, which no record mentions."""
    edit(root / "STATE.md", f"active_lesson: {SIDE}", f"active_lesson: {OPT_CHARS}")


def m_no_optional_section(root: Path) -> None:
    """A learner who has been offered nothing yet has no section at all."""
    path = root / "STATE.md"
    text = path.read_text()
    head, sep, _ = text.partition("\n## Optional lessons\n")
    assert sep, "expected the fixture to carry an '## Optional lessons' section"
    path.write_text(head + "\n")


# -- check 17, extended to optional lessons


def _stand_in_the_optional_lesson(root: Path) -> None:
    """Move active_lesson onto the deferred optional lesson, record and all."""
    edit(root / "STATE.md", f"active_lesson: {SIDE}", f"active_lesson: {OPT_PURE}")
    edit(
        root / "STATE.md", "` — deferred — offered at", "` — in-progress — offered at"
    )


def m_optional_active_without_resume(root: Path) -> None:
    _stand_in_the_optional_lesson(root)
    edit(root / "STATE.md", "resume_at: lessons/01-subcommands/LESSON.md\n", "")


def m_optional_active_with_resume(root: Path) -> None:
    """The legitimate shape: standing IN an optional lesson, with a way back."""
    _stand_in_the_optional_lesson(root)
    assert "resume_at: lessons/01-subcommands/LESSON.md" in (
        root / "STATE.md"
    ).read_text()


# -- indeterminate: a check cannot run, yet nothing is wrong on its face


def m_design_md_not_utf8(root: Path) -> None:
    (root / "DESIGN.md").write_bytes(b"# Design\n\n## Keys {#key-ordering}\n\n\xff\xfe\x00bad\n")


# -- check 22: supplies entries
#
# The baseline "automaton" declares no `supplies` key, so each mutator here
# installs one and then breaks exactly one thing - that is what makes the
# reported message attributable to a single cause.


def m_supplies_from_missing(root: Path) -> None:
    append(root / "tutorial.yaml", """
supplies:
  - from: supplies/workspace/
    to: .
    describe: the workspace this course assumes
""")


def m_supplies_from_is_a_file_declared_as_a_directory(root: Path) -> None:
    (root / "supplies").mkdir()
    (root / "supplies" / "Cargo.toml").write_text("[package]\n", encoding="utf-8")
    append(root / "tutorial.yaml", """
supplies:
  - from: supplies/Cargo.toml/
    to: Cargo.toml
    describe: the manifest this course assumes
""")


def m_supplies_to_escapes_the_workspace(root: Path) -> None:
    (root / "supplies").mkdir()
    (root / "supplies" / "Cargo.toml").write_text("[package]\n", encoding="utf-8")
    append(root / "tutorial.yaml", """
supplies:
  - from: supplies/Cargo.toml
    to: ../Cargo.toml
    describe: the manifest this course assumes
""")


def m_supplies_to_is_inside_the_instance(root: Path) -> None:
    (root / "supplies").mkdir()
    (root / "supplies" / "Cargo.toml").write_text("[package]\n", encoding="utf-8")
    append(root / "tutorial.yaml", """
supplies:
  - from: supplies/Cargo.toml
    to: tutorial/Cargo.toml
    describe: the manifest this course assumes
""")


def m_supplies_describe_is_empty(root: Path) -> None:
    (root / "supplies").mkdir()
    (root / "supplies" / "Cargo.toml").write_text("[package]\n", encoding="utf-8")
    append(root / "tutorial.yaml", """
supplies:
  - from: supplies/Cargo.toml
    to: Cargo.toml
    describe: ""
""")


def m_supplies_unknown_entry_key(root: Path) -> None:
    """A complete, otherwise-valid entry plus one extra key - breaking
    exactly the one thing this case is meant to prove, not also 'describe
    is missing' at the same time."""
    (root / "supplies").mkdir()
    (root / "supplies" / "Cargo.toml").write_text("[package]\n", encoding="utf-8")
    append(root / "tutorial.yaml", """
supplies:
  - from: supplies/Cargo.toml
    to: Cargo.toml
    describe: the manifest this course assumes
    description: a duplicate, misspelled label
""")


def m_supplies_in_an_unlisted_lesson(root: Path) -> None:
    (root / "supplies").mkdir()
    (root / "supplies" / "Cargo.toml").write_text("[package]\n", encoding="utf-8")
    (root / "lessons" / "99-orphan.md").write_text(
        "---\n"
        "id: 99-orphan\n"
        "title: Orphan\n"
        "supplies:\n"
        "  - from: supplies/Cargo.toml\n"
        "    to: Cargo.toml\n"
        "    describe: the manifest this course assumes\n"
        "---\n\n## Purpose\n\nNothing.\n",
        encoding="utf-8",
    )


def m_supplies_from_under_generated(root: Path) -> None:
    """A supplies entry must not reach into lessons.generated/: that
    directory exists only in an instance, so a bundle-authored 'from'
    pointing into it can never be shipped.

    The rule is textual - it fires without lessons.generated/ existing on
    disk at all. Creating the directory for real would also trip check 13
    (lessons.generated/ is absent in a bundle) as unrelated collateral,
    breaking a second thing this fixture is not meant to prove.
    """
    append(root / "tutorial.yaml", """
supplies:
  - from: lessons.generated/extra.md
    to: extra.md
    describe: a draft file
""")


def m_supplies_well_formed(root: Path) -> None:
    """The POSITIVE control: a valid entry in each scope reports nothing.

    Without this, every one of the mutators above is equally consistent with
    a check that always fires.
    """
    (root / "supplies").mkdir()
    (root / "supplies" / "Cargo.toml").write_text("[package]\n", encoding="utf-8")
    (root / "supplies" / "seed.txt").write_text("hello\n", encoding="utf-8")
    append(root / "tutorial.yaml", """
supplies:
  - from: supplies/Cargo.toml
    to: Cargo.toml
    describe: the manifest this course assumes
""")
    edit(
        root / "lessons" / "00-foundations.md",
        "id: 00-foundations",
        "id: 00-foundations\n"
        "supplies:\n"
        "  - from: supplies/seed.txt\n"
        "    to: seed.txt\n"
        "    describe: a starter file this lesson hands over",
    )


# -- check 22, fix round 1: a present-but-malformed 'supplies' key must be a
# finding, not silently treated the same as an absent key.


def m_supplies_key_is_not_a_list(root: Path) -> None:
    """The likeliest real author error: a missing '- ', so 'supplies:'
    holds one mapping directly instead of a list of one mapping. Before fix
    round 1 this validated as though 'supplies' were absent - the runner
    would then place nothing and every lesson that assumed these files
    would fail, silently."""
    (root / "supplies").mkdir()
    (root / "supplies" / "Cargo.toml").write_text("[package]\n", encoding="utf-8")
    append(root / "tutorial.yaml", """
supplies:
  from: supplies/Cargo.toml
  to: Cargo.toml
  describe: the manifest this course assumes
""")


def m_supplies_key_is_a_bare_string(root: Path) -> None:
    """A second shape of the same defect: 'supplies' is a scalar, not even
    a mapping."""
    append(root / "tutorial.yaml", """
supplies: supplies/Cargo.toml
""")


# -- check 22, fix round 1: seven refusal branches with no fixture before


def m_supplies_entry_is_not_a_mapping(root: Path) -> None:
    """The list itself is well-formed; one of its entries is not."""
    append(root / "tutorial.yaml", """
supplies:
  - just a string, not a mapping
""")


def m_supplies_from_is_empty(root: Path) -> None:
    append(root / "tutorial.yaml", """
supplies:
  - from: ""
    to: Cargo.toml
    describe: the manifest this course assumes
""")


def m_supplies_from_is_only_slashes(root: Path) -> None:
    append(root / "tutorial.yaml", r"""
supplies:
  - from: "///"
    to: Cargo.toml
    describe: the manifest this course assumes
""")


def m_supplies_from_directory_without_trailing_slash(root: Path) -> None:
    """The reverse of the trailing-slash mismatch already covered: a real
    directory declared WITHOUT the '/' that marks it as one."""
    (root / "supplies" / "assets").mkdir(parents=True)
    (root / "supplies" / "assets" / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    append(root / "tutorial.yaml", """
supplies:
  - from: supplies/assets
    to: assets
    describe: the icon set this course assumes
""")


def m_supplies_to_is_empty(root: Path) -> None:
    (root / "supplies").mkdir()
    (root / "supplies" / "Cargo.toml").write_text("[package]\n", encoding="utf-8")
    append(root / "tutorial.yaml", """
supplies:
  - from: supplies/Cargo.toml
    to: ""
    describe: the manifest this course assumes
""")


def m_supplies_to_has_a_backslash(root: Path) -> None:
    (root / "supplies").mkdir()
    (root / "supplies" / "Cargo.toml").write_text("[package]\n", encoding="utf-8")
    append(root / "tutorial.yaml", r"""
supplies:
  - from: supplies/Cargo.toml
    to: sub\file.txt
    describe: the manifest this course assumes
""")


def m_supplies_to_is_absolute(root: Path) -> None:
    (root / "supplies").mkdir()
    (root / "supplies" / "Cargo.toml").write_text("[package]\n", encoding="utf-8")
    append(root / "tutorial.yaml", """
supplies:
  - from: supplies/Cargo.toml
    to: /etc/passwd
    describe: the manifest this course assumes
""")


# -- check 22, fix round 1: it must also examine a GENERATED lesson's own
# supplies entries (instance mode only - no bundle-mode fixture can reach
# this scope), while skipping ONLY the listed-ness rule for one.


def m_supplies_generated_lesson_from_missing(root: Path) -> None:
    edit(
        root / "lessons.generated" / "lifetimes-and-borrows.md",
        "id: lifetimes-and-borrows",
        "id: lifetimes-and-borrows\n"
        "supplies:\n"
        "  - from: lessons/does-not-exist.md\n"
        "    to: borrow_example.rs\n"
        "    describe: a worked borrowing example",
    )


def m_supplies_generated_lesson_well_formed(root: Path) -> None:
    """The POSITIVE control for the listed-ness exemption: a generated
    lesson is never in 'lessons' or 'optional_lessons' by design (check
    16), so a well-formed entry here must not be reported as unlisted."""
    edit(
        root / "lessons.generated" / "03-reading-files-draft" / "LESSON.md",
        "id: 03-reading-files-draft",
        "id: 03-reading-files-draft\n"
        "supplies:\n"
        "  - from: lessons/00-hello-args.md\n"
        "    to: hello-reference.md\n"
        "    describe: a copy of the intro lesson kept for reference",
    )


# --------------------------------------------------------------------------
# The case table
# --------------------------------------------------------------------------


# Mutators that build their own instance, so run_case must not call
# to_instance() over the top of them.
SELF_MATERIALIZING = {
    m_instance_missing_state,
    m_instance_has_template,
    m_instance_missing_stamp,
    m_instance_id_mismatch,
    m_instance_active_lesson_unlisted,
    m_instance_active_lesson_unresolved,
    m_instance_active_lesson_is_prose,
    m_instance_no_frontmatter,
    m_instance_missing_status,
}


@dataclass
class Case:
    name: str
    check: int | None
    baseline: str
    mode: str
    mutate: Mutator
    expect: str = ""
    verify: Mutator | None = None
    #  "fires"         - the named check must report, exit 1
    #  "silent"        - the named check must NOT report, exit 0
    #  "indeterminate" - no findings, but a check did not run, exit 3
    kind: str = "fires"


CASES: list[Case] = [
    # ---- check 1
    Case("1: design_refs names a typo'd anchor", 1, "automaton", "bundle",
         m_bad_design_ref, "'tbale-model', which is not an anchor in DESIGN.md"),
    Case("1: a DESIGN.md anchor was renamed under a lesson", 1, "automaton",
         "bundle", m_anchor_renamed, "'row-cell-model', which is not an anchor"),
    Case("1: design_refs is a bare string, not a list", 1, "automaton", "bundle",
         m_design_refs_not_a_list, "design_refs must be a list"),
    # ---- check 2
    Case("2: lesson names a validator nothing declares", 2, "automaton", "bundle",
         m_undeclared_validator, "'cargo-clippy', which is not declared"),
    Case("2: a declared validator was deleted from the manifest", 2, "automaton",
         "bundle", m_validator_removed_from_manifest, "'has-lib', which is not declared"),
    # ---- check 3
    Case("3: lesson id does not equal its slug", 3, "automaton", "bundle",
         m_id_not_slug, "id is 'first-refactor' but the lesson slug is"),
    Case("3: lesson has no title", 3, "automaton", "bundle", m_no_title,
         "has no 'title'"),
    Case("3: lesson has no frontmatter at all", 3, "automaton", "bundle",
         m_no_frontmatter, "there is no YAML frontmatter"),
    Case("3: foldered lesson id copies the filename, not the folder", 3, "cli",
         "bundle", m_foldered_id_is_file_stem,
         "id is 'LESSON' but the lesson slug is '01-subcommands'"),
    # ---- check 4
    Case("4: a lesson file is not listed", 4, "automaton", "bundle",
         m_unlisted_lesson, "lessons/99-orphan.md: this lesson is not listed"),
    Case("4: a lessons entry does not resolve", 4, "automaton", "bundle",
         m_entry_does_not_resolve, "'lessons/03-the-first-refactor.md' does not resolve"),
    Case("4: a lesson is listed twice", 4, "automaton", "bundle",
         m_entry_listed_twice, "'lessons/03-first-refactor.md' 2 times"),
    Case("4: a lessons entry differs only by case", 4, "automaton", "bundle",
         m_entry_case_differs, "the case differs"),
    Case("4: a folder under lessons/ has no LESSON.md", 4, "automaton", "bundle",
         m_folder_without_lesson_md, "has no LESSON.md"),
    Case("4: a lesson body is named lesson.md, not LESSON.md", 4, "cli", "bundle",
         m_miscased_lesson_body, "must be named exactly 'LESSON.md'",
         verify=v_miscased_lesson_body),
    Case("4: lesson-folder material is listed as a lesson", 4, "cli", "bundle",
         m_material_listed_as_lesson, "resolves to a file that is not a lesson"),
    Case("4: two lessons claim the same slug", 4, "cli", "bundle",
         m_duplicate_slug, "the slug '01-subcommands' is used by more than one"),
    # ---- check 5, positive direction
    Case("5: heading annotated '(Complete)'", 5, "automaton", "bundle",
         m_marker_heading_annotated, "a heading annotated with a status"),
    Case("5: a 'Status: Complete' label line", 5, "automaton", "bundle",
         m_marker_status_label, "a Status: label"),
    Case("5: a ticked checklist box", 5, "automaton", "bundle",
         m_marker_ticked_box, "a ticked checklist box"),
    Case("5: a '## Current tutorial state' heading", 5, "automaton", "bundle",
         m_marker_current_heading, "a heading naming the current position"),
    Case("5: a 'Complete' table cell", 5, "automaton", "bundle",
         m_marker_table_cell, "a status word standing alone in a table cell"),
    Case("5: a '**Next:**' label", 5, "automaton", "bundle",
         m_marker_bold_next_label, "a Next: pointer heading or label"),
    Case("5: a 'Current lesson:' label", 5, "automaton", "bundle",
         m_marker_current_lesson_label, "a current-position label"),
    Case("5: 'status: in-progress' in lesson frontmatter", 5, "automaton",
         "bundle", m_marker_frontmatter_status, "a Status: label"),
    Case("5: a '## Current resume marker' heading", 5, "automaton", "bundle",
         m_marker_resume_heading, "a resume marker"),
    Case("5: 'Complete' alone on a bullet", 5, "automaton", "bundle",
         m_marker_lone_list_item, "a status word standing alone as a list item"),
    # ---- check 5, negative direction. Without this the check is a liability:
    # the free-text version rejected the valid sentence "while the refactor is
    # in progress, the engine is unreachable".
    Case("5: ordinary prose using the same words is NOT reported", 5,
         "automaton", "bundle", m_prose_only, kind="silent"),
    # ---- check 6
    Case("6: material no lesson names", 6, "cli", "bundle", m_unnamed_material,
         "'orphan-notes.md' is never named by LESSON.md"),
    Case("6: nested material no lesson names", 6, "foldered", "bundle",
         m_unnamed_nested_material, "'assets/unused.svg' is never named"),
    Case("6: the filename occurs only inside a longer path", 6, "cli", "bundle",
         m_material_named_only_inside_a_longer_path,
         "'notes.md' is never named by LESSON.md"),
    Case("6: the same filename, properly named, is NOT reported", 6, "cli",
         "bundle", m_material_properly_named, kind="silent"),
    # ---- check 7
    Case("7: a bundle carries STATE.md", 7, "automaton", "bundle",
         m_bundle_has_state_md, "a bundle must not contain STATE.md"),
    Case("7: a bundle has no STATE.template.md", 7, "automaton", "bundle",
         m_bundle_missing_template, "a bundle must contain STATE.template.md"),
    Case("7: a bundle carries an instance stamp", 7, "automaton", "bundle",
         m_bundle_has_instance_stamp, "A bundle must not carry it"),
    Case("7: an instance has no STATE.md", 7, "automaton", "instance",
         m_instance_missing_state, "an instance must contain STATE.md"),
    Case("7: an instance still carries STATE.template.md", 7, "automaton",
         "instance", m_instance_has_template,
         "an instance must not contain STATE.template.md"),
    Case("7: an instance has no instance stamp", 7, "automaton", "instance",
         m_instance_missing_stamp, "This one has none"),
    # ---- check 8
    Case("8: a required manifest field is missing", 8, "automaton", "bundle",
         m_missing_required_field, "the required field 'description' is missing"),
    Case("8: an unknown bundle_format", 8, "automaton", "bundle",
         m_unknown_bundle_format, "bundle_format is 2"),
    Case("8: a tab indents the manifest", 8, "automaton", "bundle",
         m_manifest_tab_indent, "a tab is used for indentation"),
    Case("8: the manifest uses a YAML anchor", 8, "automaton", "bundle",
         m_manifest_yaml_anchor, "anchors (&name) are not supported"),
    Case("8: a validator declares an unknown kind", 8, "automaton", "bundle",
         m_validator_unknown_kind, "kind 'file-exsits' is not one of"),
    Case("8: a validator omits a required field", 8, "automaton", "bundle",
         m_validator_missing_field, "requires the field 'path'"),
    Case("8: the bundle id is not [a-z0-9-]+", 8, "automaton", "bundle",
         m_id_not_slug_shaped, "must match [a-z0-9-]+"),
    Case("8: a manifest key appears twice", 8, "automaton", "bundle",
         m_duplicate_manifest_key, "duplicate key 'level'"),
    # ---- check 9
    Case("9: DESIGN.md is missing", 9, "automaton", "bundle", m_no_design_md,
         "DESIGN.md: the file is required and is missing"),
    Case("9: COURSE.md is mis-cased", 9, "automaton", "bundle",
         m_course_md_miscased, "the file is named 'Course.md'"),
    Case("9: the lessons list is empty", 9, "automaton", "bundle",
         m_empty_lessons_list, "the lessons list is empty"),
    # ---- check 10
    Case("10: an unknown workspace_kind", 10, "automaton", "bundle",
         m_unknown_workspace_kind, "workspace_kind is 'existing-repository'"),
    Case("10: an unknown ownership_policy", 10, "automaton", "bundle",
         m_unknown_ownership_policy, "ownership_policy is 'tutor-decides'"),
    Case("10: learner_owned is empty for a software course", 10, "automaton",
         "bundle", m_empty_learner_owned, "learner_owned is empty but workspace_kind"),
    Case("10: tutor_owned is empty", 10, "automaton", "bundle",
         m_empty_tutor_owned, "tutor_owned is empty"),
    # ---- check 11
    Case("11: STATE.md tutorial_id does not match the manifest", 11, "automaton",
         "instance", m_instance_id_mismatch,
         "this instance does not belong to this manifest"),
    Case("11: active_lesson is not in the lessons list", 11, "automaton",
         "instance", m_instance_active_lesson_unlisted,
         "is none of: an entry in tutorial.yaml's 'lessons' list"),
    Case("11: active_lesson does not resolve", 11, "automaton", "instance",
         m_instance_active_lesson_unresolved,
         "active_lesson 'lessons/00-foundatoins.md' does not resolve"),
    Case("11: active_lesson is not a path", 11, "automaton", "instance",
         m_instance_active_lesson_is_prose, "active_lesson must be a lesson path"),
    Case("11: STATE.md has no frontmatter", 11, "automaton", "instance",
         m_instance_no_frontmatter, "there is no YAML frontmatter"),
    Case("11: STATE.md has no status field", 11, "automaton", "instance",
         m_instance_missing_status, "the frontmatter field 'status' is missing"),
    # ---- check 12
    Case("12: template tutorial_id does not match the manifest", 12, "automaton",
         "bundle", m_template_id_mismatch, "tutorial_id is 'rust-automaton'"),
    Case("12: template active_lesson is not lessons[0]", 12, "automaton",
         "bundle", m_template_wrong_entry_lesson, "must start at lessons[0]"),
    Case("12: template status is not 'not-started'", 12, "automaton", "bundle",
         m_template_status_started, "status is 'in-progress'"),
    Case("12: template omits a required section", 12, "automaton", "bundle",
         m_template_missing_section, "'## Accepted warnings' is missing"),
    Case("12: template has no frontmatter", 12, "automaton", "bundle",
         m_template_no_frontmatter, "there is no YAML frontmatter"),
    # ---- check 13: lessons.generated/ in a bundle
    Case("13: a bundle carries lessons.generated/", 13, "cli", "bundle",
         m_bundle_has_generated_dir, "a bundle must not contain lessons.generated/"),
    Case("13: a bundle carries a mis-cased Lessons.Generated/", 13, "cli",
         "bundle", m_bundle_has_miscased_generated_dir,
         "Lessons.Generated/: a bundle must not contain"),
    # ---- check 14: provenance frontmatter
    Case("14: a generated lesson has no 'kind'", 14, "generated", "instance",
         m_generated_no_kind, "the provenance field 'kind' is missing"),
    Case("14: a generated lesson declares an unknown kind", 14, "generated",
         "instance", m_generated_unknown_kind, "kind is 'side-quest'"),
    Case("14: a generated lesson omits 'generated: true'", 14, "generated",
         "instance", m_generated_not_marked_generated,
         "the provenance field 'generated' is missing"),
    Case("14: a generated lesson declares 'generated: false'", 14, "generated",
         "instance", m_generated_marked_false, "generated is False"),
    Case("14: a generated lesson has no 'reason'", 14, "generated", "instance",
         m_generated_no_reason, "the provenance field 'reason' is missing"),
    Case("14: a generated lesson has an empty 'generated_at'", 14, "generated",
         "instance", m_generated_empty_generated_at,
         "the provenance field 'generated_at' is empty"),
    Case("14: a generated lesson has no frontmatter at all", 14, "generated",
         "instance", m_generated_no_frontmatter,
         "the provenance cannot be read"),
    Case("14: lessons.generated is a file, not a directory", 14, "generated",
         "instance", m_generated_dir_is_a_file, "is a file, not a directory"),
    Case("14: the directory is named lessons.Generated/", 14, "generated",
         "instance", m_generated_dir_miscased,
         "the directory is named 'lessons.Generated', not 'lessons.generated'",
         verify=v_generated_dir_miscased),
    # ---- check 15: 'after'
    Case("15: 'after' names a path the manifest does not list", 15, "generated",
         "instance", m_generated_after_not_a_lesson,
         "after names 'lessons/99-nope.md'"),
    Case("15: 'after' names another generated lesson", 15, "generated",
         "instance", m_generated_after_names_a_generated_lesson,
         "not another generated one"),
    Case("15: 'after' names a real file that is not a listed lesson", 15,
         "generated", "instance", m_generated_after_is_material,
         "after names 'lessons/01-subcommands/usage.txt'"),
    # ---- check 16: the manifest lessons list
    Case("16: an instance manifest lists a generated lesson", 16, "generated",
         "instance", m_manifest_lists_generated_lesson,
         "names a generated lesson"),
    Case("16: a bundle manifest lists a generated lesson", 16, "cli", "bundle",
         m_bundle_manifest_lists_generated_lesson,
         "'lessons.generated/detour.md' names a generated lesson"),
    # ---- check 17: resume_at
    Case("17: active_lesson is generated and resume_at is absent", 17,
         "generated", "instance", m_generated_active_without_resume,
         "must also carry 'resume_at'"),
    Case("17: resume_at names a generated lesson, not the main path", 17,
         "generated", "instance", m_generated_resume_unlisted,
         "which is not an entry in tutorial.yaml's 'lessons' list"),
    Case("17: resume_at is not a path", 17, "generated", "instance",
         m_generated_resume_not_a_path, "resume_at must be a lesson path"),
    Case("17: resume_at is left behind after the detour finished", 17,
         "generated", "instance", m_stale_resume_at,
         "neither a lesson in lessons.generated/ nor a key in"),
    # ---- check 17, negative direction. `after:` and `resume_at` are
    # independent, so every legitimate detour shape must validate clean.
    Case("17: a boundary detour returning to the entry after its 'after:' is "
         "NOT reported", 17, "generated", "instance", m_detour_at_a_boundary,
         kind="silent"),
    Case("17: a mid-lesson detour whose 'after:' and resume_at name the SAME "
         "entry is NOT reported", 17, "generated", "instance",
         m_detour_mid_lesson_placed_on_the_interrupted_lesson, kind="silent"),
    # ---- check 11: the relaxation must not become a hole
    Case("11: active_lesson resolves, but to neither kind of lesson", 11,
         "generated", "instance", m_active_lesson_resolves_to_neither,
         "is none of: an entry in tutorial.yaml's 'lessons' list"),
    Case("11: active_lesson names a generated lesson that was never written",
         11, "generated", "instance", m_active_lesson_generated_but_absent,
         "'lessons.generated/never-written.md' does not resolve"),
    # ---- the ordinary lesson rules, applied to a generated lesson
    Case("3: a generated lesson's id does not equal its slug", 3, "generated",
         "instance", m_generated_id_not_slug,
         "id is 'LESSON' but the lesson slug is '03-reading-files-draft'"),
    Case("1: a generated lesson names a design_ref that does not exist", 1,
         "generated", "instance", m_generated_bad_design_ref,
         "'io-boundry', which is not an anchor"),
    Case("2: a generated lesson names an undeclared validator", 2, "generated",
         "instance", m_generated_undeclared_validator,
         "'cargo-clippy', which is not declared"),
    Case("4: a foldered generated lesson's body is Lesson.md", 4, "generated",
         "instance", m_generated_miscased_lesson_md,
         "must be named exactly 'LESSON.md'",
         verify=v_generated_miscased_lesson_md),
    Case("4: two generated lessons claim the same slug", 4, "generated",
         "instance", m_generated_duplicate_slug,
         "the slug '03-reading-files-draft' is used by more than one"),
    Case("4: a generated lesson shadows an authored lesson's slug", 4,
         "generated", "instance", m_generated_shadows_an_authored_slug,
         "(lessons.generated/00-hello-args.md, lessons/00-hello-args.md)"),
    Case("6: a generated lesson folder carries material nothing names", 6,
         "generated", "instance", m_generated_unnamed_material,
         "'spare-notes.md' is never named by LESSON.md"),
    Case("5: a generated lesson carries a progress marker", 5, "generated",
         "instance", m_generated_progress_marker, "a Status: label"),
    # ---- check 18: optional_lessons
    Case("18: an optional_lessons key does not resolve", 18, "cli", "bundle",
         m_optional_key_unresolved,
         "optional_lessons.lessons/never-written.md): the optional_lessons "
         "key does not resolve: no such file"),
    Case("18: an optional_lessons key names material, not a lesson", 18, "cli",
         "bundle", m_optional_key_is_material,
         "resolves to a file that is not a lesson"),
    Case("18: an optional_lessons key names a generated lesson", 18, "cli",
         "bundle", m_optional_key_is_generated,
         "an optional lesson is AUTHORED and ships in the bundle"),
    Case("18: a lesson is listed in BOTH lessons and optional_lessons", 18,
         "cli", "bundle", m_optional_also_on_main_path,
         "this lesson is also an entry in the 'lessons' list"),
    Case("18: an optional lesson has no offer_because", 18, "cli", "bundle",
         m_optional_no_offer_because, "'offer_because' is required"),
    Case("18: offer_at is empty, so nothing can reach the lesson", 18, "cli",
         "bundle", m_optional_empty_offer_at, "'offer_at' is empty"),
    Case("18: an offer_at entry is not in the lessons list", 18, "cli",
         "bundle", m_optional_offer_at_unlisted,
         "'offer_at' names 'lessons/pure-core-and-edges.md', which is not an "
         "entry"),
    Case("18: anticipates names a failure mode nothing declares", 18, "cli",
         "bundle", m_optional_anticipates_undeclared,
         "'anticipates' names 'counting-coupled-to-i-o'"),
    Case("18: repair_in is not a lessons entry", 18, "cli", "bundle",
         m_optional_repair_in_unlisted,
         "'repair_in' names 'lessons/pure-core-and-edges.md'"),
    Case("18: required_for with nothing to anticipate", 18, "cli", "bundle",
         m_optional_gate_without_anticipates,
         "'required_for' declares a gate, but 'anticipates' is missing"),
    Case("18: optional_lessons is a list, not a mapping", 18, "cli", "bundle",
         m_optional_lessons_is_a_list, "must be a mapping of lesson path"),
    Case("18: an optional_lessons entry is a sentence, not a mapping", 18,
         "cli", "bundle", m_optional_entry_is_a_string,
         "the entry must be a mapping declaring at least offer_at and "
         "offer_because"),
    # ---- check 19: failure_modes
    Case("19: a failure mode has no summary", 19, "cli", "bundle",
         m_failure_mode_no_summary, "'summary' is required"),
    Case("19: a signal names a validator nothing declares", 19, "cli",
         "bundle", m_signal_names_undeclared_validator,
         "the signal names validator 'cargo-tests'"),
    Case("19: a signal is in none of the three permitted forms", 19, "cli",
         "bundle", m_signal_in_no_permitted_form,
         "is in none of the three permitted forms"),
    Case("19: a declared failure mode nothing anticipates", 19, "cli",
         "bundle", m_failure_mode_unanticipated,
         "no optional lesson anticipates 'test-needs-a-fixture-file'"),
    Case("19: a failure-mode id is not [a-z0-9-]+", 19, "cli", "bundle",
         m_failure_mode_id_not_slug_shaped,
         "the failure-mode id 'Test_Needs_A_Fixture_File' must match"),
    # ---- check 20: the 'optional:' frontmatter flag
    Case("20: a main-path lesson declares 'optional: true'", 20, "cli",
         "bundle", m_main_path_declares_optional,
         "lessons/00-hello-args.md: the frontmatter declares 'optional"),
    Case("20: an optional lesson omits 'optional: true'", 20, "cli", "bundle",
         m_optional_lesson_omits_the_flag,
         "its frontmatter does not declare 'optional: true'"),
    Case("20: an optional lesson declares 'optional: false'", 20, "cli",
         "bundle", m_optional_flag_is_false, "optional is False"),
    Case("20: a generated lesson declares 'optional: true'", 20, "generated",
         "instance", m_generated_lesson_declares_optional,
         "it belongs to lessons.generated/"),
    # ---- check 21: the STATE.md record
    Case("21: a record names a lesson that is not optional", 21, "generated",
         "instance", m_record_names_a_main_path_lesson,
         "'lessons/00-hello-args.md' is not a key in tutorial.yaml's "
         "'optional_lessons'"),
    Case("21: a record uses an unknown state word", 21, "generated",
         "instance", m_record_unknown_state, "is recorded as 'postponed'"),
    Case("21: a record claims the state 'not-offered'", 21, "generated",
         "instance", m_record_not_offered,
         "is recorded as 'not-offered', which is not a state"),
    Case("21: one lesson is recorded twice", 21, "generated", "instance",
         m_record_twice, "is recorded twice, as 'deferred' and 'complete'"),
    Case("21: a bullet in the section is not a record at all", 21,
         "generated", "instance", m_record_is_not_a_record, "is not a record"),
    Case("21: a record says in-progress while another lesson is active", 21,
         "generated", "instance", m_record_in_progress_but_not_active,
         "is recorded as 'in-progress', but active_lesson is"),
    Case("21: active_lesson is an optional lesson with no record", 21,
         "generated", "instance", m_active_optional_without_a_record,
         "but this section records nothing about it"),
    # ---- check 21, negative direction: a learner offered nothing yet has no
    # section, and that is the ordinary state of a fresh instance.
    Case("21: an instance with no '## Optional lessons' section at all is NOT "
         "reported", 21, "generated", "instance", m_no_optional_section,
         kind="silent"),
    # ---- check 17, extended to optional lessons
    Case("17: active_lesson is an optional lesson and resume_at is absent", 17,
         "generated", "instance", m_optional_active_without_resume,
         "is an optional lesson, so STATE.md must also carry 'resume_at'"),
    # ---- check 17 and 21, negative direction: standing IN an optional lesson
    # with a way back recorded is the shape the feature exists to allow.
    Case("17: standing in an optional lesson WITH resume_at is NOT reported",
         17, "generated", "instance", m_optional_active_with_resume,
         kind="silent"),
    Case("21: an in-progress record naming the active optional lesson is NOT "
         "reported", 21, "generated", "instance", m_optional_active_with_resume,
         kind="silent"),
    # ---- the indeterminate path: check 1 cannot run, nothing else complains
    Case("exit 3: DESIGN.md is unreadable, so check 1 cannot run", 1,
         "automaton", "bundle", m_design_md_not_utf8, kind="indeterminate"),
    # ---- check 22
    Case("22: a supplies 'from' does not exist in the bundle", 22, "automaton",
         "bundle", m_supplies_from_missing, "'supplies/workspace/' does not resolve"),
    Case("22: a file is declared with a trailing slash", 22, "automaton", "bundle",
         m_supplies_from_is_a_file_declared_as_a_directory,
         "trailing '/' means a directory"),
    Case("22: a supplies 'to' escapes the workspace", 22, "automaton", "bundle",
         m_supplies_to_escapes_the_workspace, "path component '..' is not allowed"),
    Case("22: a supplies 'to' points inside the instance", 22, "automaton", "bundle",
         m_supplies_to_is_inside_the_instance, "'tutorial/' is the instance"),
    Case("22: describe is empty", 22, "automaton", "bundle",
         m_supplies_describe_is_empty, "'describe' must be a non-empty"),
    Case("22: an entry carries an unknown key", 22, "automaton", "bundle",
         m_supplies_unknown_entry_key, "unknown key 'description'"),
    Case("22: a lesson that is not listed declares supplies", 22, "automaton",
         "bundle", m_supplies_in_an_unlisted_lesson, "is not listed"),
    Case("22: a 'from' reaches into lessons.generated/", 22, "automaton", "bundle",
         m_supplies_from_under_generated, "points inside 'lessons.generated/'"),
    # ---- check 22, positive direction: without this, every case above is
    # equally consistent with a check that always fires.
    Case("22: a well-formed entry in each scope is NOT reported", 22, "automaton",
         "bundle", m_supplies_well_formed, kind="silent"),
    # ---- check 22, fix round 1: a present-but-malformed key is a finding
    Case("22: 'supplies' is a mapping, not a list (missing '- ')", 22, "automaton",
         "bundle", m_supplies_key_is_not_a_list, "must be a list"),
    Case("22: 'supplies' is a bare scalar", 22, "automaton", "bundle",
         m_supplies_key_is_a_bare_string, "must be a list"),
    # ---- check 22, fix round 1: the seven previously-unfired refusals
    Case("22: a list entry is not a mapping at all", 22, "automaton", "bundle",
         m_supplies_entry_is_not_a_mapping,
         "is not a mapping of 'from', 'to' and 'describe'"),
    Case("22: 'from' is an empty string", 22, "automaton", "bundle",
         m_supplies_from_is_empty, "'from' must be a non-empty path"),
    Case("22: 'from' is nothing but slashes", 22, "automaton", "bundle",
         m_supplies_from_is_only_slashes,
         "does not resolve: path component '' is not allowed"),
    Case("22: a real directory is declared without a trailing slash", 22,
         "automaton", "bundle", m_supplies_from_directory_without_trailing_slash,
         "a directory's 'from' must end in '/'"),
    Case("22: 'to' is an empty string", 22, "automaton", "bundle",
         m_supplies_to_is_empty, "'to' must be a non-empty path"),
    Case("22: 'to' contains a backslash", 22, "automaton", "bundle",
         m_supplies_to_has_a_backslash, "uses a backslash"),
    Case("22: 'to' is absolute", 22, "automaton", "bundle",
         m_supplies_to_is_absolute, "must be relative to the workspace, not absolute"),
    # ---- check 22, fix round 1: it must run over GENERATED lessons too
    # (instance mode only), while exempting only the listed-ness rule
    Case("22: a generated lesson's own 'from' does not resolve", 22, "generated",
         "instance", m_supplies_generated_lesson_from_missing,
         "'lessons/does-not-exist.md' does not resolve"),
    Case("22: a generated lesson's well-formed entry is NOT reported as "
         "unlisted", 22, "generated", "instance",
         m_supplies_generated_lesson_well_formed, kind="silent"),
]


# --------------------------------------------------------------------------
# Runner
# --------------------------------------------------------------------------

_failures: list[str] = []
_notes: list[str] = []
_passed = 0
_fired_checks: set[int] = set()


def note(text: str) -> None:
    _notes.append(text)


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


def run_case(case: Case) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        try:
            root = fresh(case.baseline, tmp)
            if (
                case.mode == "instance"
                and case.baseline not in INSTANCE_BASELINES
                and case.mutate not in SELF_MATERIALIZING
            ):
                to_instance(root)
            case.mutate(root)
            if case.verify is not None:
                case.verify(root)
        except AssertionError as exc:
            record(
                False,
                case.name,
                f"the fixture itself is broken, so this case proves nothing: {exc}",
            )
            return
        except Exception:  # pragma: no cover
            record(False, case.name, "fixture build raised:\n" + traceback.format_exc())
            return

        report = vb.validate(root, case.mode)
        hits = [f for f in report.findings if f.check == case.check]

        if case.kind == "silent":
            if hits:
                record(
                    False,
                    case.name,
                    f"check {case.check} FALSE POSITIVE - it reported "
                    + "; ".join(f"{h.where}: {h.message[:110]}" for h in hits),
                )
                return
            if report.exit_code() != 0:
                record(
                    False,
                    case.name,
                    f"expected exit 0, got {report.exit_code()}: "
                    + "; ".join(str(f) for f in report.findings),
                )
                return
            record(True, case.name)
            return

        if case.kind == "indeterminate":
            if report.findings:
                record(
                    False,
                    case.name,
                    "expected no findings, got: "
                    + "; ".join(str(f) for f in report.findings),
                )
                return
            if case.check not in report.blocked_checks:
                record(
                    False,
                    case.name,
                    f"expected check {case.check} to be reported as NOT RUN; "
                    f"blocked = {report.blocked_checks}",
                )
                return
            if report.exit_code() != 3:
                record(False, case.name, f"expected exit 3, got {report.exit_code()}")
                return
            record(True, case.name)
            return

        # kind == "fires"
        if not hits:
            record(
                False,
                case.name,
                f"check {case.check} did not fire. Findings were: "
                + ("; ".join(str(f) for f in report.findings) or "(none)"),
            )
            return
        if not any(case.expect in h.message or case.expect in str(h) for h in hits):
            record(
                False,
                case.name,
                f"check {case.check} fired but no message contained "
                f"{case.expect!r}. Messages: "
                + " || ".join(f"{h.where}: {h.message}" for h in hits),
            )
            return
        if report.exit_code() != 1:
            record(False, case.name, f"expected exit 1, got {report.exit_code()}")
            return
        assert case.check is not None
        _fired_checks.add(case.check)
        record(True, case.name)


# --------------------------------------------------------------------------
# Positive controls
# --------------------------------------------------------------------------


def test_baselines_pass() -> None:
    print("\nbaselines pass, with every applicable check reported as run:")
    for name, path in BASELINES.items():
        report = vb.validate(path, "bundle")
        detail = "; ".join(str(f) for f in report.findings) or (
            f"blocked = {report.blocked_checks}"
        )
        record(
            report.exit_code() == 0,
            f"baseline {name} ({path.name}) validates as a bundle",
            detail,
        )
        applicable = [c for c in vb.CHECKS if c not in vb.INSTANCE_ONLY]
        missing = [c for c in applicable if c not in report.status]
        record(
            not missing,
            f"baseline {name}: every bundle-mode check reported a status",
            f"no status for checks {missing}",
        )

    with tempfile.TemporaryDirectory() as tmpdir:
        for name in BASELINES:
            tmp = Path(tmpdir) / name
            tmp.mkdir()
            root = fresh(name, tmp)
            to_instance(root)
            report = vb.validate(root, "instance")
            record(
                report.exit_code() == 0,
                f"baseline {name} validates as an instance once materialized",
                "; ".join(str(f) for f in report.findings)
                or f"blocked = {report.blocked_checks}",
            )
            if name in NO_OPTIONAL_BASELINES:
                states = {n: report.status.get(n, ("missing", ""))[0]
                          for n in (18, 19, 20, 21)}
                record(
                    states[18] == vb.NOT_APPLICABLE
                    and states[19] == vb.NOT_APPLICABLE
                    and states[21] == vb.NOT_APPLICABLE
                    and states[20] == vb.RAN,
                    f"baseline {name} as an instance: 18, 19 and 21 report "
                    f"n/a and 20 still runs",
                    f"states = {states}",
                )


def test_generated_baseline_is_expressible() -> None:
    """The POSITIVE control for generated lessons.

    Without this the new checks prove only that they can reject. It has to be
    possible to express a valid instance WITH generated lessons, or the
    feature is unusable however good the rejections are.
    """
    print("\na valid instance carrying generated lessons:")
    root = INSTANCE_BASELINES["generated"]
    report = vb.validate(root, "instance")
    record(
        report.exit_code() == 0,
        "the generated-lesson instance validates clean",
        "; ".join(str(f) for f in report.findings)
        or f"blocked = {report.blocked_checks}",
    )
    applicable = [c for c in vb.CHECKS if c not in vb.BUNDLE_ONLY]
    missing = [c for c in applicable if c not in report.status]
    record(
        not missing,
        "every instance-mode check reported a status on it",
        f"no status for checks {missing}",
    )
    for number in (14, 15, 17, 18, 19, 20, 21):
        state, _ = report.status.get(number, ("missing", ""))
        record(
            state == vb.RAN,
            f"check {number} actually RAN on it, rather than being skipped",
            f"status was {state!r}; an 'n/a' here would mean the positive "
            f"control proves nothing about this check",
        )

    # The fixture's own properties, verified by listing rather than by
    # exists(), because this filesystem is case-insensitive.
    generated = root / "lessons.generated"
    names = sorted(os.listdir(generated))
    record(
        "lifetimes-and-borrows.md" in names
        and "03-reading-files-draft" in names,
        "the fixture holds one single-file and one foldered generated lesson",
        f"entries = {names}",
    )
    record(
        "LESSON.md" in os.listdir(generated / "03-reading-files-draft"),
        "the foldered generated lesson's body is an exact-case LESSON.md",
        f"entries = {sorted(os.listdir(generated / '03-reading-files-draft'))}",
    )
    kinds = sorted(
        line.split(":", 1)[1].strip()
        for path in (
            generated / "lifetimes-and-borrows.md",
            generated / "03-reading-files-draft" / "LESSON.md",
        )
        for line in path.read_text().splitlines()
        if line.startswith("kind:")
    )
    record(
        kinds == ["main-path-draft", "side-lesson"],
        "both permitted kinds are exercised by the fixture",
        f"kinds = {kinds}",
    )
    state_fm, _ = vb.split_frontmatter((root / "STATE.md").read_text())
    assert state_fm is not None
    front = vb._RestrictedYaml(state_fm, "STATE.md").parse()
    record(
        front["active_lesson"].startswith("lessons.generated/")
        and front["resume_at"] in ["lessons/01-subcommands/LESSON.md"],
        "STATE.md sits ON a generated lesson and records where to resume",
        repr(front),
    )
    listed = [
        str(e)
        for e in vb._RestrictedYaml(
            (root / "tutorial.yaml").read_text(), "tutorial.yaml"
        ).parse()["lessons"]
    ]
    record(
        not any(e.startswith("lessons.generated") for e in listed),
        "the manifest lessons list was not mutated to mention them",
        repr(listed),
    )

    # The baseline is a MID-LESSON detour, and this is the assertion that
    # says so. The learner is part-way through lesson 01: the detour is
    # PLACED after lesson 00, the last lesson they completed, and it returns
    # them INTO lesson 01, which they never finished.
    #
    # The superseded rule derived the return target from `after:` and said it
    # was "the entry after the detour's `after:` in lessons". Under it there
    # was no way to record a return into an interrupted lesson at all: a
    # detour taken during lesson L had to be placed `after: L`, and the
    # learner then came back at the entry AFTER L, silently skipping the rest
    # of the lesson they were in the middle of. So this is the positive proof
    # that the fix enables the case, not merely that it stopped rejecting it.
    side_fm, _ = vb.split_frontmatter(
        (root / "lessons.generated" / "lifetimes-and-borrows.md").read_text()
    )
    assert side_fm is not None
    side = vb._RestrictedYaml(side_fm, "lifetimes-and-borrows.md").parse()
    placement = str(side["after"])
    resume = str(front["resume_at"])
    record(
        placement in listed and resume in listed,
        "the mid-lesson detour places itself, and returns, inside 'lessons'",
        f"after = {placement!r}, resume_at = {resume!r}, lessons = {listed!r}",
    )
    record(
        listed.index(resume) > listed.index(placement),
        "the mid-lesson detour returns to a LATER lesson than the one it "
        "follows - the interrupted lesson, not the one after it",
        f"after = {placement!r} at index {listed.index(placement)}, "
        f"resume_at = {resume!r} at index {listed.index(resume)}",
    )
    record(
        resume != listed[-1] and listed.index(resume) > 0,
        "and it is not the final-lesson special case, which would prove "
        "nothing about mid-lesson detours",
        f"resume_at = {resume!r}, lessons = {listed!r}",
    )

    # And it must still be rejected as a BUNDLE, on check 13.
    report = vb.validate(root, "bundle")
    hits = [f for f in report.findings if f.check == 13]
    record(
        bool(hits) and report.exit_code() == 1,
        "the same directory checked as a bundle fails check 13",
        f"findings = {[str(f) for f in report.findings]}",
    )


def test_optional_baseline_is_expressible() -> None:
    """The POSITIVE control for optional lessons.

    Without it the four new checks prove only that they can reject. It has to
    be possible to express a valid bundle WITH optional lessons, in both
    authored shapes, or the feature is unusable however good the rejections
    are.
    """
    print("\na valid bundle carrying optional lessons:")
    root = BASELINES["cli"]
    report = vb.validate(root, "bundle")
    record(
        report.exit_code() == 0,
        "the optional-lesson bundle validates clean",
        "; ".join(str(f) for f in report.findings)
        or f"blocked = {report.blocked_checks}",
    )
    for number in (18, 19, 20):
        state, _ = report.status.get(number, ("missing", ""))
        record(
            state == vb.RAN,
            f"check {number} actually RAN on it, rather than being skipped",
            f"status was {state!r}; an 'n/a' here would mean the positive "
            f"control proves nothing about this check",
        )

    manifest = vb._RestrictedYaml(
        (root / "tutorial.yaml").read_text(), "tutorial.yaml"
    ).parse()
    optional = manifest["optional_lessons"]
    record(
        set(optional) == {OPT_PURE, OPT_CHARS},
        "the fixture declares exactly the two optional lessons",
        repr(sorted(optional)),
    )
    gates = ("anticipates", "repair_in", "required_for")
    record(
        all(field in optional[OPT_PURE] for field in gates),
        "one of them is the ANTICIPATION shape - anticipates, repair_in and "
        "required_for all present",
        repr(optional[OPT_PURE]),
    )
    record(
        not any(field in optional[OPT_CHARS] for field in gates),
        "and the other is plain ENRICHMENT, declaring none of the three, "
        "which must still validate clean",
        repr(optional[OPT_CHARS]),
    )
    modes = manifest["failure_modes"]
    anticipated = set(optional[OPT_PURE]["anticipates"])
    record(
        set(modes) == anticipated and len(modes) == 2,
        "every declared failure mode is anticipated, and both are exercised",
        f"declared = {sorted(modes)}, anticipated = {sorted(anticipated)}",
    )
    forms = {
        signal.split(":", 1)[0]
        for mode in modes.values()
        for signal in mode.get("signals", [])
    }
    record(
        forms == {"validator", "token", "diagnosis"},
        "all three signal forms are exercised by the fixture",
        f"forms = {sorted(forms)}",
    )
    for rel in (OPT_PURE, OPT_CHARS):
        front, _ = vb.split_frontmatter((root / rel).read_text())
        assert front is not None
        parsed = vb._RestrictedYaml(front, rel).parse()
        record(
            parsed.get("optional") is True,
            f"{rel} declares 'optional: true' in its own frontmatter",
            repr(parsed),
        )
    listed = [str(entry) for entry in manifest["lessons"]]
    record(
        not any(entry in optional for entry in listed),
        "no lesson is on the main path AND offered",
        f"lessons = {listed!r}",
    )
    for rel in listed:
        front, _ = vb.split_frontmatter((root / rel).read_text())
        assert front is not None
        record(
            "optional" not in vb._RestrictedYaml(front, rel).parse(),
            f"the main-path lesson {rel} declares no 'optional' field",
            rel,
        )

    # Backward compatibility. A bundle that declares neither key is valid
    # exactly as it was before the keys existed, and the two checks that have
    # nothing to look at must say "n/a" rather than passing silently.
    for name in NO_OPTIONAL_BASELINES:
        other = vb.validate(BASELINES[name], "bundle")
        states = {n: other.status.get(n, ("missing", ""))[0] for n in (18, 19, 20)}
        record(
            other.exit_code() == 0,
            f"baseline {name}, which declares neither new key, still passes",
            "; ".join(str(f) for f in other.findings)
            or f"blocked = {other.blocked_checks}",
        )
        record(
            states[18] == vb.NOT_APPLICABLE and states[19] == vb.NOT_APPLICABLE,
            f"baseline {name}: checks 18 and 19 report n/a, not a pass",
            f"states = {states}",
        )
        record(
            states[20] == vb.RAN,
            f"baseline {name}: check 20 still RUNS - 'no lesson declares "
            f"optional' is a real thing to verify",
            f"states = {states}",
        )


def test_real_repositories() -> None:
    """The fixtures are copies. Check the originals too, when they are here."""
    print("\nthe real artifacts these fixtures were copied from:")
    externals = [
        (
            "bundle",
            Path.home()
            / "src/github.com/skomp/tutorail-bundles/rust-automaton-db",
        ),
        ("instance", Path.home() / "src/github.com/skomp/automaton-db/tutorial"),
        ("bundle", REPO / "skills/tutorail/examples/rust-cli-basics"),
    ]
    for mode, path in externals:
        if not path.is_dir():
            note(f"  SKIPPED: {path} is not present, so it was not checked")
            print(f"  skip {path} (not present)")
            continue
        report = vb.validate(path, mode)
        record(
            report.exit_code() == 0,
            f"{path} validates as a {mode}",
            "; ".join(str(f) for f in report.findings)
            or f"blocked = {report.blocked_checks}",
        )


def test_mode_is_never_inferred() -> None:
    """Requirement 1, and the reason check 7 can fail at all."""
    print("\nthe mode is explicit, never inferred from the state file present:")
    report = vb.validate(BASELINES["automaton"], "instance")
    hits = [f for f in report.findings if f.check == 7]
    record(
        bool(hits) and report.exit_code() == 1,
        "a valid BUNDLE checked with --instance fails check 7",
        f"findings = {[str(f) for f in report.findings]}",
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        root = fresh("automaton", Path(tmpdir))
        to_instance(root)
        report = vb.validate(root, "bundle")
        hits = [f for f in report.findings if f.check == 7]
        record(
            bool(hits) and report.exit_code() == 1,
            "a valid INSTANCE checked as a bundle fails check 7",
            f"findings = {[str(f) for f in report.findings]}",
        )


def test_cli() -> None:
    print("\nthe command line:")

    def run(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            capture_output=True,
            text=True,
        )

    done = run(str(BASELINES["automaton"]))
    record(
        done.returncode == 0 and "PASS" in done.stdout,
        "exit 0 and PASS on a good bundle",
        f"rc={done.returncode} out={done.stdout[-400:]}",
    )
    record(
        "yaml reader:" in done.stdout and "checks:" in done.stdout,
        "the output names the YAML reader and lists every check",
        done.stdout[:200],
    )
    record(
        "What a pass does and does not mean" in done.stdout,
        "a passing run states what it does not certify",
        done.stdout[-200:],
    )

    done = run(str(BASELINES["automaton"]), "--instance")
    record(
        done.returncode == 1 and "FAIL" in done.stdout,
        "exit 1 and FAIL on a bundle checked as an instance",
        f"rc={done.returncode}",
    )
    record(
        "NOT RUN" in done.stdout and "does not certify" in done.stdout,
        "a check that could not run is named as NOT RUN, never passed over",
        done.stdout[-500:],
    )

    done = run(str(SCRIPT))
    record(
        done.returncode == 2,
        "exit 2 when the path is not a directory",
        f"rc={done.returncode} err={done.stderr[:200]}",
    )

    done = run("--help")
    record(
        done.returncode == 0 and "--instance" in done.stdout,
        "--help documents --instance",
        done.stdout[:200],
    )


# --------------------------------------------------------------------------
# The restricted YAML reader
# --------------------------------------------------------------------------

REAL_MANIFEST = (BASELINES["automaton"] / "tutorial.yaml").read_text()


def test_yaml_reader() -> None:
    print("\nthe restricted YAML reader:")
    if vb._pyyaml is not None:  # pragma: no cover
        note(
            "  NOTE: PyYAML is importable here, so validate_bundle used it. "
            "The restricted reader is still tested directly below."
        )

    def load(text: str):
        return vb._RestrictedYaml(text, "<test>").parse()

    manifest = load(REAL_MANIFEST)
    record(
        manifest["bundle_format"] == 1,
        "bundle_format parses as the integer 1",
        repr(manifest.get("bundle_format")),
    )
    record(
        manifest["id"] == "rust-automaton-db",
        "a plain scalar parses as a string",
        repr(manifest.get("id")),
    )
    record(
        len(manifest["lessons"]) == 23
        and manifest["lessons"][0] == "lessons/00-foundations.md",
        "the block sequence parses in order, all 23 entries",
        repr(manifest.get("lessons"))[:160],
    )
    record(
        manifest["subjects"] == [
            "rust", "databases", "distributed-systems", "automata",
            "storage-engines",
        ],
        "a flow sequence parses",
        repr(manifest.get("subjects")),
    )
    record(
        manifest["validators"]["cargo-check"] == {
            "kind": "command",
            "command": ["cargo", "check"],
        },
        "a nested flow mapping with a flow sequence inside parses",
        repr(manifest["validators"].get("cargo-check")),
    )
    record(
        isinstance(manifest["description"], str)
        and "\n" not in manifest["description"].rstrip("\n")
        and "automaton-native" in manifest["description"],
        "a '>' folded block scalar folds onto one line",
        repr(manifest.get("description")),
    )
    record(
        manifest["one_task_at_a_time"] is True,
        "'true' parses as a boolean",
        repr(manifest.get("one_task_at_a_time")),
    )

    template_fm, _ = vb.split_frontmatter(
        (BASELINES["automaton"] / "STATE.template.md").read_text()
    )
    assert template_fm is not None
    front = load(template_fm)
    record(
        front["updated"] is None and front["status"] == "not-started",
        "'null' parses as None and frontmatter parses without the --- fences",
        repr(front),
    )

    accepted = load(
        "accepted_warnings:\n"
        "  - pattern: \"is never used\"\n"
        "    reason: 'Engine unreachable while main() is empty'\n"
        "    until_lesson: lessons/03-first-refactor.md\n"
    )
    record(
        accepted["accepted_warnings"][0] == {
            "pattern": "is never used",
            "reason": "Engine unreachable while main() is empty",
            "until_lesson": "lessons/03-first-refactor.md",
        },
        "a sequence of mappings parses (STATE.md's accepted_warnings shape)",
        repr(accepted),
    )
    record(
        load("a: value # not a comment marker inside\nb: 'has # inside'\n")
        == {"a": "value", "b": "has # inside"},
        "comments are stripped, but not a '#' inside quotes",
        repr(load("a: value # c\nb: 'has # inside'\n")),
    )
    record(
        load("s: |\n  line one\n  line two\n")["s"] == "line one\nline two\n",
        "a '|' literal block scalar keeps its newlines",
        repr(load("s: |\n  line one\n  line two\n")),
    )
    record(
        load("v: local:../tutorail-bundles/rust-automaton-db")["v"]
        == "local:../tutorail-bundles/rust-automaton-db",
        "a plain scalar containing a colon is not split",
        repr(load("v: local:../x")),
    )
    record(
        load("e: {}\nf: []\n") == {"e": {}, "f": []},
        "empty flow collections parse",
        repr(load("e: {}\nf: []\n")),
    )

    # The rejections. These are the point: the restricted reader must refuse
    # what it does not support rather than guessing.
    rejections = [
        ("a YAML anchor", "a: &x 1\nb: 2\n", "anchors"),
        ("a YAML alias", "a: 1\nb: *x\n", "aliases"),
        ("a tag", "a: !!set 1\n", "tags"),
        ("a merge key", "a: 1\n<<: b\n", "merge keys"),
        ("a tab in the indentation", "a:\n\t- 1\n", "tab"),
        ("a duplicate key", "a: 1\na: 2\n", "duplicate key"),
        (
            "a plain scalar continued onto the next line",
            "a: one\n  two\n",
            "cannot continue onto the next line",
        ),
        ("a second document", "a: 1\n---\nb: 2\n", "multiple YAML documents"),
        ("a document-end marker", "a: 1\n...\n", "'...'"),
        ("'key:value' with no space", "a:1\n", "with a space after the colon"),
        ("an unterminated quote", 'a: "open\n', "unterminated"),
        ("an unterminated flow sequence", "a: [1, 2\n", "unterminated flow sequence"),
        ("an unterminated flow mapping", "a: {k: v\n", "unterminated flow mapping"),
        (
            "an explicit block-scalar indent indicator",
            "a: >2\n   text\n",
            "is not supported",
        ),
        ("text after a flow collection", "a: [1] junk\n", "unexpected text"),
        ("a bare line that is not key: value", "just text\n", "expected 'key: value'"),
        (
            "an unsupported escape",
            'a: "\\x41"\n',
            "escape sequence",
        ),
    ]
    for label, text, expect in rejections:
        try:
            value = load(text)
        except vb.YamlError as exc:
            record(
                expect in str(exc),
                f"rejects {label}",
                f"rejected, but the message was {str(exc)!r}, "
                f"which does not mention {expect!r}",
            )
        except Exception as exc:  # pragma: no cover
            record(False, f"rejects {label}", f"raised {type(exc).__name__}: {exc}")
        else:
            record(
                False,
                f"rejects {label}",
                f"it did NOT reject it - it guessed, and returned {value!r}",
            )


def test_names_file() -> None:
    print("\ncheck 6's material-mention match (delimiter-aware, not substring):")
    cases = [
        (True, "read `usage.txt` when the learner asks", "usage.txt"),
        (True, "See [the usage text](usage.txt).", "usage.txt"),
        (True, "the file usage.txt holds it", "usage.txt"),
        (True, "show `assets/dafsa.svg` to them", "assets/dafsa.svg"),
        (True, "show `dafsa.svg` to them", "assets/dafsa.svg"),
        (True, "sentence ends with usage.txt.", "usage.txt"),
        (False, "https://example.invalid/archive/usage.txt.bak", "usage.txt"),
        (False, "the old-usage.txt file is gone", "usage.txt"),
        (False, "usage.txt2 is a different thing", "usage.txt"),
        (False, "nothing here names it at all", "usage.txt"),
    ]
    for expected, text, name in cases:
        got = vb.names_file(text, name)
        record(
            got == expected,
            f"names_file({name!r}) is {expected} for {text[:46]!r}",
            f"got {got}",
        )


def test_supplies_helpers() -> None:
    """collect_supplies and supplies_covers, exercised directly.

    check 22 does not call either function itself, and A2 consumes both by
    name, so this is the only place in this suite that proves them right.
    """
    print("\ncollect_supplies and supplies_covers, exercised directly:")
    with tempfile.TemporaryDirectory() as tmpdir:
        root = fresh("automaton", Path(tmpdir))
        edit(
            root / "lessons" / "00-foundations.md",
            "id: 00-foundations",
            "id: 00-foundations\n"
            "supplies:\n"
            "  - from: lessons/00-foundations.md\n"
            "    to: notes.md\n"
            "    describe: a starter note\n"
            "  - not a mapping\n",
        )
        report = vb.Report(mode="bundle", target=root)
        lessons, _ = vb.discover_lessons(root, report)
        manifest = {
            "supplies": [
                {"from": "supplies/Cargo.toml", "to": "Cargo.toml", "describe": "x"},
                "not a mapping either",
            ]
        }

        pairs = vb.collect_supplies(root, manifest, lessons)
        wheres = sorted(where for where, _ in pairs)
        record(
            wheres == ["lessons/00-foundations.md", "tutorial.yaml"],
            "collect_supplies finds one manifest-scope and one lesson-scope entry",
            f"got {wheres}",
        )
        record(
            all(isinstance(entry, dict) for _, entry in pairs),
            "collect_supplies drops the non-mapping entry in both scopes",
            f"got {[entry for _, entry in pairs]}",
        )

        entries = [entry for _, entry in pairs]
        record(
            vb.supplies_covers(entries, "supplies/Cargo.toml"),
            "supplies_covers matches an exact 'from'",
        )
        record(
            not vb.supplies_covers(entries, "supplies/Cargo2.toml"),
            "supplies_covers does not match an unrelated path "
            "(negative control)",
        )

        dir_entries = [
            {"from": "lessons/13-load-gltf-model/model/", "to": "x", "describe": "x"}
        ]
        record(
            vb.supplies_covers(
                dir_entries, "lessons/13-load-gltf-model/model/Duck.glb"
            ),
            "supplies_covers matches a file under a declared directory",
        )
        record(
            not vb.supplies_covers(
                dir_entries, "lessons/13-load-gltf-model/model2/x.bin"
            ),
            "supplies_covers does not treat a directory name as a string "
            "prefix (negative control - 'model' must not cover 'model2/x')",
        )


def test_supplies_status_text() -> None:
    """check 22's status, not just its exit code - fix round 1.

    A "silent" Case only proves "no finding, exit 0", which cannot tell
    "both entries were seen and are clean" apart from "nothing was seen at
    all". Reading the exact status tuple closes that gap. This also pins
    the ABSENT-key n/a reason, so it cannot regress back to reporting n/a
    for a PRESENT-but-malformed key (fix round 1's Critical finding).
    """
    print("\ncheck 22's status text, for an absent key and a well-formed one:")
    with tempfile.TemporaryDirectory() as tmpdir:
        root = fresh("automaton", Path(tmpdir))
        report = vb.validate(root, "bundle")
        record(
            report.status.get(22) == (vb.NOT_APPLICABLE, "no bundle declares supplies"),
            "no 'supplies' key anywhere: check 22 is n/a, with that reason",
            f"got {report.status.get(22)}",
        )

    with tempfile.TemporaryDirectory() as tmpdir:
        root = fresh("automaton", Path(tmpdir))
        m_supplies_well_formed(root)
        report = vb.validate(root, "bundle")
        record(
            report.exit_code() == 0,
            "the well-formed fixture still validates clean",
            "; ".join(str(f) for f in report.findings),
        )
        record(
            report.status.get(22)
            == (vb.RAN, "2 supplies entries across 2 declaration sites"),
            "both the manifest-scope and lesson-scope entry were counted",
            f"got {report.status.get(22)}",
        )

    with tempfile.TemporaryDirectory() as tmpdir:
        # The singular form, alongside the plural above: "1 ... entry ...
        # site", not "1 ... entries ... sites".
        root = fresh("automaton", Path(tmpdir))
        m_supplies_describe_is_empty(root)
        report = vb.validate(root, "bundle")
        record(
            report.status.get(22)
            == (vb.RAN, "1 supplies entry across 1 declaration site"),
            "one entry at one site is pluralised as singular, not plural",
            f"got {report.status.get(22)}",
        )

    with tempfile.TemporaryDirectory() as tmpdir:
        # The third repro from fix round 1's Critical finding: 'supplies: []'
        # is PRESENT (so not n/a) and is already a well-formed, empty list
        # (so it is not a malformed-key finding either) - it just has
        # nothing to check.
        root = fresh("automaton", Path(tmpdir))
        append(root / "tutorial.yaml", "\nsupplies: []\n")
        report = vb.validate(root, "bundle")
        record(
            report.exit_code() == 0 and not report.findings,
            "an explicitly empty 'supplies: []' is well-formed, not a finding",
            "; ".join(str(f) for f in report.findings),
        )
        record(
            report.status.get(22)
            == (vb.RAN, "0 supplies entries across 1 declaration site"),
            "'supplies: []' is present, so check 22 is 'ran' with 0 entries, not n/a",
            f"got {report.status.get(22)}",
        )


def test_check_coverage() -> None:
    print("\nmeta: every check has a fixture that makes it fire:")
    for number, description in sorted(vb.CHECKS.items()):
        record(
            number in _fired_checks,
            f"check {number} was demonstrated firing  ({description[:58]})",
            "NO fixture in this suite makes this check report a finding, so it "
            "is a false oracle: it can only be shown passing.",
        )


# --------------------------------------------------------------------------


def main() -> int:
    print("validate_bundle.py test suite")
    print(f"  script:      {SCRIPT}")
    print(f"  yaml reader: {vb.YAML_READER}")
    print(f"  python:      {sys.version.split()[0]}")

    print("\nbroken fixtures, each asserting its own check fires:")
    for case in CASES:
        run_case(case)

    test_baselines_pass()
    test_generated_baseline_is_expressible()
    test_optional_baseline_is_expressible()
    test_real_repositories()
    test_mode_is_never_inferred()
    test_cli()
    test_yaml_reader()
    test_names_file()
    test_supplies_helpers()
    test_supplies_status_text()
    test_check_coverage()

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
