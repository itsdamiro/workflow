---
type: decision
status: accepted
date: 2026-10-08
projects: [workflow]
concepts: [Portability]
amends: [002]
supersedes: []
tags: [type/decision, status/accepted, project/workflow, topic/portability]
---

# 008 — The project template and its scripts live in this repository

> **Summary.** The template, the git-safety hook, the two skills and the install and adopt scripts are in `template/`. This repo's own standards and scripts are symlinks to it, so there is one copy. Moving the live hook over, and removing the old copy, are not decided yet.

## Context

The template began in the owner's private workstation-setup repository, which is the wrong home: it is for setting up one machine, and a public README cannot point readers at a private repository. The hook and the skills run live from there (`~/.claude` symlinks into it), so they cannot simply be deleted.

## Decision

- `template/` holds the template documents, `scripts/gates` and `scripts/mutate.py`, `hooks/git_safety.py` with its tests, `skills/`, `adopt.sh`, `install.sh`, and the contents-page templates. It is the source of truth.
- This repo adopts its own template: `docs/COLLABORATION_STANDARDS.md`, `docs/CODE_QUALITY_STANDARDS.md`, `docs/CLOSING_A_SLICE.md`, `scripts/gates` and `scripts/mutate.py` are relative symlinks into `template/`, so a change is made once and the paths the standards mention still resolve.
- Two gates cover the copied code: the hook's unit tests and a shell syntax check.
- The code was reviewed rather than copied unread. Three bugs were fixed (see GOTCHAS): `gates` skipped a last line with no newline and printed a warning on a comment containing a quote; `adopt.sh` left a placeholder and a `.bak` file when the project name contained `/` or `&`. Every rule in the hook is a standing rule, so none was dropped. Gaps in the hook are listed in GOTCHAS and left as they are until the owner decides.

## Consequences

`install.sh` links from this checkout, so the live hook and skills keep pointing at the old location until it is run from here (then re-run it if the repository moves). Projects already on the template keep their snapshots; `adopt.sh --check` reports drift.

## Not yet decided

Running `install.sh` from here, removing the old copy, and hardening the hook.

## Alternatives rejected

- **Copy everything unchanged.** Two copies to maintain, and unreviewed code in a public repository.
- **Describe the steps only in prose.** The scripts are what make a new project one command.
- **Recreate the scripts from scratch.** The existing ones are tested and in daily use; rewriting them adds risk for no gain.

## Amendment (2026-10-08): what else the template carries

- ADR 012 adds the record template, the vault conventions page, two procedures and a shape-check gate (`adr_check.py`) to the template, and makes this repository's own copies symlinks to them.
