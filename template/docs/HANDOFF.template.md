# Handoff

> Copy to `docs/HANDOFF.md`. Rewrite it at the close of every slice, under 60 lines. It holds only what is **volatile**: where the work stands, what is next, what waits on the owner. Durable things do not live here: a decision is an ADR, a recipe or a trap is in `docs/reference/`, a number (test count, commit hash) is whatever `git log -1` and `scripts/gates` say today. Prose that copies those goes stale. Name things one way throughout (one term per concept).

## Now

- **Working on:** [one line: the slice or task, and its decision record]
- **Done when:** [the acceptance check, one line]
- **Left off at:** [the exact next action, e.g. "slice 3, step: write the merge test"]

## Next, in order

1. [the next slice, with its decision record]
2. [then]
3. [then]

## Waiting on the owner

- [a decision only the owner can make, with the options and your recommendation]
- None. *(Write "None." when there is nothing: an empty section reads as forgotten.)*

## New since the last handoff

- [a trap or a fact learned this session that the next one needs. At the close, move each to `docs/reference/GOTCHAS.md` or an ADR and delete it here.]

## How to pick this up cold

```
scripts/gates            # every gate, one line each; a failure shows its last lines
git log --oneline -5     # what just landed
git status -sb           # whether anything is uncommitted or unpushed
```

## Contents of the rest (read when the task needs it, one level down)

- Working rules: `CLAUDE.md`, `docs/COLLABORATION_STANDARDS.md`, `docs/CODE_QUALITY_STANDARDS.md`
- How a slice is closed: `docs/CLOSING_A_SLICE.md`
- Traps and recipes: `docs/reference/GOTCHAS.md`
- Decisions: `docs/decisions/`
- Why the project exists: `docs/VISION.md` *(if the project has one)*

## Check this file

A fresh session reads only this file and the pointers above, then answers: what is next, how do I run the gates, what must I not do, what is waiting on the owner. Every wrong or hesitant answer is a line to fix here (see the `checking-a-handoff` skill).
