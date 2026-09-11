# tutorAIl

Interactive tutorials that run inside a coding agent.

The agent you already use — Claude Code or Codex — is the runtime. tutorAIl supplies the
teaching protocol, a portable course format, and a progress lifecycle. There is no app,
no server, and no model API key.

```
"I want to learn Rust."
        │
        ▼
  discover matching tutorials in your catalogue
        │
        ▼
  you choose one
        │
        ▼
  the course is materialized into your project as tutorial/
        │
        ▼
  one lesson is loaded — not the course
        │
        ▼
  one task at a time, you write the code
```

## Why it exists

A tutor that holds an entire course in context is expensive and forgetful. tutorAIl loads
the manifest, your progress, and exactly one lesson. A 23-lesson course costs the same per
turn as a 3-lesson one.

Progress lives in your repository, not in a chat log. Close the conversation, come back a
month later in a fresh session, and the tutor resumes at the right task.

## Install

**Claude Code**

```
/plugin marketplace add skomp/tutorAIl
/plugin install tutorail@tutorail
```

**Codex**

```
codex plugin marketplace add https://github.com/skomp/tutorAIl
codex plugin add tutorail
```

One skill body serves both hosts. Only the packaging manifest differs.

## Use

Start a tutorial:

```
I want to learn Rust.
Teach me distributed systems.
Show me database tutorials.
```

You are shown the matching courses and you pick one. If several match, you always get a
choice — the runner never silently selects for you.

Resume one, from the directory holding the course:

```
Continue the tutorial.
```

No selection, no catalogue. The runner finds `tutorial/`, reads your progress, and picks up
at the pending task.

## How a course is laid out

A **bundle** is a course. It is written once and taken by many learners, so it holds no
progress:

```
rust-automaton-db/
├── tutorial.yaml        manifest: id, subjects, ordered lessons, validators, ownership
├── COURSE.md            goal, teaching philosophy, chapter map
├── DESIGN.md            durable subject decisions, anchored per section
├── STATE.template.md    the shape a fresh learner starts in
└── lessons/
    ├── 00-foundations.md
    └── 08-automaton-machinery/
        ├── LESSON.md            a lesson that ships material
        └── worked-example.md
```

An **instance** is your copy, inside your own project, and it is the only place progress
exists:

```
my-project/
├── src/                 yours; the tutor never edits it
└── tutorial/
    ├── tutorial.yaml
    ├── COURSE.md
    ├── DESIGN.md
    ├── STATE.md         ← your progress
    └── lessons/
```

The rule, which a script enforces:

> A bundle contains `STATE.template.md` and never `STATE.md`.
> An instance contains `STATE.md` and never `STATE.template.md`.

## What the tutor will and will not do

It reads your source, runs the course's configured checks (`cargo test`, a file check,
whatever the bundle declares), explains concepts, and records progress once you have
demonstrated it.

It does **not** write your code. It will not edit learner-owned paths or finish an exercise
for you, even when you are stuck — unless you explicitly ask, or the bundle's
`ownership_policy` allows it. A compiler error is part of the course, not an accident to be
cleaned up behind you.

## Adding your own tutorials

Courses live outside this repository. `skomp/tutorail-bundles` holds a collection; each
subfolder is one bundle.

Register one by adding it to your catalogue at `~/.config/tutorail/catalog.yaml`:

```yaml
catalog_version: 1
tutorials:
  - id: rust-automaton-db
    title: Learn Rust by Building AutomatonDB
    description: Project-driven Rust, database internals, distributed systems.
    subjects: [rust, databases, distributed-systems]
    level: intermediate-to-advanced
    workspace_kind: existing-or-new-repository
    source:
      type: local
      path: ~/src/github.com/skomp/tutorail-bundles/rust-automaton-db
```

`source.type` is the extension point. `local` works today; `git` and `archive` are declared
and will fail explicitly rather than silently until implemented. An online catalogue can be
added later without changing anything about how tutorials run.

## Writing a bundle

`skills/tutorail/references/bundle-format.md` is the normative contract. It is
self-contained — hand it to a person or paste it into another model and it is enough on its
own.

`skills/tutorail/examples/rust-cli-basics/` is a small worked example in both lesson forms.

Check your work before shipping it:

```
python3 skills/tutorail/scripts/validate_bundle.py path/to/bundle
python3 skills/tutorail/scripts/validate_bundle.py --instance path/to/project/tutorial
```

The validator is an authoring tool. Learners never run it. It checks structure — that
references resolve, that no progress leaked into the course, that every lesson is reachable.
It says nothing about whether the course is any good.

## Design

`docs/superpowers/specs/2026-09-11-tutorial-runner-design.md` records the architecture, the
measured host facts behind the packaging choices, and the designs that were tried and
rejected.

## Licence

MIT.
