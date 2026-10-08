# Gotchas and recipes

> The durable half of the handoff: traps that have already cost time, and the exact recipe for each recurring chore.
> One entry per trap, each with the symptom, the cause and the fix. When an entry stops being true, delete it.

## Contents
1. Traps
2. Recipes

## 1. Traps

### Counting screenshot reads by their text overstates reading
- **Symptom:** a transcript measurement says reading cost about four times what it really did.
- **Cause:** an image read is stored as base64 text, so characters divided by four counts the encoding, not what the
  model is charged for the image.
- **Do this:** classify reads by file extension first; count image reads by number, not by characters.

### The git-safety hook is a guard against accidents, not a lock
- **Symptom:** a command the policy forbids runs without the hook stopping it.
- **Cause:** the hook reads the first word of each shell segment and long flags. These slip through (tested): a leading
  `VAR=1 git ...`, `env git ...`, `bash -c 'git add .'`, a combined short flag such as `git commit -sm x`, and a message
  read from a file (`git commit -F msg.txt`, never scanned for a trailer). Input that is not valid JSON lets the command run.
- **Do this:** do not rely on it for the no-trailer rule alone; check `git log --format=%B` before a push. Hardening
  (skip env prefixes, unwrap `env` and `bash -c`, split combined flags, scan the `-F` file) is waiting on the owner.

### `gates` used to skip a last line with no trailing newline
- **Symptom:** a failing gate at the end of `gates.conf` was never run, and the script exited 0.
- **Cause:** `read` returns failure on a final line without a newline. Fixed in `template/scripts/gates`; projects
  adopted earlier keep the old copy until they are updated (`adopt.sh --check` shows `differs`). `template/scripts/test_gates.sh`
  guards it (a gate here); it fails on the old script. Sympose was updated 2026-10-08.
- **Do this:** update the project's `scripts/gates` from the template.

### `echo ====…` fails in zsh
- **Symptom:** `zsh: ===== not found`, and the rest of the command line does not run.
- **Cause:** zsh expands a word that starts with `=` as a command lookup.
- **Do this:** quote separators (`echo '--- title'`) or use `printf`.

## 2. Recipes

### Re-run the context measurement (ADR 001)
```
python3 adapters/claude/context-report/context_report.py ~/.claude/projects/<project-folder>
```
Prints session length, context size and what a cap of 150k, 200k and 300k would save (`--caps`, `--restart-extra`).
Aggregates only. Claude Code transcripts only, main thread only. It does not reproduce ADR 001's split of reads by kind;
count image reads by number when you add that.
