# workflow

A model-agnostic workflow for AI-assisted software projects: decisions, handoffs and a personal Obsidian vault of ideas, kept as plain markdown and small scripts.

**Status: working, still growing.** The specification, the decision records, the procedures and the vault scripts (the sync, the lint, the stats line) are written and tested. See "Usage" for what works today.

## What problem it solves

An AI assistant starts every session knowing nothing, and long sessions get expensive because the whole conversation is re-read on every message. This project makes three things cheap:

1. **Handing a session over.** One procedure, `/handoff`, closes a slice of work: it commits and pushes the slice, updates the vault, scans for patterns, writes the handoff, adds a stats row and reports. The option `check` adds a `/code-review` and an over-engineering review of the slice's diff before the commit and a fresh-reader test of the handoff.
2. **Remembering decisions.** Each project keeps decision records (ADRs); a script turns them into short, linked notes.
3. **Connecting ideas across projects and outside sources.** The notes live in one Obsidian vault, organised by project, concept and pattern, so a decision in one project can meet an idea from another.

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
template/install.sh             # links the git-safety hook and the skills into ~/.claude, writes the Gemini /handoff
                                # command into ~/.gemini/commands, and adds the hook to
                                # ~/.claude/settings.json (a backup of settings.json is kept)
```

The hook and the skills are for Claude Code, the command for Gemini CLI. Other tools follow the procedures in `docs/sop/` instead. For the machine-wide ignore of assistant files, see `template/README.md`.

### Start a new project

```bash
template/adopt.sh <path-to-project> --name "<Project Name>"     # add --gemini for GEMINI.md
template/adopt.sh <path-to-project> --check                     # later: report drift from the template, change nothing
```

It creates what is missing, never overwrites, adds the ignore block for assistant files, and installs a `commit-msg` git hook that refuses an attribution trailer, whatever tool made the commit. Then:

1. Fill in the blanks in `CLAUDE.md` and `scripts/gates.conf` (one check per line: `name | directory | command`), and run `scripts/gates` until it shows what you expect.
2. List generated-output folders in `.claude/git-safety.deny-add`; the hook then blocks `git add <folder>`.
3. Write `docs/HANDOFF.md` (under 60 lines, volatile facts only) and test it with `docs/sop/check-a-handoff.md`.
4. Add the section of `template/CONTRIBUTING.snippet.md` to the project's `CONTRIBUTING.md`, with your own identity.
5. Write the first decision record from `docs/decisions/TEMPLATE.md` before the first code.

### Put a project's decisions in the vault

```bash
python3 scripts/vault_sync.py <project-path> <vault-path> --dry-run   # say what would be written
python3 scripts/vault_sync.py <project-path> <vault-path>            # write it
```

Reads the project's committed `docs/decisions/` and writes read-only cards, a "Rejected ideas" note and a hub note under `<vault>/Projects/<name>/`. It also copies a committed `docs/reference/GOTCHAS.md`. Only notes marked `generated: true` are ever replaced; nothing is deleted. See ADR 009 (and ADR 016: the workflow reads documents, not code).

### Add a stats row at the close

```bash
python3 scripts/stats_line.py <project-path> <vault-path> --context-tokens <N>   # N is optional
python3 adapters/claude/context-report/last_context.py   # Claude Code: prints N for the current session, or exits 1 with nothing
```

Adds one row to `<vault>/Projects/<name>/<name> - Stats.md`: the day, the commit, the commits since the last row and their first and last subject. Earlier rows are never rewritten, and a second run on the same commit changes nothing. `/handoff` runs both. See ADR 014 and ADR 015.

### Check the vault

```bash
python3 scripts/vault_lint.py <vault-path>
```

Read-only. Errors (bad frontmatter, a missing field, a broken link, a bad tag, a concept with no note) exit 1; warnings (a note with no links, an orphan, no tags, a topic not yet listed in `Tags.md`) nudge and exit 0. See ADR 010.

### Each slice of work

Decide first (a decision record), then build with tests, then close the slice with `docs/CLOSING_A_SLICE.md`. The last step is the handoff: tell any assistant "follow `docs/sop/handoff.md`", then start the next session fresh from `docs/HANDOFF.md`.

### Planned (not built)

- The `/handoff` command for tools other than Claude Code (today they follow `docs/sop/handoff.md`), and the pattern scan and checklist pane in the session guard.

## Where to read

- `docs/SPEC.md`: the design.
- `docs/decisions/`: why each choice was made, with the alternatives rejected.
- `docs/sop/`: the step-by-step procedures.

## Not in this repository

No personal notes, transcripts or prompts. The vault is separate and personal; examples here are synthetic.
