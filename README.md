# workflow

A model-agnostic workflow for AI-assisted software projects: decisions, handoffs and a personal Obsidian vault of
ideas, kept as plain markdown and small scripts.

**Status: design phase.** The specification and the first decision records are written; the scripts are not built yet.

## What problem it solves

An AI assistant starts every session knowing nothing, and long sessions get expensive because the whole conversation
is re-read on every message. This project makes three things cheap:

1. **Handing a session over.** One procedure, `/handoff`, closes a slice of work: it writes the handoff, checks that a
   fresh reader could pick it up, and updates the vault.
2. **Remembering decisions.** Each project keeps decision records (ADRs); a script turns them into short, linked notes.
3. **Connecting ideas across projects and outside sources.** The notes live in one Obsidian vault, organised by
   project, concept and pattern, so a decision in one project can meet an idea from another.

## How it stays portable

Three layers, outermost last. The system works with only the first two.

| Layer | What it is | Works with |
|---|---|---|
| Files and scripts | Markdown with YAML frontmatter; plain shell or Python standard library | any tool, or a human |
| Procedures | `docs/sop/*.md`, steps any assistant can follow | any model |
| Adapters | A few lines per tool that say "follow this procedure" (a Claude skill and mod, a Gemini command, ...) | one tool each, optional |

## Where to read

- `docs/SPEC.md`: the design.
- `docs/decisions/`: why each choice was made, with the alternatives rejected.
- `docs/sop/`: the step-by-step procedures.

## Not in this repository

No personal notes, transcripts or prompts. The vault is separate and personal; examples here are synthetic.
