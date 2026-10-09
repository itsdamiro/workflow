# Gotchas and recipes

> The durable half of the handoff: traps that have already cost time, and the exact recipe for each recurring chore. One entry per trap, each with the symptom, the cause and the fix. When an entry stops being true, delete it.

## Contents
1. Traps
2. Recipes

## 1. Traps

### Counting screenshot reads by their text overstates reading
- **Symptom:** a transcript measurement says reading cost about four times what it really did.
- **Cause:** an image read is stored as base64 text, so characters divided by four counts the encoding, not what the model is charged for the image.
- **Do this:** classify reads by file extension first; count image reads by number, not by characters.

### The git-safety hook is a guard against accidents, not a lock
- **Symptom:** a command the policy forbids runs without the hook stopping it.
- **Cause:** the hook reads the command's text, not what it will do. It reads through leading `VAR=1`, `env`, `sudo` and similar wrappers, `bash -c '...'` and `eval "..."` strings, a leading `(` or `{`, combined short flags (`-sm`, `-fu`) and the file given to `git commit -F`. It still misses a command built at run time (`$(...)`, a script file), a wrapper with an option that takes a value (`sudo -u x git ...`), `git -C <other> commit -F <relative file>`, and `--no-verify`. Input that is not valid JSON lets the command run, on purpose: a guard that can wedge every command is worse than a gap.
- **Do this:** the backstop for the no-trailer rule is git itself: `template/git-hooks/commit-msg` (installed by `adopt.sh`) sees the final message however it was given. `git commit --no-verify` skips any git hook. Before a push, `git log --format=%B` shows what is about to go out.

### `gates` used to skip a last line with no trailing newline
- **Symptom:** a failing gate at the end of `gates.conf` was never run, and the script exited 0.
- **Cause:** `read` returns failure on a final line without a newline. Fixed in `template/scripts/gates`; projects adopted earlier keep the old copy until they are updated (`adopt.sh --check` shows `differs`). `template/scripts/test_gates.sh` guards it (a gate here); it fails on the old script. Sympose was updated 2026-10-08.
- **Do this:** update the project's `scripts/gates` from the template.

### `echo ====…` fails in zsh
- **Symptom:** `zsh: ===== not found`, and the rest of the command line does not run.
- **Cause:** zsh expands a word that starts with `=` as a command lookup.
- **Do this:** quote separators (`echo '--- title'`) or use `printf`.

### In zsh an unquoted `${N:+--opt $N}` passes the option and its value as one argument
- **Symptom:** `close_slice.py: error: unrecognized arguments: --context-tokens 172415`, with the option and its value printed as one word.
- **Cause:** zsh does not split an unquoted expansion on spaces (bash does), so `${N:+--context-tokens $N}` is a single argument.
- **Do this:** write the option out (`--context-tokens "$N"`), or branch with `if [ -n "$N" ]`. It hit two closes on 2026-10-09.

### A mod's button does nothing, and the app logs `ui_press not handled`
- **Symptom:** the button draws and can be pressed, nothing happens, and the app log (`claude.ai-web.log`) has `engine surface: ui_press not handled` with the plugin and the key. The session guard's **Close slice** did this for two days (fixed in 0.3.0).
- **Cause:** the press handler threw, the engine skipped that hook, and the app reports a skipped handler as "not handled". The engine's notes list other causes (no press site, a stale drawing, a key mismatch), which sent the first look at the load path and at redraws. Here the cause was `$.prompt.submit({ text: '/handoff' })`: the engine refuses a prompt that begins with `/`.
- **Do this:** run a slash command with `$.command.run({ command, args })`. To tell a skipped handler from a stale drawing, press the button inside the plugin's own test (`claude plugin test <folder>`, with `$.ui.mount` and `press`), which prints the reason the hook was skipped; the app prints none. Hide a band only after the action has not thrown.

## 2. Recipes

### Re-run the context measurement (ADR 001)
```
python3 adapters/claude/context-report/context_report.py ~/.claude/projects/<project-folder>
```
Prints session length, context size and what a cap of 150k, 200k and 300k would save (`--caps`, `--restart-extra`). Aggregates only. Claude Code transcripts only, main thread only. It does not reproduce ADR 001's split of reads by kind; count image reads by number when you add that.

`adapters/claude/context-report/last_context.py` (ADR 015) prints one number, the context of the current session's last answer, from `$CLAUDE_CODE_SESSION_ID`; it exits 1 and prints nothing when it cannot name that transcript, and the stats row then shows a dash.
