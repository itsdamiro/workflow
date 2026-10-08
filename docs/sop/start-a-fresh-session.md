# SOP: start a fresh session from a handoff

For any assistant. A long session re-reads its whole conversation on every message, so the cheap way to continue is to
start fresh from the written handoff (ADR 001). This procedure covers when to do it and how to begin.

## When to restart

- A slice is closed (`docs/sop/handoff.md` is done and the handoff has passed its check).
- Or the session has grown long: soft limit about 150k tokens of context, hard limit about 200k (the defaults of the
  session guard). Finish the step you are on, then close the slice; do not restart halfway through an edit.
- Not while work is uncommitted and undescribed: write the state to a file first, or the next session cannot know it.

## Before you leave the old session

1. The slice's work is committed (only on the owner's go-ahead) or its state is written in `docs/HANDOFF.md`.
2. `docs/HANDOFF.md` has passed `docs/sop/check-a-handoff.md`.
3. Anything learned that the next session needs is in `docs/reference/GOTCHAS.md` or a decision record, not only in the
   conversation.

## Starting

1. Open a new session in the project folder.
2. Read the project's contents page, then `docs/HANDOFF.md`. Read nothing else until the task needs it.
3. Say back, in a few lines: the next action, what it is done when, what you must not do, and what waits on the owner.
   If any of those cannot be answered from the handoff, that is a defect in the handoff: tell the owner, and fix it
   after the task.
4. Run `scripts/gates` and `git status -sb` to see the real state before trusting the handoff's account of it.
5. Begin the next action. Do not re-derive decisions that a record already settles.

## Do not

- Paste the old conversation in. If something was worth carrying, it belongs in a file.
- Treat the handoff as proof: check a claim against the repository when the task depends on it.
