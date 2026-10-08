---
type: decision
status: accepted
date: 2026-10-08
projects: [workflow]
concepts: [Handoff]
amends: []
supersedes: []
tags: [type/decision, status/accepted, project/workflow, topic/vault, topic/patterns]
---

# 005 — One `/handoff` procedure closes a slice

> **Summary.** A single procedure runs the vault sync, the lints, the pattern scan and the handoff draft, checks the handoff with a fresh reader, and reports what awaits the owner's acceptance.

## Context

Closing a slice already ends with a handoff (step 9 of `docs/CLOSING_A_SLICE.md`). Cheap restarts (ADR 001) need that step to be quick and complete, and the vault needs updating at the same moment.

## Decision

`docs/sop/handoff.md` defines the steps; scripts do the deterministic ones; a model drafts the rest; the owner accepts. It runs when the slice's work is done and commits it first, because the sync reads committed state; running it is the owner's go-ahead to commit and push (see the amendment of 2026-10-08). Outside it, commit and push stay the owner's call. Writing the ADR is not part of it: that happens before the code.

## Consequences

One command from the owner's side. The work inside a long session costs tokens, which is why the guard reminds early. Without an adapter the owner says "follow `docs/sop/handoff.md`".

## Alternatives rejected

- **A hook that runs it automatically.** It would act before the owner has reviewed the slice, and the draft needs acceptance.
- **Separate commands for each part.** More to remember; the parts belong to one moment.

## Amendment (2026-10-08): the fresh-reader check on request

- **Why:** the first full run took about eight minutes, most of it, as far as I can tell, the fresh-reader check (a subagent per round, often two or three rounds). Run at every 150k to 200k of context, that is too much development time. The vault sync and lint take about half a second; the pattern scan reads only the slice's diff.
- **Decided by the owner:** `/handoff` keeps the ground check, the vault sync and lint, the pattern scan, the handoff draft and the report. The fresh-reader check runs only when named: `/handoff check`. Use it after a rewrite that changed the shape of the handoff, or before another assistant takes over.
- ADR 006 is unchanged: the pattern scan still runs at every handoff.

## Amendment (2026-10-08): `/handoff` commits and pushes the slice

- **Why:** the procedure stopped at step 1 on uncommitted work and told the owner to commit first. The session guard's button fires on a token count, not at a clean tree, so it usually found work in progress and stopped, which defeats a one-click close. The owner asked that the handoff commit and push instead of stopping.
- **Decided by the owner:** typing `/handoff` (or pressing the guard's close button) is the owner's go-ahead for this one procedure to commit the slice's work and push it. This replaces "Commit and push stay the owner's call" in the Decision above, for `/handoff` only. Everywhere else the rule stands: outside this procedure, commit and push only on the owner's word.
- **The order:** the ground check runs the gates first. If they pass, the slice's work is committed, because the sync reads committed state; then the sync, the lint, the pattern scan and the handoff draft run as before; the push comes last, after the lint has no error. If the gates fail or the lint has an error, nothing is committed or pushed and the assistant asks the owner how to proceed.
- **The limits, none of which `/handoff` relaxes:** it stages named files only, never `git add .`, `-A` or `-u`, and only files that belong to the slice. If it cannot tell which changed files belong to the slice, it commits none of the doubtful ones and asks. It reads the diff before committing, as the standards require, and on a public repository stops on anything private. The commit carries no attribution trailer and one author identity. It never force-pushes. `docs/HANDOFF.md` is local-only and is not committed.
- **Not changed:** the git-safety hook still asks before a `git push`, so the owner confirms the push in the prompt unless they have allowed it. That pause is kept on purpose: the amendment removes the instruction to stop, not the hook's check.
- **Follows:** `docs/sop/handoff.md` (step 1, the "Do not" list and the opening line) is amended to match, on the owner's word.
