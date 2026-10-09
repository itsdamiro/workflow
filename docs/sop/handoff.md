# SOP: close a slice with `/handoff`

For any assistant. Run it when the slice's work is done; it commits that work and pushes it (ADR 005, amendment of 2026-10-08), so running it is the owner's go-ahead for those two things and no others. The two reviews of the diff and the fresh-reader check of the handoff are part of every run (ADR 005, amendment of 2026-10-09). The vault sync and lint are a script run, and the pattern scan reads only the slice's diff. You need the project's repo, the vault path and the owner.

## Steps

1. **Check the ground, review, then commit.** `scripts/gates` passes; if it fails, stop and ask the owner how to proceed, and commit nothing. Then run the two reviews of the slice's diff ("The checks" below) and fix their findings; the gates pass again. Then commit the slice's work, because the sync reads committed state: read the diff first (on a public repository, stop on anything private), stage named files only that belong to the slice, and write a message that says why. If you cannot tell whether a changed file belongs to the slice, leave it out and ask. A clean tree (`git status -sb`, apart from local-only files) needs no commit. The rest of `docs/CLOSING_A_SLICE.md` steps 1 to 8 is still the slice's own checklist.
2. **Sync the vault.** Run `python3 scripts/vault_sync.py <project-path> <vault-path> --dry-run`, read what it would do, then run it without `--dry-run`. It reads the project's committed decision records and writes only notes marked `generated: true`. Record what it created, changed and refused; a refusal is a name clash or a hand-written note in the way, and is for the owner to settle, never to force.
3. **Run the lint.** `python3 scripts/vault_lint.py <vault-path>` (ADR 010). It exits 1 on an error (bad frontmatter, a missing field, an unknown type or status, a broken link, a bad tag, a duplicate name, a concept with no note) and 0 with only warnings (no links, an orphan, no tags, an unlisted topic). List every error, and give the warning counts. Do not fix a note the script did not generate without asking.
4. **Scan the slice's diff for patterns.** Read the diff from the last handoff to now (`git diff <ref>..HEAD`), not the whole codebase. For each reusable pattern, draft a note in `Patterns/` with `status: draft`, citing the file and lines it comes from and any ADR. "No new pattern" is a valid result; do not invent one.
5. **Draft the handoff, then check it.** Rewrite `docs/HANDOFF.md` (under 60 lines, volatile facts only). Move anything durable to `docs/reference/` or an ADR. Facts come from `git log`, `git status` and the gates, not from memory. Then run the fresh-reader check on it ("The checks" below) until every answer is right.
6. **Write the stats line.** Run `python3 scripts/stats_line.py <project-path> <vault-path> --context-tokens <N>`, with `N` the session's context size if your adapter can tell you, and without the option if it cannot (the row then shows a dash). Under Claude Code, `N` is the output of `python3 adapters/claude/context-report/last_context.py`, run from the workflow checkout; if it exits 1, leave the option out (ADR 015). It adds one row to `<name> - Stats.md` (the day, the commit, the commits since the last row, their first and last subject, the context size) and never rewrites an earlier row; run twice on the same commit it adds nothing (ADR 014). A refusal is for the owner to settle.
7. **Push.** Only if the lint had no error: push the current branch to its upstream, never forced. The git-safety hook may ask the owner to confirm; that is expected. If the lint had an error, do not push and say so in the report.
8. **Report to the owner**, in this order: what was committed and whether it was pushed; what was synced; the stats row; what failed lint; what the two reviews and the fresh-reader check found and what was done about each (and, if one could not run, which and why: the close is then not complete); what is waiting for acceptance (the handoff draft, pattern drafts, concept tags on any new ADR); and whether it is safe to start a fresh session.

## The checks (every close)

Two independent checks are part of every run (ADR 005, amendments of 2026-10-08 and 2026-10-09). `/handoff check` is still accepted and means the same close.

- **Before step 1's commit, the two reviews of `docs/CLOSING_A_SLICE.md` step 5, together** over the slice's diff (the uncommitted changes, or else `git diff <ref>..HEAD` from the last handoff). Correctness: run `/code-review`, saying the level first: `high`, unless the owner named another. Over-engineering: a reader who did not write the code (a read-only subagent, or `/simplify`) is asked whether every new thing earns its place, using step 5b's list. Fix the findings of both in one round: each real finding (tests first, gates after; a simplification must not change behaviour a test pins) or decline it with one line saying why. Step 1 commits only after that.
- **Between 5 and 6, before the stats line, the fresh-reader check:** follow `docs/sop/check-a-handoff.md`. A new session, or another model with no access to this conversation, reads only the handoff and its pointers and answers the six questions. Every wrong or hesitant answer is a line to fix; fix it and ask again.
- **A check is never skipped, and never run without saying so.** If one cannot run (no reviewer or subagent is available, the session was interrupted), the report names which and why, and the close is not complete. They cost minutes and a subagent per round; that is the price of reviewing every slice.

## Under Gemini CLI

The command is `/handoff` (`/handoff check` is accepted and means the same; `template/commands/handoff.toml`, written to `~/.gemini/commands/` by `template/install.sh`; ADR 005 and the SPEC §7 table are the design). It is untested in Gemini as of its commit. Without the command, the owner says "follow `docs/sop/handoff.md`" and the same steps apply. What differs from Claude Code:

- **Loading this file.** The command loads it with a shell `cat`, so Gemini asks the owner to confirm that first. It does not use `@{}`, because Gemini allows an absolute `@{}` path only inside the workspace and the workflow repository is usually outside the project's. If a context file is missing, say so and stop rather than improvise.
- **Confirmations.** Gemini asks before each shell command, and the git-safety hook is Claude-only. The rules in "Do not" bind you all the same: stage named files, no trailer, no force-push, and commit and push only inside this procedure. The `scripts/` of the workflow repository are run by their full path.
- **The vault path** comes from the owner's message, else from the terms at the top of the project's `docs/HANDOFF.md`, else ask.
- **The context size (step 6).** There is no Gemini adapter for it, so leave `--context-tokens` out and the row shows a dash (ADR 015 covers the Claude one only).
- **There is no `/code-review` or `/simplify`.** Do the two reviews of the slice's diff yourself, as a reader looking for faults rather than as its author: for correctness, wrong logic, unhandled cases, a caller or test the change breaks, and a path read from git without checking what it is; for over-engineering, `docs/CLOSING_A_SLICE.md` step 5b's list. Give each finding as `file:line`, then fix it (tests first, gates after) or decline it with one line. Say in the report that the review was the same model that wrote the code, so it is weaker than an independent one; a second session with no access to this conversation, or the owner's own read, is stronger.
- **The fresh-reader check** needs a reader with no access to this conversation: a new Gemini session pointed only at `docs/HANDOFF.md`, or another assistant. If neither is available, see "The checks" above.

## Do not

- Commit or push anything but the slice's work: no `git add .`, `-A` or `-u`, no force-push, no attribution trailer, and no commit or push of `docs/HANDOFF.md`, which is local-only. Outside this procedure, commit and push only on the owner's word.
- Skip a check, or run one without saying so ("The checks" above).
- Edit a note without `generated: true` except to add drafts the owner will review.
- Write anything from this procedure into the project's repository except `docs/HANDOFF.md` and `docs/reference/`.

## Adapters

The Claude skill (`template/skills/handoff`, linked by `template/install.sh`), mod button or Gemini command (`template/commands/handoff.toml`, written by `template/install.sh` with this checkout's path filled in) each say: "follow `docs/sop/handoff.md`". Nothing more.
