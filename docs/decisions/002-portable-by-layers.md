---
type: decision
status: accepted
date: 2026-10-08
projects: [workflow]
concepts: [Portability]
amends: []
supersedes: []
tags: [type/decision, status/accepted, project/workflow, topic/portability]
---

# 002 — Portable by layers: files and scripts, procedures, optional adapters

> **Summary.** Logic lives in plain files and scripts; procedures are markdown any assistant can follow; per-tool adapters are thin and optional. The system must work with zero adapters.

## Context

The owner uses more than one assistant and expects the set to change. A workflow built on one tool's skills, hooks or subagents would be lost with that tool.

## Decision

1. **Files and scripts** hold the logic: markdown with YAML frontmatter; POSIX shell or Python standard library.
2. **Procedures** are `docs/sop/*.md`, written with capabilities ("read the diff", "run this script", "ask a fresh reader"), never one tool's verbs.
3. **Adapters** (a Claude skill and mod, a Gemini command, others) are a few lines saying "follow the SOP". They may add convenience, not behaviour.
4. The same contents page is generated under each tool's file name (`CLAUDE.md`, `GEMINI.md`, `AGENTS.md`), all listed in the no-trace ignore block.
5. Rules that must hold whatever the tool belong in tool-neutral places where possible: a git `commit-msg` hook can enforce "no trailer" for any tool. Commands git never sees (`reset --hard`) stay in a tool hook.

## Consequences

Some conveniences are lost on tools without adapters: the automatic reminder, the fresh-subagent check (replaced by a new session or another model). Quality of drafted notes varies by model; the owner's acceptance gate covers that.

## Alternatives rejected

- **Build on one tool's native features** (skills, subagents, mods). Quicker to start; locks the workflow to the tool.
- **A custom orchestration program.** Portable but a new thing to maintain; scripts plus procedures get the same result.
