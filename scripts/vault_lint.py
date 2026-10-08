#!/usr/bin/env python3
"""Report where the vault breaks the rules of ADR 004 and ADR 010. Read-only: it never fixes a note.

Usage: python3 scripts/vault_lint.py <vault-path> [--inbox-days N]

Reads every *.md under the vault except hidden folders. Errors (bad frontmatter, a missing field, an unknown type or
status, a broken link, a bad tag, a duplicate name, a concept without a note) make the exit code 1. Warnings (no links,
an orphan, no tags, an unlisted topic, a topic that spans one concept, a generated card with no date, a concept named
by an old alias) nudge and never fail the run. Exit 2 is a usage error,
including a vault with no Tags.md or one that does not list the values of type/ and status/.
"""

from __future__ import annotations

import argparse
import difflib
import os
import re
import sys
import time
import unicodedata
from collections import Counter
from typing import NamedTuple

LINK = re.compile(r"\[\[([^\[\]|#\\]*)(?:#[^\[\]|]*)?(?:\\?\|[^\[\]]*)?\]\]")
FILE_NAME = re.compile(r"\.(?=[a-z0-9]*[a-z])[a-z0-9]{2,5}$", re.I)
CLOSING_FENCE = re.compile(r"^\s*(`{3,}|~{3,})\s*$")
BLOCK_ITEM = re.compile(r"^\s*-(?:\s+(.*))?$")
TAG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*/[a-z0-9]+(?:-[a-z0-9]+)*$")
KEY_LINE = re.compile(r"^([A-Za-z_][\w-]*):(?:\s+(.*))?$")
NAMESPACE_LINE = re.compile(r"^[ \t]*[-*][ \t]+`([a-z0-9-]+)/`[ \t]*:[ \t]*(.*)$", re.M)
LISTED_TOPIC = re.compile(r"`topic/([a-z0-9]+(?:-[a-z0-9]+)*)`")
CLOSED_NAMESPACES = ("type", "status")
NEEDS_PROJECTS = {"decision", "idea", "pattern", "source"}
NEEDS_TOPIC = {"decision", "concept", "pattern", "idea", "source"}
MAX_LISTED = 5
INBOX_DAYS = 14


class Finding(NamedTuple):
    path: str
    severity: str
    rule: str
    detail: str


class Note(NamedTuple):
    path: str
    name: str
    fields: dict
    problem: str
    body: str
    mtime: float


class Tags(NamedTuple):
    namespaces: set
    closed: dict
    topics: set


def parse_value(raw: str):
    """A frontmatter value: a quoted string, a flow list or a plain scalar. Raises ValueError on anything else."""
    s = raw.strip()
    if s.startswith("["):
        items, cur, quote = [], "", ""
        for i, c in enumerate(s[1:], 1):
            if quote:
                if c == quote:
                    quote = ""
                else:
                    cur += c
            elif c in "\"'" and not cur.strip():
                quote = c
            elif c == ",":
                items.append(cur.strip())
                cur = ""
            elif c == "[":
                raise ValueError("a [ inside a list must be quoted")
            elif c == "]":
                items.append(cur.strip())
                if s[i + 1:].strip() and not s[i + 1:].strip().startswith("#"):
                    raise ValueError("text after the list")
                return [x for x in items if x]
            else:
                cur += c
        raise ValueError("the list is not closed")
    if s and s[0] in "\"'":
        end = s.find(s[0], 1)
        if end < 0:
            raise ValueError("the quote is not closed")
        if s[end + 1:].strip() and not s[end + 1:].strip().startswith("#"):
            raise ValueError("text after the quote")
        return s[1:end]
    return re.split(r"(?:^|\s+)#", s, maxsplit=1)[0].strip()


