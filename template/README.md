# coding-standards: the project template

How every project of this machine is run with an AI assistant: the standards, the handoff, the way a slice is closed, and the scripts and hooks that enforce what wording cannot. Generalized from Sympose and Stylo (2026-09, 2026-10) and from Anthropic's skill-authoring practices (progressive disclosure, checklists with go-back lines, feedback loops, enforce the never-break rules in code).

Version: see `VERSION` (copied into each project as `docs/.template-version`).

## The three layers

| Layer | Lives in | Holds |
|---|---|---|
| Machine-wide, once | `~/.claude` (linked from here by `install.sh`), `~/.gemini/commands` (written by it) | the git-safety hook, the skills, the Gemini `/handoff` command |
| Template, per project | copied by `adopt.sh` | `CLAUDE.md` (a contents page), the standards, the handoff, the closing checklist, `scripts/gates`, `scripts/mutate.py`, `scripts/md_wrap_check.py`, `scripts/adr_check.py`, the record template and the vault conventions |
| Project facts | the project itself | its gate commands, its rules, its decisions, its handoff |

## What is in here

```
coding-standards/
├── VERSION
├── install.sh                 once per machine: links hook + skills, writes the Gemini command, adds the hook to ~/.claude/settings.json
├── adopt.sh                   per project: scaffold the template; --check reports drift. Never overwrites.
├── CLAUDE.template.md         → <project>/CLAUDE.md  (contents page, under 40 lines)
├── GEMINI.template.md         → <project>/GEMINI.md  (same, for Gemini)
├── CONTRIBUTING.snippet.md    → paste into <project>/CONTRIBUTING.md (the committed home of the no-trace policy)
├── docs/
│   ├── COLLABORATION_STANDARDS.md   how the assistant behaves; where each kind of thing is written
│   ├── CODE_QUALITY_STANDARDS.md    the engineering process; §12 is "enforce by code, not wording"
│   ├── CLOSING_A_SLICE.md           the checklist, with "return to" lines
│   ├── HANDOFF.template.md          → docs/HANDOFF.md: volatile facts only, under 60 lines
│   ├── VAULT_CONVENTIONS.md         names, fields, tags and links, so the owner's vault can read the records
│   ├── decisions/TEMPLATE.md        the decision-record template (frontmatter, summary, sections)
│   ├── sop/write-an-adr.md          write a decision record before the code
│   ├── sop/rename-a-concept.md      name a concept, and rename one without breaking records
│   ├── sop/check-a-handoff.md       test a handoff with a fresh reader (a copy of docs/sop/check-a-handoff.md)
│   └── reference/GOTCHAS.template.md  → docs/reference/GOTCHAS.md: traps and recipes (the durable half)
├── scripts/
│   ├── gates (+ gates.conf.template)  every gate, one line each, failures show their last lines
│   ├── mutate.py                      mutation check for new tests; restores from a copy, never git
│   ├── md_wrap_check.py               fails on hard-wrapped Markdown prose (a gate; test_md_wrap_check.py beside it)
│   └── adr_check.py                   fails on a decision record without frontmatter, a summary or an index row (a gate; ADR 012)
├── commands/
│   └── handoff.toml           Gemini `/handoff`: injects docs/sop/handoff.md with a shell `cat` (an `@{}` path must be inside the workspace); install.sh fills in this checkout's path
├── hooks/
│   ├── git_safety.py          PreToolUse hook; blocks the git commands that lose work or leave a trace
│   └── test_git_safety.py     both paths of every rule (python3 -m unittest discover -s hooks)
└── skills/
    ├── closing-a-slice/       runs the project's CLOSING_A_SLICE.md
    ├── checking-a-handoff/    tests a handoff with a fresh reader and six questions
    └── handoff/               `/handoff`: follows docs/sop/handoff.md (vault sync and lint, pattern scan, new handoff; `check` adds a code review, an over-engineering review and a fresh-reader test)
```

The `.template.md` suffixes are deliberate: the machine-wide gitignore (`.gitignore_global`) excludes a literal `CLAUDE.md` / `GEMINI.md`, which is what keeps AI-tooling config out of every repository. `adopt.sh` renames them. To have the same machine-wide ignore, point git at a global ignore file (`git config --global core.excludesFile ~/.gitignore_global`) and put the no-trace block from `CONTRIBUTING.snippet.md` in it. Without one, `adopt.sh` still adds the block to each project's own `.gitignore`.

## Using it

**Once per machine**

```
./install.sh --dry-run     # see what changes
./install.sh               # link the hook and skills, write the Gemini command, add the hook to ~/.claude/settings.json (a backup is kept)
```

**A new project, or one moving onto the template**

```
./adopt.sh <path-to-project> --name "<Project Name>"      # add --gemini for GEMINI.md
```

It creates what is missing and reports what differs; it never overwrites. Then:

1. Fill the blanks in `CLAUDE.md` and `scripts/gates.conf`; run `scripts/gates` until it shows what you expect.
2. List generated-output directories in `.claude/git-safety.deny-add` (the hook then blocks `git add <dir>`).
3. Write `docs/HANDOFF.md`, and run the `checking-a-handoff` skill on it.
4. Add the section of `CONTRIBUTING.snippet.md` to the project's `CONTRIBUTING.md`.
5. A project that already has its own versions of the standards keeps them; `adopt.sh --check` shows how they differ from the template, and anything worth generalizing comes back here (below).

**A project that already has a checklist or journal.** Move it in this order, keeping the old file until the new handoff passes its check: hooks and gates first (additive, invisible when behaving), then the handoff and `docs/reference/`, then shrink `CLAUDE.md` to a contents page, then archive the old file outside the repo.

## The no-trace policy

Standing across every repository (see `docs/COLLABORATION_STANDARDS.md`): one author identity, no attribution trailers, assistant and editor tooling never committed. The hook enforces the trailer rule even when a harness tries to add one. Because `.claude/` is ignored machine-wide, per-project hook settings (`.claude/git-safety.deny-add`) are local to the machine by design.

## Keeping it in sync

These files are the source of truth; a project's copies are snapshots, not forks. When a project's work finds something worth generalizing, change it here first (bump `VERSION`), then `./adopt.sh <project> --check` in each active project and merge what differs by hand. Run the hook tests after any change to the hook.
