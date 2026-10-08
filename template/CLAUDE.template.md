# [PROJECT NAME] — Guidelines for Claude

[One or two sentences: what this project is and who it is for.]

This file is a contents page: short on purpose. The substance is one level down, in the files it links to.

## Start here

1. Read `docs/HANDOFF.md`: where the work stands and what is next.
2. Read `docs/COLLABORATION_STANDARDS.md` and `docs/CODE_QUALITY_STANDARDS.md`. They are binding, not background: candid over flattering, state written through to files, evidence before "done", no simulated delays, ask rather than guess.
3. Closing a slice of work follows `docs/CLOSING_A_SLICE.md`.

## Primary commands

- All gates, one line each: `scripts/gates` (the list is `scripts/gates.conf`)
- Tests: `___`   Lint: `___`   Typecheck: `___`   Build: `___`   Run locally: `___`

## Never-break rules (enforced by hooks where a hook can, otherwise by you)

- No `git checkout -- <file>`, `git restore`, `git reset --hard`, `git clean -f`: undo by copying a saved backup back.
- Stage named files only; never `git add .` or a directory that holds generated output.
- Commits carry no attribution trailer and one author identity. Commit and push only on the owner's go-ahead.
- Markdown prose is one paragraph or list item per line, never hard-wrapped (`scripts/md_wrap_check.py` is a gate).
- [Add this project's own: data it must never touch, a name that must never be hard-coded, ...]

## Project-specific rules

[Architecture constraints, safety boundaries, naming, performance limits: anything that is true of this project only.]

## Contents of the rest

- Traps and recipes: `docs/reference/GOTCHAS.md`
- Decisions: `docs/decisions/`
- Why: `docs/VISION.md` *(if there is one)*
