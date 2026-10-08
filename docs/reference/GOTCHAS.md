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
- **Cause:** the hook reads the command's text, not what it will do. It reads through leading `VAR=1`, `env`, `sudo` and
  similar wrappers, `bash -c '...'` and `eval "..."` strings, a leading `(` or `{`, combined short flags (`-sm`, `-fu`) and
  the file given to `git commit -F`. It still misses a command built at run time (`$(...)`, a script file), a wrapper with
  an option that takes a value (`sudo -u x git ...`), `git -C <other> commit -F <relative file>`, and `--no-verify`.
  Input that is not valid JSON lets the command run, on purpose: a guard that can wedge every command is worse than a gap.
- **Do this:** the backstop for the no-trailer rule is git itself: `template/git-hooks/commit-msg` (installed by
  `adopt.sh`) sees the final message however it was given. `git commit --no-verify` skips any git hook. Before a push,
  `git log --format=%B` shows what is about to go out.

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
