---
name: handoff
disable-model-invocation: true
description: Closes a slice for the next session — runs the gates, commits the slice's work, runs the vault sync, stats row and lint as one script, scans the diff for patterns, rewrites docs/HANDOFF.md, pushes and reports. `/handoff full` adds the two reviews of the diff (correctness and over-engineering) before the commit and a fresh-reader test of the handoff. Run by the user typing /handoff.
---

# Handoff

The procedure is `docs/sop/handoff.md` in the workflow repository, not here: read it and follow it step by step, saying so for any step it marks *planned*.

There are two closes. Plain `/handoff` is the light close and never runs the checks. `/handoff full` (or `/handoff check`) adds the `/code-review` and the over-engineering review of the diff before the commit, and the fresh-reader test of the handoff. In `full`, if a check cannot run, say which and why in the report; the close is then not complete. Do not choose the mode yourself: follow the argument the owner typed.

To find the repository, resolve the symlink this skill folder is reached through (it points into `template/skills/handoff` of the workflow repository); the repository root is two levels up from there. The close script (`scripts/close_slice.py`, which runs the sync, the stats line and the lint) is in its `scripts/`, and the project to hand off is the current working directory.

You need the vault path: take it from the user's message, else from the terms at the top of the project's `docs/HANDOFF.md`, else ask. Do not guess one.

If the procedure cannot be found, say so and stop; do not improvise a different one.

Running this skill is the owner's go-ahead to commit the slice's named files and push (ADR 005 amendment); outside it, commit and push only when the owner says so.
