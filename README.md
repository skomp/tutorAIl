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
git clone git@github.com:skomp/tutorAIl.git ~/src/tutorAIl
mkdir -p ~/.agents/skills
ln -s ~/src/tutorAIl/skills/tutorail ~/.agents/skills/tutorail
```

`~/.agents/skills/` is Codex's documented user scope, and it follows symlinks, so
edits to the clone take effect immediately.

Not `codex plugin add`. Codex refuses a marketplace entry whose source path is the
marketplace root — it registers the marketplace and then enumerates nothing, with no
error — and putting the plugin in a subdirectory whose `skills/` is a symlink installs a
plugin with no skills in it, also without an error. Until that is resolved, the skills
directory is the supported Codex install.

One skill body serves both hosts.

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
    ├── 08-automaton-machinery/
    │   ├── LESSON.md            a lesson that ships material
    │   └── worked-example.md
    └── interior-mutability.md   an optional lesson, offered rather than sequenced
```

A bundle may also declare `supplies` in `tutorial.yaml` or in a lesson — files it hands
your workspace, such as a model or a dataset — which the tutor places and reports as setup
rather than asking you to copy them yourself.

## Lessons the tutor offers instead of teaching

Most lessons sit on the main path and every learner walks them in order. A course can also
carry **optional lessons**, which the tutor offers at a point the author names.

The useful case is a mistake the author can see coming. The tutor warns you in a sentence,
offers the lesson, and lets you say "not now" — and then leaves it alone. If the failure it
anticipated actually turns up later, the tutor recognises it, tells you this is the thing
you set aside and where, and offers the lesson again. Take it, and you come back to repair
the work that caused the failure.

Deferring is a real answer, not a delay. The tutor does not raise an offer a second time
without new evidence, and it never offers a lesson you have already taken. A course must
still be finishable by someone who declines every offer.

`optional_lessons` and `failure_modes` in `tutorial.yaml` are how an author expresses it;
`bundle-format.md` sections 2 and 12 carry the contract and a worked example.

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

You configure which catalogues to read in `~/.config/tutorail/catalogs.yaml`. A catalogue
may be a local file, or a Git repository — including a private one.

```yaml
catalogs:
  - id: skomp
    source:
      type: git
      url: git@github.com:skomp/tutorail-bundles.git
      ref: main
      path: catalog.yaml        # repository root, or any subfolder
  - id: mine
    source: { type: file, path: ~/tutorials/catalog.yaml }
  - id: builtin
    source: { type: bundled }
```

**A bundles repository carries its own catalogue.** Put a `catalog.yaml` at its root listing
its bundles by relative path, and adding the repository brings the bundles with it. Bundle
paths resolve from the directory holding their catalogue file, with no exceptions.

**Private repositories need no extra setup.** Fetching uses the Git credentials you already
have — an SSH key, or `gh`. tutorAIl stores no tokens and never asks for one.

Entries are read in the order you list them and **the first match for a tutorial id wins**,
so put your own catalogues above `builtin` to override a shipped course. When an entry is
shadowed, the runner says which catalogue supplied it and which were overridden.

Catalogues refresh when a discovery request starts — never on every turn, and never during a
resume. If one cannot be reached, the others are still served: the runner names the one that
failed, falls back to its last successful copy, says the results are cached, and
distinguishes an unreachable host from a repository you lack access to from a repository with
no catalogue file, because those have three different repairs.

```
python3 skills/tutorail/scripts/catalogs.py discover   # refresh and list
python3 skills/tutorail/scripts/catalogs.py status     # report without fetching
```

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

The runner runs the same script. It validates the instance it has just materialized, before
the first task, so that a defect in your bundle is found by the runner rather than by a
learner several lessons in. It does not run on a teaching turn, and a learner never invokes
it by hand. Your run and the runner's run are the same checks over the same files, which is
the point: a bundle that passes here starts cleanly there.

It checks structure — that references resolve, that no progress leaked into the course, that
every lesson is reachable. It says nothing about whether the course is any good.

One thing it cannot check is worth knowing before you ship: a course carrying optional
lessons must still be finishable by a learner who declines every offer. Nothing enforces
that, and `bundle-format.md` section 13 explains why it is the invariant that keeps an
older runner — which ignores the offers entirely — from teaching a broken course.

## Design

`docs/superpowers/specs/2026-09-11-tutorial-runner-design.md` records the architecture, the
measured host facts behind the packaging choices, and the designs that were tried and
rejected.

## Licence

MIT.
