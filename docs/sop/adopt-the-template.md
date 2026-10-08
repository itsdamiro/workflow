# SOP: adopt the template in a project

For any assistant, with the owner. Works for a new project and for one moving onto the template. The scripts need only
`bash`, `git` and Python 3. Paths below are from the workflow repository's root.

## Once per machine

1. `template/install.sh --dry-run`, and read what it would change.
2. `template/install.sh`. It links the git-safety hook and two skills into the assistant's config folder and adds the hook
   to its settings (a backup is kept). The links point at this checkout; run it again if the repository moves.
3. For the machine-wide ignore of assistant files, see `template/README.md`.

## Per project

1. Create the repository (`git init -b main`) or open the existing one.
2. `template/adopt.sh <path-to-project> --name "<Project Name>"` (add `--gemini` for a `GEMINI.md`). It creates what is
   missing, never overwrites, and adds the ignore block for assistant files.
3. Fill the blanks in the contents page and `scripts/gates.conf`; run `scripts/gates` until it shows what you expect. A gate
   that cannot fail is not a gate.
4. List generated-output folders in `.claude/git-safety.deny-add`.
5. Write `docs/HANDOFF.md`, then run `docs/sop/check-a-handoff.md` on it.
6. Add the section of `template/CONTRIBUTING.snippet.md` to the project's `CONTRIBUTING.md`, with the owner's own identity.
7. Write the first decision record (`docs/sop/write-an-adr.md`) before the first code.

## A project that already has its own checklist or journal

Keep the old file until the new handoff passes its check. Order: hooks and gates first (additive), then the handoff and
`docs/reference/`, then shrink the contents page, then archive the old file outside the repository.

## Later

`template/adopt.sh <path-to-project> --check` reports how the project differs from the template, and changes nothing.
Differences in files meant to be filled in are expected; differences in shared files (standards, `scripts/gates`,
`scripts/mutate.py`) mean the project is behind.