def parse_note(path: str, name: str, text: str, mtime: float) -> Note:
    lines = text.split("\n")
    if lines[0].rstrip() != "---":
        return Note(path, name, {}, "", text, mtime)
    end = next((i for i in range(1, len(lines)) if lines[i].rstrip() == "---"), 0)
    if not end:
        return Note(path, name, {}, "the frontmatter fence is not closed", text, mtime)
    fields, problem, open_key = {}, "", ""
    for number, line in enumerate(lines[1:end], 2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        item, match = BLOCK_ITEM.match(line), KEY_LINE.match(line)
        try:
            if item and open_key:  # "key:" followed by "- value" lines, as Obsidian writes tags and aliases
                value = parse_value(item.group(1) or "")
                if isinstance(value, list):
                    raise ValueError("a list inside a list")
                fields[open_key] = (fields[open_key] or []) + ([value] if value else [])
                continue
            if not match:
                raise ValueError("not a `key: value` line")
            fields[match.group(1)] = parse_value(match.group(2) or "")
            open_key = match.group(1) if fields[match.group(1)] == "" else ""
        except ValueError as err:
            problem = problem or f"line {number}: {err}"
    for key in ("type", "status"):
        if isinstance(fields.get(key), list):
            problem = problem or f"{key} must be a single value, not a list"
    return Note(path, name, fields, problem, "\n".join(lines[end + 1:]), mtime)


def as_list(value) -> list:
    return value if isinstance(value, list) else [value] if value else []


def prose(body: str) -> str:
    """The body without code fences and inline code, where a [[link]] is not a link."""
    kept, fence = [], ""
    for line in body.split("\n"):
        if fence:
            closing = CLOSING_FENCE.match(line)
            if closing and closing.group(1)[0] == fence[0] and len(closing.group(1)) >= len(fence):
                fence = ""
            continue
        opening = re.match(r"^\s*(`{3,}|~{3,})", line)
        if opening:
            fence = opening.group(1)
        else:
            kept.append(line)
    return re.sub(r"`[^`\n]*`", "", "\n".join(kept))


def fold(name: str) -> str:
    """The form in which names are compared: Unicode-composed and lower case, as Obsidian resolves them."""
    return unicodedata.normalize("NFC", name).lower()


def target_name(target: str) -> str:
    name = fold(target.rsplit("/", 1)[-1].strip())
    return name[:-3] if name.endswith(".md") else name


def tags_of(note: Note) -> list[str]:
    return [str(t) for t in as_list(note.fields.get("tags"))]


def concept_names(note: Note) -> list[str]:
    return [target_name(m.group(1) if (m := LINK.search(c)) else c) for c in map(str, as_list(note.fields.get("concepts")))]


def link_targets(note: Note) -> list[tuple[str, bool]]:
    """(folded target name, is it from the concepts field) for every link a note makes; [[#Heading]] has no target."""
    found = [(target_name(m.group(1)), False) for m in LINK.finditer(prose(note.body))]
    for key, value in note.fields.items():
        if key != "concepts":
            found += [(target_name(m.group(1)), False) for item in as_list(value) for m in LINK.finditer(str(item))]
    return [(name, from_concepts) for name, from_concepts in found + [(n, True) for n in concept_names(note)] if name]


def concept_index(notes: list[Note], by_name: dict[str, list[Note]]) -> tuple[dict[str, str], list[Finding]]:
    """Folded concept name or alias -> the name of the concept note, and the findings about ambiguous aliases."""
    concepts = {fold(n.name): n.name for n in notes if n.path.startswith("Concepts/")}
    findings, owner = [], {}
    for note in sorted((n for n in notes if n.path.startswith("Concepts/") and not n.problem), key=lambda n: n.path):
        for alias in dict.fromkeys(fold(str(a)) for a in as_list(note.fields.get("aliases"))):
            if alias == fold(note.name):
                continue
            if alias in by_name:
                findings.append(Finding(note.path, "error", "duplicate-name",
                                        f"alias {alias!r} is also the name of {by_name[alias][0].path}"))
            elif alias in owner:
                findings.append(Finding(note.path, "error", "duplicate-name",
                                        f"alias {alias!r} is also an alias of {owner[alias]}"))
            else:
                owner[alias] = note.path
                concepts[alias] = note.name
    return concepts, findings


def did_you_mean(name: str, concepts: dict[str, str]) -> str:
    close = difflib.get_close_matches(name, list(concepts), n=1, cutoff=0.6)
    return f"; did you mean [[{concepts[close[0]]}]]?" if close else ""


def read_tags(text: str) -> Tags:
    namespaces, closed = set(), {}
    for ns, rest in NAMESPACE_LINE.findall(text):
        namespaces.add(ns)
        if ns in CLOSED_NAMESPACES:
            closed[ns] = {v.strip(" .`") for v in rest.split(",")} - {""}
    for ns in CLOSED_NAMESPACES:
        if not closed.get(ns):
            raise ValueError(f"Tags.md lists no values for {ns}/ (a line like \"- `{ns}/`: a, b, c\")")
    return Tags(namespaces, closed, set(LISTED_TOPIC.findall(text)))


def read_vault(root: str) -> list[Note]:
    notes = []
    for folder, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if not d.startswith("."))
        for file in sorted(f for f in files if f.endswith(".md") and not f.startswith(".")):
            full = os.path.join(folder, file)
            path = os.path.relpath(full, root)
            try:
                with open(full, encoding="utf-8-sig") as f:
                    text = f.read()
                notes.append(parse_note(path, file[:-3], text, os.path.getmtime(full)))
            except UnicodeDecodeError:
                notes.append(Note(path, file[:-3], {}, "the file is not UTF-8", "", 0))
            except OSError as err:
                notes.append(Note(path, file[:-3], {}, f"cannot read the file: {err.strerror}", "", 0))
    return notes


