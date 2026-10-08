---
type: decision
status: accepted
date: 2026-10-08
projects: [workflow]
concepts: [Vault conventions, Source of truth]
amends: [009]
supersedes: []
tags: [type/decision, status/accepted, project/workflow, topic/vault, topic/architecture]
---

# 013 — The code map is the committed Python module docstrings, copied unchanged

> **Summary.** The sync writes one generated note per project, `<name> - Code map.md`, listing each committed Python file with the first paragraph of its module docstring, read with `ast` and never executed. The text is the author's own, so no claim of ours lands in a generated note. It costs one extractor and one note per project, and a file without a docstring is listed as a gap.

## Context

SPEC §6 promises a `Code map.md` made from module docstrings, "Python first", and ADR 009 deferred it. The point is a place in the vault where a reader (the owner, or a session starting cold) can see what each file is for, without a model's summary that may be wrong.

Facts, measured on 2026-10-08 on the committed Python of the two projects that have any:

- Sympose: 87 files in `sympose/` and `scripts/`, 86 with a module docstring, all multi-line, median 357 characters, longest 1,206. Of its 348 tracked `.py` files, 157 have `test` in the path.
- This repository: 7 scripts, all with a docstring, median 686 characters.
- The lint ignores code fences, so a `[[link]]` or `#tag` inside one is neither a link nor a tag (`scripts/vault_lint.py`, `CLOSING_FENCE`). A docstring copied as plain text could carry one and break the lint.
- Python's `ast.parse` reads source without importing or running it, and fails with `SyntaxError` on code newer than the interpreter running the sync.

## Decision

1. **Scope.** Tracked `*.py` files on `REF`, read through git as ADR 009 does. Test files are left out: a path with a `tests` or `test` directory, or a name matching `test_*.py` or `*_test.py`. Other languages are not handled; each adds an extractor when a project needs one (Stylo is not planned).
2. **Extraction.** `ast.get_docstring(ast.parse(source))`, which cleans the indentation. The source is never imported or run. The first paragraph (up to the first blank line) is kept, cut at 600 characters at a word boundary with an ellipsis, the same limit as a card's fallback summary. The text is otherwise unchanged.
3. **The note.** `Projects/<name>/<name> - Code map.md`, `type: reference`, `status: active`, `generated: true`, `created` the day the earliest listed file was first added (never the sync date), `projects`, `source` (the string `module docstrings`), the structural tags. The name carries the project, as the Gotchas note does, because a plain `Code map` would collide across projects.
4. **The body.** Files grouped under one heading per directory, in path order. Each file is its path in backticks, then its paragraph in a fenced code block (a fence longer than any backtick run inside the text), so no link or tag in a docstring reaches the vault. A file with no docstring, or an empty one, is listed by path under "No module docstring"; a file `ast` cannot read is listed under "Unreadable" with the error class. Neither stops the sync. A footer names the hub, the commit and the count of files, and says the next sync overwrites the note.
5. **The same rules as every generated note** (ADR 009, items 6 to 8): only a `generated: true` note is replaced, a name used elsewhere in the vault is refused, a write is atomic and a second run changes nothing, nothing is deleted. A project with no listed Python file gets no note and no complaint. A newly made hub links to the note; an existing hub is the owner's and gets a `hint:` line.
6. **Tests** in `scripts/test_vault_sync.py`: each rule above has a test that fails against a weakened extractor, checked with `scripts/mutate.py` as for the sync.
7. **SPEC §6** is amended: the row's output becomes `<name> - Code map.md`, and the "Python first; a later version" wording is replaced by this record's scope.

## Consequences

The vault gains a map the owner can trust to be only what the code says about itself. It is as good as the docstrings: Sympose's are, and a project without them gets a list of gaps, which is itself a finding. A stale docstring is shown as written, so the map can be out of date with the code it describes; the repair is to edit the docstring. The note is rebuilt on every sync and changes only when a listed file does, because the footer names the last commit that touched one. Open: a map of classes and functions, a `governs:` link from a record to the files it explains, and any language but Python.

## Alternatives rejected

- **A model-written summary of each file.** Unreviewed claims in a generated note, against the rule that a model drafts and the owner accepts. Would be right when the owner reviews each draft before it lands, as ADR 009 also said.
- **Every docstring in full.** Sympose's would run to about 30 KB of one note (86 files at a median 357 characters), too long to scan. Would be right if the note were searched rather than read; the path is given, so the full text is one click away in the repository.
- **Functions and classes as well as modules.** A far larger note and a harder test surface for a first version. Would be right when a reader needs to find a function by purpose rather than a file.
- **A note per file.** Hundreds of generated notes would swamp the graph and the lint's orphan check. Would be right only if each file were a concept the owner writes about.
- **Importing the module to read `__doc__`.** Runs the project's code inside a sync that must be safe to run on anything. Never right.
- **Copying the docstring as plain text.** A `[[x]]` or `#tag` in it becomes a link or tag and can fail the lint. Fencing is cheaper than escaping.

**Accepted** by the owner on 2026-10-08, in chat, as written: a paragraph of at most 600 characters per file, tests left out, the note named `<name> - Code map`.

## Amendment (2026-10-08): the first real run

- **The Context figure was too low.** It said Sympose has 87 non-test Python files; the sync lists 191 (`git ls-files '*.py'` gives 348, of which 157 are tests, as the Context also says). The 87 counted only part of the tree, so the estimate of about 30 KB for every docstring in full, which the "Every docstring in full" alternative leans on, was wrong too.
- **What it produced.** Sympose's note is 191 files under four folder headings, about 67 KB, with one file (`sympose/__init__.py`) without a docstring and none unreadable. This repository's is 7 files. The sync of Sympose took about 4 seconds.
- **Not changed.** The decision stands as accepted: the paragraph cap is still 600 characters. Whether 67 KB is too long to scan is for the owner to judge in Obsidian; a shorter cap (the first sentence) is a one-line change to `DOCSTRING_MAX` and the cut rule, and would be recorded here.
