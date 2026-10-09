#!/usr/bin/env python3
"""The owner's own typed messages in a Claude Code session, for a capture's quote check (ADR 017).

Usage: python3 owner_messages.py [SESSION_ID] [--projects-dir DIR]

Prints the text the owner typed, one message after another, each separated from the next by a form feed on a line of its
own (the break that vault_write.py splits on). That includes a message sent while the assistant was working, which the
transcript stores as a queued command. Not printed: tool results (stored with the user role), subagent events, hook,
plugin and peer messages, and anything the assistant wrote, so a quote cannot be passed by text the assistant produced.
The transcript is found as in last_context.py (ADR 015): by session id, never the newest file.
Exit 0 with the text; exit 1 with nothing on stdout and one line on stderr when no transcript can be named.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "context-report"))
import last_context as lc  # noqa: E402

BREAK = "\n\f\n"


def flatten(content) -> str:
    if isinstance(content, list):
        content = "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    return content.replace("\f", " ").strip() if isinstance(content, str) else ""


def is_human(origin) -> bool:
    return isinstance(origin, dict) and origin.get("kind") == "human"


def typed_text(event: dict) -> str:
    """The text the owner typed in one transcript event, or "" if the event is anything else."""
    if event.get("isSidechain"):
        return ""
    if event.get("type") == "attachment":  # a message sent while the assistant was working is stored as a queued command
        a = event.get("attachment")
        return flatten(a.get("prompt")) if isinstance(a, dict) and a.get("type") == "queued_command" and is_human(a.get("origin")) else ""
    if event.get("type") != "user" or event.get("isMeta") or "toolUseResult" in event:
        return ""
    if event.get("origin") is not None and not is_human(event["origin"]):
        return ""
    return flatten((event.get("message") or {}).get("content"))


def owner_messages(path: str) -> list[str]:
    out = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if isinstance(event, dict) and typed_text(event):
                out.append(typed_text(event))
    return out


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("session_id", nargs="?", default=os.environ.get("CLAUDE_CODE_SESSION_ID"))
    ap.add_argument("--projects-dir", default=os.path.expanduser("~/.claude/projects"))
    a = ap.parse_args(argv)
    try:
        text = BREAK.join(owner_messages(lc.find_transcript(a.session_id, a.projects_dir)))
    except (LookupError, OSError) as e:
        print(f"owner_messages: {e}", file=sys.stderr)
        return 1
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