def check_fields(note: Note, tags: Tags) -> list[Finding]:
    out, fields = [], note.fields
    generated = fields.get("generated") == "true"
    if note.problem:
        return [Finding(note.path, "error", "bad-frontmatter", note.problem)]
    for field in ("type", "status", "created"):
        if not fields.get(field):
            severity = "warning" if field == "created" and generated else "error"
            out.append(Finding(note.path, severity, "missing-field", field))
    if fields.get("type") in NEEDS_PROJECTS and "projects" not in fields:
        out.append(Finding(note.path, "error", "missing-field", "projects"))
    for field, rule in (("type", "unknown-type"), ("status", "unknown-status")):
        value = fields.get(field)
        if value and value not in tags.closed[field]:
            out.append(Finding(note.path, "error", rule, f"{value!r} is not listed in Tags.md"))
    return out


def check_tags(note: Note, tags: Tags, projects: set[str]) -> list[Finding]:
    out = []
    for tag in tags_of(note):
        ns, _, value = tag.partition("/")
        if not TAG.match(tag):
            why = "is not lowercase kebab-case as namespace/value"
        elif ns not in tags.namespaces:
            why = f"has a namespace that Tags.md does not list ({ns}/)"
        elif ns in CLOSED_NAMESPACES and value not in tags.closed[ns]:
            why = f"has a value that Tags.md does not list for {ns}/"
        elif ns in CLOSED_NAMESPACES and note.fields.get(ns) and value != note.fields[ns]:
            why = f"disagrees with the {ns} field ({note.fields[ns]})"
        elif ns == "project" and value not in projects:
            why = "names a project with no folder under Projects/"
        else:
            continue
        out.append(Finding(note.path, "error", "bad-tag", f"{tag} {why}"))
    return out


