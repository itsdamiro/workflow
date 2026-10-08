---
type: decision
status: accepted
date: 2026-10-09
projects: [workflow]
concepts: [Handoff, Session length]
amends: [014]
supersedes: []
tags: [type/decision, status/accepted, project/workflow, topic/vault, topic/observability]
---

# 015 — The Claude adapter reads the context size from the session's own transcript, and gives a dash when it cannot

> **Summary.** A small script next to `context_report.py` prints the context size of the current session's last answer, found by the session id Claude Code puts in the environment, and `/handoff` passes it to the stats line. When it cannot name that transcript it prints nothing and the row shows a dash. It costs one more script and a dependency on Claude Code's transcript format.

## Context

ADR 014 made the stats line take `--context-tokens N` from the adapter and left open where the adapter finds N and which transcript it reads. Without it every row shows a dash, and the line's purpose, tuning the guard's thresholds against evidence (ADR 001), is not served.

Facts checked on 2026-10-09:

- Claude Code writes each session to `~/.claude/projects/<folder named from the working directory>/<session id>.jsonl`, one JSON object per line. The session id is in the environment variable `CLAUDE_CODE_SESSION_ID`, and in this session it names the newest file in that folder.
- A main-thread `assistant` event carries `message.usage`; `adapters/claude/context-report/context_report.py` already defines a context as `input_tokens + cache_read_input_tokens + cache_creation_input_tokens` and counts each message id once, skipping `isSidechain` events (subagents).
- The folder name is derived from the path, so building it means copying Claude Code's own encoding; a session id is a UUID, so searching every project folder for `<id>.jsonl` needs no encoding.
- Another session in the same project can write at the same time, so "the newest file" can be the wrong session.

## Decision

1. **The script.** `adapters/claude/context-report/last_context.py [SESSION_ID] [--projects-dir DIR]`, Python standard library. `SESSION_ID` defaults to `$CLAUDE_CODE_SESSION_ID`, `DIR` to `~/.claude/projects`. It prints one integer, the context of the last main-thread assistant message that has usage, and exits 0.
2. **Which transcript.** The one file named `<SESSION_ID>.jsonl` in any folder directly under `DIR`. The id must look like a UUID before it is used in a path. No id, no such file, more than one such file, or no message with usage: print nothing on stdout, one line on stderr saying which, exit 1. It never falls back to the newest file.
3. **Reading.** The message-reading in `context_report.py` is moved into a function both scripts call (`session_contexts(path)`); `load_sessions` keeps its behaviour and its tests. The new script does not apply the five-message minimum: a short session still has a size.
4. **Output only.** The script prints a number and no prompt, path or file content, as the report does.
5. **The step.** `docs/sop/handoff.md` step 6 says: with Claude Code, run the script and pass its output as `--context-tokens`; if it exits 1, run the stats line without the option. Another assistant passes its own number or none, as ADR 014 already says.
6. **Tests** in `adapters/claude/context-report/test_context_report.py`, already a gate: the last message is chosen, a sidechain or usage-less message is not, a missing, duplicated or malformed id gives exit 1 and no output, and a wrong-session file in the same folder is never read. Each rule is checked against a weakened script with `scripts/mutate.py`.
7. **The documents follow.** ADR 014's open items lose the adapter; SPEC §6 and §7 name the script; `docs/reference/GOTCHAS.md` lists it beside the report.

## Consequences

Each `/handoff` run under Claude Code records a number. The number is the size of the context the last answer was read over, so it is slightly under the size at the moment of the close (the handoff's own last steps are not in it), and it includes cached tokens, as the report does. It is the same measure the guard's thresholds are written in, so rows compare with the thresholds directly.

It depends on the transcript layout and on the environment variable, which Claude Code does not promise; when either changes the script exits 1 and rows show dashes, which is visible and harmless. After a compaction the last message's context is the compacted size, which is what the next answer is read over.

Left open: a config directory other than `~/.claude` (`--projects-dir` covers it by hand; reading `CLAUDE_CONFIG_DIR` is a small change when it first matters), and other assistants' adapters.

## Alternatives rejected

- **The newest `.jsonl` in the project's folder.** Needs no id, but picks the wrong session when two run at once, and a wrong number in a history that is meant for tuning is worse than a dash. Would be right if the id were not available.
- **The guard mod passes the number.** The mod already sees the token count, but it runs only in the app, cannot be loaded or tested from a session (HANDOFF), and would tie a stats row to one UI. Would be right if the guard became the place every adapter reads state from.
- **Building the folder name from the working directory.** Direct, but copies Claude Code's encoding, which can change and differs for paths with dots or non-ASCII characters. Would be right if the search below were too slow, which at a few hundred folders it is not.
- **Making `stats_line.py` read the transcript.** Rejected in ADR 014 (Claude-only against ADR 002); nothing has changed.
- **Counting output tokens too.** The next answer is read over the output as well, but the guard's thresholds are written in input context; mixing the two would break the comparison. Would be right if a threshold were ever set on total size.

**Accepted** by the owner on 2026-10-09, in chat, as written.
