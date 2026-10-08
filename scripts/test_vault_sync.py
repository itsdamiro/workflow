"""Tests for vault_sync.py on throwaway repositories and vaults. Run: python3 -m unittest discover -s scripts -p 'test_vault_sync.py'"""

import contextlib
import io
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(__file__))
import vault_sync as v  # noqa: E402

NEW = """---
type: decision
status: accepted
date: 2026-10-08
projects: [demo]
concepts: [round-trip-frugality]
amends: [1]
supersedes: []
tags: [type/decision, status/proposed, project/demo, topic/cost]  # status here is stale on purpose
---

# 002 — The second decision

> **Summary.** One line
> and a second line.

## Context

Facts.

## Decision

Do it.

## Alternatives rejected

- **Option A.** Not now because of cost.
- **Option B.** Never.

## Amendment (2026-10-09): changed the thing

Text.
"""
OLD = """# 001 — First decision: with a colon

> **Status: Accepted** (2026-09-27, the owner approved).

## Context

Facts.

## Decision

**Configured list:** a comma-separated list of paths. It is long.
Second line of the same paragraph.

Second paragraph, not in the summary.

## Alternatives rejected

- **Keep it.** Rejected.
"""
BARE = "# 003 — No status\n\n## Decision\n\nText.\n"
INDEX = "| # | Decision | Status |\n|---|---|---|\n| [001](001-first-decision.md) | First | Accepted |\n| [003](003-no-status.md) | No status | Proposed |\n"


def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, check=True).stdout


