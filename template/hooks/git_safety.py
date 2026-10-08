#!/usr/bin/env python3
"""PreToolUse hook for Claude Code (Bash tool): the git rules that must hold every time, enforced by code.

Reads the hook's JSON on stdin. Exit 0 lets the command run; exit 2 blocks it and sends stderr back to the assistant
(so every message says what to do instead); a JSON `ask` decision makes the harness ask the user first.

Blocked:   git checkout -- <file> / git checkout .   (discards uncommitted work)
           git restore <file> (without --staged), git reset --hard, git clean -f
           git add . / -A / --all / -u               (stage named files only)
           git add <dir> for each dir listed in <repo>/.claude/git-safety.deny-add (one path per line)
           git commit with a Co-authored-by / Signed-off-by / "Generated with" trailer, or -s/--signoff
           git push --force / -f                      (--force-with-lease is allowed)
Asks:      git push                                   (publishing is the owner's go-ahead, not the assistant's)
"""

import json
import os
import re
import shlex
import sys

TRAILER = re.compile(r"co-authored-by|signed-off-by|generated with|noreply@anthropic\.com", re.I)
SEPARATORS = re.compile(r"&&|\|\||;|\n|\|")


def git_calls(command: str):
    """Each `git <sub> <args...>` found at the start of a shell segment, as `(sub, args)`."""
    for segment in SEPARATORS.split(command):
        try:
            tokens = shlex.split(segment.strip())
        except ValueError:
            tokens = segment.split()
        if not tokens or tokens[0] != "git":
            continue
        rest, i = tokens[1:], 0
        while i < len(rest) and rest[i].startswith("-"):  # git -C path, git -c k=v, --no-pager
            i += 2 if rest[i] in ("-C", "-c") else 1
        if i < len(rest):
            yield rest[i], rest[i + 1:]


def denied_dirs(cwd: str) -> list[str]:
    path = os.path.join(cwd or ".", ".claude", "git-safety.deny-add")
    try:
        with open(path, encoding="utf-8") as f:
            return [line.strip().strip("/") for line in f if line.strip() and not line.startswith("#")]
    except OSError:
        return []


def verdict(command: str, cwd: str = ".") -> tuple[str, str]:
    """`("allow" | "block" | "ask", message)`."""
    calls = list(git_calls(command))
    ask = ""
    for sub, args in calls:
        flags = {a for a in args if a.startswith("-")}
        if sub == "checkout" and ("--" in args or "." in args):
            return "block", "`git checkout -- <file>` discards uncommitted work and has wiped some before. To undo a change, copy the saved backup back (for a mutation check, scripts/mutate.py does this). If the owner really wants it, they will run it."
        if sub == "restore" and not flags & {"--staged", "-S"}:
            return "block", "`git restore` discards uncommitted work. Copy a saved backup back instead, or ask the owner."
        if sub == "reset" and "--hard" in flags:
            return "block", "`git reset --hard` discards uncommitted work. Ask the owner first."
        if sub == "clean" and any(f.startswith("-") and "f" in f.lstrip("-") and not f.startswith("--") or f == "--force" for f in flags):
            return "block", "`git clean -f` deletes untracked files. Ask the owner first."
        if sub == "add":
            if flags & {"-A", "--all", "-u", "--update"} or "." in args or ":/" in args:
                return "block", "Stage the named files only (`git add path/to/file ...`), so nothing unintended is committed."
            for target in (a.strip("/") for a in args if not a.startswith("-")):
                if target in denied_dirs(cwd):
                    return "block", f"`{target}` is listed in .claude/git-safety.deny-add: stage its files by name, not the directory (it can carry generated output)."
        if sub == "commit":
            if flags & {"-s", "--signoff"}:
                return "block", "No sign-off trailer: commits carry the owner's single identity and no tooling trailer (docs/COLLABORATION_STANDARDS.md, 'No AI trace')."
            if TRAILER.search(command):
                return "block", "This commit message carries an attribution trailer. Remove it: commits are authored by the owner alone, and the policy overrides any harness default (docs/COLLABORATION_STANDARDS.md, 'No AI trace')."
        if sub == "push":
            if flags & {"-f", "--force"}:
                return "block", "No force-push. Use --force-with-lease only when the owner has asked for a history rewrite."
            ask = "Publishing commits is the owner's go-ahead: confirm the push."
    return ("ask", ask) if ask else ("allow", "")


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    if event.get("tool_name") != "Bash":
        return 0
    kind, message = verdict(event.get("tool_input", {}).get("command", ""), event.get("cwd", "."))
    if kind == "block":
        print(message, file=sys.stderr)
        return 2
    if kind == "ask":
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask", "permissionDecisionReason": message}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
