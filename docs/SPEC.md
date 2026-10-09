# Workflow: specification

Status: design, 2026-10-08. Decisions and their alternatives are in `docs/decisions/`; step-by-step procedures are in `docs/sop/`. Where this file and an ADR disagree, the ADR wins until this file is corrected.

## Contents
1. Purpose
2. Principles
3. Layers
4. The vault
5. ADR format
6. Extraction (`vault-sync`)
7. `/handoff`
8. Session guard
9. Project types
10. Open questions

## 1. Purpose

Stop AI-assisted projects losing their thinking between sessions, keep long sessions cheap, and turn what projects learn into personal, connected notes: with any model or tool.

## 2. Principles

- **Portable by layers** (ADR 002): files and scripts first, procedures second, tool adapters last and optional.
- **The repo is the source of truth; the vault is personal output** (ADR 003). Nothing from the vault is committed to a project, and nothing personal is committed here.
- **Deterministic first.** A script does what a script can do. A model drafts only what needs judgment, and the owner accepts it. Generated notes carry no model-written claims.
- **Write state through to files.** Nothing that matters lives only in a conversation.
- **No AI trace in commits or repositories** (see `docs/COLLABORATION_STANDARDS.md`).

## 3. Layers

| Layer | Contents | Rule |
|---|---|---|
| Files and scripts | Markdown, YAML frontmatter, shell or Python standard library | runs without any assistant |
| Procedures | `docs/sop/*.md` | steps name capabilities ("read the diff", "run this script", "ask a fresh reader"), never one tool's verbs |
| Adapters | a Claude skill and mod, a Gemini command, others | a few lines each: "follow `docs/sop/<name>.md`" |

An adapter may add convenience (a reminder, a button). It may not add behaviour that the SOP does not describe.

`AGENTS.md` (local-only, on the no-trace list) is the tool-neutral twin of `CLAUDE.md`. Gemini CLI reads `GEMINI.md` by default and reads `AGENTS.md` only when `context.fileName` in its `settings.json` lists it, for example `["AGENTS.md", "GEMINI.md"]`.

## 4. The vault

The central vault is `garden`, started empty on 2026-10-08. It is local with no remote; it is to be git-initialised for history (not yet done).

```
Projects/<name>/   <name>.md (hub, yours), decisions/, <name> - Rejected ideas.md, <name> - Gotchas.md (when committed), <name> - Stats.md (one row per `/handoff`)
Concepts/          one note per idea you name (the vocabulary)
Patterns/          reusable building blocks, each citing code and any ADR
Ideas/             your own notes
Inbox/             outside sources, unevaluated
Templates/
```

Each top-level folder has a definition note named after the folder (`Projects/Projects.md`) stating its purpose and the frontmatter template for its notes (Sympose's folder-definition convention).

**Names.** A decision card is `NNN - Sentence from the slug.md` (`040 - The persona looks up notes itself.md`). The leading number is the key the script matches on; the sentence is built from the repo filename's slug, not the heading, so it is short and has no characters Obsidian rejects. Links are written `[[040 - The persona looks up notes itself|ADR 040]]`. If two cards would get the same name the script stops and reports.

**Renames and removals.** A renamed slug leaves a one-line redirect note at the old name. A removed ADR leaves a tombstone card (status removed, date, one line why) so links to it still resolve.

**Concept names** (ADR 011). A concept is a singular noun phrase in sentence case (`Pattern scan`), and its note may list old names under `aliases:`. An ADR's `concepts:` line names the note or an alias; an alias gives a warning that names the current name, and a name that matches nothing is an error with a "did you mean" hint. Renaming: `docs/sop/rename-a-concept.md`.

**Frontmatter, on every note.**

```yaml
---
type: decision          # decision | concept | pattern | idea | source | reference | project | folder-definition | index | redirect
status: accepted
created: 2026-10-08
projects: [workflow]
concepts: []
generated: true         # only on notes a script owns
tags: [type/decision, status/accepted, project/workflow]
---
```

**Links.** Every note should link to at least one other, and be linked from one (the lint warns; it does not fail). Cards link to their project hub, their concepts and what they amend. An idea links to at least one project or concept. `Inbox/` notes may stay unlinked for a set number of days. Links in frontmatter must be quoted; the main links go in the body.

**Tags.** Lowercase, namespaced, kebab-case: `type/`, `status/`, `project/`, `topic/`, `lang/`, `source/`. The sync adds the structural tags from the fields; each record's author writes its `topic/` tags (at least one, usually one to three, from the list in `Tags.md`, never a concept's own name; ADR 010 and 012 amendments). A `Tags` note lists the allowed namespaces and the lint rejects others. Rule: if you would write about it, it is a concept; if you would only filter or count by it, it is a tag.

