#!/usr/bin/env python3
"""Run the mechanical part of /handoff in one command: the vault sync, the stats line and the lint (ADR 005).

Usage: python3 scripts/close_slice.py <project-path> <vault-path> [--name NAME] [--ref REF] [--context-tokens N] [--dry-run]

Runs scripts/vault_sync.py, scripts/stats_line.py and scripts/vault_lint.py in that order (so the lint also reads the
stats note) and prints one short block: the sync's counts, the stats row, the lint's errors (every one) and warning count, and the vault notes the close
created and updated, by path (a hash of every Markdown file before and after; ADR 005, amendment of 2026-10-09). Refusals and hints are
printed as the scripts print them; they are for the owner to settle and do not stop the close. Then, if the lint had no
error and this is not a dry run, it commits in the vault's own git repository every changed note marked `generated: true`,
by named path and nothing else, and prints one `vault git:` line (ADR 020); it never pushes, and a reason it could not
commit does not change the exit code. Exit 0: the lint had no error, so the push may go ahead. Exit 1: the lint had an
error, so do not push. Exit 2: a script could not run, or a usage error.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vault_sync  # noqa: E402
import vault_write  # noqa: E402
TOTALS = re.compile(r"^(\d+) error\(s\), (\d+) warning\(s\)$")


def run(script: str, *args: str) -> tuple[int, list[str]]:
    done = subprocess.run([sys.executable, os.path.join(HERE, script), *args], capture_output=True, encoding="utf-8", errors="replace")
    return done.returncode, (done.stdout + done.stderr).splitlines()


def snapshot(vault: str) -> dict[str, str]:
    """A hash for every Markdown note in the vault, by path from its root; hidden folders (.obsidian, .git) are skipped."""
    notes = {}
    for folder, dirs, files in os.walk(vault):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for name in files:
            if name.endswith(".md") and not name.startswith("."):
                path = os.path.join(folder, name)
                with open(path, "rb") as f:
                    notes[os.path.relpath(path, vault)] = hashlib.sha1(f.read()).hexdigest()
    return notes


def git(vault: str, *args: str) -> tuple[int, str]:
    """Run git in the vault with literal pathspecs, so a note named with `*` or `[` is matched as written."""
    done = subprocess.run(["git", "-C", vault, "--literal-pathspecs", *args], capture_output=True, encoding="utf-8", errors="replace")
    return done.returncode, done.stdout if done.returncode == 0 else (done.stderr.strip() or done.stdout.strip())


def is_generated(vault: str, rel: str) -> bool:
    try:
        with open(os.path.join(vault, rel), encoding="utf-8") as f:
            return vault_sync.parse_frontmatter(f.read())[0].get("generated") == "true"
    except (OSError, UnicodeDecodeError):
        return False


def changed_generated_notes(vault: str) -> tuple[list[str], bool]:
    """Paths git shows as modified or untracked that are Markdown outside any hidden folder and say `generated: true` (ADR 020, decision 1),
    and whether any path is unmerged. A deleted file cannot be read, so a deletion never qualifies; a rename is the owner's act and is skipped."""
    code, status = git(vault, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    if code:
        return [], False
    fields, found, unmerged, i = status.split("\0"), [], False, 0
    while i < len(fields):
        entry = fields[i]
        i += 1
        if len(entry) < 4:
            continue
        flags, rel = entry[:2], entry[3:]
        if "R" in flags or "C" in flags:
            i += 1  # the original path follows
            continue
        if "U" in flags or flags in ("AA", "DD"):
            unmerged = True
            continue
        if not rel.endswith(".md") or any(part.startswith(".") for part in rel.split("/")):
            continue
        if is_generated(vault, rel):
            found.append(rel)
    return sorted(found), unmerged


def commit_vault(vault: str, name: str, project: str) -> list[str]:
    """Commit the vault's changed generated notes by named path (ADR 020). Returns the lines to print; never raises, never pushes."""
    real = os.path.realpath(vault)
    code, top = git(vault, "rev-parse", "--show-toplevel")
    if code or os.path.realpath(top.strip()) != real:
        return ["vault git: not committed (the vault is not a git repository of its own)"]
    code, gitdir = git(vault, "rev-parse", "--absolute-git-dir")
    if code:
        return [f"vault git: not committed ({gitdir})"]
    gitdir = gitdir.strip()
    for marker, what in (("MERGE_HEAD", "a merge"), ("CHERRY_PICK_HEAD", "a cherry-pick"), ("REVERT_HEAD", "a revert"),
                         ("rebase-merge", "a rebase"), ("rebase-apply", "a rebase"), ("index.lock", "another git command (index.lock)")):
        if os.path.exists(os.path.join(gitdir, marker)):
            return [f"vault git: not committed ({what} is in progress in the vault)"]
    notes, unmerged = changed_generated_notes(vault)
    if unmerged:
        return ["vault git: not committed (the vault has unmerged paths)"]
    if not notes:
        return ["vault git: nothing to commit"]
    lines = []
    code, ahead = git(vault, "rev-list", "--count", "@{upstream}..HEAD")
    ahead = ahead.strip()
    if code == 0 and ahead != "0":
        lines.append(f"vault git: the vault was already {ahead} commit(s) ahead of its remote, so do not push it (ADR 020)")
    elif code:
        lines.append("vault git: the vault has no upstream branch or no commit, so there is nothing to push it to")
    code, short = git(project, "rev-parse", "--short", "HEAD")
    message = f"Close {name} at {short.strip() if code == 0 else 'unknown'}: {len(notes)} generated note(s)"
    code, out = git(vault, "add", "--", *notes)
    if code == 0:
        code, out = git(vault, "commit", "--only", "-q", "-m", message, "--", *notes)
    if code:
        return lines + [f"vault git: not committed ({out.splitlines()[0] if out else 'git failed'})"]
    _, sha = git(vault, "rev-parse", "--short", "HEAD")
    return lines + [f"vault git: committed {len(notes)} note(s) as {sha.strip()}"]


def lines_of(output: list[str], *prefixes: str) -> list[str]:
    return [line for line in output if line.startswith(prefixes)]


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("project")
    ap.add_argument("vault")
    ap.add_argument("--name")
    ap.add_argument("--ref")
    ap.add_argument("--context-tokens", type=int)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    shared = [args.project, args.vault]
    named = (["--name", args.name] if args.name else []) + (["--ref", args.ref] if args.ref else [])
    dry = ["--dry-run"] if args.dry_run else []
    context = ["--context-tokens", str(args.context_tokens)] if args.context_tokens is not None else []

    before = snapshot(args.vault)
    code, sync = run("vault_sync.py", *shared, *named, *dry)
    if code not in (0, 1):  # 1 is a refusal, which is reported; anything else is a failure
        print("close_slice: the sync failed:", *sync, sep="\n  ", file=sys.stderr)
        return 2
    code, stats = run("stats_line.py", *shared, *named, *context, *dry)
    if code not in (0, 1):
        print("close_slice: the stats line failed:", *stats, sep="\n  ", file=sys.stderr)
        return 2

    name = args.name or os.path.basename(os.path.realpath(args.project))
    code, lint = run("vault_lint.py", args.vault, "--repo", f"{name}={args.project}")  # so a pattern's `code:` is checked
    totals = next((TOTALS.match(line.strip()) for line in reversed(lint) if TOTALS.match(line.strip())), None)
    if code not in (0, 1) or not totals:
        print("close_slice: the lint failed:", *lint, sep="\n  ", file=sys.stderr)
        return 2
    errors, warnings = int(totals.group(1)), int(totals.group(2))
    print("sync:  " + (lines_of(sync, "created ", "would ") or ["(no summary)"])[0])
    for line in lines_of(sync, "refused:", "hint:"):
        print("       " + line)
    print("stats: " + (lines_of(stats, "created ", "would ") or ["(no summary)"])[0])
    for line in lines_of(stats, "row:", "refused:", "hint:"):
        print("       " + line)
    print(f"lint:  {errors} error(s), {warnings} warning(s)")
    for line in (x for x in lint if ": error: " in x):
        print("       " + line)
    for ns, value in vault_write.missing_values(args.vault):  # the lint passed, so Tags.md parses
        print(f"       hint: Tags.md does not list {ns}/{value}, which vault_write.py writes; add-value --namespace {ns} --value {value} adds it")
    after = snapshot(args.vault)
    created = sorted(n for n in after if n not in before)
    updated = sorted(n for n in after if n in before and after[n] != before[n])
    if args.dry_run:
        print("vault: nothing written (dry run)")
    elif not created and not updated:
        print("vault: no note changed")
    else:
        print(f"vault: {len(created)} note(s) created, {len(updated)} updated")
        for label, names in (("created", created), ("updated", updated)):
            for note in names:
                print(f"       {label}: {note}")
    if args.dry_run:
        print("vault git: not committed (dry run)")
    elif errors:
        print("vault git: not committed (the lint has an error)")
    else:
        for line in commit_vault(args.vault, name, args.project):
            print(line)
    if errors:
        print("do not push: the lint has an error")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
