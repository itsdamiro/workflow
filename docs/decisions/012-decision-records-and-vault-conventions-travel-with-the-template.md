---
type: decision
status: accepted
date: 2026-10-08
projects: [workflow]
concepts: [Portability, Vault conventions]
amends: [008]
supersedes: []
tags: [type/decision, status/accepted, project/workflow, topic/vault]
---

# 012 — Decision records and vault conventions travel with the template

> **Summary.** A project adopted from the template gets the decision-record template with frontmatter, one short page of vault conventions (names, fields, tags, links), the procedures for writing a decision and naming a concept, and a gate that checks the shape of its records. Without them a project writes old-style records that the vault cannot connect, which is what happened to Sympose. It costs four files and one script per project, and a version bump.

## Context

On 2026-10-08 the vault sync, the lint and the concept vocabulary were built (ADRs 009 to 011), and Sympose's 78 records were backfilled with a `concepts:` line by hand. Sympose was adopted before these existed, and `adopt.sh` (template version 10) carries none of them: no record template, no procedure for writing a decision, nothing that says how a concept is named or a link written. A new Sympose record would again be old-style, and the owner is about to start the same work in other projects.

Facts: the procedures live in this repository's `docs/sop/`, written with this repository's paths in mind. The template carries `CLAUDE.template.md`, the standards, `scripts/gates`, `mutate.py` and `md_wrap_check.py`. The sync and the lint stay here and take paths as arguments, so a project does not need them.

## Decision

1. **Four files go into every adopted project**, none overwritten (the `adopt.sh` rule):
   - `docs/decisions/TEMPLATE.md`: the record template, with the frontmatter of ADR 004 and a three-line summary.
   - `docs/VAULT_CONVENTIONS.md`: one page, the only place the rules are written for a project: card and concept names, the frontmatter fields, the tag namespaces, how a wikilink is written, what `concepts:` takes, and how to run the sync and the lint from this repository.
   - `docs/sop/write-an-adr.md` and `docs/sop/rename-a-concept.md`, generalized to name no path of this repository.
2. **The contents page points at them.** `CLAUDE.template.md` gains one line under "Contents of the rest" for writing a decision, so a new session finds the procedure before writing a record.
3. **A shape check, `scripts/adr_check.py`, is a gate.** It reads `docs/decisions/` and fails on a record with no frontmatter, a missing field, an empty `concepts:`, a concept name that is not sentence case, or no row in the index. It reads files only: whether a concept has a note is the lint's job. A `--from NNN` argument skips older records, so a project can start the gate before every old record is backfilled.
4. **One copy.** The sources move into `template/` and this repository's own copies become symlinks to them, as ADR 008 did for the standards.
5. **Version 11.** `adopt.sh --check` reports a project that lacks the four files. Tests cover the new files, "never overwrites" and `--check`.
6. **Rolling out is per project and reviewed.** Sympose first: the files are added, and its older records are backfilled with the full frontmatter (status and date from what the sync already reads, `amends` from the text) as a diff for the owner to read. Other projects follow with `adopt.sh --check`.

## Consequences

A new project writes records the vault can connect from the first one, and a project that drifts is caught by a gate rather than by someone remembering. The cost is one more document set per project to keep in step; the template remains the source and `--check` reports drift. The rules now exist in three places (ADR 004, the SPEC and `VAULT_CONVENTIONS.md`); the project page is the short version, and a change goes to ADR 004 first.

## Alternatives rejected

- **Procedures only, no gate.** Cheaper, but the standards say a rule enforced by wording alone is not enforced (CODE_QUALITY §12), and the Sympose gap is exactly that. Would be right if records were few and one person wrote them all.
- **Copy the whole `docs/sop/` folder.** It includes the handoff and weekly procedures that refer to this repository's scripts. Would be right once those are portable too (the `/handoff` adapters are still planned).
- **Put the conventions inside `write-an-adr.md`.** One file fewer, but names, tags and links matter to anyone writing a note, not only an ADR. Would be right if the vault only ever held records.
- **Make `adr_check.py` check the vault** (that every concept has a note). It would tie every project's gates to one machine's vault path. The lint already does it after the sync.
- **Backfill every project's records in this slice.** Reviewing 78 records in one project is already a diff to read; the rest wait for their own pass.

## Amendment (2026-10-08): accepted

- **Accepted** by the owner on 2026-10-08, with these answers: the shape check is a gate; the conventions are a page of their own (`docs/VAULT_CONVENTIONS.md`); the template comes first and Sympose is the next step, not part of this slice.

## Amendment (2026-10-08): how Sympose's records were backfilled

- **Dates.** A record whose text gives no date got the date of the git commit that added its file (37 of 78), which is when the file appeared and not necessarily when the choice was made. A "Proposed YYYY-MM-DD" in the status line wins over a later "built" date.
- **Amends and supersedes** were read from the status line's "Amends" and "Replaces" sentences and cut off at "builds on" and "reverses"; they were not read from the body.
- **Summaries were drafted by a model** from each record and written in at the owner's word, in bulk, without a line-by-line review. A summary is edited in the project's record and then synced; an edit made to a generated vault card is replaced by the next sync. A separate reader then checked every summary and field against its record and found errors in about a third of them (summaries that a later amendment in the same record had overturned, and missing `amends`); those were fixed, so a bulk draft is not to be trusted unchecked.
- **The gate starts at record 1** in Sympose, because every record now has the full shape.

## Amendment (2026-10-08): topics in the shape check

- **The shape check requires a topic.** A record's `tags:` must include at least one `topic/` tag, and a topic that is only the kebab-case of one of the record's own `concepts:` is refused, because the record already links to its concepts and the tag would add nothing to filter by. Whether a topic is a good one is for the owner's review; the vault lint warns when a topic is unlisted or spans one concept (ADR 010 amendment).
- **The prompts carry the rule.** `VAULT_CONVENTIONS.md`, `docs/decisions/TEMPLATE.md` and `docs/sop/write-an-adr.md` tell the author: one to three topics, a question to filter by, from the list in the vault's `Tags.md`, never a concept's name; if none fits, ask the owner to list a new one with the question it answers.
- **Version 12.** The first attempt derived each record's topics from its concepts, which passed every check and added nothing; the check above exists so that shortcut is refused.
- **Accepted** by the owner on 2026-10-08, in chat.
