---
type: decision
status: accepted
date: 2026-10-08
projects: [workflow]
concepts: [Vault conventions]
amends: [004, 010]
supersedes: []
tags: [type/decision, status/accepted, project/workflow, topic/vault]
---

# 011 — Concept names: readable, with aliases that survive a rename

> **Summary.** A concept is named in plain readable words (`Pattern scan`), and its note may list old names under `aliases:`. The lint accepts an ADR that still uses an alias, with a warning that names the current name, and it suggests the closest concept when a name matches none. A rename therefore never breaks the vault; it leaves a list of records to update.

## Context

On 2026-10-08 the first lint run reported ten missing concept notes. Writing them showed three things:

- ADR 004 gives decision cards a sentence name (`NNN - Sentence`) but says nothing about concept names. The ADRs had used lowercase slugs (`patterns`), and one of them (`patterns`) collided with the folder note `Patterns/Patterns.md`, because Obsidian compares names without regard to case.
- A concept's name is the key that ADRs in the repo and the note in the vault share. The sync copies the name from the record, so a rename in the vault alone is undone by the next sync, and a rename in the records alone makes every card an error until the note is renamed too.
- Obsidian already resolves `[[Old name]]` to a note that lists it under `aliases:`, and the lint's frontmatter parser already reads block lists, which is how Obsidian writes aliases.

## Decision

1. **Readable names.** A concept is a singular noun phrase in sentence case (`Session length`, `Pattern scan`), with no ADR numbers and no punctuation Obsidian rejects. Names are compared without regard to case or Unicode form, so spelling matters and capitals do not. A concept may not share a name with a folder note (`Patterns`, `Tags`, `Concepts`); the duplicate-name check already reports it.
2. **Aliases.** A note in `Concepts/` may list old or alternative names under `aliases:`. The lint treats a name in an ADR's `concepts:` field as resolved when it matches a concept note's name or one of its aliases.
3. **An alias in use is a warning, `old-concept-name`.** It names the record, the alias and the note's current name ("use `[[Pattern scan]]`"). It never fails the run, and the concept note counts as linked, so it is not reported as an orphan.
4. **A name that matches nothing is still the error `missing-concept`**, and when a concept name or alias is close to it (`difflib`, standard library) the detail ends with "did you mean `Pattern scan`?". A typo or a singular/plural slip then points at its fix.
5. **An alias must be unambiguous.** An alias equal to another note's name, or listed by two concept notes, is a `duplicate-name` error on the concept note. An alias equal to its own note's name is ignored. Aliases on notes outside `Concepts/` are not checked.
6. **Aliases are honoured in the `concepts:` field only.** A `[[Old name]]` link in a note body is still checked against file names alone; Obsidian resolves it, the lint does not yet.
7. **Renaming a concept** is the procedure in `docs/sop/rename-a-concept.md`: rename the note in Obsidian, add the old name to `aliases:`, change the `concepts:` line of each record that uses it, commit, sync, and lint until the `old-concept-name` warnings are gone. The sync needs no change: it copies the name the record carries.

## Consequences

A rename is cheap and safe, and the warnings are the to-do list for the records. The cost is one more field on concept notes, one more warning in the lint and a hint on one error. A name that is changed in the vault but not given an alias still fails loudly, which is the safeguard.

## Alternatives rejected

- **Keep lowercase slugs.** They match the repo's file style and need no change, but they read badly in Obsidian's graph and links, and the owner prefers sentence names (2026-10-08). Would be right if the vault were read mostly by scripts.
- **Make the lint fix a stale name** or rewrite the records. It would write into notes the owner wrote and into the public records (ADR 010, "Never fixes").
- **A redirect note for each renamed concept.** ADR 004 uses redirects for renamed cards, which the sync generates. For a hand-written concept an alias does the same job in one line and Obsidian understands it. Would be right if a concept were split in two, where an alias cannot say which half an old link meant.
- **Resolving aliases in body links too.** It needs the lint to read aliases for every note. Would be right if body links to old names turn up in practice.
- **A rename script that edits the vault and the records together.** It writes across two places, one of them a public repo. Would be right once renames are frequent enough that the manual list is a burden.

## Amendment (2026-10-08): accepted

- **Accepted** by the owner on 2026-10-08: readable concept names; aliases with a warning; a "did you mean" hint; the rename procedure.
