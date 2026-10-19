---
type: decision
status: accepted
date: 2026-10-19
projects: [workflow]
concepts: [Handoff, Vault upkeep]
amends: [005]
supersedes: []
tags: [type/decision, status/accepted, project/workflow, topic/vault, topic/consent, topic/privacy]
---

# 020 — The close commits the vault's generated notes by path, and pushes the vault beside the project

> **Summary.** After a clean lint, `/handoff` commits in the vault's own repository every changed note marked `generated: true`, by named path and nothing else, and the assistant pushes it next to the project's push, only when the vault had no unpushed commit of its own. Script output gets a history and a backup without asking for the owner's attention; the owner's notes, the drafts and anything outside Markdown stay theirs to commit. It costs one more step in the close script, a second push the hook asks about, and a vault working tree that is still never clean on its own.

## Context

- ADR 005 (amendment of 2026-10-09, "two closes") leaves committing the vault's repository undecided, and its next amendment ("Limit") says the vault's `git status` accumulates across closes, so it cannot show what the owner changed by hand. The vault is a git repository with a private remote (`docs/HANDOFF.md`, Terms).
- Who writes what into the vault, from the scripts' own docstrings and records: the sync writes cards, the rejected-ideas note and the gotchas copy, all `generated: true`, and the hub once, when missing, without that mark (ADR 009); the stats line appends to a `generated: true` note (ADR 014); the writer writes captures, new notes, appended lines and closed-list values on the owner's side, never `generated: true`, refusing that mark (ADR 017); the pattern scan writes model drafts with `status: draft` (ADR 006); the board app writes images and lookup files under `Board/` and appends to Moodboard notes (ADR 018). The owner edits by hand in Obsidian and Sympose.
- The vault, read on 2026-10-19 (counts only, no names): the last commit is of 2026-10-16 and is not pushed (the branch is one ahead of its remote). 33 tracked files are modified: 25 generated notes, 7 other notes and `.gitignore`. 161 paths are untracked: 37 generated notes, 35 other notes (drafts and hand-written notes), 78 files under Obsidian's `.trash/`, and 11 files under `Board/`.
- In that working tree `.gitignore` has lost its `Board/` line (an uncommitted change; no script writes `.gitignore`), so `Board/`'s images and lookup files now show as untracked. `.trash/` is not ignored. A commit of everything would push both to the remote, against ADR 018 decision 3.
- Earlier closes were committed into the vault by hand (subjects starting "Sync …", up to 2026-10-09), so the gap is real, not theoretical: since then nothing a close wrote has a history or a copy off the machine.
- Binding rules: this repository is public and vault note names are private, so the close's vault list stays in chat (ADR 005, amendment of 2026-10-09); a model drafts and the owner accepts, and nothing reaches the owner's side without their yes (ADR 017); stage named files only, no force-push, one author identity and no trailer (`CLAUDE.md`); the git-safety hook's pause before a push is kept on purpose (ADR 005, amendment of 2026-10-08); a close step is judged by whether it asks for the owner's attention (ADR 005, amendment of 2026-10-09).

## Decision

1. **What is committed: every changed note a script owns, and nothing else.** A path qualifies when it is a `.md` file outside any hidden folder, its working-tree frontmatter says `generated: true`, and `git status` shows it modified or untracked. Deletions never qualify (no script deletes; a deletion is the owner's act), nor does anything outside Markdown, so `Board/` and `.trash/` are never touched whatever `.gitignore` says. Generated notes hold only text copied from committed records, GOTCHAS and git (ADRs 009 and 014): no model claim and no owner text, which is why they can be committed without review. This includes generated notes left over from earlier closes; the first run sweeps that backlog (25 modified and 37 untracked on 2026-10-19).
2. **Who runs it and when.** `scripts/close_slice.py` gains a fourth step after the lint, run only when the lint had no error and not on `--dry-run`: it stages the qualifying paths by name and commits only them (`git commit --only`, so anything the owner had staged stays staged and out of the commit). The message is mechanical, `Close <project> at <short commit>: <n> generated note(s)`, with the vault's own git identity and no trailer. It prints one line, `vault git: committed <n> note(s) as <sha>` or `vault git: nothing to commit` or the reason it did not (not a git repository, a merge or rebase in progress, an index lock held by another close). None of these stops the close or changes its exit code.
3. **The push is the assistant's, in step 5, beside the project's.** `git -C <vault> push`, never forced, only if the close script exited 0 and the vault was not ahead of its remote before this close's commit. If it was ahead (the owner's own commits waiting), the vault commit stays local and the report says so in one line; the close never pushes the owner's commits. A rejected push is reported, not retried, pulled or merged. The push runs as a visible `git push`, not inside the Python script, so the git-safety hook asks as it does for the project.
4. **What stays the owner's.** The hub the sync creates, pattern drafts, everything the writer writes, the owner's hand edits, `Board/`, `.trash/` and `.gitignore` are not committed by the close. The report's vault list (step 6) is unchanged and stays in chat; the vault commit message names the project and counts, never a note, and lives only in the private vault repository.
5. **Follows, on acceptance:** `scripts/close_slice.py` and its test (each rule above against a weakened script with `scripts/mutate.py`, on a synthetic vault: a hand-written note, a draft, a deletion, a staged owner change, a file in a hidden folder and a non-Markdown file are all left out; an ahead branch is reported), `docs/sop/handoff.md` steps 2, 5 and 6, SPEC §7, and the "Not decided here" and "Limit" lines of ADR 005, which point here.

## Consequences

