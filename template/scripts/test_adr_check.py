"""Tests for adr_check.py (ADR 012). Usage: python3 -m unittest discover -s template/scripts -p 'test_adr_check.py'"""

import contextlib
import io
import os
import tempfile
import unittest

import adr_check as ac

GOOD = """---
type: decision
status: accepted
date: 2026-10-08
projects: [demo]
concepts: [Session length, Pattern scan]
amends: []
supersedes: []
tags: [type/decision, status/accepted, project/demo]
---

# 001 — A good record

> **Summary.** What, why, cost.

## Context
"""


def record(**changes) -> str:
    text = GOOD
    for old, new in changes.items():
        text = text.replace(old.replace("__", " "), new, 1) if new is not None else text
    return text


class Case(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = os.path.join(self.tmp.name, "docs", "decisions")
        os.makedirs(self.dir)
        self.put("README.md", "| [001](001-a-good-record.md) | A good record | Accepted |\n")
        self.put("001-a-good-record.md", GOOD)

    def put(self, name, text):
        with open(os.path.join(self.dir, name), "w", encoding="utf-8") as f:
            f.write(text)

    def found(self):
        return ac.check(self.dir, 1)

    def has(self, fragment):
        return any(fragment in line for line in self.found())


class Values(unittest.TestCase):
    def test_flow_lists_split_outside_quotes_only(self):
        self.assertEqual(ac.parse_value('["Cost, speed", a]'), ["Cost, speed", "a"])
        self.assertEqual(ac.parse_value("[a, b , c]"), ["a", "b", "c"])
        self.assertEqual(ac.parse_value("[Dan's note, b]"), ["Dan's note", "b"])
        self.assertEqual(ac.parse_value("[]"), [])

    def test_scalars_lose_quotes_and_comments(self):
        self.assertEqual(ac.parse_value(' "accepted" # x'), "accepted")
        self.assertEqual(ac.parse_value("a#b"), "a#b")


class Shape(Case):
    def test_a_good_record_passes(self):
        self.assertEqual(self.found(), [])

    def test_no_frontmatter(self):
        self.put("001-a-good-record.md", "# 001 — Old style\n\n> **Summary.** x\n")
        self.assertTrue(self.has("no frontmatter"))

    def test_unclosed_frontmatter_and_a_bad_line(self):
        self.put("001-a-good-record.md", "---\ntype: decision\n")
        self.assertTrue(self.has("not closed"))
        self.put("001-a-good-record.md", "---\ntype decision\n---\n")
        self.assertTrue(self.has("not a `key: value` line"))
        self.put("001-a-good-record.md", "---\nconcepts: [a, b\n---\n")
        self.assertTrue(self.has("the list is not closed"))

    def test_each_missing_field_is_named(self):
        for key in ac.REQUIRED:
            text = "\n".join(line for line in GOOD.split("\n") if not line.startswith(key + ":"))
            self.put("001-a-good-record.md", text)
            self.assertTrue(self.has(f"missing field: {key}"), key)

    def test_type_status_and_date_values(self):
        self.put("001-a-good-record.md", GOOD.replace("type: decision", "type: idea"))
        self.assertTrue(self.has("not decision"))
        self.put("001-a-good-record.md", GOOD.replace("status: accepted", "status: maybe"))
        self.assertTrue(self.has("status 'maybe'"))
        self.put("001-a-good-record.md", GOOD.replace("2026-10-08", "8 Oct"))
        self.assertTrue(self.has("is not YYYY-MM-DD"))

    def test_lists_must_be_lists(self):
        self.put("001-a-good-record.md", GOOD.replace("projects: [demo]", "projects: demo"))
        self.assertTrue(self.has("projects must be a list"))

    def test_projects_and_concepts_may_not_be_empty(self):
        self.put("001-a-good-record.md", GOOD.replace("projects: [demo]", "projects: []"))
        self.assertTrue(self.has("projects is empty"))
        self.put("001-a-good-record.md", GOOD.replace("concepts: [Session length, Pattern scan]", "concepts: []"))
        self.assertTrue(self.has("concepts is empty"))


    def test_concept_names_are_sentence_case_and_clean(self):
        for bad in ("session-length", "session length", "Pattern/scan", "A: b", "[[Pattern scan]]", "A | b", "A  b", "A^b", "A#b", "A\\b"):
            self.put("001-a-good-record.md", GOOD.replace("[Session length, Pattern scan]", f"[{bad}]"))
            self.assertTrue(self.has("sentence case"), bad)

    def test_quoted_concepts_are_read_without_the_quotes(self):
        self.put("001-a-good-record.md", GOOD.replace("[Session length, Pattern scan]", '["Session length"]'))
        self.assertEqual(self.found(), [])

    def test_tags_must_carry_the_type_and_status(self):
        self.put("001-a-good-record.md", GOOD.replace("type/decision, ", ""))
        self.assertTrue(self.has("tags lack type/decision"))
        self.put("001-a-good-record.md", GOOD.replace("status/accepted", "status/proposed"))
        self.assertTrue(self.has("tags lack status/accepted"))

    def test_the_summary_line(self):
        self.put("001-a-good-record.md", GOOD.replace("> **Summary.** What, why, cost.", "Just text."))
        self.assertTrue(self.has("no `> **Summary.**` line"))
        self.put("001-a-good-record.md", GOOD.replace("> **Summary.** What, why, cost.", "> **Summary.**"))
        self.assertTrue(self.has("no `> **Summary.**` line"))

    def test_the_heading_must_carry_the_number(self):
        self.put("001-a-good-record.md", GOOD.replace("# 001 — A good record", "# 002 — A good record"))
        self.assertTrue(self.has("must start with `# 001`"))
        self.put("001-a-good-record.md", GOOD.replace("# 001 — A good record", "# A good record"))
        self.assertTrue(self.has("must start with `# 001`"))

    def test_a_longer_number_in_the_heading_is_not_the_number(self):
        self.put("001-a-good-record.md", GOOD.replace("# 001 — A good record", "# 0011 — A good record"))
        self.assertTrue(self.has("must start with `# 001`"))

    def test_quoted_scalars_are_read_without_the_quotes(self):
        self.put("001-a-good-record.md", GOOD.replace("status: accepted", 'status: "accepted"'))
        self.assertEqual(self.found(), [])

    def test_a_list_where_a_single_value_belongs_is_a_problem_not_a_crash(self):
        self.put("001-a-good-record.md", GOOD.replace("status: accepted", "status: [accepted]"))
        self.assertTrue(self.has("status must be a single value"))
        self.put("001-a-good-record.md", GOOD.replace("type: decision", "type: [decision]"))
        self.assertTrue(self.has("type must be a single value"))
        self.put("001-a-good-record.md", GOOD.replace("date: 2026-10-08", "date: [2026-10-08]"))
        self.assertTrue(self.has("date must be a single value"))

    def test_a_file_that_is_not_utf8_is_a_problem_not_a_crash(self):
        with open(os.path.join(self.dir, "001-a-good-record.md"), "wb") as f:
            f.write(b"\xff not text")
        self.assertTrue(self.has("not UTF-8"))

    def test_block_lists_are_read_like_flow_lists(self):
        text = GOOD.replace("concepts: [Session length, Pattern scan]", "concepts:\n  - Session length\n  - \"Pattern scan\"")
        self.put("001-a-good-record.md", text)
        self.assertEqual(self.found(), [])
        self.put("001-a-good-record.md", text.replace("  - Session length\n  - \"Pattern scan\"", ""))
        self.assertTrue(self.has("concepts must be a list"))

    def test_a_comma_inside_quotes_does_not_split_a_name(self):
        self.put("001-a-good-record.md", GOOD.replace("[Session length, Pattern scan]", '["Cost, speed", Pattern scan]'))
        self.assertEqual(self.found(), [])

    def test_a_name_may_start_with_a_digit_but_not_a_lowercase_letter(self):
        self.put("001-a-good-record.md", GOOD.replace("[Session length, Pattern scan]", "[3D printing]"))
        self.assertEqual(self.found(), [])
        self.put("001-a-good-record.md", GOOD.replace("[Session length, Pattern scan]", "[3d Printing, éclair]"))
        self.assertEqual(len([line for line in self.found() if "sentence case" in line]), 1)

    def test_every_block_item_is_kept(self):
        self.put("001-a-good-record.md", GOOD.replace("[Session length, Pattern scan]", "\n  - bad name\n  - Good name"))
        self.assertEqual(len([line for line in self.found() if "sentence case" in line]), 1)

    def test_a_stray_list_item_after_a_filled_value_is_a_problem_not_a_crash(self):
        self.put("001-a-good-record.md", GOOD.replace("status: accepted", "status: accepted\n  - extra"))
        self.assertTrue(self.has("not a `key: value` line"))

    def test_the_index_row(self):
        self.put("README.md", "| nothing |\n")
        self.assertTrue(self.has("no row in README.md"))
        os.remove(os.path.join(self.dir, "README.md"))
        self.assertTrue(self.has("no row in README.md"))

    def test_a_row_for_another_file_does_not_count(self):
        self.put("README.md", "| [001](001-other.md) |\n")
        self.assertTrue(self.has("no row in README.md"))

    def test_a_byte_order_mark_is_ignored(self):
        with open(os.path.join(self.dir, "001-a-good-record.md"), "w", encoding="utf-8-sig") as f:
            f.write(GOOD)
        self.assertEqual(self.found(), [])



class Selection(Case):
    def test_only_numbered_record_files_are_read(self):
        self.put("TEMPLATE.md", "no frontmatter")
        self.put("notes.md", "no frontmatter")
        self.put("1-short.md", "no frontmatter")
        self.assertEqual(self.found(), [])

    def test_from_skips_older_records(self):
        self.put("001-a-good-record.md", "# 001 — Old style\n")
        self.assertEqual(ac.check(self.dir, 2), [])
        self.assertTrue(ac.check(self.dir, 1))


    def test_a_missing_directory_is_not_a_problem(self):
        self.assertEqual(ac.check(os.path.join(self.tmp.name, "nope"), 1), [])

    def test_problems_name_the_file(self):
        self.put("002-two.md", "# 002 — Old style\n")
        self.assertTrue(all(line.startswith(self.dir + "/002-two.md: ") for line in self.found()))


class Command(Case):
    def run_cli(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = ac.main(list(args))
        return code, out.getvalue()

    def test_ok_exits_zero(self):
        self.assertEqual(self.run_cli("--dir", self.dir), (0, "decision records ok\n"))

    def test_problems_exit_one_with_a_count(self):
        self.put("002-two.md", "# 002 — Old style\n")
        code, out = self.run_cli("--dir", self.dir)
        self.assertEqual(code, 1)
        self.assertIn("002-two.md: no frontmatter\n", out)
        self.assertTrue(out.endswith("1 problem(s)\n"))

    def test_from_is_passed_on(self):
        self.put("002-two.md", "# 002 — Old style\n")
        self.assertEqual(self.run_cli("--dir", self.dir, "--from", "3")[0], 0)


if __name__ == "__main__":
    unittest.main()
