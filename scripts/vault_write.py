#!/usr/bin/env python3
"""Write one note, or one line, on the owner's side of the vault, after the owner approved it in chat (ADR 017).

Usage: python3 scripts/vault_write.py VAULT capture --project NAME --source FILE|- --quote TEXT --title TITLE
                                              --about NOTE [--about NOTE ...] --topic WORD [--topic WORD ...]
       python3 scripts/vault_write.py VAULT new --path RELPATH --text-file FILE|-
       python3 scripts/vault_write.py VAULT add-line --path RELPATH --line TEXT [--under HEADING]
       python3 scripts/vault_write.py VAULT add-value --namespace type|status --value WORD

Every subcommand writes nothing and exits 1 with the reason on stderr if a check fails. The script cannot see the chat:
that the owner approved the text is the caller's duty, and the report lists every write. It never replaces or deletes.
"""

import argparse
import datetime
import os
import re
import shutil
import sys
import tempfile

import vault_lint as vl

BAD_TITLE = re.compile(r'[\[\]#^|\\/:*?"<>\x00-\x1f]')
HEADING = re.compile(r"^(#{1,6})[ \t]+(.*?)(?:[ \t]+#+)?[ \t]*$")
MESSAGE_BREAK = "\f"  # the source file separates the owner's messages with a form feed
FENCE = re.compile(r"^\s*(`{3,}|~{3,})")
NEEDED = {"type": "capture", "status": "draft"}  # the values of Tags.md's closed lists that this script writes


class Refused(Exception):
    pass


