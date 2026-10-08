# SOP: close a slice with `/handoff`

For any assistant. Run it after the slice's commits have landed and the gates pass. You need: the project's repo, the vault path, and the owner. Scripts marked *planned* are not built yet: do that step by hand and say so.

## Steps

1. **Check the ground.** The slice's work is committed (`git status -sb` is clean apart from local-only files) and `scripts/gates` passes. If not, stop and tell the owner; this is `docs/CLOSING_A_SLICE.md` steps 1 to 8.
2. **Sync the vault.** Run `python3 scripts/vault_sync.py <project-path> <vault-path> --dry-run`, read what it would do, then run it without `--dry-run`. It reads the project's committed decision records and writes only notes marked `generated: true`. Record what it created, changed and refused; a refusal is a name clash or a hand-written note in the way, and is for the owner to settle, never to force.
3. **Run the lints.** `scripts/vault-lint <vault>` (*planned*): required fields, links that resolve, orphans, tags, concepts. List every failure. Do not fix a note the script did not generate without asking.
4. **Scan the slice's diff for patterns.** Read the diff from the last handoff to now (`git diff <ref>..HEAD`), not the whole codebase. For each reusable pattern, draft a note in `Patterns/` with `status: draft`, citing the file and lines it comes from and any ADR. "No new pattern" is a valid result; do not invent one.
5. **Draft the handoff.** Rewrite `docs/HANDOFF.md` (under 60 lines, volatile facts only). Move anything durable to `docs/reference/` or an ADR. Facts come from `git log`, `git status` and the gates, not from memory.
6. **Check the handoff with a fresh reader.** Follow `docs/sop/check-a-handoff.md`: a new session, or another model with no access to this conversation, reads only the handoff and its pointers and answers the six questions. Every wrong or hesitant answer is a line to fix; fix it and ask again.
7. **Write the stats line.** Append to the project's stats note: date, slice name, context size at close. (*planned*)
8. **Report to the owner**, in this order: what was synced; what failed lint; what is waiting for acceptance (the handoff draft, pattern drafts, concept tags on any new ADR); whether it is safe to start a fresh session.

## Do not

- Commit or push. Only on the owner's word.
- Edit a note without `generated: true` except to add drafts the owner will review.
- Write anything from this procedure into the project's repository except `docs/HANDOFF.md` and `docs/reference/`.

## Adapters

The Claude skill, mod button or Gemini command each say: "follow `docs/sop/handoff.md`". Nothing more.
