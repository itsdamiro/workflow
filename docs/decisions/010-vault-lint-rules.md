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

# 010 — `vault_lint.py`: what it checks, and what it never does

> **Summary.** A read-only, standard-library Python script reports, per note, where the vault breaks the rules of ADR 004: missing fields, links that do not resolve, notes nothing links to, tags outside the vocabulary, concepts without a note. Broken structure is an error; a note that lacks links or tags is a warning that nudges, because the owner's word (2026-10-08) is that orphans are tolerated but every note should try, as best it can, to link and to be tagged. It fixes nothing, and its report is the list the handoff shows the owner.

## Context

ADR 004 says "a lint enforces all of the above" and SPEC §4 lists five checks in one line. Building it needs the details that line leaves open. Facts from the vault on 2026-10-08:

- `Tags.md` lists namespaces (`type/`, `status/`, `project/`, `topic/`, `lang/`, `source/`) and, for `type/` and `status/`, the allowed values. It does not list `topic/` values or project names.
- `Concepts/` holds only its folder definition, so every concept a card names today (`vault-conventions`) has no note. The check will fail on day one, which is correct: the owner writes concept notes.
- Notes link with `[[Name]]`, `[[Name|alias]]` and `[[Name#Heading]]`; frontmatter links are quoted (`"[[Name]]"`). Names are unique across the vault (ADR 004), so a link resolves by file name alone.
- The sync (ADR 009) writes read-only cards from committed records; the owner writes everything else by hand, including notes with frontmatter in shapes the sync never produces.

## Decision

1. **Command.** `python3 scripts/vault_lint.py <vault-path> [--inbox-days N]`. Python standard library only; tests in `scripts/test_vault_lint.py`, shown to fail against weakened versions. It reads every `*.md` under the vault except hidden folders (`.obsidian`, `.git`) and writes nothing.
2. **Frontmatter** is read by a small parser for the shapes the vault uses: scalars, quoted strings, flow lists, block lists, and the `---` fence on line 1. Anything it cannot read is itself a finding (`bad-frontmatter`), never a silent skip.
3. **Checks**, each a rule name in the report:
   - `missing-field`: `type`, `status` and `created` on every note (a card's `created` is the record's date, and is absent when the record has none: that case is reported as a warning, not an error); `projects` on `decision`, `idea`, `pattern` and `source`; `generated` is optional.
   - `unknown-type`, `unknown-status`: the value is not in the lists in `Tags.md`.
   - `broken-link`: a body or frontmatter link whose target is no note in the vault. A `#Heading` part is not checked.
   - `no-links` (warning): a note with no outgoing link. The report lists the names of notes the text mentions without linking ("could link: Foo, Bar"), found by plain string match, so the fix is one edit. `Inbox/` is exempt for `--inbox-days` days (default 14, the owner's choice; counted from the file's modification time), then it is reported.
   - `orphan` (warning): a note nothing links to, outside `Inbox/`. Orphans are tolerated, so this never fails the run; the root note `Garden.md` and any note still marked `status: draft` are not reported (amendments of 2026-10-09).
   - `no-tags` (warning): a note with no tags, and, for `decision`, `concept`, `pattern`, `idea` and `source` notes, no `topic/` tag.
   - `unlisted-topic` (warning): a `topic/` tag that is neither listed in `Tags.md` (written `topic/name` in backticks) nor the name of a note. `topic/` tags are free-form: any may be used, and the warning is the nudge to list it in `Tags.md` and, better, to give it a note of its own to refer to. It matters most for a coined word or a name (Sympose, Stylo), which a reader cannot guess. The report names the tag and the notes using it.
   - `bad-tag`: a tag whose namespace is not listed, a `type/` or `status/` tag whose value is not listed, a `type/` or `status/` tag that disagrees with the field, a `project/` tag with no folder under `Projects/`, or any tag not lowercase kebab-case.
   - `duplicate-name`: two notes with one file name (case aside), because a link resolves by name alone.
   - `missing-concept`: a name in `concepts` with no note in `Concepts/`.
4. **Report.** One line per finding, `path: rule: detail`, sorted, then a count per rule. Errors and warnings are marked. The errors are `bad-frontmatter`, `missing-field`, `unknown-type`, `unknown-status`, `broken-link`, `bad-tag`, `duplicate-name` and `missing-concept`; the warnings are `no-links`, `orphan`, `no-tags`, `unlisted-topic` and a card's missing `created`. Exit 0 when there are no errors, 1 otherwise, 2 for a usage error. Warnings do not fail the exit code, and the handoff shows their count so the nudge is seen.
5. **Never fixes.** A failing lint is reported, never silently fixed (SPEC §4). No `--fix`.
6. **Run by the handoff.** `docs/sop/handoff.md` runs it after the sync and shows its counts to the owner.

