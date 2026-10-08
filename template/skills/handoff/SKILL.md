---
name: handoff
description: Closes a slice for the next session — runs the gates, commits the slice's work, syncs the vault and runs the lint, scans the diff for patterns, rewrites docs/HANDOFF.md, adds a stats row, pushes and reports. The option check adds the slow independent checks: the two reviews of the diff (correctness and over-engineering) before the commit, and a fresh-reader test of the handoff. Use when the user types /handoff, asks to hand off, or says the session is getting long and the slice is done.
---

# Handoff

The procedure is `docs/sop/handoff.md` in the workflow repository, not here: read it and follow it step by step, saying so for any step it marks *planned*.

Run the check steps (the `/code-review` and the over-engineering review of the diff, and the fresh-reader test) only if the user typed `/handoff check`; never add either yourself, and say in the report that they were not run.

To find the repository, resolve the symlink this skill folder is reached through (it points into `template/skills/handoff` of the workflow repository); the repository root is two levels up from there. The sync and the lint (`scripts/vault_sync.py`, `scripts/vault_lint.py`) are in its `scripts/`, and the project to hand off is the current working directory.

You need the vault path: take it from the user's message, else from the terms at the top of the project's `docs/HANDOFF.md`, else ask. Do not guess one.

If the procedure cannot be found, say so and stop; do not improvise a different one.

Running this skill is the owner's go-ahead to commit the slice's named files and push (ADR 005 amendment); outside it, commit and push only when the owner says so.
