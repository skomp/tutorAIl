---
id: 01-state-merging
title: State merging, with material
design_refs: [material-loading, nested-folders]
validators: [reads-the-example, judged]
---

## Purpose

Show a lesson that ships material, and name that material explicitly.

## Prerequisites

- `00-single-file`

## Learning objectives

- Explain why a folder costs nothing until the lesson asks for its contents
- Describe state merging at a high level

## Theory

A folder lesson keeps a long example out of the body. The body is loaded every
turn; a sibling file is loaded only when the body names it.

For the state-merging walkthrough, read `worked-example.md`.

If the learner asks how minimisation differs from a trie, show
`assets/dafsa.svg`.

## Concepts to teach

Progressive disclosure; why unnamed material is unreachable.

## Constraints

Do not paste the worked example into the conversation wholesale.

## Suggested progression

Read the body. Open the worked example only if the learner asks for a walk
through the merge.

## Completion conditions

The learner explains, unprompted, why material that the lesson never names is
dead weight.

## On completion, persist

Record the learner's explanation in DESIGN.md under `#material-loading`.

## Optional deeper paths

None.
