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
- **Symptom:** the button draws and can be pressed, nothing happens, and the app log (`claude.ai-web.log`) has `engine surface: ui_press not handled` with the plugin and the key. The session guard's **Close slice** (since removed, ADR 001 amendment of 2026-10-20) did this for two days.
- **Cause:** the press handler threw, the engine skipped that hook, and the app reports a skipped handler as "not handled". The engine's notes list other causes (no press site, a stale drawing, a key mismatch), which sent the first look at the load path and at redraws. Here the cause was `$.prompt.submit({ text: '/handoff' })`: the engine refuses a prompt that begins with `/`.
- **Do this:** run a slash command with `$.command.run({ command, args })`. To tell a skipped handler from a stale drawing, press the button inside the plugin's own test (`claude plugin test <folder>`, with `$.ui.mount` and `press`), which prints the reason the hook was skipped; the app prints none. Hide a band only after the action has not thrown.

### A mod loaded by `CLAUDE_CODE_PLUGIN_DIRS` does not show in a session that was already open
- **Symptom:** a mod that validates and passes its tests is missing from another thread of the same app.
- **Cause:** the variable is read from the user settings' `env` when a session starts, so a thread opened before the setting was written never loads the folder. A new thread does.
- **Do this:** open a new session to check a mod, not the old one. Seen on 2026-10-27 with a status-line mod: a thread opened before the setting showed nothing, the next new thread showed it, so the desktop app does draw `$.ui.status`.

## 2. Recipes

### Validate and test a mod from inside a session
- **When:** `claude` is not on the session shell's PATH (the desktop app's shell), so `claude plugin validate <folder>` and `claude plugin test <folder>` report "command not found".
- **Do this:** run the app's own copy, `claude.app/Contents/MacOS/claude` under the app support folder's `claude-code/<version>/<hash>/` (the sibling `claude-code-vm` one is Linux and fails with "exec format error"). `validate` passes with an icon warning that does not matter for a local mod.
- **In a `*.test.ts`:** register every `on(...)` hook that stands for the engine before the first call on `$`; a second `on` after the test has used `$` throws, so a case that needs a second run is its own `test`.

### `strip()` on `git status --porcelain -z` corrupts the first path
- **Symptom:** a script that reads git's status takes the first changed file for a different path, or drops it, only when that file is modified and unstaged.
- **Cause:** the status line is two flag characters, a space and the path, and an unstaged change starts with a space (` M name`). A helper that strips the whole output removes that space from the first entry only, so every later entry parses and the first does not.
- **Do this:** strip the right end only (`rstrip`) or not at all. `scripts/close_slice.py` reads the status through `git()` for this reason, and a test pins a first entry that is modified and unstaged.

### A child session started with a stronger model runs on the parent's
- **Symptom:** a session started with `start_session` and a model above the parent's (Opus asked for from a Sonnet parent) answers as the parent's model.
- **Cause:** `start_session` ignores a model above the parent's.
- **Do this:** clear the child session, set the model with `set_session_model` (and the effort), confirm it with `get_session`, then send the brief. Measured once, on one ADR-sized task at medium effort: both models wrote about 1,800 words, the 5-hour meter moved about 3 points (Sonnet) and 4 (Opus), child context 100k and 118k tokens; Opus caught more cases (an edit to a note the owner may have hand-edited, a `git push` inside a script bypassing the git-safety hook). One pair proves little.
- **Measured again (2026-10-19), a correctness review and a pattern scan of one build by each model, at high effort, against defects known from the fixes made after it:** Opus found 6 of 7 and Sonnet 5 (two only as plausible), and Opus added two findings the fixes never covered (one was real: the ahead check read `@{upstream}`, a push goes to `@{push}`). The scans gave the same core patterns from both; Opus cited lines of the file where Sonnet cited lines of the diff, which the lint's cited-code check cannot use. Each run took 69k to 95k tokens. Two pairs: Opus is one or two findings better on a review, not a different class.

### Read a session's context size (ADR 015)
The report that measured session length and simulated context caps (ADR 001) was removed on 2026-10-20.

`adapters/claude/context-report/last_context.py` (ADR 015) prints one number, the context of the current session's last answer, from `$CLAUDE_CODE_SESSION_ID`; it exits 1 and prints nothing when it cannot name that transcript, and the stats row then shows a dash.

### Give Claude Code's `/goal` a goal its checker can see
```
/goal scripts/gates exits 0 and you show its output; stop after 15 turns
```
The checker reads only the conversation: it runs nothing and opens no files, so a goal is met only when its proof appears there. Name the command and ask for its output, and give a turn limit. Checked against code.claude.com/docs/en/goal on 2026-10-18.

### Fork the conversation in Claude Code
`/subtask` forks the conversation: a copy that knows everything so far and reuses the parent's prompt cache, for a side task that needs the conversation (`CODE_QUALITY_STANDARDS.md` §13). Before v2.1.212 the command was `/fork`. The name lives only here, never in a procedure, because it has already changed once. Checked against code.claude.com/docs/en/sub-agents on 2026-10-18.