**Lint** (`scripts/vault_lint.py`, ADR 010; a failing lint is reported, never silently fixed). Errors, which fail the run: unreadable or missing frontmatter fields, an unknown type or status, a link that does not resolve, a tag outside the vocabulary, two notes with one name, a concept with no note in `Concepts/`. Warnings, which nudge and never fail the run: a note with no links, an orphan outside `Inbox/`, a note with no tags (or no `topic/` tag), a `topic/` tag neither listed in `Tags.md` nor a note, a topic whose decision cards all name one concept, a generated card with no date, a concept named by an old alias (ADR 011), a pattern that cites no code or code that is not in its project's repo (ADR 010, amendment of 2026-10-09: the repo is given with `--repo NAME=PATH`, which `scripts/close_slice.py` does).

## 5. ADR format

ADRs stay in each project's `docs/decisions/`, numbered, with Context, Decision, Consequences, Alternatives rejected and dated amendments (`## Amendment (date): title`). New ADRs add frontmatter (`type`, `status`, `date`, `projects`, `concepts`, `amends`, `supersedes`) and a three-line summary at the top. `governs:` (paths of the code an ADR explains, checked by a gate) is optional and not yet decided. See `docs/decisions/TEMPLATE.md`, `docs/VAULT_CONVENTIONS.md` and the shape-check gate `scripts/adr_check.py` (ADR 012); all three travel with the template.

## 6. Extraction (`scripts/vault_sync.py`)

A script, no model, idempotent. It reads the committed state of each project's default branch (so unmerged drafts are not published) and writes into `Projects/<name>/`.

| Source | Output | How |
|---|---|---|
| each ADR | a decision card: title, status, summary, amendments, rejected alternatives, link back | parsed from the headings |
| every "Alternatives rejected" | `<name> - Rejected ideas.md` | parsed |
| `docs/reference/GOTCHAS.md`, if committed | `<name> - Gotchas.md` | copied as committed; a local-only file is skipped (ADR 009 amendment) |
| `git log` and the adapter's context size (ADR 015), one row per `/handoff` | `<name> - Stats.md` | `scripts/stats_line.py`, not the sync: a row is added to an append-only note and no earlier row is rewritten (ADR 014) |

The first version (ADR 009) does the cards and the Rejected-ideas note only; the `GOTCHAS` mirror followed (ADR 009 amendment): it copies the file as committed, and a project where the file is local-only gets none. A code map followed (ADR 013) and was removed (ADR 016): the workflow reads a project's documents, never its source. Concept notes are the owner's: the cards that name a concept appear in its backlinks.

The script only overwrites notes marked `generated: true`. It never touches a note without the marker.

## 7. `/handoff`

One procedure, run when a slice's work is done (`docs/sop/handoff.md`); it commits the slice's named files and pushes (ADR 005 amendment). There are two closes (ADR 005, amendment of 2026-10-09): `/handoff`, the light close, and `/handoff full`, which adds the rows marked *full*; `/handoff check` means `full`.

| Step | When | Who |
|---|---|---|
| review the slice's diff for correctness (`/code-review`) and for over-engineering, together, before the commit | full | model reviews, owner decides |
| run the gates, then commit the slice's named files | always | script and model |
| run the vault sync, the stats line and the lint, as one script (`scripts/close_slice.py`) | always | script |
| scan the slice's diff for a reusable pattern (cites file and lines; "none" is a valid result; drafts wait quietly) | always | model drafts, owner accepts when they choose |
| draft `docs/HANDOFF.md` | always | model drafts, owner accepts |
| check the handoff with a fresh reader and the six questions | full | fresh session or another model |
| push the branch, when the lint has no error | always | script and model |
| report, short: what was pushed, what failed or was refused, the vault notes created and updated (by path; the close script lists them), what needs the owner | always | script and model |

The stats line records the day, commit, commits since the last row, their first and last subject, and the context size at close, from the adapter (`adapters/claude/context-report/last_context.py` under Claude Code, ADR 015); `close_slice.py` runs it.

Running `/handoff` is the owner's go-ahead to commit and push the slice; outside it, commit and push stay the owner's call. Writing the ADR itself happens before the code and is not part of this.

## 8. Session guard

Optional adapter (a Claude Code mod). It shows context size in the status line, shows a band with one close button (**Close slice** submits `/handoff`, the light close) at a soft threshold (default 150k tokens) and a stronger one at a hard threshold (default 200k). It never blocks. It may also show rate-limit windows and the closing checklist. Prototype in `adapters/claude/session-guard/`: validated, not yet checked drawing on the desktop app. The hard git rules stay in a hook, not in the mod.

## 9. Project types

Language-neutral. `gates.conf` is `name | directory | command`. SOPs avoid assuming a UI, a server or a language. Only the code-map extractor is language-specific.

## 10. Open questions

- Stylo uses a journal and a wiki, not `decisions/`: write an extractor or migrate it.
- Is `governs:` worth its upkeep?
- Does Sympose parse the chosen tag and list syntax? Test with sample notes before fixing the format.
- Does the mod draw on the desktop app, and can it read tokens as well as a percent of the window?
- Do structural tags add noise to Sympose's connections?
