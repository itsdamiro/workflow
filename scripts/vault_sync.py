#!/usr/bin/env python3
"""Turn a project's committed decision records into read-only cards in the vault (ADR 009).

Usage: python3 scripts/vault_sync.py <project-path> <vault-path> [--name NAME] [--ref REF] [--dry-run]

Reads docs/decisions/NNN-slug.md as committed on REF (default: the local branch the remote's HEAD names, else main or
master), through git, so a draft is never published. Writes under <vault>/Projects/NAME/: a card per record in
decisions/, "NAME - Rejected ideas.md", "NAME - Gotchas.md" (a copy of docs/reference/GOTCHAS.md when that file is
committed), and the hub NAME.md only if it is missing. Every sentence in a generated note is
text taken from a record. Only notes marked `generated: true` are replaced; nothing is deleted (a record that vanishes
becomes a tombstone card, a renamed one leaves a redirect). Exit 0 clean, 1 if anything was refused, 2 usage error.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime
import json
import os
import re
import subprocess
import sys
import tempfile

RECORD = re.compile(r"^(\d{3})-(.+)\.md$")
INDEX_ROW = re.compile(r"^\|\s*\[(\d{3})\]\([^)]*\)\s*\|.*\|\s*([^|]+?)\s*\|\s*$")
ISO_DAY = re.compile(r"\d{4}-\d{2}-\d{2}")
UNSAFE = re.compile(r'[\\/:*?"<>|#^\[\]]')
STATUSES = {"proposed", "accepted", "superseded", "removed"}
SUMMARY_MAX, BULLET_MAX, NAME_MAX = 600, 300, 80
GOTCHAS_PATH = "docs/reference/GOTCHAS.md"


class SyncError(Exception):
    pass


def git(project: str, *args: str, check: bool = True) -> str:
    done = subprocess.run(["git", "-C", project, *args], capture_output=True, encoding="utf-8", errors="replace")
    if check and done.returncode:
        raise SyncError(f"git {' '.join(args)}: {done.stderr.strip()}")
    return done.stdout


def default_ref(project: str) -> str:
    head = git(project, "symbolic-ref", "--short", "refs/remotes/origin/HEAD", check=False).strip()
    for ref in (head.split("/", 1)[1] if "/" in head else "", "main", "master"):
        if ref and git(project, "rev-parse", "--verify", "--quiet", ref + "^{commit}", check=False).strip():
            return ref
    raise SyncError("no default branch found; pass --ref")


def list_records(project: str, ref: str) -> dict[int, list[tuple[str, str]]]:
    found: dict[int, list[tuple[str, str]]] = {}
    for path in git(project, "ls-tree", "-r", "--name-only", "-z", ref, "--", "docs/decisions").split("\0"):
        match = RECORD.match(os.path.basename(path))
        if match and os.path.dirname(path) == "docs/decisions":
            found.setdefault(int(match.group(1)), []).append((path, match.group(2)))
    return found


# ---- reading a record ------------------------------------------------------------------------------------------------


def split_flow(inner: str) -> list[str]:
    parts, current, quote = [], "", ""
    for ch in inner:
        if quote:
            quote = "" if ch == quote else quote
        elif ch in "\"'":
            quote = ch
        elif ch == ",":
            parts.append(current)
            current = ""
            continue
        current += ch
    return parts + [current]


def parse_value(raw: str):
    if not raw.startswith(("\"", "'")):
        raw = re.sub(r"\s+#.*$", "", raw)
    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1].strip()
        return [x.strip().strip("\"'") for x in split_flow(inner)] if inner else []
    return raw.strip().strip("\"'")


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """The flat `key: value` and `key: [a, b]` subset the records use. Not a YAML parser."""
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end < 0:
        return {}, text
    meta = {}
    for line in text[4:end].splitlines():
        match = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if match:
            meta[match.group(1)] = parse_value(match.group(2).strip())
    return meta, text[end + 4:].lstrip("\n")


def listify(value) -> list:
    return value if isinstance(value, list) else ([value] if value else [])


def clip(text: str, limit: int) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + "…"


def section(body: str, name: str) -> list[str]:
    lines, out, inside = body.splitlines(), [], False
    for line in lines:
        if re.match(r"^##\s", line):
            inside = line[2:].strip().lower().startswith(name)
            continue
        if inside:
            out.append(line)
    return out


def bullets(lines: list[str]) -> list[str]:
    """Each top-level `- ` or `* ` item, joined with the lines that wrap it (a blank line ends the item)."""
    items: list[str] = []
    open_item = False
    for line in lines:
        if re.match(r"^[-*] ", line):
            items.append(line[2:].strip())
            open_item = True
        elif open_item and line.strip():
            items[-1] += " " + line.strip()
        else:
            open_item = False
    return items


def summary_of(body: str) -> str:
    lines = body.splitlines()
    for i, line in enumerate(lines):
        match = re.match(r">\s*\*\*Summary\.?\*\*\s*(.*)$", line)
        if match:
            parts = [match.group(1)]
            for following in lines[i + 1:]:
                if not following.startswith(">"):
                    break
                parts.append(following[1:].strip())
            return clip(" ".join(p for p in parts if p), SUMMARY_MAX)
    paragraph: list[str] = []
    for line in section(body, "decision"):
        if not line.strip():
            if paragraph:
                break
            continue
        paragraph.append(line.strip())
    return clip(" ".join(paragraph), SUMMARY_MAX)


def first_status(text: str) -> str:
    match = re.match(r"\W*([A-Za-z]+)", text or "")
    word = match.group(1).lower() if match else ""
    return word if word in STATUSES else "unknown"


def parse_record(text: str, number: int, slug: str, index_status: str) -> dict:
    meta, body = parse_frontmatter(text)
    title = next((line[2:].strip() for line in body.splitlines() if line.startswith("# ")), f"{number:03d} — {sentence(slug)}")
    status_line = re.search(r"^>?\s*\**Status:\**.*$", body, re.M)
    status = first_status(str(meta.get("status", "")))
    if status == "unknown" and status_line:
        status = first_status(re.sub(r"^>?\s*\**Status:\**", "", status_line.group(0)))
    if status == "unknown":
        status = index_status
    day = str(meta.get("date", ""))
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
        found = re.search(r"\d{4}-\d{2}-\d{2}", status_line.group(0) if status_line else "")
        day = found.group(0) if found else ""
    amendments = [
        (m.group(1) or "", m.group(2).strip())
        for m in (re.match(r"^##\s+Amendment\b\s*(?:\(([^)]*)\))?\s*[:—–-]*\s*(.*)$", line) for line in body.splitlines())
        if m
    ]
    rejected = [clip(b, BULLET_MAX) for b in bullets(section(body, "alternatives rejected"))]
    amends = [int(n) for value in listify(meta.get("amends")) for n in re.findall(r"\d+", str(value))]
    concepts = [re.sub(r"^\[\[|\]\]$", "", str(c)).strip() for c in listify(meta.get("concepts")) if str(c).strip()]
    return {
        "number": number, "slug": slug, "title": title, "status": status, "date": day, "summary": summary_of(body),
        "amends": amends, "concepts": concepts, "amendments": amendments, "rejected": rejected,
        "topic_tags": [t for t in listify(meta.get("tags")) if not re.match(r"(type|status|project)/", t)],
    }


# ---- rendering -------------------------------------------------------------------------------------------------------


def sentence(slug: str) -> str:
    text = re.sub(r"\s+", " ", UNSAFE.sub("", slug.replace("-", " "))).strip() or "Untitled"
    text = text[:1].upper() + text[1:]
    return text if len(text) <= NAME_MAX else text[:NAME_MAX].rsplit(" ", 1)[0]


def card_name(number: int, slug: str) -> str:
    return f"{number:03d} - {sentence(slug)}"


def kebab(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


YAML_WORDS = {"true", "false", "null", "yes", "no", "on", "off", "y", "n"}


def yq(value: str) -> str:
    """The value as YAML reads it back unchanged: plain when that is safe, else double-quoted (JSON quoting is valid YAML)."""
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9._/-]*", value) and value.lower() not in YAML_WORDS:
        return value
    return json.dumps(value, ensure_ascii=False)


def flow(values: list[str]) -> str:
    return "[" + ", ".join(yq(v) for v in values) + "]"


def tags(kind: str, status: str, project: str, *extra: str) -> str:
    return flow(list(dict.fromkeys([f"type/{kind}", f"status/{status}", f"project/{kebab(project)}", *extra])))


def frontmatter(fields: list[tuple[str, str]]) -> str:
    return "---\n" + "".join(f"{k}: {v}\n" for k, v in fields) + "---\n"


def render_card(rec: dict, project: str, names: dict[int, str], sha: str, path: str) -> str:
    fields = [("type", "decision"), ("status", rec["status"])]
    if rec["date"]:
        fields.append(("created", rec["date"]))
    fields += [
        ("projects", flow([project])), ("concepts", flow([f"[[{c}]]" for c in rec["concepts"]])), ("adr", str(rec["number"])),
        ("source", yq(path)), ("generated", "true"), ("tags", tags("decision", rec["status"], project, *rec["topic_tags"])),
    ]
    out = frontmatter(fields) + f"\n# {rec['title']}\n\n"
    if rec["summary"]:
        out += f"> **Summary.** {rec['summary']}\n\n"
    out += f"Project: [[{project}]]\n"
    links = [f"[[{names[n]}|ADR {n:03d}]]" if n in names else f"ADR {n:03d}" for n in rec["amends"]]
    if links:
        out += "Amends: " + ", ".join(links) + "\n"
    if rec["amendments"]:
        out += "\n## Amendments\n\n" + "".join(f"- {d + ': ' if d else ''}{t}\n" for d, t in rec["amendments"])
    if rec["rejected"]:
        out += "\n## Rejected alternatives\n\n" + "".join(f"- {b}\n" for b in rec["rejected"])
    return out + f"\n---\nGenerated from `{path}` at `{sha}`. The next sync overwrites this note; edit the record instead.\n"


def render_tombstone(number: int, project: str, day: str) -> str:
    fields = [("type", "decision"), ("status", "removed"), ("projects", flow([project])), ("concepts", "[]"), ("adr", str(number)),
              ("generated", "true"), ("tags", tags("decision", "removed", project))]
    return frontmatter(fields) + f"\n# {number:03d} — removed\n\nThe record was removed from the repository (seen missing on {day}). Kept so links to it still resolve.\nProject: [[{project}]]\n"


def render_redirect(number: int, project: str, target: str) -> str:
    fields = [("type", "redirect"), ("status", "active"), ("projects", flow([project])), ("adr", str(number)), ("generated", "true"),
              ("tags", tags("redirect", "active", project))]
    return frontmatter(fields) + f"\nMoved to [[{target}|ADR {number:03d}]].\n"


def render_rejected(project: str, records: list[dict], names: dict[int, str]) -> str:
    days = [r["date"] for r in records if ISO_DAY.fullmatch(r["date"])]
    fields = [("type", "index"), ("status", "active")] + ([("created", min(days))] if days else []) + [
        ("projects", flow([project])), ("generated", "true"), ("tags", tags("index", "active", project))]
    out = frontmatter(fields) + f"\n# {project} — Rejected ideas\n\nAlternatives that decision records turned down, with the record that did it. Back to [[{project}]].\n"
    for rec in sorted(records, key=lambda r: r["number"]):
        if rec["rejected"] and rec["number"] in names:
            out += f"\n## [[{names[rec['number']]}|ADR {rec['number']:03d}]]\n\n" + "".join(f"- {b}\n" for b in rec["rejected"])
    return out


def render_gotchas(project: str, text: str, day: str, sha: str) -> str:
    fields = [("type", "reference"), ("status", "active"), ("created", day), ("projects", flow([project])), ("source", yq(GOTCHAS_PATH)),
              ("generated", "true"), ("tags", tags("reference", "active", project))]
    return (frontmatter(fields) + "\n" + text.rstrip("\n") + "\n\n---\n"
            f"Project: [[{project}]]. Generated from `{GOTCHAS_PATH}` at `{sha}`. The next sync overwrites this note; edit the file instead.\n")


def render_hub(project: str, today: str, gotchas: bool = False) -> str:
    fields = [("type", "project"), ("status", "active"), ("created", today), ("tags", tags("project", "active", project))]
    more = f" and [[{project} - Gotchas]]" if gotchas else ""
    return frontmatter(fields) + f"\n# {project}\n\nHub for the project. Part of [[Projects]]. See [[{project} - Rejected ideas]]{more}.\n"


# ---- writing ---------------------------------------------------------------------------------------------------------


class Report:
    def __init__(self) -> None:
        self.created: list[str] = []
        self.updated: list[str] = []
        self.unchanged: list[str] = []
        self.tombstoned: list[str] = []
        self.redirected: list[str] = []
        self.refused: list[tuple[str, str]] = []
        self.hints: list[str] = []


def is_generated(text: str) -> bool:
    return str(parse_frontmatter(text)[0].get("generated", "")).lower() == "true"


def read_text(path: str) -> str:
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def write_note(path: str, text: str, vault_real: str, dry: bool, report: Report, bucket: list[str] | None = None) -> bool:
    """Writes the note unless something is in the way. True when the note is, or would be, as `text` says."""
    target_dir = os.path.realpath(os.path.dirname(path))
    if os.path.commonpath([vault_real, target_dir]) != vault_real:
        report.refused.append((path, "outside the vault"))
        return False
    label = os.path.relpath(os.path.join(target_dir, os.path.basename(path)), vault_real)
    if os.path.exists(path):
        current = read_text(path)
        if not is_generated(current):
            report.refused.append((label, "exists and is not marked generated: left alone"))
            return False
        if current == text:
            report.unchanged.append(label)
            return True
        (bucket if bucket is not None else report.updated).append(label)
        mode = os.stat(path).st_mode & 0o777
    else:
        (bucket if bucket is not None else report.created).append(label)
        umask = os.umask(0)
        os.umask(umask)
        mode = 0o666 & ~umask
    if dry:
        return True
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".sync-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.remove(tmp)
        raise
    return True


def names_elsewhere(vault: str, skip_dir: str) -> dict[str, str]:
    taken: dict[str, str] = {}
    for root, dirs, files in os.walk(vault):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        if os.path.realpath(root) == os.path.realpath(skip_dir):
            dirs[:] = []
            continue
        for f in files:
            if f.endswith(".md"):
                taken.setdefault(f[:-3].lower(), os.path.relpath(os.path.join(root, f), vault))
    return taken


def taken_by(taken: dict[str, str], label: str, note: str, vault: str) -> str:
    """The vault path of another note already using `label`, or "" when the name is free for `note`."""
    used = taken.get(label.lower(), "")
    return used if used != os.path.relpath(note, vault) else ""


def mirror_gotchas(project: str, ref: str, name: str, base: str, taken: dict[str, str], vault: str, vault_real: str, dry: bool,
                   report: Report) -> bool:
    """Copies GOTCHAS as committed on `ref`. A project where it is not committed gets no note, and no complaint. True when the note is, or would be, in place."""
    entry = git(project, "ls-tree", ref, "--", GOTCHAS_PATH).split("\t")[0].split()
    if not entry:
        return False
    label = f"{name} - Gotchas"
    if entry[:2] not in (["100644", "blob"], ["100755", "blob"]):
        report.refused.append((label, f"{GOTCHAS_PATH} is not a regular file on {ref}"))
        return False
    note = os.path.join(base, f"{label}.md")
    used = taken_by(taken, label, note, vault)
    if used:
        report.refused.append((label, f"the name is already used by {used}"))
        return False
    text = git(project, "show", f"{ref}:{GOTCHAS_PATH}")
    if text.startswith("---"):
        report.refused.append((label, f"{GOTCHAS_PATH} starts with its own frontmatter, which would make a second block in the note"))
        return False
    log = git(project, "log", "--follow", "--format=%H %as", ref, "--", GOTCHAS_PATH).splitlines()  # newest first; --follow reaches before a move
    sha, days = log[0].split()[0][:8], [line.split()[1] for line in log]
    return write_note(note, render_gotchas(name, text, min(days), sha), vault_real, dry, report)


def sync(project: str, vault: str, name: str, ref: str | None = None, dry: bool = False, today: str | None = None) -> Report:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._ -]*", name):
        raise SyncError(f"project name {name!r} must be letters, digits, space, dot, dash or underscore")
    if not os.path.isdir(vault):
        raise SyncError(f"vault {vault!r} is not a folder")
    top = git(project, "rev-parse", "--show-toplevel", check=False).strip()
    if not top:
        raise SyncError(f"{project!r} is not a git repository")
    if os.path.realpath(top) != os.path.realpath(project):
        raise SyncError(f"{project!r} is inside a repository: run it on the repository's top folder, {top!r}")
    ref = ref or default_ref(project)
    today = today or datetime.date.today().isoformat()
    vault_real, report = os.path.realpath(vault), Report()
    base = os.path.join(vault, "Projects", name)
    decisions = os.path.join(base, "decisions")

    found = list_records(project, ref)
    if not found:
        raise SyncError(f"no decision records under docs/decisions on {ref}: wrong ref or wrong project? Nothing was changed")
    index_text = git(project, "show", f"{ref}:docs/decisions/README.md", check=False)
    index = {int(m.group(1)): first_status(m.group(2)) for m in map(INDEX_ROW.match, index_text.splitlines()) if m}
    taken = names_elsewhere(vault, decisions)

    records, names, paths, held, wrote = {}, {}, {}, set(), {}
    for number, entries in sorted(found.items()):
        if len(entries) > 1:
            held.add(number)
            report.refused.append((f"ADR {number:03d}", "two files carry this number: " + ", ".join(p for p, _ in entries)))
            continue
        path, slug = entries[0]
        card = card_name(number, slug)
        used = taken_by(taken, card, os.path.join(decisions, card + ".md"), vault)
        if used:
            held.add(number)
            report.refused.append((card, f"the name is already used by {used}"))
            continue
        text = git(project, "show", f"{ref}:{path}")
        records[number], names[number], paths[number] = parse_record(text, number, slug, index.get(number, "unknown")), card, path
    for number, rec in records.items():
        sha = git(project, "log", "-1", "--format=%H", ref, "--", paths[number]).strip()[:8]
        wrote[number] = write_note(os.path.join(decisions, names[number] + ".md"), render_card(rec, name, names, sha, paths[number]), vault_real, dry, report)
    rejected = os.path.join(base, f"{name} - Rejected ideas.md")
    used = taken_by(taken, f"{name} - Rejected ideas", rejected, vault)
    if used:
        report.refused.append((f"{name} - Rejected ideas", f"the name is already used by {used}"))
    else:
        write_note(rejected, render_rejected(name, list(records.values()), names), vault_real, dry, report)
    mirrored = mirror_gotchas(project, ref, name, base, taken, vault, vault_real, dry, report)
    hub = os.path.join(base, f"{name}.md")
    if not os.path.exists(hub) and name.lower() not in taken:  # a hub the owner keeps elsewhere is the hub
        write_note(hub, render_hub(name, today, mirrored), vault_real, dry, report)
    elif mirrored and os.path.exists(hub) and f"[[{name} - Gotchas" not in read_text(hub):  # the hub is the owner's: say so, never edit it
        report.hints.append(f"{os.path.relpath(hub, vault)} does not link to [[{name} - Gotchas]]: add the link if you want it")

    if os.path.isdir(decisions):
        for entry in sorted(os.listdir(decisions)):
            match = re.match(r"^(\d{3}) - .*\.md$", entry)
            if not match:
                continue
            old_path, number = os.path.join(decisions, entry), int(match.group(1))
            card_path = os.path.join(decisions, names[number] + ".md") if number in names else ""
            if number in held or (card_path and os.path.exists(card_path) and os.path.samefile(old_path, card_path)):
                continue  # refused above, or one file under two spellings (a case-insensitive filesystem)
            old = read_text(old_path)
            if not is_generated(old):
                continue
            if number in names and wrote.get(number):
                write_note(old_path, render_redirect(number, name, names[number]), vault_real, dry, report, report.redirected)
            elif number in names:
                report.refused.append((os.path.relpath(old_path, vault), "the new card was refused, so no redirect was written"))
            elif parse_frontmatter(old)[0].get("status") != "removed":
                write_note(old_path, render_tombstone(number, name, today), vault_real, dry, report, report.tombstoned)
    return report


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("project")
    ap.add_argument("vault")
    ap.add_argument("--name")
    ap.add_argument("--ref")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    try:
        report = sync(args.project, args.vault, args.name or os.path.basename(os.path.realpath(args.project)), args.ref, args.dry_run)
    except SyncError as e:
        print(f"vault_sync: {e}", file=sys.stderr)
        return 2
    prefix = "would " if args.dry_run else ""
    print(f"{prefix}created {len(report.created)}, updated {len(report.updated)}, unchanged {len(report.unchanged)}, "
          f"tombstoned {len(report.tombstoned)}, redirected {len(report.redirected)}, refused {len(report.refused)}")
    for label, reason in report.refused:
        print(f"refused: {label}: {reason}")
    for hint in report.hints:
        print(f"hint: {hint}")
    return 1 if report.refused else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
