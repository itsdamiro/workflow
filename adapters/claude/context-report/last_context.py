#!/usr/bin/env python3
"""The context size of a Claude Code session's last answer, for the stats line (ADR 015).

Usage: python3 last_context.py [SESSION_ID] [--projects-dir DIR]

Prints one integer: the context (new, cache-written and cache-read input tokens, as in context_report.py) the session's
last main-thread answer was read over. SESSION_ID defaults to $CLAUDE_CODE_SESSION_ID and DIR to ~/.claude/projects. The
transcript is the one file <SESSION_ID>.jsonl directly under a folder of DIR; it is never guessed from the newest file.
Exit 0 with the number; exit 1 with nothing on stdout and one line on stderr when no number can be named.
"""

import argparse
import glob
import os
import re
import sys

import context_report as cr

UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)


def find_transcript(session_id: str | None, projects_dir: str) -> str:
    """The path of the session's transcript; raises LookupError saying why there is none."""
    if not session_id:
        raise LookupError("no session id (CLAUDE_CODE_SESSION_ID is not set)")
    if not UUID.match(session_id):
        raise LookupError("the session id is not a UUID")
    found = glob.glob(os.path.join(glob.escape(projects_dir), "*", session_id + ".jsonl"))
    if not found:
        raise LookupError("no transcript for the session id")
    if len(found) > 1:
        raise LookupError("more than one transcript for the session id")
    return found[0]


def last_context(session_id: str | None, projects_dir: str) -> int:
    ctx = cr.session_contexts(find_transcript(session_id, projects_dir))
    if not ctx:
        raise LookupError("the transcript has no answer with usage")
    return ctx[-1]


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("session_id", nargs="?", default=os.environ.get("CLAUDE_CODE_SESSION_ID"))
    ap.add_argument("--projects-dir", default=os.path.expanduser("~/.claude/projects"))
    a = ap.parse_args(argv)
    try:
        print(last_context(a.session_id, a.projects_dir))
    except (LookupError, OSError) as e:
        print(f"last_context: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
