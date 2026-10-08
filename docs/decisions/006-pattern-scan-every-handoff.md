---
type: decision
status: accepted
date: 2026-10-08
projects: [workflow]
concepts: [Pattern scan]
amends: []
supersedes: []
tags: [type/decision, status/accepted, project/workflow, topic/patterns]
---

# 006 — Scan each slice's diff for reusable patterns

> **Summary.** At every `/handoff` a model reads only the slice's diff and drafts a note for any reusable pattern. Each candidate cites file and lines; "none" is a normal result; the owner accepts.

## Context

ADRs cover deliberate decisions. In one project, several reusable building blocks (atomic file writes, path guards) appear in few or no ADRs by a crude keyword search, and live only in module docstrings. Scanning a whole codebase is costly and invites invented patterns.

## Decision

Scan the diff of the slice, not the codebase. A candidate must cite the file and line range it comes from. Drafts are marked `status: draft` in `Patterns/` until the owner promotes them.

## Consequences

A few thousand tokens per slice. Weaker models may suggest weaker candidates; acceptance filters them.

## Alternatives rejected

- **Scan the whole codebase on a schedule.** Expensive, and finds old code, not what the slice taught.
- **Only document patterns by hand.** They are mostly forgotten.
