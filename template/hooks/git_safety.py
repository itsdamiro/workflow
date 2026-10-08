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
Reads through: leading VAR=value words and env/command/sudo/exec/time/nohup/nice, bash|sh|zsh -c '...' and eval "...",
           a leading ( or {, combined short flags (-sm, -fu), and the file given to `git commit -F` / `--file`.
Not read:  a command built at run time ($(...), a script file), a wrapper that takes an option with a value (`sudo -u x`).
Malformed input lets the command run: a guard that can wedge every command would be worse than a gap.
"""

import json
import os
import re
import shlex
import sys

TRAILER = re.compile(r"co-authored-by|signed-off-by|generated with|noreply@anthropic\.com", re.I)
TRAILER_IN_FILE = re.compile(r"^(co-authored-by|signed-off-by):|generated with|noreply@anthropic\.com", re.I | re.M)
SEPARATORS = re.compile(r"&&|\|\||;|\n|\|")
ENV_ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
WRAPPERS = {"env", "command", "sudo", "exec", "time", "nohup", "nice"}
INNER_SHELL = re.compile(
    r"""\b(?:(?:bash|sh|zsh|dash|ksh)\b(?:\s+-[A-Za-z-]+)*?\s+-[A-Za-z]*c[A-Za-z]*|eval)\s+(?:'([^']*)'|"((?:[^"\\]|\\.)*)")"""
)


def unwrap(tokens: list[str]) -> list[str]:
    """Drop leading `VAR=value` words and wrapper commands (and their options), so `FOO=1 env -i git add .` reads as `git add .`."""
    i = 0
    while i < len(tokens) and (ENV_ASSIGN.match(tokens[i]) or tokens[i] in WRAPPERS or (i > 0 and tokens[i].startswith("-"))):
        i += 1
    return tokens[i:]


def git_calls(command: str):
    """Each `git <sub> <args...>` found at the start of a shell segment (or inside `sh -c '...'`), as `(sub, args)`."""
    for inner in INNER_SHELL.finditer(command):
        yield from git_calls(inner.group(1) or inner.group(2))
    for segment in SEPARATORS.split(command):
        segment = segment.strip()
        if segment[:1] in ("(", "{", "!"):  # a group: `(git add .)`, `{ git add .; }`
            segment = segment.lstrip("({! ").rstrip("}) ")
        try:
            tokens = shlex.split(segment)
        except ValueError:
            tokens = segment.split()
        tokens = unwrap(tokens)
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


def flags_of(args: list[str]) -> set[str]:
    """Every flag given, with a cluster of short ones split too (`-sm` is `-s` and `-m`)."""
    flags = set()
    for a in args:
        if a.startswith("-"):
            flags.add(a)
        if re.fullmatch(r"-[A-Za-z]+", a):
            flags.update("-" + c for c in a[1:])
    return flags


def message_files(args: list[str]) -> list[str]:
    """The files given to `git commit -F <file>`, `-F<file>`, `--file <file>` or `--file=<file>`."""
    paths = []
    for i, a in enumerate(args):
        if a in ("-F", "--file") and i + 1 < len(args):
            paths.append(args[i + 1])
        elif a.startswith("--file="):
            paths.append(a[len("--file="):])
        elif re.fullmatch(r"-F.+", a):
            paths.append(a[2:])
    return paths


def has_trailer(path: str, cwd: str) -> bool:
    """Whether the message file carries a trailer. A file that cannot be read is not judged (the git hook is the backstop)."""
    try:
        with open(os.path.join(cwd or ".", os.path.expanduser(path)), encoding="utf-8", errors="replace") as f:
            return bool(TRAILER_IN_FILE.search(f.read(200000)))
    except OSError:
        return False


def verdict(command: str, cwd: str = ".") -> tuple[str, str]:
    """`("allow" | "block" | "ask", message)`."""
    calls = list(git_calls(command))
    ask = ""
    for sub, args in calls:
        flags = flags_of(args)
        if sub == "checkout" and ("--" in args or "." in args):
            return "block", "`git checkout -- <file>` discards uncommitted work and has wiped some before. To undo a change, copy the saved backup back (for a mutation check, scripts/mutate.py does this). If the owner really wants it, they will run it."
        if sub == "restore" and not flags & {"--staged", "-S"}:
            return "block", "`git restore` discards uncommitted work. Copy a saved backup back instead, or ask the owner."
        if sub == "reset" and "--hard" in flags:
            return "block", "`git reset --hard` discards uncommitted work. Ask the owner first."
        if sub == "clean" and flags & {"-f", "--force"}:
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
            if any(has_trailer(p, cwd) for p in message_files(args)):
                return "block", "The commit message file carries an attribution trailer. Remove it: commits are authored by the owner alone (docs/COLLABORATION_STANDARDS.md, 'No AI trace')."
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
