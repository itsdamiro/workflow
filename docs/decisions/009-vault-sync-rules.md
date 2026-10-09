---
type: decision
status: accepted
date: 2026-10-08
projects: [workflow]
concepts: [Vault conventions]
amends: [004]
supersedes: []
tags: [type/decision, status/accepted, project/workflow, topic/vault]
---

# 009 — `vault_sync.py`: what it reads, what it writes, and when it refuses

> **Summary.** A standard-library Python script turns a project's committed decision records into read-only cards, plus a "Rejected ideas" note, in the vault. It reads text out of the records and never writes a claim of its own, overwrites only notes marked `generated: true`, and deletes nothing.

## Context

SPEC §6 sketches the sync; building it settles details the sketch left open.

- Two record shapes exist. This project's records carry frontmatter and a `> **Summary.**` line. Sympose's 79 records have none: a title heading, sometimes a `> **Status: Accepted** (date)` line, the four sections, dated amendments, and an index table with a status per record.
- Sympose's `GOTCHAS` is local-only (gitignored), so it cannot be read from a branch.
- A note name must be unique in the vault for a plain link to resolve. A note called `Rejected ideas` in every project would collide.
- Obsidian and Sympose both show a note's backlinks, so a note listing the cards that name a concept adds nothing.
- Checked on 2026-10-08 with Sympose's own code: frontmatter parses as YAML (flow lists, `type/decision`-style tags, a quoted `"[[Concept]]"`), and `[[NNN - Sentence|ADR NNN]]` links resolve. Untested: whether a tag shared by many notes adds noise to Sympose's connections.

## Decision