- Easier: every close leaves the vault's script output committed and, normally, pushed, with no question asked and no review to read. The vault's `git status` shrinks to what is the owner's (their edits, drafts, the writer's approved writes), so it starts to show what changed by hand, the thing ADR 005's "Limit" said it could not.
- Harder: a second push per close, which the hook asks about unless the owner allows it. A lint error anywhere in the vault, even in an owner note, now also holds back the vault's commit, as it already holds back the project's push.
- Not solved: the owner's side still accumulates until the owner commits it, and `Board/` still has no backup (ADR 018). Two closes in different projects at the same moment may meet the vault's index lock; the second reports it and leaves its notes for the next close.
- Risk accepted: a generated note the owner edited by hand is committed with that edit. In a card the sync overwrites such an edit at its next run (ADR 009); in the stats note, which keeps its text byte for byte (ADR 014), the edit stays and is committed. Either way the text goes only to the private remote, where the vault already lives.

## Open for the owner

1. **The scope.** Generated notes only (recommended), or also this close's pattern drafts and new files from the writer. The second keeps more off-machine, but drafts are model text the owner has not accepted, and the selection would come from a list the model passes rather than a property the script reads.
2. **The push.** Push beside the project (recommended), or commit locally and leave every vault push to the owner.
3. **The backlog.** Let the first close sweep the 62 waiting generated notes into one commit (recommended: they are script output), or commit them by hand first.
4. **Before any of this runs:** the working tree's `.gitignore` has lost `Board/` and `.trash/` is not ignored; whether to restore the one and add the other is the owner's, and matters for any commit of everything they make by hand. The vault's one unpushed commit (2026-10-16) also holds back the push of decision 3 until the owner pushes it.

## Alternatives rejected

- **Never commit the vault (today).** No new code, and the owner keeps full control, but script output has no history or copy off the machine and `git status` stays useless as a signal. Right if the vault is backed up some other way and the owner prefers to commit it by hand.
- **Commit exactly what this close wrote** (the close script's measured created and updated list). Ties one commit to one close, but leaves the earlier backlog forever, and the list includes the hub, which is not generated. What makes a path safe to commit unattended is that a script owns it, not that this close touched it. Right if the owner wants one vault commit per close and nothing more.
- **Show the owner the vault's status and commit everything after their yes.** Covers the owner's side too, but today that is about 190 paths, including `.trash/` and, with the ignore line gone, `Board/`'s images; it asks for attention at every close and stages by directory, which the staging rule forbids. Right as the owner's own occasional act, or if the vault's working tree were usually small and its ignores sound.
- **Commit everything the close wrote, drafts and the writer's writes included.** The writer's appended line lands in an owner note that may carry uncommitted hand edits, so committing the path would commit those edits unseen. Right if the writer recorded its writes and the script committed a path only when its whole diff is that write.
- **A separate command (`/vault-commit`).** Clean separation, but ADR 005 rejected separate commands for parts of one moment, and a step the owner must remember is a step that is skipped. Right if vault commits should follow the owner's schedule rather than the closes, or several projects close at once routinely.
- **Push from inside the close script.** One command does all, but a `git push` inside Python is invisible to the git-safety hook, removing the pause ADR 005 kept on purpose. Right if the owner allows vault pushes outright.
- **An Obsidian git plugin committing on a timer.** No workflow code, but it commits whatever is there, ignores and trash included, outside any procedure. Right if the owner wants a whole-vault backup and accepts that it is unreviewed.

## Accepted (2026-10-19)

**Decided by the owner** in chat on 2026-10-19, answering the four questions under "Open for the owner" one by one, each with the recommended option:

1. **Scope:** generated notes only.
2. **Push:** beside the project's, as the assistant's visible `git push`.
3. **Backlog:** the first close sweeps the waiting generated notes into one commit.
4. **`.gitignore`:** accepted as it is. The owner will restore `Board/` and decide on `.trash/` themselves; the close never touches `.gitignore`, `Board/` or `.trash/`, so this does not hold up the build.

## Amendment (2026-10-19): what the review of the build added

The two reviews of `/handoff full` read the first build and found cases the Decision did not name. Each is now in the script and pinned by a test:

- **More refusals, none stopping the close:** a detached HEAD (a commit there is on no branch), an unmerged path (a failed `stash pop` leaves one without a `MERGE_HEAD`), and a `git status` that fails (reported, not read as "nothing to commit").
- **More paths that never qualify:** a symlink, and a path with an index entry `D` (the owner deleted or untracked it, so committing the file back would undo their act). A note's `generated:` value is read as the sync reads it (`True` counts).
- **A refused commit** (a hook, no identity) unstages the notes it had added, so they do not look like the owner's staged changes.
- **A git that cannot run** is reported on the `vault git:` line and does not change the exit code.
- **Declined:** the six-marker list (cherry-pick and revert were dropped: git refuses the commit itself and the failure line says so); the "no upstream" line stays, since it saves a doomed push prompt.

## Amendment (2026-10-19): the ahead check measures where a push goes

- **Why:** a second review, by a different model, read the first build and found that the check counted commits ahead of `@{upstream}`, the tracked branch, while `git push` goes to `@{push}`. With `branch.<name>.pushRemote` (or `remote.pushDefault`) naming another remote and `push.default=current`, a vault level with the tracked remote could still hold the owner's commits that the push remote lacks, and the close said nothing. Reproduced in a scratch repository before the fix.
- **Decided:** the close counts against both refs and reports the larger count as "already N commit(s) ahead". When the tracked branch is level but `@{push}` does not resolve (the push remote has no such branch yet), it prints `vault git: where a push would go cannot be measured, so do not push it`. Step 5 of `docs/sop/handoff.md` lists that line with the other two that stop the vault push. The commit itself is unchanged.
- **Declined:** a refusal for a bisect in progress. A bisect, with or without `--no-checkout`, leaves HEAD detached, which the close already refuses (checked in a scratch repository); a `BISECT_LOG` marker would add nothing.

