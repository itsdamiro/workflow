---
type: decision
status: accepted
date: 2026-10-08
projects: [workflow]
concepts: [source-of-truth]
amends: []
supersedes: []
tags: [type/decision, status/accepted, project/workflow, topic/vault]
---

# 003 — The repo is the source of truth; the vault is personal output

> **Summary.** Decisions and docs stay in each project's repo. `/handoff` writes summaries and ideas only into the
> owner's vault, never back into a repo. The vault is for personal ideas and mind-mapping.

## Context

Having both the repo and the vault editable means two copies that drift. The owner wants the vault for personal thinking,
not as a second home for project documents. A symlink from a repo into the vault cannot be committed (it points at a
path on one machine), and Sympose refuses paths that resolve outside the vault.

## Decision

- ADRs, vision, standards and gotchas are written and committed in the project, as now.
- `vault-sync` reads the committed state of the project's default branch and writes generated notes into
  `Projects/<name>/` in the vault. It overwrites only notes marked `generated: true`.
- Ideas, concepts and patterns are written in the vault by the owner, or drafted by an assistant and accepted.
- Nothing in the vault is copied into a repo. The central vault is `garden`, started empty on 2026-10-08.

## Consequences

No drift gate and no committed copies are needed. The vault can be rebuilt from the repos plus the owner's own notes.
Generated notes are overwritten on every sync, so the vault keeps local git history.

## Alternatives rejected

- **Author docs in the vault and export to the repo.** Needs a drift check and committed generated copies; rejected once
  the vault was scoped to personal output.
- **One vault per project.** Sympose searches one active vault at a time, so cross-project links would not resolve.
