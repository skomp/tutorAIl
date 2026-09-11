# Design

## Lesson forms {#lesson-forms}

A lesson is a single Markdown file, or a folder holding `LESSON.md` plus the
material that lesson needs.

## Material loading {#material-loading}

Material loads only when `LESSON.md` names it. A file the lesson never names
cannot be discovered by the tutor.

## Unresolved: nested folders {#nested-folders}

Whether material may itself sit in subfolders is not settled. This fixture
uses one, so the behaviour is at least pinned.