def lint(root: str, inbox_days: int = INBOX_DAYS, now: float | None = None) -> list[Finding]:
    now = time.time() if now is None else now
    with open(os.path.join(root, "Tags.md"), encoding="utf-8") as f:
        tags = read_tags(f.read())
    notes = read_vault(root)
    projects_dir = os.path.join(root, "Projects")
    projects = {d.lower() for d in (os.listdir(projects_dir) if os.path.isdir(projects_dir) else [])
                if os.path.isdir(os.path.join(projects_dir, d))}
    by_name: dict[str, list[Note]] = {}
    for note in notes:
        by_name.setdefault(fold(note.name), []).append(note)
    findings = [Finding(other.path, "error", "duplicate-name", f"same name as {group[0].path}")
                for group in by_name.values() for other in group[1:]]
    concepts, alias_findings = concept_index(notes, by_name)
    findings += alias_findings
    linked: set[str] = set()
    topics: dict[str, dict[str, None]] = {}
    spans: dict[str, dict[str, set]] = {}  # topic -> decision card -> the concept notes it names (aliases resolved)
    for note in notes:
        findings += check_fields(note, tags) + ([] if note.problem else check_tags(note, tags, projects))
        resolved = set()
        for name, from_concepts in link_targets(note):
            if from_concepts:
                current = concepts.get(name)
                if current is None:
                    findings.append(Finding(note.path, "error", "missing-concept",
                                            f"{name} has no note in Concepts/{did_you_mean(name, concepts)}"))
                elif fold(current) != name:
                    findings.append(Finding(note.path, "warning", "old-concept-name",
                                            f"{name} is an alias; use [[{current}]]"))
                    name = fold(current)
            if name in by_name:
                resolved.add(name)
            elif not from_concepts and not FILE_NAME.search(name):  # a file such as pic.png is not checked
                findings.append(Finding(note.path, "error", "broken-link", f"[[{name}]] is not a note"))
        resolved.discard(fold(note.name))
        linked |= resolved
        findings += nudges(note, resolved, notes, now, inbox_days)
        for tag in tags_of(note):
            if tag.startswith("topic/") and TAG.match(tag):
                topics.setdefault(tag[6:], {})[note.path] = None
                if note.fields.get("type") == "decision":
                    spans.setdefault(tag[6:], {})[note.path] = {concepts.get(fold(c), c) for c in concept_names(note)}
    for note in notes:
        if not note.path.startswith("Inbox/") and note.path != "Garden.md" and fold(note.name) not in linked:
            findings.append(Finding(note.path, "warning", "orphan", "no note links here"))
    for topic, users in sorted(topics.items()):
        if topic not in tags.topics and topic.replace("-", " ") not in by_name and topic not in by_name:
            more = f" and {len(users) - MAX_LISTED} more" if len(users) > MAX_LISTED else ""
            shown = ", ".join(list(users)[:MAX_LISTED]) + more
            findings.append(Finding("Tags.md", "warning", "unlisted-topic",
                                    f"topic/{topic} is not listed here and has no note; used by {shown}"))
    for topic, cards in sorted(spans.items()):
        named = set().union(*cards.values())
        if len(cards) > 1 and len(named) == 1:
            findings.append(Finding("Tags.md", "warning", "narrow-topic",
                                    f"topic/{topic} spans one concept ({next(iter(named))}) over {len(cards)} "
                                    "decisions; a topic should cut across concepts, so use the concept note instead"))
    return sorted(findings)


def nudges(note: Note, resolved: set[str], notes: list[Note], now: float, inbox_days: int) -> list[Finding]:
    """The warnings that ask a note to link and to be tagged. A note with unreadable frontmatter gets only its error."""
    if note.problem:
        return []
    out, tags = [], tags_of(note)
    if not tags:
        out.append(Finding(note.path, "warning", "no-tags", "no tags"))
    elif note.fields.get("type") in NEEDS_TOPIC and not any(t.startswith("topic/") for t in tags):
        out.append(Finding(note.path, "warning", "no-tags", "no topic/ tag"))
    waiting = note.path.startswith("Inbox/") and now - note.mtime <= inbox_days * 86400
    if not resolved and not waiting:
        text = prose(note.body)
        hints = sorted(n.name for n in notes if n.name != note.name and re.search(
            rf"(?<![\w-]){re.escape(n.name)}(?![\w-])", text, re.I))
        hint = f"; could link: {', '.join(hints[:MAX_LISTED])}" if hints else ""
        out.append(Finding(note.path, "warning", "no-links", f"links to no other note{hint}"))
    return out


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Report where the vault breaks the rules of ADR 004 and 010.")
    parser.add_argument("vault")
    parser.add_argument("--inbox-days", type=int, default=INBOX_DAYS)
    args = parser.parse_args(argv)
    if not os.path.isfile(os.path.join(args.vault, "Tags.md")):
        print(f"no Tags.md in {args.vault}: not a vault, or the tag list is missing")
        return 2
    try:
        findings = lint(args.vault, args.inbox_days)
    except ValueError as err:
        print(err)
        return 2
    for f in findings:
        print(f"{f.path}: {f.severity}: {f.rule}: {f.detail}")
    counts = Counter(f.rule for f in findings)
    errors = sum(f.severity == "error" for f in findings)
    warnings = len(findings) - errors
    print(("\n" if findings else "") + "".join(f"  {rule}: {n}\n" for rule, n in sorted(counts.items()))
          + f"{errors} error(s), {warnings} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
