# session-guard (Claude Code mod)

Advisory only: it never blocks anything. It shows the context size and the five-hour rate-limit use in the status line,
and when the context passes a soft limit (default 150k tokens) it shows a band above the prompt with two buttons:
**Close slice** submits a prompt asking the assistant to close the slice and rewrite the handoff (it does not commit or
push); **Later** hides the band until the next level (hard limit, default 200k). A toast warns when a rate-limit window
passes 80%. Settings (`softTokens`, `hardTokens`, `limitPercent`, `handoffPrompt`) are rows in the config menu.

This is an adapter (ADR 002): the procedure it points at is `docs/sop/handoff.md`; nothing here adds behaviour the
procedure does not describe.

## Use

```bash
claude --plugin-dir adapters/claude/session-guard     # load it for one session
claude plugin validate adapters/claude/session-guard  # check it without loading
```

In the desktop app, copy the folder into the session's mods folder and answer "Enable hot reloading" (the mod
reloads when edited). To see the band without a long session, set `softTokens` low (for example 30000).

## Status

Validated (`claude plugin validate` passes). Not yet checked drawing on the desktop app.
