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

### `strip()` on `git status --porcelain -z` corrupts the first path
- **Symptom:** a script that reads git's status takes the first changed file for a different path, or drops it, only when that file is modified and unstaged.
- **Cause:** the status line is two flag characters, a space and the path, and an unstaged change starts with a space (` M name`). A helper that strips the whole output removes that space from the first entry only, so every later entry parses and the first does not.
- **Do this:** strip the right end only (`rstrip`) or not at all. `scripts/close_slice.py` reads the status through `git()` for this reason, and a test pins a first entry that is modified and unstaged.

### A child session started with a stronger model runs on the parent's
- **Symptom:** a session started with `start_session` and a model above the parent's (Opus asked for from a Sonnet parent) answers as the parent's model.
- **Cause:** `start_session` ignores a model above the parent's.
- **Do this:** clear the child session, set the model with `set_session_model` (and the effort), confirm it with `get_session`, then send the brief. Measured once, on one ADR-sized task at medium effort: both models wrote about 1,800 words, the 5-hour meter moved about 3 points (Sonnet) and 4 (Opus), child context 100k and 118k tokens; Opus caught more cases (an edit to a note the owner may have hand-edited, a `git push` inside a script bypassing the git-safety hook). One pair proves little.
- **Measured again (2026-10-19), two read-only subagents per task at high effort, on the diff of the ADR 020 build, whose real defects are known from the fixes made after it:** the correctness review found 5 of 7 for Sonnet (2 of them only as PLAUSIBLE, and the failing `git status` was missed) and 6 of 7 for Opus (all stated as confirmed, one backed by a run), and Opus added two findings the fixes never covered (a bisect in progress, and the ahead check reading `@{upstream}` where a push goes to `@{push}`); both missed the `generated: True` spelling. The pattern scan gave Sonnet 4 candidates and Opus 6, the same core in both (commit by named paths, preconditions before an automated commit, the vault as its own repository, `-z` parsing), Opus with one more that was real (measure ahead before the commit) and Sonnet with the better advice to drop and merge; Sonnet cited line numbers of the diff, not of the file, which the lint's cited-code check cannot use. Each run took 69k to 95k tokens (the Opus review the most, and the slowest at about 3 minutes against 2). Two pairs: Opus finds more on a review and cites checkably on a scan; the gap is one or two findings, not a different class.

### Re-run the context measurement (ADR 001)
```
python3 adapters/claude/context-report/context_report.py ~/.claude/projects/<project-folder>
```
Prints session length, context size and what a cap of 150k, 200k and 300k would save (`--caps`, `--restart-extra`). Aggregates only. Claude Code transcripts only, main thread only. It does not reproduce ADR 001's split of reads by kind; count image reads by number when you add that.

`adapters/claude/context-report/last_context.py` (ADR 015) prints one number, the context of the current session's last answer, from `$CLAUDE_CODE_SESSION_ID`; it exits 1 and prints nothing when it cannot name that transcript, and the stats row then shows a dash.

### Give Claude Code's `/goal` a goal its checker can see
```
/goal scripts/gates exits 0 and you show its output; stop after 15 turns
```
The checker reads only the conversation: it runs nothing and opens no files, so a goal is met only when its proof appears there. Name the command and ask for its output, and give a turn limit. Checked against code.claude.com/docs/en/goal on 2026-10-18.

### Fork the conversation in Claude Code
`/subtask` forks the conversation: a copy that knows everything so far and reuses the parent's prompt cache, for a side task that needs the conversation (`CODE_QUALITY_STANDARDS.md` §13). Before v2.1.212 the command was `/fork`. The name lives only here, never in a procedure, because it has already changed once. Checked against code.claude.com/docs/en/sub-agents on 2026-10-18.
