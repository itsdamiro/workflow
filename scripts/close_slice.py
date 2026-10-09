#!/usr/bin/env python3
"""Run the mechanical part of /handoff in one command: the vault sync, the stats line and the lint (ADR 005).

Usage: python3 scripts/close_slice.py <project-path> <vault-path> [--name NAME] [--ref REF] [--context-tokens N] [--dry-run]

Runs scripts/vault_sync.py, scripts/stats_line.py and scripts/vault_lint.py in that order (so the lint also reads the
stats note) and prints one short block: the sync's counts, the stats row, the lint's errors (every one) and warning count, and the vault notes the close
created and updated, by path (a hash of every Markdown file before and after; ADR 005, amendment of 2026-10-09). Refusals and hints are
printed as the scripts print them; they are for the owner to settle and do not stop the close. Exit 0: the lint had no
error, so the push may go ahead. Exit 1: the lint had an error, so do not push. Exit 2: a script could not run, or a
usage error.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
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
    if errors:
        print("do not push: the lint has an error")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
