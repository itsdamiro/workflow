---
type: decision
status: accepted
date: 2026-10-08
projects: [workflow]
concepts: [Handoff, Session length]
amends: [009]
supersedes: []
tags: [type/decision, status/accepted, project/workflow, topic/vault, topic/observability]
---

# 014 — The stats line is a row added to an append-only note, never rewritten

> **Summary.** Each `/handoff` adds one row to `<name> - Stats.md`: the day, the commit, how many commits since the last row, their first and last subject copied from git, and the context size the adapter passes in. The note is `generated: true` but only ever appended to, so its history survives the sync. It costs a script, a note per project, and a history that lives only in the vault.

## Context

SPEC §7 lists "write the stats line (context size at close, slice number)" as planned, and ADR 009 left it open. The point is to see over time how long sessions run before a close, so the guard's thresholds (150k and 200k tokens) can be tuned against evidence rather than a guess (ADR 001).

Constraints already decided:

- A model drafts and the owner accepts; no model-written claim lands in a generated note (CLAUDE.md, ADR 003).
- Scripts overwrite only notes marked `generated: true`, and delete nothing (ADR 009).
- Scripts are portable by layers (ADR 002): only Claude Code records a session's context size, so the script cannot read it itself.
- This repository is public; the vault is not. Nothing from the vault is copied here.
- Git knows commits and dates but not context size, so a note rebuilt from git on every sync could not hold the number this line exists for.

The owner chose, on 2026-10-08, in chat: an append-only generated note; the context size passed in by the adapter; the slice described by commit subjects since the last row.

## Decision

1. **The script.** `scripts/stats_line.py <project-path> <vault-path> [--name NAME] [--ref REF] [--context-tokens N] [--dry-run]`, Python standard library, reusing the git, quoting and write helpers of `scripts/vault_sync.py`. Exit 0 clean, 1 if refused, 2 usage error. `REF` defaults as in the sync.
2. **The note.** `Projects/<name>/<name> - Stats.md`, `type: reference`, `status: active`, `generated: true`, `created` the day of its first row, `projects`, `source` (the string `git log`), the structural tags. One paragraph saying what it is and that rows are never rewritten, then a table with the columns Day, Commit, Commits since the last row, First and last subject, Context at close.
3. **A row.** Day is the day the script runs. Commit is the first 8 characters of `REF`'s head. Commits is `git rev-list --count <previous row's commit>..<head>`. The subjects are the oldest and the newest of those commits, as git has them, each cut at 60 characters at a word with an ellipsis, written as inline code with a `|` escaped, so no link, tag or table break reaches the vault. Context is the integer given by `--context-tokens`, or a dash when none was given.
4. **The first row, and a lost row.** With no previous row, or a previous commit that is no longer in the history (a rewrite), the count is a dash and only the head's subject is shown. That is a row, not a refusal.
5. **Append-only.** The existing text is kept byte for byte and the new row is added after the last row. The write is atomic and goes through the sync's `write_note`, so a note without `generated: true` is refused and left alone, and a name used elsewhere in the vault is refused. If the last line of the note is not a row it can read, the script refuses rather than guess where the previous row ended.
6. **Idempotent.** If the last row's commit is the head, nothing is written, whatever `--context-tokens` says. A dry run writes nothing.
7. **The hub is the owner's.** The script never edits it; if it does not link to the note, the script prints a `hint:`, as the sync does.
8. **The context size comes from the adapter.** The script takes the number as an argument; the Claude adapter will read it from the session's last message in a later slice, and another assistant passes its own number or none. `context_report.py` already reads those transcripts.
9. **Tests** in `scripts/test_stats_line.py`, a line in `scripts/gates.conf`, and each rule above has a test that fails against a weakened script, checked with `scripts/mutate.py`.
10. **The documents follow.** `docs/sop/handoff.md` gains the step, after the handoff is drafted; SPEC §6 lists the note and §7's row stops saying "planned" and drops "slice number", which the commit count replaces; ADR 009's open items lose the stats line.

## Consequences

A close leaves one more row, so a series of closes shows how large the context was each time and how much work lay between them. Subjects are verbatim from git, so a row says what was committed, not how a model would describe the slice. The sync never touches the note, so rows survive it, and an error in a row can be fixed by hand because the script never rewrites one.

The history lives only in the vault, which is local and not yet under git: a deleted or overwritten note loses it, and git cannot rebuild the context column. A rewritten history shows as a dash in one row. The row's day is the machine's local day. The default `REF` is the default branch, as in the sync, so a `/handoff` run on another branch records that branch's base unless the adapter passes `--ref` (a code review raised it; the sync's reason, not publishing a draft, does not apply to a stats row, so the default may change to the checked-out branch when it first matters). Open: the Claude adapter that supplies the context size, a chart of the rows, and a row for work done without `/handoff`.

## Alternatives rejected

- **A hand-written note that the script appends to.** Keeps "scripts write only generated notes" literal, but needs a manual first step in every project and a note that can silently lack the marker. Would be right if the owner wanted to annotate rows in the same note.
- **A note rebuilt from git on each sync.** Safe to overwrite, but git holds no context size, so the main column would vanish. Would be right if the line were only about commits.
- **The script reading Claude's transcripts itself.** One less argument, but it makes the script Claude-only against ADR 002. Would be right if no other assistant were ever used.
- **A slice name the owner types, or the "Working on" line.** Reads better, but the second is model-drafted text in a generated note and the first is one more thing to type at every close. Would be right if the owner accepted and edited the row at the close.
- **One row per commit.** Most commits are not closes, so it records activity and not sessions. Would be right if the question were how fast commits come.
- **A CSV or JSON file.** Easier to chart, but invisible in Obsidian and not a note the vault lint knows. Would be right when a chart is built.

**Accepted** by the owner on 2026-10-08, in chat, as written.

## Amendment (2026-10-09): the Claude adapter exists

The adapter that supplies `--context-tokens` under Claude Code is `adapters/claude/context-report/last_context.py`, which reads the session's own transcript by `$CLAUDE_CODE_SESSION_ID` and gives a dash when it cannot (ADR 015). The decision above is unchanged; the Claude adapter is no longer open.