def put(repo, rel, text):
    path = os.path.join(repo, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def commit(repo, message="change"):
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo, self.vault = os.path.join(self.tmp.name, "demo"), os.path.join(self.tmp.name, "vault")
        os.makedirs(self.vault)
        git(self.tmp.name, "init", "-q", "-b", "main", self.repo)
        git(self.repo, "config", "user.name", "t")
        git(self.repo, "config", "user.email", "t@example.com")
        put(self.repo, "docs/decisions/001-first-decision.md", OLD)
        put(self.repo, "docs/decisions/002-second-decision.md", NEW)
        put(self.repo, "docs/decisions/003-no-status.md", BARE)
        put(self.repo, "docs/decisions/README.md", INDEX)
        put(self.repo, "docs/decisions/TEMPLATE.md", "# NNN — Title\n")
        commit(self.repo, "records")
        self.cards = os.path.join(self.vault, "Projects", "demo", "decisions")

    def sync(self, **kw):
        return v.sync(self.repo, self.vault, kw.pop("name", "demo"), **kw)

    def card(self, name):
        return read(os.path.join(self.cards, name + ".md"))


class Cards(Base):
    def test_a_card_for_each_record_and_none_for_the_index_or_template(self):
        report = self.sync()
        self.assertEqual(sorted(os.listdir(self.cards)), ["001 - First decision.md", "002 - Second decision.md", "003 - No status.md"])
        self.assertEqual((len(report.created), len(report.refused)), (5, 0))  # three cards, the rejected note, the hub

    def test_a_record_with_frontmatter(self):
        self.sync()
        text = self.card("002 - Second decision")
        for line in ("type: decision", "status: accepted", "created: 2026-10-08", "projects: [demo]", 'concepts: ["[[round-trip-frugality]]"]',
                     "adr: 2", "source: docs/decisions/002-second-decision.md", "generated: true",
                     "tags: [type/decision, status/accepted, project/demo, topic/cost]",
                     "# 002 — The second decision", "Project: [[demo]]",
                     "Amends: [[001 - First decision|ADR 001]]", "## Amendments", "- 2026-10-09: changed the thing",
                     "## Rejected alternatives", "- **Option A.** Not now because of cost.", "- **Option B.** Never."):
            with self.subTest(line=line):
                self.assertIn(line, text)

    def test_the_summary_is_exactly_the_summary_lines_and_nothing_after_them(self):
        self.sync()
        line = next(l for l in self.card("002 - Second decision").splitlines() if l.startswith("> **Summary.**"))
        self.assertEqual(line, "> **Summary.** One line and a second line.")

    def test_a_status_line_decides_when_the_index_has_no_row(self):
        put(self.repo, "docs/decisions/006-from-the-line.md", "# 006 — From the line\n\n> **Status: Proposed** (2026-10-01).\n")
        commit(self.repo)
        self.sync()
        text = self.card("006 - From the line")
        self.assertIn("status: proposed", text)
        self.assertIn("created: 2026-10-01", text)

    def test_a_rejected_alternative_wrapped_over_several_lines_is_one_bullet(self):
        put(self.repo, "docs/decisions/010-wrapped.md",
            "# 010 — Wrapped\n\n## Alternatives rejected\n\n- **Option C.** First part of the reason\n  and the second part.\n- **Option D.** Short.\n\nA closing paragraph, not a bullet.\n")
        commit(self.repo)
        self.sync()
        text = self.card("010 - Wrapped")
        self.assertIn("- **Option C.** First part of the reason and the second part.\n", text)
        self.assertIn("- **Option D.** Short.\n", text)
        self.assertNotIn("closing paragraph", text)

    def test_a_plain_status_line_with_a_name_before_the_date(self):
        put(self.repo, "docs/decisions/007-plain-status.md", "# 007. Plain status\n\nStatus: Accepted (damiro, 2026-10-01). Closes #99.\n\n## Context\n")
        put(self.repo, "docs/decisions/008-bold-colon.md", "# 008 — Bold colon\n\n> **Status:** Superseded by 009.\n")
        put(self.repo, "docs/decisions/009-prose.md", "# 009 — Prose\n\nStatus quo as of 2026-01-02 is not a status line.\n")
        commit(self.repo)
        self.sync()
        plain = self.card("007 - Plain status")
        self.assertIn("status: accepted", plain)
        self.assertIn("created: 2026-10-01", plain)
        self.assertIn("status: superseded", self.card("008 - Bold colon"))
        self.assertIn("status: unknown", self.card("009 - Prose"))
        self.assertNotIn("created:", self.card("009 - Prose"))

    def test_a_record_in_the_old_shape_takes_status_and_date_from_its_status_line_and_its_summary_from_the_decision(self):
        self.sync()
        text = self.card("001 - First decision")
        self.assertIn("status: accepted", text)
        self.assertIn("created: 2026-09-27", text)
        self.assertIn("> **Summary.** **Configured list:** a comma-separated list of paths. It is long. Second line of the same paragraph.", text)
        self.assertNotIn("Second paragraph", text)
        self.assertIn("concepts: []", text)

    def test_a_record_with_no_status_takes_the_index_row(self):
        self.sync()
        self.assertIn("status: proposed", self.card("003 - No status"))
        self.assertNotIn("created:", self.card("003 - No status"))

    def test_the_rejected_note_lists_only_records_that_have_alternatives(self):
        self.sync()
        text = read(os.path.join(self.vault, "Projects", "demo", "demo - Rejected ideas.md"))
        self.assertIn("## [[001 - First decision|ADR 001]]", text)
        self.assertIn("## [[002 - Second decision|ADR 002]]", text)
        self.assertNotIn("ADR 003", text)
        self.assertLess(text.index("ADR 001"), text.index("ADR 002"))
        self.assertIn("type: index", text)

    def rejected(self):
        return read(os.path.join(self.vault, "Projects", "demo", "demo - Rejected ideas.md"))

    def test_the_rejected_note_is_created_on_the_earliest_record_date(self):
        put(self.repo, "docs/decisions/004-earlier.md", "---\ndate: 2026-01-02\n---\n# 004 — Earlier\n\n## Alternatives rejected\n\n- **X.** No.\n")
        put(self.repo, "docs/decisions/005-junk-date.md", "---\ndate: 2025-soon\n---\n# 005 — Junk\n")
        commit(self.repo)
        self.sync()
        self.assertIn("\ncreated: 2026-01-02\n", self.rejected())

    def test_the_rejected_note_has_no_created_when_no_record_has_a_valid_date(self):
        records = [{"number": 1, "date": "", "rejected": []}, {"number": 2, "date": "soon", "rejected": []}]
        self.assertNotIn("created:", v.render_rejected("demo", records, {}))
        self.assertIn("\ncreated: 2026-03-04\n", v.render_rejected("demo", records + [{"number": 3, "date": "2026-03-04", "rejected": []}], {}))

    def test_the_rejected_note_is_unchanged_by_a_second_sync(self):
        self.sync()
        report = self.sync()
        self.assertEqual(report.updated, [])

    def test_a_record_in_a_nested_folder_is_not_a_record(self):
        put(self.repo, "docs/decisions/archive/009-old.md", "# 009 — Old\n")
        commit(self.repo)
        self.sync()
        self.assertFalse(os.path.exists(os.path.join(self.cards, "009 - Old.md")))

    def test_an_amends_link_to_a_record_that_does_not_exist_is_plain_text(self):
        put(self.repo, "docs/decisions/005-amends-a-ghost.md", "---\namends: [9]\n---\n# 005 — Ghost\n")
        commit(self.repo)
        self.sync()
        text = self.card("005 - Amends a ghost")
        self.assertIn("Amends: ADR 009\n", text)
        self.assertNotIn("[[", text.split("Amends:")[1].split("\n")[0])

    def test_a_project_name_with_a_space_is_quoted_and_its_tag_is_kebab_case(self):
        self.sync(name="My project")
        text = read(os.path.join(self.vault, "Projects", "My project", "decisions", "002 - Second decision.md"))
        self.assertIn('projects: ["My project"]', text)
        self.assertIn("project/my-project", text)
        self.assertIn("Project: [[My project]]", text)

    def test_a_long_decision_is_cut_at_a_word_with_an_ellipsis(self):
        put(self.repo, "docs/decisions/004-long.md", "# 004 — Long\n\n## Decision\n\n" + "word " * 200 + "\n")
        commit(self.repo)
        self.sync()
        line = next(l for l in self.card("004 - Long").splitlines() if l.startswith("> **Summary.**"))
        summary = line[len("> **Summary.** "):]
        self.assertTrue(summary.endswith("word…"))
        self.assertLessEqual(len(summary), v.SUMMARY_MAX + 1)


class Idempotence(Base):
    def test_a_second_run_changes_nothing(self):
        self.sync()
        before = {n: os.stat(os.path.join(self.cards, n)).st_mtime_ns for n in os.listdir(self.cards)}
        report = self.sync()
        self.assertEqual((len(report.created), len(report.updated), len(report.unchanged)), (0, 0, 4))  # the hub exists and is not touched
        self.assertEqual(before, {n: os.stat(os.path.join(self.cards, n)).st_mtime_ns for n in os.listdir(self.cards)})

    def test_a_dry_run_writes_nothing(self):
        report = self.sync(dry=True)
        self.assertEqual(len(report.created), 5)
        self.assertEqual(os.listdir(self.vault), [])

    def test_the_hub_is_made_once_and_never_overwritten(self):
        self.sync()
        hub = os.path.join(self.vault, "Projects", "demo", "demo.md")
        self.assertIn("type: project", read(hub))
        self.assertNotIn("generated", read(hub))
        with open(hub, "w") as f:
            f.write("mine\n")
        self.sync()
        self.assertEqual(read(hub), "mine\n")


class WhatIsRead(Base):
    def test_only_committed_text_is_read(self):
        put(self.repo, "docs/decisions/002-second-decision.md", NEW.replace("One line", "DRAFT line"))
        put(self.repo, "docs/decisions/004-draft.md", "# 004 — Draft\n")
        self.sync()
        self.assertNotIn("DRAFT", self.card("002 - Second decision"))
        self.assertFalse(os.path.exists(os.path.join(self.cards, "004 - Draft.md")))

    def test_a_ref_reads_that_commit(self):
        put(self.repo, "docs/decisions/002-second-decision.md", NEW.replace("One line", "Newer line"))
        commit(self.repo)
        self.sync(ref="HEAD~1")
        self.assertIn("One line", self.card("002 - Second decision"))

    def test_the_default_ref_is_the_local_main_or_master(self):
        self.assertEqual(v.default_ref(self.repo), "main")
        git(self.repo, "branch", "-m", "master")
        self.assertEqual(v.default_ref(self.repo), "master")

    def test_two_files_with_one_number_are_refused_and_an_old_card_is_kept(self):
        self.sync()
        before = self.card("001 - First decision")
        put(self.repo, "docs/decisions/001-other-take.md", OLD)
        commit(self.repo)
        report = self.sync()
        self.assertEqual([r[0] for r in report.refused], ["ADR 001"])
        self.assertEqual(self.card("001 - First decision"), before)


class Safety(Base):
    def test_a_note_that_is_not_generated_is_left_alone(self):
        os.makedirs(self.cards)
        mine = os.path.join(self.cards, "002 - Second decision.md")
        with open(mine, "w") as f:
            f.write("my own words\n")
        report = self.sync()
        self.assertEqual(read(mine), "my own words\n")
        self.assertEqual(len(report.refused), 1)
        self.assertEqual(len(report.created), 4)

    def test_a_name_already_used_elsewhere_in_the_vault_is_refused(self):
        os.makedirs(os.path.join(self.vault, "Ideas"))
        with open(os.path.join(self.vault, "Ideas", "002 - Second decision.md"), "w") as f:
            f.write("an idea\n")
        report = self.sync()
        self.assertEqual([r[0] for r in report.refused], ["002 - Second decision"])
        self.assertFalse(os.path.exists(os.path.join(self.cards, "002 - Second decision.md")))
        self.assertTrue(os.path.exists(os.path.join(self.cards, "001 - First decision.md")))

    def test_a_hidden_folder_does_not_count_as_a_name_in_use(self):
        os.makedirs(os.path.join(self.vault, ".trash"))
        with open(os.path.join(self.vault, ".trash", "002 - Second decision.md"), "w") as f:
            f.write("deleted\n")
        self.assertEqual(self.sync().refused, [])

    def test_a_hand_written_note_in_the_cards_folder_is_not_taken_for_a_removed_record(self):
        os.makedirs(self.cards)
        mine = os.path.join(self.cards, "009 - My own note.md")
        with open(mine, "w") as f:
            f.write("mine\n")
        report = self.sync()
        self.assertEqual((read(mine), report.tombstoned, report.refused), ("mine\n", [], []))

    def test_a_folder_that_leads_outside_the_vault_is_refused(self):
        outside = os.path.join(self.tmp.name, "outside")
        os.makedirs(outside)
        os.makedirs(os.path.join(self.vault, "Projects"))
        os.symlink(outside, os.path.join(self.vault, "Projects", "demo"))
        report = self.sync()
        self.assertEqual(os.listdir(outside), [])
        self.assertTrue(report.refused and all(r[1] == "outside the vault" for r in report.refused))

    def test_bad_arguments_are_errors(self):
        for kwargs in ({"name": "a/b"}, {"name": ""}, {"name": ".hidden"}):
            with self.subTest(kwargs=kwargs), self.assertRaises(v.SyncError):
                self.sync(**kwargs)
        with self.assertRaises(v.SyncError):
            v.sync(self.repo, os.path.join(self.tmp.name, "missing"), "demo")
        with self.assertRaisesRegex(v.SyncError, "not a git repository"):
            v.sync(self.tmp.name, self.vault, "demo")


class RemovalsAndRenames(Base):
    def test_a_removed_record_becomes_a_tombstone_that_stays_put(self):
        self.sync(today="2026-10-10")
        git(self.repo, "rm", "-q", "docs/decisions/003-no-status.md")
        commit(self.repo)
        report = self.sync(today="2026-10-11")
        self.assertEqual(len(report.tombstoned), 1)
        text = self.card("003 - No status")
        self.assertIn("status: removed", text)
        self.assertIn("seen missing on 2026-10-11", text)
        report = self.sync(today="2026-10-12")
        self.assertEqual(len(report.tombstoned), 0)
        self.assertIn("seen missing on 2026-10-11", self.card("003 - No status"))

    def test_a_renamed_record_leaves_a_redirect(self):
        self.sync()
        git(self.repo, "mv", "docs/decisions/002-second-decision.md", "docs/decisions/002-second-choice.md")
        commit(self.repo)
        report = self.sync()
        self.assertEqual(len(report.redirected), 1)
        old = self.card("002 - Second decision")
        self.assertIn("type: redirect", old)
        self.assertIn("[[002 - Second choice|ADR 002]]", old)
        self.assertIn("# 002 — The second decision", self.card("002 - Second choice"))
        again = self.sync()
        self.assertEqual((again.redirected, again.refused), ([], []))


class Parsing(unittest.TestCase):
    def test_frontmatter_subset(self):
        meta, body = v.parse_frontmatter('---\na: 1\nb: [x, "y, z", \'w\']  # note\nc: "quoted"\nd: []\n---\n\nBody\n')
        self.assertEqual(meta, {"a": "1", "b": ["x", "y, z", "w"], "c": "quoted", "d": []})
        self.assertEqual(body, "Body\n")
        self.assertEqual(v.parse_frontmatter("no frontmatter\n"), ({}, "no frontmatter\n"))
        self.assertEqual(v.parse_frontmatter("---\nunclosed\n"), ({}, "---\nunclosed\n"))
        rule = "# Title\n\ntext\n---\nkey: value\n---\nrest\n"  # a horizontal rule lower down is not frontmatter
        self.assertEqual(v.parse_frontmatter(rule), ({}, rule))

    def test_names_are_numbered_sentences_without_unsafe_characters(self):
        self.assertEqual(v.card_name(40, "the-persona-looks-up-notes-itself"), "040 - The persona looks up notes itself")
        self.assertEqual(v.card_name(7, "fix-a:b-[c]-#d"), "007 - Fix ab c d")
        long = v.card_name(1, "word-" * 40)
        self.assertLessEqual(len(long), len("001 - ") + v.NAME_MAX)
        self.assertEqual(v.card_name(2, "---"), "002 - Untitled")

    def test_scalar_fields_are_read_as_one_value(self):
        rec = v.parse_record("---\namends: 003\nconcepts: Round trip\n---\n# 5 — T\n", 5, "t", "unknown")
        self.assertEqual((rec["amends"], rec["concepts"]), ([3], ["Round trip"]))

    def test_status_words(self):
        for text, want in (("Accepted for stage 1", "accepted"), ("**Proposed**", "proposed"), ("Amended", "unknown"), ("", "unknown")):
            with self.subTest(text=text):
                self.assertEqual(v.first_status(text), want)


class Review(Base):
    """What the review of the first version found."""

    def test_values_that_yaml_would_misread_are_quoted_and_the_rest_stay_plain(self):
        for plain in ("demo", "topic/cost", "a.b-c_d", "docs/decisions/001-x.md"):
            with self.subTest(plain=plain):
                self.assertEqual(v.yq(plain), plain)
        for text in ("null", "2024", "a\\q", 'a"b', "x: y", "x #y", "yes", "", "é", "[a]", "True", "2026-10-08"):
            with self.subTest(text=text):
                self.assertNotEqual(v.yq(text), text)
                self.assertEqual(json.loads(v.yq(text)), text)

    def test_non_ascii_text_stays_readable_inside_quotes(self):
        self.assertEqual(v.yq("é"), '"é"')

    def test_repeated_tags_are_written_once(self):
        put(self.repo, "docs/decisions/016-twice.md", "---\ntags: [topic/cost, topic/cost, type/decision]\n---\n# 016 — Twice\n")
        commit(self.repo)
        self.sync()
        self.assertIn("tags: [type/decision, status/unknown, project/demo, topic/cost]\n", self.card("016 - Twice"))

    def test_a_record_that_is_not_valid_utf8_is_read_not_a_crash(self):
        path = os.path.join(self.repo, "docs", "decisions", "015-latin.md")
        with open(path, "wb") as f:
            f.write("# 015 - Caf\xe9\n\n## Decision\n\nCaf\xe9 au lait.\n".encode("latin-1"))
        commit(self.repo)
        self.sync()
        self.assertTrue(os.path.exists(os.path.join(self.cards, "015 - Latin.md")))

    def test_an_updated_note_keeps_its_file_mode(self):
        self.sync()
        card = os.path.join(self.cards, "001 - First decision.md")
        os.chmod(card, 0o600)
        put(self.repo, "docs/decisions/001-first-decision.md", OLD.replace("Facts.", "More facts.", 1) + "\n- extra line\n")
        commit(self.repo)
        put(self.repo, "docs/decisions/001-first-decision.md", OLD.replace("It is long.", "It is much longer."))
        commit(self.repo)
        self.assertEqual(len(self.sync().updated), 1)
        self.assertEqual(stat.S_IMODE(os.stat(card).st_mode), 0o600)

    def test_a_source_path_with_a_colon_is_quoted(self):
        put(self.repo, "docs/decisions/011-a: b.md", "# 011 — A\n")
        commit(self.repo)
        self.sync()
        self.assertIn('source: "docs/decisions/011-a: b.md"', self.card("011 - A b"))

    def test_a_record_with_a_non_ascii_name_is_not_dropped(self):
        put(self.repo, "docs/decisions/014-café.md", "# 014 — Café\n")
        commit(self.repo)
        self.sync()
        self.assertTrue(os.path.exists(os.path.join(self.cards, "014 - Café.md")))

    def test_a_note_that_is_not_valid_utf8_is_refused_not_a_crash(self):
        os.makedirs(self.cards)
        with open(os.path.join(self.cards, "002 - Second decision.md"), "wb") as f:
            f.write(b"caf\xe9\n")
        with open(os.path.join(self.cards, "009 - Latin one.md"), "wb") as f:
            f.write(b"caf\xe9\n")
        report = self.sync()
        self.assertEqual([r[0] for r in report.refused], [os.path.join("Projects", "demo", "decisions", "002 - Second decision.md")])
        self.assertEqual(report.tombstoned, [])
        with open(os.path.join(self.cards, "009 - Latin one.md"), "rb") as f:
            self.assertEqual(f.read(), b"caf\xe9\n")

    def test_a_ref_with_no_records_is_an_error_and_leaves_the_cards_alone(self):
        self.sync()
        before = self.card("001 - First decision")
        git(self.repo, "rm", "-q", "docs/decisions/001-first-decision.md", "docs/decisions/002-second-decision.md", "docs/decisions/003-no-status.md")
        commit(self.repo)
        with self.assertRaisesRegex(v.SyncError, "no decision records"):
            self.sync()
        self.assertEqual(self.card("001 - First decision"), before)

    def test_a_project_that_is_a_subfolder_of_a_repository_is_an_error(self):
        sub = os.path.join(self.repo, "sub")
        put(self.repo, "sub/docs/decisions/001-sub.md", "# 001 — Sub\n")
        commit(self.repo)
        with self.assertRaisesRegex(v.SyncError, "top folder"):
            v.sync(sub, self.vault, "sub")

    def test_a_redirect_is_not_written_when_the_new_card_was_refused(self):
        self.sync()
        git(self.repo, "mv", "docs/decisions/002-second-decision.md", "docs/decisions/002-second-choice.md")
        commit(self.repo)
        with open(os.path.join(self.cards, "002 - Second choice.md"), "w") as f:
            f.write("the owner's note\n")
        report = self.sync()
        self.assertEqual(report.redirected, [])
        self.assertIn("# 002 — The second decision", self.card("002 - Second decision"))
        self.assertEqual(self.card("002 - Second choice"), "the owner's note\n")
        self.assertTrue(any("002 - Second decision" in r[0] and "redirect" in r[1] for r in report.refused))

    def test_a_hub_elsewhere_is_not_duplicated(self):
        os.makedirs(os.path.join(self.vault, "Projects"))
        with open(os.path.join(self.vault, "Projects", "demo.md"), "w") as f:
            f.write("my hub\n")
        self.sync()
        self.assertFalse(os.path.exists(os.path.join(self.vault, "Projects", "demo", "demo.md")))

    def test_the_rejected_note_name_is_checked_like_a_card_name(self):
        os.makedirs(os.path.join(self.vault, "Ideas"))
        with open(os.path.join(self.vault, "Ideas", "demo - Rejected ideas.md"), "w") as f:
            f.write("mine\n")
        report = self.sync()
        self.assertEqual([r[0] for r in report.refused], ["demo - Rejected ideas"])
        self.assertFalse(os.path.exists(os.path.join(self.vault, "Projects", "demo", "demo - Rejected ideas.md")))

    def test_a_hand_written_rejected_note_at_its_own_path_is_left_alone(self):
        base = os.path.join(self.vault, "Projects", "demo")
        os.makedirs(base)
        with open(os.path.join(base, "demo - Rejected ideas.md"), "w") as f:
            f.write("mine\n")
        report = self.sync()
        self.assertEqual(read(os.path.join(base, "demo - Rejected ideas.md")), "mine\n")
        self.assertEqual(len(report.refused), 1)

    def test_a_name_that_differs_only_in_case_counts_as_in_use(self):
        os.makedirs(os.path.join(self.vault, "Ideas"))
        with open(os.path.join(self.vault, "Ideas", "002 - second decision.md"), "w") as f:
            f.write("x\n")
        self.assertEqual([r[0] for r in self.sync().refused], ["002 - Second decision"])

    def test_a_case_only_rename_never_turns_a_card_into_a_redirect_to_itself(self):
        self.sync()
        git(self.repo, "mv", "docs/decisions/002-second-decision.md", "docs/decisions/002-Second-Decision.md")
        commit(self.repo)
        for _ in range(2):
            self.sync()
        folded = [n for n in os.listdir(self.cards) if n.lower() == "002 - second decision.md"]
        if len(folded) == 1:  # a case-insensitive filesystem: one file, and it must still be a card
            self.assertIn("# 002 — The second decision", read(os.path.join(self.cards, folded[0])))

    def test_the_default_ref_follows_the_remote_head_to_a_local_branch(self):
        git(self.repo, "branch", "-m", "trunk")
        git(self.repo, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/trunk")
        self.assertEqual(v.default_ref(self.repo), "trunk")

    def test_a_status_line_beats_the_index_row(self):
        put(self.repo, "docs/decisions/README.md", INDEX + "| [011](011-differs.md) | D | Accepted |\n")
        put(self.repo, "docs/decisions/011-differs.md", "# 011 — Differs\n\n> **Status: Proposed**\n")
        commit(self.repo)
        self.sync()
        self.assertIn("status: proposed", self.card("011 - Differs"))

    def test_a_long_rejected_alternative_is_cut_at_a_word(self):
        put(self.repo, "docs/decisions/012-long-bullet.md", "# 012 — Long\n\n## Alternatives rejected\n\n- " + "word " * 100 + "\n")
        commit(self.repo)
        self.sync()
        bullet = next(l for l in self.card("012 - Long bullet").splitlines() if l.startswith("- word"))
        self.assertTrue(bullet.endswith("word…"))
        self.assertLessEqual(len(bullet), len("- ") + v.BULLET_MAX + 1)

    def test_a_long_summary_line_is_cut_too(self):
        put(self.repo, "docs/decisions/013-long-summary.md", "# 013 — Long\n\n> **Summary.** " + "word " * 200 + "\n")
        commit(self.repo)
        self.sync()
        line = next(l for l in self.card("013 - Long summary").splitlines() if l.startswith("> **Summary.**"))
        self.assertTrue(line.endswith("word…"))

    def test_the_footer_hash_has_a_fixed_length(self):
        self.sync()
        self.assertRegex(self.card("001 - First decision"), r" at `[0-9a-f]{8}`\.")

    def test_a_written_note_gets_the_ordinary_file_mode(self):
        self.sync()
        umask = os.umask(0)
        os.umask(umask)
        mode = stat.S_IMODE(os.stat(os.path.join(self.cards, "001 - First decision.md")).st_mode)
        self.assertEqual(mode, 0o666 & ~umask)

    def test_a_failed_write_leaves_no_temporary_file(self):
        original = os.replace
        def broken(*a, **k):
            raise OSError("disk full")
        os.replace = broken
        try:
            with self.assertRaises(OSError):
                self.sync()
        finally:
            os.replace = original
        leftovers = [n for _, _, files in os.walk(self.vault) for n in files if n.startswith(".sync-")]
        self.assertEqual(leftovers, [])

    def test_a_dry_run_reports_a_tombstone_without_writing_it(self):
        self.sync()
        git(self.repo, "rm", "-q", "docs/decisions/003-no-status.md")
        commit(self.repo)
        before = self.card("003 - No status")
        report = self.sync(dry=True)
        self.assertEqual(len(report.tombstoned), 1)
        self.assertEqual(self.card("003 - No status"), before)

    def test_a_dry_run_reports_a_redirect_without_writing_it(self):
        self.sync()
        git(self.repo, "mv", "docs/decisions/002-second-decision.md", "docs/decisions/002-second-choice.md")
        commit(self.repo)
        report = self.sync(dry=True)
        self.assertEqual((len(report.redirected), report.refused), (1, []))
        self.assertIn("# 002 — The second decision", self.card("002 - Second decision"))
        self.assertFalse(os.path.exists(os.path.join(self.cards, "002 - Second choice.md")))

    def test_a_removed_record_that_comes_back_is_a_card_again(self):
        self.sync()
        git(self.repo, "rm", "-q", "docs/decisions/003-no-status.md")
        commit(self.repo)
        self.sync()
        put(self.repo, "docs/decisions/003-no-status.md", BARE)
        commit(self.repo)
        self.sync()
        self.assertIn("# 003 — No status", self.card("003 - No status"))
        self.assertNotIn("status: removed", self.card("003 - No status"))

    def test_a_path_with_a_space_works(self):
        spaced = os.path.join(self.tmp.name, "my project")
        os.rename(self.repo, spaced)
        v.sync(spaced, self.vault, "my project")
        self.assertTrue(os.path.exists(os.path.join(self.vault, "Projects", "my project", "decisions", "001 - First decision.md")))

    def test_a_ref_that_does_not_exist_is_an_error(self):
        with self.assertRaises(v.SyncError):
            self.sync(ref="no-such-ref")


class Command(Base):
    def run_main(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = v.main(list(args))
        return code, out.getvalue(), err.getvalue()

    def test_exit_codes_and_report(self):
        code, out, _ = self.run_main(self.repo, self.vault)
        self.assertEqual(code, 0)
        self.assertIn("created 5, updated 0, unchanged 0, tombstoned 0, redirected 0, refused 0", out)
        os.makedirs(os.path.join(self.vault, "Ideas"))
        with open(os.path.join(self.vault, "Ideas", "003 - No status.md"), "w") as f:
            f.write("x\n")
        os.remove(os.path.join(self.cards, "003 - No status.md"))
        code, out, _ = self.run_main(self.repo, self.vault)
        self.assertEqual(code, 1)
        self.assertIn("refused: 003 - No status: the name is already used by Ideas/003 - No status.md", out)
        code, _, err = self.run_main(self.repo, os.path.join(self.tmp.name, "missing"))
        self.assertEqual(code, 2)
        self.assertIn("is not a folder", err)

    def test_the_project_name_defaults_to_the_folder_name(self):
        self.run_main(self.repo, self.vault)
        self.assertTrue(os.path.isdir(os.path.join(self.vault, "Projects", "demo")))

    def test_dry_run_says_would(self):
        _, out, _ = self.run_main(self.repo, self.vault, "--dry-run")
        self.assertTrue(out.startswith("would created 5"))


if __name__ == "__main__":
    unittest.main()
