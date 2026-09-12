---
id: 00-parse-a-query
title: From a query string to a plan
design_refs: [plan-shape]
validators: [go-build, go-test]
---

## Purpose

Turn a query string into an operator tree, so every later lesson has something
to execute.

## Learning objectives

- Tokenise a small query language
- Build an operator tree from the tokens
- Reject a query the engine cannot promise to run, with a reason

## Theory

A parser that accepts everything and fails at execution time moves the error to
where the user can do least about it. Reject early, and say why.

## Completion conditions

`go test ./...` passes, and parsing a query naming an unknown field returns an
error that names the field.
