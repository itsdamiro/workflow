# session-guard (Claude Code mod)

Advisory only: it never blocks anything. It shows the context size and the five-hour rate-limit use in the status line, and when the context passes a soft limit (default 150k tokens) it shows a band above the prompt with two buttons: **Close slice** submits `/handoff`, the same command you would type, so the button and the command run one procedure (`docs/sop/handoff.md`, through the `handoff` skill) and a change to it reaches both; the procedure commits the slice's named files and pushes (ADR 005 amendment), so pressing the button is the go-ahead for that, and it is the light close, without the two reviews and the fresh-reader test, which `/handoff full` adds (ADR 005, amendment of 2026-10-09); **Later** hides the band until the next level (hard limit, default 200k). A toast warns when a rate-limit window passes 80%. Settings (`softTokens`, `hardTokens`, `limitPercent`, `handoffPrompt`) are rows in the config menu.

This is an adapter (ADR 002): the procedure it points at is `docs/sop/handoff.md`; nothing here adds behaviour the procedure does not describe.

## Use

```bash
claude --plugin-dir adapters/claude/session-guard     # load it for one session
claude plugin validate adapters/claude/session-guard  # check it without loading
```

In the desktop app, copy the folder into the session's mods folder and answer "Enable hot reloading" (the mod reloads when edited). To see the band without a long session, set `softTokens` low (for example 30000).

## Status

Validated with `claude plugin validate`, and `hooks/close-button.test.ts` presses **Close slice** on the terminal and desktop surfaces (`claude plugin test adapters/claude/session-guard`; the `claude` binary is not on the PATH in the desktop app, so it is not a gate). The button once did nothing: the engine refuses `$.prompt.submit` with text that begins with `/`, the press handler was skipped, and the app logged `ui_press not handled`; the button now runs the command with `$.command.run`, and hides the band only after that has not thrown. Not yet checked: that `$.command.run` starts the `handoff` skill exactly as typed text does. If `handoffPrompt` is set to text that does not begin with `/` (for example "Follow docs/sop/handoff.md"), it is submitted as a prompt. After a plugin reload the desktop app may show no band until the app itself is reloaded. A value already saved in the config menu overrides the default: reset it. Raise `version` in `.claude-plugin/plugin.json` with any change to that file, so the host loads the new copy (not checked: the host may reload without it).