def collapse(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def read_text(arg: str) -> str:
    try:
        if arg == "-":
            return sys.stdin.read()
        with open(arg, encoding="utf-8") as f:
            return f.read()
    except (OSError, UnicodeDecodeError) as err:
        raise Refused(f"cannot read {arg}: {getattr(err, 'strerror', None) or err}")


def inside(root: str, rel: str) -> str:
    """The absolute path of a note inside the vault, outside hidden folders, symlinks followed."""
    parts = rel.replace("\\", "/").split("/")
    if not rel.endswith(".md") or any(p in ("", ".", "..") or p.startswith(".") for p in parts):
        raise Refused(f"{rel!r} is not a note path inside the vault (relative, ending in .md, no hidden folder)")
    full = os.path.join(root, *parts)
    base = os.path.realpath(root)
    if os.path.commonpath([base, os.path.realpath(full)]) != base:
        raise Refused(f"{rel!r} leaves the vault")
    return full


def lint_with(root: str, rel: str, text: str) -> None:
    """Refuse a note the vault lint would reject, tested on a copy of the vault with the note added."""
    def skip(folder, names):
        return [n for n in names if n.startswith(".") or (os.path.isfile(os.path.join(folder, n)) and not n.endswith(".md"))]
    with tempfile.TemporaryDirectory() as tmp:
        copy = os.path.join(tmp, "vault")
        shutil.copytree(root, copy, ignore=skip)
        path = os.path.join(copy, *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        bad = [f for f in vl.lint(copy) if f.path == os.path.normpath(rel) and (f.severity == "error" or f.rule == "no-links")]
    if bad:
        raise Refused("the vault lint would reject this note: " + "; ".join(f"{f.rule}: {f.detail}" for f in bad))


def write_new(root: str, rel: str, text: str) -> None:
    full = inside(root, rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "x", encoding="utf-8", newline="") as f:  # "x": never over an existing file
        f.write(text)


def vault_facts(root: str):
    if not os.path.isfile(os.path.join(root, "Tags.md")):
        raise Refused(f"{root} has no Tags.md: not a vault")
    with open(os.path.join(root, "Tags.md"), encoding="utf-8") as f:
        tags = vl.read_tags(f.read())
    return tags, {vl.fold(n.name) for n in vl.read_vault(root)}


def capture(root: str, a) -> str:
    tags, names = vault_facts(root)
    quote = collapse(a.quote)
    messages = [collapse(m) for m in read_text(a.source).split(MESSAGE_BREAK)]
    if not quote or not any(quote in m for m in messages):
        raise Refused("the quote does not occur in one message of the owner's as one run of text (only whitespace may differ)")
    if not a.about or not a.topic:
        raise Refused("a capture needs at least one --about and one --topic")
    if not os.path.isdir(os.path.join(root, "Projects", a.project)):
        raise Refused(f"no folder Projects/{a.project}")
    missing = [n for n in a.about if vl.fold(n) not in names]
    if missing:
        raise Refused(f"no note named {', '.join(missing)}")
    unlisted = [t for t in a.topic if t not in tags.topics]
    if unlisted:
        raise Refused(f"topic not listed in Tags.md: {', '.join(unlisted)}")
    if not a.title.strip() or BAD_TITLE.search(a.title) or a.title.startswith("."):
        raise Refused(f"{a.title!r} cannot be a note name")
    if vl.fold(a.title) in names:
        raise Refused(f"a note named {a.title!r} exists")
    topics = ", ".join(f"topic/{t}" for t in a.topic)
    text = (f"---\ntype: capture\nstatus: draft\ncreated: {a.created}\nprojects: [{a.project}]\n"
            f"tags: [type/capture, status/draft, project/{a.project.lower()}, {topics}]\n---\n"
            f"> {quote}\n\nAbout: {', '.join(f'[[{n}]]' for n in a.about)}\n")
    rel = f"Projects/{a.project}/Captured/{a.title}.md"
    inside(root, rel)
    lint_with(root, rel, text)
    write_new(root, rel, text)
    return rel


def new(root: str, a) -> str:
    _, names = vault_facts(root)
    inside(root, a.path)
    text = read_text(a.text_file)
    name = a.path.replace("\\", "/").rsplit("/", 1)[-1][:-3]
    if vl.fold(name) in names:
        raise Refused(f"a note named {name!r} exists")
    note = vl.parse_note(a.path, name, text, 0)
    if note.problem:
        raise Refused(f"unreadable frontmatter: {note.problem}")
    if note.fields.get("generated") == "true":
        raise Refused("generated: true is for notes a script owns")
    if note.fields.get("status") != "draft":
        raise Refused("a new note is written with status: draft")
    lint_with(root, a.path, text)
    write_new(root, a.path, text)
    return a.path


def section_end(lines: list[str], heading: str) -> int:
    """Where a line goes to extend the section: after the section's last non-blank line."""
    start = level = fence = None
    first = 0  # headings start after the frontmatter, whose `#` lines are comments
    if lines and lines[0].rstrip() == "---":
        first = next((k + 1 for k in range(1, len(lines)) if lines[k].rstrip() == "---"), 0)
    for k in range(first, len(lines)):
        if FENCE.match(lines[k]):
            fence = None if fence else True
            continue
        m = None if fence else HEADING.match(lines[k].rstrip("\r\n"))
        if m and start is None and m.group(2) == heading:
            start, level = k, len(m.group(1))
        elif m and start is not None and len(m.group(1)) <= level:
            return trim(lines, start, k)
    if start is None:
        raise Refused(f"no heading {heading!r} in the note")
    return trim(lines, start, len(lines))


def trim(lines: list[str], start: int, end: int) -> int:
    while end > start + 1 and not lines[end - 1].strip():
        end -= 1
    return end


def _replace(full: str, text: str) -> None:
    with open(full, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def add_line(root: str, a) -> str:
    full = inside(root, a.path)
    if not os.path.isfile(full):
        raise Refused(f"{a.path} does not exist")
    if not a.line.strip() or "\n" in a.line or "\r" in a.line:
        raise Refused("the line is empty or has a line break")
    with open(full, encoding="utf-8", newline="") as f:
        old = f.read()
    note = vl.parse_note(a.path, "", old.lstrip("﻿"), 0)
    if note.problem or note.fields.get("generated") == "true":
        raise Refused("the note is generated or its frontmatter is unreadable, so it is not the owner's to extend")
    lines = old.splitlines(keepends=True)
    if any(l.rstrip("\r\n") == a.line for l in lines):
        raise Refused("the line is already in the note")
    at = section_end(lines, a.under) if a.under else len(lines)
    eol = "\r\n" if "\r\n" in old else "\n"
    gap = eol if at and not lines[at - 1].endswith(("\n", "\r")) else ""
    expected = "".join(lines[:at]) + gap + a.line + eol + "".join(lines[at:])
    write_checked(full, old, expected)
    return a.path


def write_checked(full: str, old: str, expected: str) -> None:
    _replace(full, expected)
    with open(full, encoding="utf-8", newline="") as f:
        written = f.read()
    if written != expected:
        with open(full, "w", encoding="utf-8", newline="") as f:  # put the old content back
            f.write(old)
        raise Refused("the file did not read back as the old content plus the addition; the old content was put back")


def missing_values(root: str) -> list[tuple[str, str]]:
    """The values this script writes that Tags.md does not list, as (namespace, value)."""
    tags, _ = vault_facts(root)
    return [(ns, v) for ns, v in NEEDED.items() if v not in tags.closed[ns]]


def add_value(root: str, a) -> str:
    """Extend the one-line list of a closed namespace (type/, status/) in Tags.md by one value, at the end of the line."""
    tags, _ = vault_facts(root)
    if not vl.TAG.match(f"{a.namespace}/{a.value}"):
        raise Refused(f"{a.value!r} is not a lowercase kebab-case word")
    if a.value in tags.closed[a.namespace]:
        raise Refused(f"{a.namespace}/{a.value} is already listed")
    full = os.path.join(root, "Tags.md")
    with open(full, encoding="utf-8", newline="") as f:
        old = f.read()
    lines = old.splitlines(keepends=True)
    hits = [k for k, l in enumerate(lines) if re.match(rf"[ \t]*[-*][ \t]+`{a.namespace}/`[ \t]*:", l)]
    if len(hits) != 1:
        raise Refused(f"Tags.md does not have exactly one list line for {a.namespace}/")
    body = lines[hits[0]].rstrip("\r\n")
    if body.rstrip().endswith((".", ",")):
        raise Refused(f"the {a.namespace}/ line ends in punctuation, so it is not a plain list to extend; the owner edits it")
    lines[hits[0]] = body.rstrip() + f", {a.value}" + lines[hits[0]][len(body):]
    write_checked(full, old, "".join(lines))
    return "Tags.md"


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("vault")
    sub = p.add_subparsers(dest="kind", required=True)
    c = sub.add_parser("capture")
    c.add_argument("--project", required=True)
    c.add_argument("--source", required=True)
    c.add_argument("--quote", required=True)
    c.add_argument("--title", required=True)
    c.add_argument("--about", action="append", default=[])
    c.add_argument("--topic", action="append", default=[])
    c.add_argument("--created", default=datetime.date.today().isoformat())
    n = sub.add_parser("new")
    n.add_argument("--path", required=True)
    n.add_argument("--text-file", required=True)
    d = sub.add_parser("add-line")
    d.add_argument("--path", required=True)
    d.add_argument("--line", required=True)
    d.add_argument("--under")
    v = sub.add_parser("add-value")
    v.add_argument("--namespace", required=True, choices=vl.CLOSED_NAMESPACES)
    v.add_argument("--value", required=True)
    args = p.parse_args(argv)
    try:
        if not os.path.isdir(args.vault):
            raise Refused(f"{args.vault} is not a folder")
        written = {"capture": capture, "new": new, "add-line": add_line, "add-value": add_value}[args.kind](args.vault, args)
    except Refused as err:
        print(f"refused: {err}", file=sys.stderr)
        return 1
    except ValueError as err:  # Tags.md lists no type/ or status/ values
        print(f"refused: {err}", file=sys.stderr)
        return 1
    print(written)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
