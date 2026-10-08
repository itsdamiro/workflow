# workflow

A model-agnostic workflow for AI-assisted software projects: decisions, handoffs and a personal Obsidian vault of
ideas, kept as plain markdown and small scripts.

**Status: design phase.** The specification, the first decision records and the procedures are written; the vault
scripts are not built yet. See "Usage" for what works today.

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

## Usage

The project template, with its scripts, lives in `template/`. Everything below needs only `bash`, `git` and Python 3.

### Once per machine

```bash
template/install.sh --dry-run   # shows what would change; changes nothing
template/install.sh             # links the git-safety hook and two skills into ~/.claude, and adds the hook to
                                # ~/.claude/settings.json (a backup of settings.json is kept)
```

This is for Claude Code. Other tools follow the procedures in `docs/sop/` instead. For the machine-wide ignore of
assistant files, see `template/README.md`.

### Start a new project

```bash
template/adopt.sh <path-to-project> --name "<Project Name>"     # add --gemini for GEMINI.md
template/adopt.sh <path-to-project> --check                     # later: report drift from the template, change nothing
```

It creates what is missing, never overwrites, and adds the ignore block for assistant files. Then:

1. Fill in the blanks in `CLAUDE.md` and `scripts/gates.conf` (one check per line: `name | directory | command`), and run
   `scripts/gates` until it shows what you expect.
2. List generated-output folders in `.claude/git-safety.deny-add`; the hook then blocks `git add <folder>`.
3. Write `docs/HANDOFF.md` (under 60 lines, volatile facts only) and test it with `docs/sop/check-a-handoff.md`.
4. Add the section of `template/CONTRIBUTING.snippet.md` to the project's `CONTRIBUTING.md`, with your own identity.
5. Write the first decision record from `docs/decisions/TEMPLATE.md` before the first code.

### Each slice of work

Decide first (a decision record), then build with tests, then close the slice with `docs/CLOSING_A_SLICE.md`. The last
step is the handoff: tell any assistant "follow `docs/sop/handoff.md`", then start the next session fresh from
`docs/HANDOFF.md`.

### Planned (not built)

- `scripts/vault-sync` and `scripts/vault-lint`: turn each project's decision records into linked notes in the vault.
- `/handoff` as one command, and a reminder to use it when a session gets long (adapters for specific tools).
- `adopt.sh` carrying the decision-record template and the procedures into new projects.

## Where to read

- `docs/SPEC.md`: the design.
- `docs/decisions/`: why each choice was made, with the alternatives rejected.
- `docs/sop/`: the step-by-step procedures.

## Not in this repository

No personal notes, transcripts or prompts. The vault is separate and personal; examples here are synthetic.
