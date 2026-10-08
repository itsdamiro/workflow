#!/usr/bin/env python3
"""Add one row to a project's append-only stats note in the vault (ADR 014).

Usage: python3 scripts/stats_line.py <project-path> <vault-path> [--name NAME] [--ref REF] [--context-tokens N] [--dry-run]

Writes <vault>/Projects/NAME/NAME - Stats.md: the day, the head commit of REF, the number of commits since the previous
row, the oldest and newest of their subjects as git has them, and the context size N the adapter passes in (a dash when
none). Existing text is kept byte for byte and the row is added after it, so the history survives; running it again on
the same head changes nothing. Only a note marked `generated: true` is written. Exit 0 clean, 1 if refused, 2 usage error.
"""

from __future__ import annotations

import argparse
import datetime
import os
import re
import subprocess
import sys

import vault_sync as vs

SUBJECT_MAX = 60
HEAD = "| Day | Commit | Commits since the last row | First and last subject | Context at close |\n|---|---|---|---|---|\n"
ROW = re.compile(r"^\|\s*\d{4}-\d{2}-\d{2}\s*\|\s*([0-9a-f]{8})\s*\|")
DASH = "–"


def cell(subject: str) -> str:
    """A commit subject as inline code that cannot break the table, make a link or make a tag."""
    subject = subject or "(no subject)"
    if len(subject) > SUBJECT_MAX:
        subject = subject[:SUBJECT_MAX].rsplit(None, 1)[0] + "…"
    return vs.span(subject).replace("|", "\\|")


class StatsReport(vs.Report):
    def __init__(self) -> None:
        super().__init__()
        self.row = ""


def is_ancestor(project: str, previous: str, head: str) -> bool:
    """Whether `previous` is in the history of `head`. A commit that is gone (a rewrite) is a plain no; any other git failure is an error."""
    if not vs.git(project, "rev-parse", "--verify", "--quiet", previous + "^{commit}", check=False).strip():
        return False
    done = subprocess.run(["git", "-C", project, "merge-base", "--is-ancestor", previous, head], capture_output=True, encoding="utf-8",
                          errors="replace")
    if done.returncode not in (0, 1):
        raise vs.SyncError(f"git merge-base: {done.stderr.strip()}")
    return done.returncode == 0


def since(project: str, previous: str, head: str) -> list[str]:
    """Subjects of the commits after `previous` up to `head`, newest first; [] when `previous` is not an ancestor of `head`."""
    if not is_ancestor(project, previous, head):
        return []
    return vs.git(project, "log", "--format=%s", f"{previous}..{head}").splitlines()


def make_row(project: str, head: str, previous: str, day: str, context: int | None) -> str:
    subjects = since(project, previous, head) if previous else []
    if subjects:
        count, shown = str(len(subjects)), cell(subjects[-1]) + (f" → {cell(subjects[0])}" if len(subjects) > 1 else "")
    else:  # the first row, or a previous commit that history no longer holds
        count, shown = DASH, cell(vs.git(project, "log", "-1", "--format=%s", head).strip())
    return f"| {day} | {head[:8]} | {count} | {shown} | {DASH if context is None else context} |\n"


def render_new(name: str, day: str, row: str) -> str:
    fields = [("type", "reference"), ("status", "active"), ("created", day), ("projects", vs.flow([name])), ("source", vs.yq("git log")),
              ("generated", "true"), ("tags", vs.tags("reference", "active", name))]
    return (vs.frontmatter(fields) + f"\n# {name} — Stats\n\nOne row for each `/handoff`, added by `scripts/stats_line.py` and never rewritten. "
            f"Back to [[{name}]].\n\n" + HEAD + row)


def add_row(project: str, vault: str, name: str, ref: str | None = None, context: int | None = None, dry: bool = False,
            today: str | None = None) -> StatsReport:
    vs.check_inputs(project, vault, name)
    ref = ref or vs.default_ref(project)
    head = vs.git(project, "rev-parse", "--verify", ref + "^{commit}").strip()
    day, report = today or datetime.date.today().isoformat(), StatsReport()
    base = os.path.join(vault, "Projects", name)
    label, note = f"{name} - Stats", os.path.join(base, f"{name} - Stats.md")
    used = vs.taken_by(vs.names_elsewhere(vault, os.path.join(base, "decisions")), label, note, vault)
    if used:
        report.refused.append((label, f"the name is already used by {used}"))
        return report
    shown = os.path.relpath(note, vault)
    if os.path.exists(note):
        old = vs.read_text(note)
        if not vs.is_generated(old):
            report.refused.append((shown, "exists and is not marked generated: left alone"))
            return report
        last = old.rstrip("\n").splitlines()[-1]  # a note marked generated has frontmatter, so it has lines
        found = ROW.match(last)
        if not found:
            report.refused.append((shown, "its last line is not a row this script wrote: nothing was added"))
            return report
        if head.startswith(found.group(1)):
            report.unchanged.append(shown)
            return report
        row = make_row(project, head, found.group(1), day, context)
        text = (old if old.endswith("\n") else old + "\n") + row
    else:
        row = make_row(project, head, "", day, context)
        text = render_new(name, day, row)
    vs.write_note(note, text, os.path.realpath(vault), dry, report)
    report.row = row.rstrip("\n")
    hub = os.path.join(base, f"{name}.md")
    if os.path.exists(hub) and f"[[{label}" not in vs.read_text(hub):  # the hub is the owner's: say so, never edit it
        report.hints.append(f"{os.path.relpath(hub, vault)} does not link to [[{label}]]: add the link if you want it")
    return report


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("project")
    ap.add_argument("vault")
    ap.add_argument("--name")
    ap.add_argument("--ref")
    ap.add_argument("--context-tokens", type=int)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    if args.context_tokens is not None and args.context_tokens < 0:
        ap.error("--context-tokens must not be negative")
    try:
        report = add_row(args.project, args.vault, args.name or os.path.basename(os.path.realpath(args.project)), args.ref,
                         args.context_tokens, args.dry_run)
    except vs.SyncError as e:
        print(f"stats_line: {e}", file=sys.stderr)
        return 2
    prefix = "would " if args.dry_run else ""
    print(f"{prefix}created {len(report.created)}, updated {len(report.updated)}, unchanged {len(report.unchanged)}, refused {len(report.refused)}")
    if report.created or report.updated:
        print(f"row: {report.row}")
    for label, reason in report.refused:
        print(f"refused: {label}: {reason}")
    for hint in report.hints:
        print(f"hint: {hint}")
    return 1 if report.refused else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
