# Workflow: specification

Status: design, 2026-10-08. Decisions and their alternatives are in `docs/decisions/`; step-by-step procedures are in
`docs/sop/`. Where this file and an ADR disagree, the ADR wins until this file is corrected.

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

Stop AI-assisted projects losing their thinking between sessions, keep long sessions cheap, and turn what projects learn
into personal, connected notes: with any model or tool.

## 2. Principles

- **Portable by layers** (ADR 002): files and scripts first, procedures second, tool adapters last and optional.
- **The repo is the source of truth; the vault is personal output** (ADR 003). Nothing from the vault is committed to a
  project, and nothing personal is committed here.
- **Deterministic first.** A script does what a script can do. A model drafts only what needs judgment, and the owner
  accepts it. Generated notes carry no model-written claims.
- **Write state through to files.** Nothing that matters lives only in a conversation.
- **No AI trace in commits or repositories** (see `docs/COLLABORATION_STANDARDS.md`).

## 3. Layers

| Layer | Contents | Rule |
|---|---|---|
| Files and scripts | Markdown, YAML frontmatter, shell or Python standard library | runs without any assistant |
| Procedures | `docs/sop/*.md` | steps name capabilities ("read the diff", "run this script", "ask a fresh reader"), never one tool's verbs |
| Adapters | a Claude skill and mod, a Gemini command, others | a few lines each: "follow `docs/sop/<name>.md`" |

An adapter may add convenience (a reminder, a button). It may not add behaviour that the SOP does not describe.

## 4. The vault

The central vault is `garden`, started empty on 2026-10-08. It is local with no remote; it is to be git-initialised for history (not yet done).

```
Projects/<name>/   <name>.md (hub, yours), decisions/, Rejected ideas.md, Code map.md, GOTCHAS.md, stats
Concepts/          one note per idea you name (the vocabulary)
Patterns/          reusable building blocks, each citing code and any ADR
Ideas/             your own notes
Inbox/             outside sources, unevaluated
Templates/
```

Each top-level folder has a definition note named after the folder (`Projects/Projects.md`) stating its purpose and
the frontmatter template for its notes (Sympose's folder-definition convention).

**Names.** A decision card is `NNN - Sentence from the slug.md` (`040 - The persona looks up notes itself.md`). The
leading number is the key the script matches on; the sentence is built from the repo filename's slug, not the heading,
so it is short and has no characters Obsidian rejects. Links are written
`[[040 - The persona looks up notes itself|ADR 040]]`. If two cards would get the same name the script stops and reports.

**Renames and removals.** A renamed slug leaves a one-line redirect note at the old name. A removed ADR leaves a
tombstone card (status removed, date, one line why) so links to it still resolve.

**Frontmatter, on every note.**

```yaml
---
type: decision          # decision | concept | pattern | idea | source | project | folder-definition
status: accepted
created: 2026-10-08
projects: [workflow]
concepts: []
generated: true         # only on notes a script owns
tags: [type/decision, status/accepted, project/workflow]
---
```

**Links.** Every note links to at least one other. Cards link to their project hub, their concepts and what they amend.
An idea links to at least one project or concept. `Inbox/` notes may stay unlinked for a set number of days. Links in
frontmatter must be quoted; the main links go in the body.

**Tags.** Lowercase, namespaced, kebab-case: `type/`, `status/`, `project/`, `topic/`, `lang/`, `source/`. The sync adds
the structural tags from the fields; the owner adds `topic/` tags. A `Tags` note lists the allowed namespaces and the
lint rejects others. Rule: if you would write about it, it is a concept; if you would only filter or count by it, it is
a tag.

**Lint** (a failing lint is reported, never silently fixed): required fields present; every link resolves; no orphans
outside `Inbox/`; every tag is in the list; every concept used is a note in `Concepts/`.

## 5. ADR format

ADRs stay in each project's `docs/decisions/`, numbered, with Context, Decision, Consequences, Alternatives rejected and
dated amendments (`## Amendment (date): title`). New ADRs add frontmatter (`type`, `status`, `date`, `projects`,
`concepts`, `amends`, `supersedes`) and a three-line summary at the top. `governs:` (paths of the code an ADR explains,
checked by a gate) is optional and not yet decided. See `docs/decisions/TEMPLATE.md`.

## 6. Extraction (`vault-sync`)

A script, no model, idempotent. It reads the committed state of each project's default branch (so unmerged drafts are
not published) and writes into `Projects/<name>/`.

| Source | Output | How |
|---|---|---|
| each ADR | a decision card: title, status, summary, amendments, rejected alternatives, link back | parsed from the headings |
| every "Alternatives rejected" | `Rejected ideas.md` | parsed |
| `docs/reference/GOTCHAS.md` | mirrored | copied |
| module docstrings | `Code map.md` | Python first; other languages add an extractor when a project needs one |
| ADR `concepts` fields | notes in `Concepts/` listing the cards that carry them | derived |

The script only overwrites notes marked `generated: true`. It never touches a note without the marker.

## 7. `/handoff`

One procedure, run after a slice's commits land (`docs/sop/handoff.md`).

| Step | Who |
|---|---|
| run `vault-sync` and the lints | script |
| scan the slice's diff for a reusable pattern (cites file and lines; "none" is a valid result) | model drafts, owner accepts |
| draft `docs/HANDOFF.md` | model drafts, owner accepts |
| check the handoff with a fresh reader and the six questions | fresh session or another model |
| write the stats line (context size at close, slice number) | script |
| report: synced, lint failures, what awaits acceptance | script and model |

Commit and push stay the owner's call. Writing the ADR itself happens before the code and is not part of this.

## 8. Session guard

Optional adapter (a Claude Code mod). It shows context size in the status line, shows a band with a "Run /handoff"
button at a soft threshold (default 150k tokens) and a stronger one at a hard threshold (default 200k). It never blocks.
It may also show rate-limit windows and the closing checklist. Prototype in `adapters/claude/session-guard/`: validated, not yet checked drawing on
the desktop app. The hard git rules stay in a hook, not in the mod.

## 9. Project types

Language-neutral. `gates.conf` is `name | directory | command`. SOPs avoid assuming a UI, a server or a language.
Only the code-map extractor is language-specific.

## 10. Open questions

- Is `AGENTS.md` read by the tools you use? Add it to the no-trace list either way.
- Stylo uses a journal and a wiki, not `decisions/`: write an extractor or migrate it.
- Is `governs:` worth its upkeep?
- Does Sympose parse the chosen tag and list syntax? Test with sample notes before fixing the format.
- Does the mod draw on the desktop app, and can it read tokens as well as a percent of the window?
- Do structural tags add noise to Sympose's connections?