## Consequences

The first run reports the missing concept notes and whatever the owner's hand-written notes lack; that list is the real backlog, not a bug. A new tag value in `type/` or `status/` has to be added to `Tags.md` first, which is the point. `topic/` values stay free, so a typo shows up as an unlisted topic, until it is listed. Ordinary words (`vault`) are nudged once too; listing one is a single line in `Tags.md`.

## Alternatives rejected

- **A `--fix` mode.** It would write into notes the owner wrote. Would be right for generated notes only (`generated: true`), where re-running the sync already repairs them.
- **Judging a coined word by the system word list.** Tried on 2026-10-08: `/usr/share/dict/words` has `stylo` (an old word, so Stylo would pass) and lacks `handoff` and `yaml`, and the file is not on every machine. Would be right with a word list the owner curates.
- **Judging "uncommon" by how many notes use a tag.** A coined word used twice is still coined, and an ordinary word used once is not. Would be right if the owner wants only a count-based nudge.
- **A closed list of allowed `topic/` values.** The owner chose free-form tags (2026-10-08): it would make every new topic a two-file change. The nudge above covers the coined ones instead. Would become right once near-duplicates (`topic/vault`, `topic/vaults`) appear; the lint could then warn on near-matches.
- **Checking the heading part of `[[Name#Heading]]`.** A second parser for little gain; renamed headings are rare.
- **Obsidian's own tooling or a YAML library.** A dependency for a handful of shapes. Would be right if the frontmatter grows nested values.
- **Orphans and unlinked or untagged notes as errors.** The owner tolerates them and wants a nudge, not a stop. Would become right for notes the sync writes (`generated: true`), which are always linked and tagged, so a miss there is a bug.
- **Failing the exit code on warnings.** The handoff would stop on a missing date the record never had.

## Amendment (2026-10-08): accepted

- **Accepted** by the owner on 2026-10-08, with these answers: orphans are tolerated but notes should try to link and be tagged (warnings); the Inbox grace period is 14 days; `topic/` tags are free-form, with a nudge to list a topic and, better, give it a note.

## Amendment (2026-10-08): built, and what the two reviews changed

