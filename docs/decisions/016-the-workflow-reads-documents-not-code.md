---
type: decision
status: accepted
date: 2026-10-09
projects: [workflow]
concepts: [Vault conventions, Source of truth]
amends: []
supersedes: [13]
tags: [type/decision, status/accepted, project/workflow, topic/vault, topic/architecture]
---

# 016 — The workflow reads documents, not code

> **Summary.** The vault sync stops writing a Code map note, and the workflow's tools read only what a project writes as documents (decision records, gotchas, the handoff, the stats line), never its source. Reading code means a comment convention, a language table and a size cap per language, for a note nobody has yet said they use. It costs the quick orientation a map gave, which the project's own architecture documents and records carry instead.

## Context

- ADR 013 (2026-10-08) added `<name> - Code map.md`: the first paragraph of each committed non-test Python file's module docstring. It handles Python only, and said other languages would add an extractor when a project needed one.
- Measured on 2026-10-09: Sympose has 191 mapped Python files (a 67 KB note) and about 380 TypeScript and JavaScript files that the map does not see. Stylo is TypeScript, so its map listed only the template's own scripts.
- Making the map read any language was costed that day on the non-test TypeScript of two projects. A file's leading comment is present in 52 of 136 Stylo files and 22 of 355 Sympose files. Taking the first doc comment after the imports raises that to 105 and 125, and the rest (31 and 230 files) are gaps. A usable version also needs a comment-syntax table, test-file patterns per language, a shorter cap to keep the note readable, and, to stop the gaps growing, a standard and a gate.
- The handoff still asks the owner whether the existing maps are too long to scan and whether to link them from the hubs. Nobody has said the map is read.
- The owner's direction, in chat on 2026-10-09: remove the extraction of the meaning of the code from the workflow entirely, and focus on the documents and the architecture.

## Decision

1. **Remove the code map from the sync.** The code-map section of `scripts/vault_sync.py`, its two hooks (the call in `sync` and the hub link), the helpers only it used, and its tests. A new hub no longer links to a code map. The module docstring and the README stop mentioning it.
2. **Supersede ADR 013.** Its status becomes `superseded` with a link here; its text stays as written.
3. **Amend SPEC §6** to drop the "module docstrings" source and the promise of other-language extractors, and the README to match.
4. **Notes already in the vault** are not touched (a test pins this). The sync deletes nothing, so each existing `<name> - Code map.md` stays, unchanged and stale, until the owner deletes it; the lint's orphan warning for it remains until then. A hub that links one (a hub the sync made while the map existed does) must lose that link first, or the lint reports a broken link.
5. **The rule going forward.** The workflow's scripts read what a project keeps as documents, written to be read: records, gotchas, the handoff, the stats row. What the code does is for the project's own architecture documents and records, written by its authors. No script here interprets source, in any language.
6. **No header-comment standard and no gate.** Neither is added to `docs/CODE_QUALITY_STANDARDS.md` or `scripts/gates`.

## Consequences

- Less code to keep right: about 100 lines of the sync (121 removed, 18 added) and 26 of its 107 tests go, with the Python-only limit and the question of other languages.
- The vault loses a way to see what a Python file says about itself. A reader who wants it opens the file, or the project's architecture document.
- Every project is treated alike: a TypeScript project no longer has a half-empty map beside a full one for Python.
- ADR 009's note that a code map was deferred (item 9) and ADR 013 are now history; the stats line (ADR 014) is unaffected.
- Open: when a project wants a code orientation, it writes an architecture document and a record for it; the workflow only syncs those.

## Alternatives rejected

- **Keep the Python map as it is.** Works, but is lopsided across projects and its use is unproven. Would be right if the owner confirms they read it and only Python projects matter.
- **Read any language** (rule B: the leading comment, else the first doc comment after the imports; first sentence, 200 characters). Costed above: 230 of Sympose's 355 TypeScript files would be gaps, and a standard and a gate would follow to close them. Would be right if a cold session repeatedly has to open files to learn what they are for.
- **Model-written file summaries, accepted one by one.** ADR 013 rejected unreviewed ones; reviewed ones still cost the owner a review of hundreds of files. Would be right for a small project.
- **A header-comment standard enforced by a gate on new files only.** Cheap in wording, but a gate in every adopted project, and a starting point per project, for a note not yet shown to be useful. Would be right with the revisit trigger below.
- **Revisit trigger:** the owner or a fresh session needs to know what a source file is for and has to open it to find out, more than once. Start with the cheapest thing, a plain-wording header-comment habit, before any extractor.
