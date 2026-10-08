# session-guard (Claude Code mod)

Advisory only: it never blocks anything. It shows the context size and the five-hour rate-limit use in the status line, and when the context passes a soft limit (default 150k tokens) it shows a band above the prompt with three buttons: **Close slice** submits `/handoff`, the same command you would type, so the button and the command run one procedure (`docs/sop/handoff.md`, through the `handoff` skill) and a change to it reaches both; the procedure commits the slice's named files and pushes (ADR 005 amendment), so pressing the button is the go-ahead for that; **Close + check** submits `/handoff check`, which adds the slow checks (a `/code-review` and an over-engineering review of the diff before the commit, and the fresh-reader test); **Later** hides the band until the next level (hard limit, default 200k). A toast warns when a rate-limit window passes 80%. Settings (`softTokens`, `hardTokens`, `limitPercent`, `handoffPrompt`, `handoffCheckPrompt`) are rows in the config menu.

This is an adapter (ADR 002): the procedure it points at is `docs/sop/handoff.md`; nothing here adds behaviour the procedure does not describe.

## Use

```bash
claude --plugin-dir adapters/claude/session-guard     # load it for one session
claude plugin validate adapters/claude/session-guard  # check it without loading
```

In the desktop app, copy the folder into the session's mods folder and answer "Enable hot reloading" (the mod reloads when edited). To see the band without a long session, set `softTokens` low (for example 30000).

## Status

Validated on an earlier version (`claude plugin validate` passed); not run again since the buttons changed. Not yet checked drawing on the desktop app, nor that the button's `/handoff` starts the skill as typed text does. If it only sends the literal text, set `handoffPrompt` to "Follow docs/sop/handoff.md" (and `handoffCheckPrompt` to the same plus "and run its check step") in the config menu. A value already saved in the config menu overrides the default: reset it. Raise `version` in `.claude-plugin/plugin.json` with any change to that file, so the host loads the new copy (not checked: the host may reload without it).
