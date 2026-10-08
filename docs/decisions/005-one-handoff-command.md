---
type: decision
status: accepted
date: 2026-10-08
projects: [workflow]
concepts: [handoff]
amends: []
supersedes: []
tags: [type/decision, status/accepted, project/workflow, topic/handoff]
---

# 005 — One `/handoff` procedure closes a slice

> **Summary.** A single procedure runs the vault sync, the lints, the pattern scan and the handoff draft, checks the handoff with a fresh reader, and reports what awaits the owner's acceptance.

## Context

Closing a slice already ends with a handoff (step 9 of `docs/CLOSING_A_SLICE.md`). Cheap restarts (ADR 001) need that step to be quick and complete, and the vault needs updating at the same moment.

## Decision

`docs/sop/handoff.md` defines the steps; scripts do the deterministic ones; a model drafts the rest; the owner accepts. It runs after the slice's commits land, because the sync reads committed state. Commit and push stay the owner's call. Writing the ADR is not part of it: that happens before the code.

## Consequences

One command from the owner's side. The work inside a long session costs tokens, which is why the guard reminds early. Without an adapter the owner says "follow `docs/sop/handoff.md`".

## Alternatives rejected

- **A hook that runs it automatically.** It would act before the owner has reviewed the slice, and the draft needs acceptance.
- **Separate commands for each part.** More to remember; the parts belong to one moment.