1. **Command.** `python3 scripts/vault_sync.py <project-path> <vault-path> [--name NAME] [--ref REF] [--dry-run]`. Python standard library only. Tests in `scripts/test_vault_sync.py`, shown to fail against weakened versions.
2. **Reads.** The committed `docs/decisions/NNN-slug.md` files of `REF` (default: the local branch the remote's HEAD names, else `main` or `master`), through git, so an unmerged draft is never published and the working tree is untouched. `README.md` and `TEMPLATE.md` are skipped.
3. **Writes**, under `<vault>/Projects/<name>/`: a card per record in `decisions/`; `<name> - Rejected ideas.md`; and the hub `<name>.md` only if it does not exist (the owner's, never overwritten).
4. **A card** holds frontmatter (`type`, `status`, `created` when known, `projects`, `concepts` as quoted links, `adr`, `source`, `generated: true`, tags), the title, a summary, a link to the hub, `amends` links, the dated amendments, and the each rejected alternative, joined across its wrapped lines and cut at 300 characters. Everything is text taken from the record. The summary is the `> **Summary.**` line, else the first paragraph of the Decision section cut at a word boundary (600 characters, marked with an ellipsis). Status is the frontmatter's, else the `> **Status: …**` line's, else the index row's, else `unknown`.
5. **Names.** `NNN - Sentence.md`, built from the file's slug (ADR 004). If two cards would get one name, the script writes neither and reports it.
6. **Overwrite rule.** Only a note whose frontmatter says `generated: true` is replaced. Any other note in the way is left alone and reported. A write goes to a temporary file and is renamed into place; unchanged content is not rewritten.
7. **Removals and renames.** A record that disappears becomes a tombstone card (`status: removed`, the sync date, one line); a record whose slug changed leaves the old card as a redirect note to the new one. Nothing is deleted.
8. **Report.** Counts of created, updated, unchanged, tombstoned, redirected and refused, and each refusal with its reason. Exit 0 when nothing was refused, 1 otherwise, 2 for a usage error. `--dry-run` writes nothing and says what it would do.
9. **Not in this version.** The `GOTCHAS` mirror (added later, see the last amendment), the code map, generated concept notes (backlinks do that job; the owner writes concept notes), and the stats line. SPEC §6 is amended to match.

## Consequences

Sympose's records have no `concepts`, so its cards link to none until they are backfilled, and their summaries are excerpts, not summaries. The result is rebuilt from the repository at any time. A project with local-only documents has them absent from the vault until the `GOTCHAS` question is settled.

## Alternatives rejected

- **A model-written summary.** Unreviewed claims in a generated note; revisit when the owner reviews drafts before they land.
- **Generated concept notes.** They would collide with the owner's own, and backlinks already list the cards.
- **Reading the working tree.** It would publish drafts. Would be right for local-only files, under its own decision.
- **Deleting a card whose record is gone.** Breaks every link to it; a tombstone keeps them.
- **One `Rejected ideas` note name for every project.** Plain links would be ambiguous.

## Amendment (2026-10-08): accepted, and three details from building it

- **Accepted** by the owner on 2026-10-08, including dropping generated concept notes and deferring the `GOTCHAS` mirror.
- **Default ref** is the *local* branch the remote's HEAD names, not the remote-tracking one, so commits made but not yet pushed are seen.
- **Status** is read from the frontmatter, else from a status line in any of the three shapes the records use (`> **Status: X**`, `> **Status:** X`, `Status: X (name, date)`), else from the index row, else `unknown`. The record's date is the first date on that line.
- **A rejected alternative** is the whole bullet, joined across the lines it wraps over (a blank line ends it), because the records wrap their lines and a first line alone stops mid-sentence.
- **Two note types are added** to the vocabulary: `index` (the Rejected-ideas note) and `redirect`.
- Built and checked: 36 tests, 52 of 52 mutants caught; on Sympose's 78 real records, 153 links resolve, no status is unknown, and a second run changes nothing.

## Amendment (2026-10-08): a date on the Rejected-ideas note

- The "Rejected ideas" note now carries `created`, the earliest valid `YYYY-MM-DD` date among the project's records, so the lint no longer warns about it and a second sync still leaves it unchanged. It is taken from the records, never from the day the sync runs. With no valid date among them the field is left out, as on a card.

## Amendment (2026-10-08): the GOTCHAS mirror, committed text only

- **Decided by the owner:** the mirror copies a project's `docs/reference/GOTCHAS.md` as committed on `REF`, and nothing else. A project where the file is local-only (not tracked) gets no mirror; the sync says nothing and the vault simply lacks the note. The rule "the sync reads committed state only" has no exception. Working-tree reading stays rejected (see above) and would need its own decision.
- **The note** is `<name> - Gotchas.md` under `Projects/<name>/`, `type: reference` (a new note type, added to the vocabulary with this amendment), `status: active`, `created` the day the file was first committed (never the sync date), `source` the file's path, `generated: true`. Its body is the file's text unchanged, then one footer line naming the hub, the path and the commit. A newly made hub links to it.
- **The same rules as a card:** only a `generated: true` note is replaced, a name already used elsewhere in the vault is refused, a second run changes nothing. If the file is later removed from the branch, the old note stays (nothing is deleted); the owner removes it.
- **Edge cases (from the code review):** `created` follows the file across a move (`git log --follow`, the earliest date). An entry at the path that is not a regular file (a directory, symlink or submodule) is refused with a reason, and the rest of the sync still runs. A file that starts with its own frontmatter is refused, since the note would carry two blocks. Links and tags inside the file are copied as written. An existing hub is the owner's and is never edited: when it lacks the link the report prints a `hint:` line, which does not change the exit code.
- This closes item 9's deferral for the mirror. The code map and the stats line remained open here; see the last amendment.

## Amendment (2026-10-08): the code map and the stats line

- Item 9's two remaining deferrals are decided elsewhere: the code map in ADR 013 (written by the sync; removed by ADR 016) and the stats line in ADR 014 (written by `scripts/stats_line.py`, not by the sync, because it adds a row instead of rebuilding a note). The sync never touches the stats note.