- `scripts/vault_lint.py` and `scripts/test_vault_lint.py`: 113 tests; a mutation check of 135 mutants, all caught.
- **A `Tags.md` that lists no values for `type/` or `status/` is a usage error (exit 2)**, not an open vocabulary, so a damaged tag list cannot make every note pass.
- On the owner's vault the first run reports the nine missing concept notes (the backlog this ADR predicted), five unlisted topics, and one card with no date (the project's "Rejected ideas" note).
- A fresh reader found crashes and false errors on inputs a real vault holds; each was reproduced, tested, then fixed:
  - **Never a traceback.** A `type` or `status` written as a list, a file that cannot be read (a broken link, no permission) and a file that is not UTF-8 are each a `bad-frontmatter` error on that note, and the run goes on. A note with unreadable frontmatter gets no link or tag nudge, only its error.
  - **Frontmatter shapes** now also include block lists (`tags:` then `- a` lines), which is what Obsidian writes when tags are edited in the app. A byte-order mark is ignored. An apostrophe inside an unquoted list item is text. Still unsupported, and reported loudly: YAML escapes inside quotes (`'it''s'`, `"say \"hi\""`).
  - **Links.** `[[#Heading]]` (the note's own heading) has no target and is skipped. `[[Name\|alias]]` (the form a table needs) is an alias. `[[Note.md]]` means `Note`. A target that looks like a file (`pic.png`, `doc.pdf`: a dot, then two to five characters with a letter) and is not a note is not checked, so an image embed does not fail the run. Names are compared Unicode-composed and in lower case, so a file name typed in a different Unicode form still matches.
  - **Code is not text.** Links inside code fences and inline code are ignored (`prose()`), because decision records quote `[[Name]]` in backticks. A closing fence has no info string.
  - **Smaller.** Hidden files are skipped like hidden folders. A `project/` tag matches its folder whatever the case. A topic used twice in one note names the note once, and a badly written topic (`topic/Zzz`) is only a `bad-tag`.
  - **Known gaps, left on purpose:** fences inside blockquotes, `%% comments %%` and links split over two lines are read as Obsidian would not.
- A second reader, for over-engineering, found one bug (an empty `status/` line in `Tags.md` swallowed the next line as its values) and six small trims, all applied.

## Amendment (2026-10-08): concept aliases

- ADR 011 adds the warning `old-concept-name` (an ADR names a concept by an alias listed on the concept note), a "did you mean" hint on `missing-concept`, and `duplicate-name` for an ambiguous alias. The sentence "every concept a card names has no note" above describes the first run only.

## Amendment (2026-10-08): a topic is not a concept

- **A new warning, `narrow-topic`.** A `topic/` tag used on two or more decision cards that all name the same single concept is reported, with the concept and the card count. A topic is a question to filter by and cuts across concepts; one that spans a single concept is that concept's note again. A topic used on one card, or on cards naming two or more concepts, is not reported.
- **Topics stay free-form** (the decision above is unchanged: no closed list). What changes is the guidance and who writes them: the record's author picks from the list in `Tags.md`, and the shape check (ADR 012 amendment) refuses a record with no topic or with one that repeats its own concept.
- **Accepted** by the owner on 2026-10-08, in chat, after a discussion of the options (concept-derived topics, cross-cutting topics, none). Sympose's 78 records were tagged with 11 cross-cutting topics at the same time.

## Amendment (2026-10-08): a code span may be delimited by several backticks

- **Why:** the lint removed inline code with a pattern that allowed no backtick inside the span, so a span written with two backticks to hold one (CommonMark, and what Obsidian renders) left its contents visible, and a `[[link]]` inside it counted as a link. A commit subject with a backtick in it, copied into the stats note (ADR 014), hit this.
- **Rule:** a run of backticks opens a span that the next run of the same length closes, on one line. The code fences and the single-backtick case are unchanged. Tested in `scripts/test_vault_lint.py`.

## Amendment (2026-10-09): a draft pattern is not an orphan

- **Why:** the pattern scan at each `/handoff` (ADR 006) writes drafts that wait for the owner to read them, and the owner has no time to read each as it is made. Each one raised an orphan warning, so an unread draft looked like something wrong. Three of the four orphan warnings on 2026-10-09 were drafts.
- **Decided by the owner:** an unlinked note with `type: pattern` and `status: draft` is not reported as an orphan. Once it is accepted (`status` changes) the check applies as to any note.
- **Not changed:** every other check. A draft pattern with a broken link or a bad tag still fails.

## Amendment (2026-10-09): a pattern must cite code that exists

- **Why:** ADR 006 says a pattern candidate must cite the file and line range it comes from, and a draft carries that in its `code:` field. Nothing checked it, so a model could draft a pattern with no citation or a wrong one, and the owner would find out only on reading it. The owner has no time to read each draft, so the citation has to be checked by code (`docs/CODE_QUALITY_STANDARDS.md` §12).
- **Decided by the owner:** the lint warns, never fails, on a note with `type: pattern` when (1) it has no `code:` (`pattern-no-code`), or (2) a citation is not `path`, `path:line` or `path:first-last`, or, when the project's repo is known, names a file that is not inside it, or lines past the end of the file (`pattern-stale-code`). A list of citations is checked one by one. The repo is given with the option `--repo NAME=PATH` (repeatable), and `scripts/close_slice.py` passes the project it closes; without the option only the first check and the form are tested.
- **Why a warning:** cited lines drift as the code changes, so an old accepted pattern would fail every close for no fault of the owner's.
- **Path safety:** the cited path is resolved through symlinks and must stay inside the repo before the file is opened, so a `..`, an absolute path or a symlink in a draft cannot make the lint read elsewhere.
- **Not changed:** every other check. A draft pattern is still not an orphan (the amendment above).

## Amendment (2026-10-09): any draft is not an orphan, and a capture needs `projects` (ADR 017)

- **Why:** ADR 017 has the assistant write notes as `status: draft` (captures, new concept or folder notes) that wait for the owner to read and link them, as draft patterns do.
- **Rule:** an unlinked note with `status: draft` is not reported as an orphan, whatever its `type`. A draft idea, which the first amendment did not cover, is now exempt too. The type `capture` requires `projects`. `Tags.md` in the vault must list `capture` under `type/`, or the lint reports an unknown type.
- **Not changed:** every other check, including the orphan check for `proposed`, `accepted` and `active` notes.
