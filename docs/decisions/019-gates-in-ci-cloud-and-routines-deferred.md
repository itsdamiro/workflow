---
type: decision
status: accepted
date: 2026-10-18
projects: [workflow]
concepts: [Portability]
amends: []
supersedes: []
tags: [type/decision, status/accepted, project/workflow, topic/architecture]
---

# 019 — Gates run in CI for every project; cloud sessions and routines wait for a job that needs them

> **Summary.** The template gains a GitHub Actions workflow that runs `scripts/gates` on every push and pull request, with no assistant involved. Cloud sessions and routines are not built into the workflow yet: they would run without the contents page, the handoff and the hooks, and no job needs them.

## Context

- Checked on 2026-10-18 against Claude Code's own documentation (code.claude.com, cloud environments, routines, hooks). A cloud session or routine starts from a clone of the repository. It loads a committed `CLAUDE.md` and committed `.claude/` files. It does not load `~/.claude` (user settings, hooks, skills), and `.git/hooks` is not mentioned. Routines are a research preview; one trigger kind is capped at 30 runs an hour.
- The template makes `CLAUDE.md`, `.claude/` and `docs/HANDOFF.md` local-only (`docs/COLLABORATION_STANDARDS.md`, the no-trace block), so a cloud clone would have no contents page, no handoff, no git-safety hook and none of the three skills. Making them reach the cloud means committing assistant tooling, which the no-trace rule forbids, or keeping a setup script in the cloud environment's own settings.
- The one routine that was worth considering is "run the gates on a pull request". The gates are deterministic scripts (`scripts/gates`, ADR 002), so they need no model.
- Neither this repository nor the template had any CI before this record.
- The owner, 2026-10-18, after the recommendation: "ok lets do all that" (a CI gates workflow in the template, and no cloud or routine work for now).

## Decision

1. `template/ci/gates.yml` is a GitHub Actions workflow: check out, run `scripts/gates`. `adopt.sh` installs it as `.github/workflows/gates.yml` and never overwrites one that exists. This repository adopts it too.
2. A project whose gates need a toolchain beyond a stock Ubuntu runner adds a setup step to its own copy; the workflow says so in a comment.
3. No cloud session, routine, `/advisor`-style adapter or unattended-run rule is added now. The go-ahead rule (commit and push only when the owner says) stays as it is, with nothing written for an unattended run.

## Consequences

- Easier: a failing gate shows on every push without anyone running it, for any assistant or none, and costs no tokens.
- Harder: each project's gates must run on a clean Linux checkout; one that needs a local path or a machine-only tool fails in CI until it is fixed or marked.
- Open: the workflow was written and not yet run on GitHub; the first push will show whether this repository's gates pass there. A later record decides what an unattended run may commit.

## Alternatives rejected

- **A cloud routine that runs the gates on a pull request.** It does the same job through a preview feature, with a model in the loop, and without the rules and handoff. It becomes right if a job needs a model and nobody at the keyboard: a review of every pull request, or a recurring chore. That record also has to say what an unattended run may commit.
- **Committing `CLAUDE.md` and `.claude/` so the cloud sees them.** It breaks the no-trace rule (`docs/COLLABORATION_STANDARDS.md`). It becomes right only if the owner changes that rule.
- **A cloud setup script that writes the rules into the machine.** Possible, and it keeps the repository clean, but it lives outside the repository and nobody reviews it. Right if cloud runs become routine.
