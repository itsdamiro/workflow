# SOP: close a slice with `/handoff`

For any assistant. Run it when the slice's work is done; it commits that work and pushes it (ADR 005, amendment of 2026-10-08), so running it is the owner's go-ahead for those two things and no others. It is quick by default: the vault sync and lint are a script run, and the pattern scan reads only the slice's diff. The one slow part, the fresh-reader check, runs only when the owner names it. You need the project's repo, the vault path and the owner.

## Steps

1. **Check the ground, then commit.** `scripts/gates` passes; if it fails, stop and ask the owner how to proceed, and commit nothing. Then commit the slice's work, because the sync reads committed state: read the diff first (on a public repository, stop on anything private), stage named files only that belong to the slice, and write a message that says why. If you cannot tell whether a changed file belongs to the slice, leave it out and ask. A clean tree (`git status -sb`, apart from local-only files) needs no commit. The rest of `docs/CLOSING_A_SLICE.md` steps 1 to 8 is still the slice's own checklist.
2. **Sync the vault.** Run `python3 scripts/vault_sync.py <project-path> <vault-path> --dry-run`, read what it would do, then run it without `--dry-run`. It reads the project's committed decision records and writes only notes marked `generated: true`. Record what it created, changed and refused; a refusal is a name clash or a hand-written note in the way, and is for the owner to settle, never to force.
3. **Run the lint.** `python3 scripts/vault_lint.py <vault-path>` (ADR 010). It exits 1 on an error (bad frontmatter, a missing field, an unknown type or status, a broken link, a bad tag, a duplicate name, a concept with no note) and 0 with only warnings (no links, an orphan, no tags, an unlisted topic). List every error, and give the warning counts. Do not fix a note the script did not generate without asking.
4. **Scan the slice's diff for patterns.** Read the diff from the last handoff to now (`git diff <ref>..HEAD`), not the whole codebase. For each reusable pattern, draft a note in `Patterns/` with `status: draft`, citing the file and lines it comes from and any ADR. "No new pattern" is a valid result; do not invent one.
5. **Draft the handoff.** Rewrite `docs/HANDOFF.md` (under 60 lines, volatile facts only). Move anything durable to `docs/reference/` or an ADR. Facts come from `git log`, `git status` and the gates, not from memory.
6. **Write the stats line.** Run `python3 scripts/stats_line.py <project-path> <vault-path> --context-tokens <N>`, with `N` the session's context size if your adapter can tell you, and without the option if it cannot (the row then shows a dash). Under Claude Code, `N` is the output of `python3 adapters/claude/context-report/last_context.py`, run from the workflow checkout; if it exits 1, leave the option out (ADR 015). It adds one row to `<name> - Stats.md` (the day, the commit, the commits since the last row, their first and last subject, the context size) and never rewrites an earlier row; run twice on the same commit it adds nothing (ADR 014). A refusal is for the owner to settle.
7. **Push.** Only if the lint had no error: push the current branch to its upstream, never forced. The git-safety hook may ask the owner to confirm; that is expected. If the lint had an error, do not push and say so in the report.
8. **Report to the owner**, in this order: what was committed and whether it was pushed; what was synced; the stats row; what failed lint; what is waiting for acceptance (the handoff draft, pattern drafts, concept tags on any new ADR); whether it is safe to start a fresh session; and that the fresh-reader check was not run, unless it was.

## Option: `check`, only when named

`/handoff check` adds two independent checks (ADR 005, amendment of 2026-10-08):

- **Before step 1, the two reviews of `docs/CLOSING_A_SLICE.md` step 5, together** over the slice's diff (the uncommitted changes, or else `git diff <ref>..HEAD` from the last handoff). Correctness: run `/code-review`, saying the level first: `high`, unless the owner named another. Over-engineering: a reader who did not write the code (a read-only subagent, or `/simplify`) is asked whether every new thing earns its place, using step 5b's list. Fix the findings of both in one round. Fix each real finding (tests first, gates after; a simplification must not change behaviour a test pins) or decline it with one line saying why; step 1 commits only after that.
- **Between 5 and 6, before the stats line, the fresh-reader check:** follow `docs/sop/check-a-handoff.md`.

The fresh-reader check works like this: a new session, or another model with no access to this conversation, reads only the handoff and its pointers and answers the six questions. Every wrong or hesitant answer is a line to fix; fix it and ask again. Both are slow and cost tokens (a subagent per round for the second, often two or three rounds): use `check` after a rewrite that changed the shape of the handoff, for a slice that touches data, links, permissions or a real user's files, or before handing the project to a different assistant, not after every slice.

## Do not

- Commit or push anything but the slice's work: no `git add .`, `-A` or `-u`, no force-push, no attribution trailer, and no commit or push of `docs/HANDOFF.md`, which is local-only. Outside this procedure, commit and push only on the owner's word.
- Run `check`, or either of its two parts, unless the owner named it.
- Edit a note without `generated: true` except to add drafts the owner will review.
- Write anything from this procedure into the project's repository except `docs/HANDOFF.md` and `docs/reference/`.

## Adapters

The Claude skill (`template/skills/handoff`, linked by `template/install.sh`), mod button or Gemini command each say: "follow `docs/sop/handoff.md`", passing along `check` if the owner typed it. Nothing more.
