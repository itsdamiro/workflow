"""Tests for stats_line.py on throwaway repositories and vaults. Run: python3 -m unittest discover -s scripts -p 'test_stats_line.py'"""

import contextlib
import io
import os
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(__file__))
import stats_line as s  # noqa: E402
import vault_lint  # noqa: E402
import vault_sync as v  # noqa: E402
from test_vault_sync import git, put, read  # noqa: E402


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo, self.vault = os.path.join(self.tmp.name, "demo"), os.path.join(self.tmp.name, "vault")
        os.makedirs(self.vault)
        git(self.tmp.name, "init", "-q", "-b", "main", self.repo)
        git(self.repo, "config", "user.name", "t")
        git(self.repo, "config", "user.email", "t@example.com")
        self.note = os.path.join(self.vault, "Projects", "demo", "demo - Stats.md")
        self.n = 0
        self.commit("first work")

    def commit(self, subject):
        self.n += 1
        put(self.repo, f"f{self.n}.txt", "x\n")
        git(self.repo, "add", f"f{self.n}.txt")
        git(self.repo, "commit", "-q", "-m", subject)

    def head(self):
        return git(self.repo, "rev-parse", "HEAD").strip()[:8]

    def add(self, **kw):
        kw.setdefault("today", "2026-10-08")
        return s.add_row(self.repo, self.vault, "demo", **kw)

    def rows(self):
        return [line for line in read(self.note).splitlines() if re.match(r"^\| \d{4}-", line)]

    def cells(self, row):
        return [c.strip() for c in re.split(r"(?<!\\)\|", row)[1:-1]]


class Rows(Base):
    def test_the_first_row_makes_the_note_with_the_head_its_subject_and_a_dash_for_the_count(self):
        report = self.add(context=148200)
        self.assertEqual(report.created, ["Projects/demo/demo - Stats.md"])
        self.assertEqual(self.cells(self.rows()[0]), ["2026-10-08", self.head(), "–", "`first work`", "148200"])
        meta = v.parse_frontmatter(read(self.note))[0]
        self.assertEqual((meta["type"], meta["status"], meta["generated"], meta["created"], meta["source"]),
                         ("reference", "active", "true", "2026-10-08", "git log"))
        self.assertEqual(meta["tags"], ["type/reference", "status/active", "project/demo"])
        self.assertIn("| Day | Commit | Commits since the last row | First and last subject | Context at close |", read(self.note))

    def test_no_context_is_a_dash(self):
        self.add()
        self.assertEqual(self.cells(self.rows()[0])[4], "–")

    def test_a_later_row_counts_the_commits_since_and_shows_the_oldest_and_newest_subject(self):
        self.add()
        for subject in ("second", "third", "fourth"):
            self.commit(subject)
        self.add(today="2026-10-09", context=90000)
        self.assertEqual(self.cells(self.rows()[1]), ["2026-10-09", self.head(), "3", "`second` → `fourth`", "90000"])

    def test_one_commit_since_shows_one_subject(self):
        self.add()
        self.commit("only one")
        self.add()
        self.assertEqual(self.cells(self.rows()[1])[2:4], ["1", "`only one`"])

    def test_a_second_run_on_the_same_head_changes_nothing_whatever_the_context(self):
        self.add(context=1)
        before = read(self.note)
        report = self.add(context=999)
        self.assertEqual((read(self.note), report.created, report.updated, report.unchanged), (before, [], [], ["Projects/demo/demo - Stats.md"]))

    def test_existing_text_is_kept_byte_for_byte_even_when_the_owner_edited_a_row(self):
        self.add(context=100)
        edited = read(self.note).replace("| 100 |", "| 111 |  ").replace("Back to", "Back (edited) to") + "\n\n"  # trailing blank lines are the owner's too
        with open(self.note, "w", encoding="utf-8") as f:
            f.write(edited)
        self.commit("next")
        self.add()
        self.assertTrue(read(self.note).startswith(edited))
        self.assertEqual(len(self.rows()), 2)
        self.assertEqual(v.parse_frontmatter(read(self.note))[0]["created"], "2026-10-08")

    def test_a_note_without_a_final_newline_gets_its_row_on_a_new_line(self):
        self.add()
        trimmed = read(self.note).rstrip("\n")
        with open(self.note, "w", encoding="utf-8") as f:
            f.write(trimmed)
        self.commit("next")
        self.add()
        self.assertEqual(len(self.rows()), 2)

    def test_a_dry_run_writes_nothing(self):
        report = self.add(dry=True)
        self.assertEqual(report.created, ["Projects/demo/demo - Stats.md"])
        self.assertFalse(os.path.exists(self.note))
        self.add()
        before = read(self.note)
        self.commit("next")
        self.assertEqual(self.add(dry=True).updated, ["Projects/demo/demo - Stats.md"])
        self.assertEqual(read(self.note), before)

    def test_a_previous_commit_that_history_no_longer_holds_gives_a_dash_and_the_head_subject(self):
        self.commit("second")
        self.add()
        git(self.repo, "reset", "-q", "--hard", "HEAD~1")
        self.commit("rewritten")
        self.add()
        self.assertEqual(self.cells(self.rows()[1])[2:4], ["–", "`rewritten`"])

    def test_a_previous_commit_on_another_branch_is_not_an_ancestor(self):
        git(self.repo, "checkout", "-q", "-b", "side")
        self.commit("on the side")
        self.add(ref="side")
        git(self.repo, "checkout", "-q", "main")
        self.commit("on main")
        self.add(ref="main")
        self.assertEqual(self.cells(self.rows()[1])[2], "–")

    def test_a_ref_is_read_not_the_checked_out_branch(self):
        git(self.repo, "checkout", "-q", "-b", "side")
        self.commit("only on side")
        self.add(ref="main")
        self.assertEqual(self.cells(self.rows()[0])[3], "`first work`")


class Subjects(Base):
    def test_a_pipe_a_link_a_tag_and_a_backtick_cannot_break_the_row_or_reach_the_lint(self):
        self.commit("fix a|b, see [[Some Note]] and #tag and `code`")
        self.add()
        row = self.rows()[0]
        self.assertEqual(len(self.cells(row)), 5)
        self.assertNotIn("Some Note", vault_lint.prose(read(self.note)))
        self.assertIn("fix a\\|b", row)

    def test_a_long_subject_is_cut_at_a_word_with_an_ellipsis(self):
        self.commit("word " * 40)
        self.add()
        shown = self.cells(self.rows()[0])[3]
        self.assertTrue(shown.endswith("word…`"))
        self.assertLessEqual(len(shown), s.SUBJECT_MAX + 3)

    def test_a_subject_of_exactly_the_limit_is_not_cut(self):
        subject = "x" * s.SUBJECT_MAX
        self.assertEqual(s.cell(subject), f"`{subject}`")
        self.assertEqual(s.cell("x" * s.SUBJECT_MAX + "y")[-2], "…")


class Git(Base):
    def test_a_git_failure_other_than_a_missing_commit_is_an_error_not_a_dash(self):
        self.add()
        self.commit("next")
        real = subprocess.run

        def broken(cmd, *a, **kw):
            if "merge-base" in cmd:
                return subprocess.CompletedProcess(cmd, 2, "", "fatal: broken")
            return real(cmd, *a, **kw)

        with mock.patch.object(s.subprocess, "run", broken):
            with self.assertRaises(v.SyncError):
                self.add()
        self.assertEqual(len(self.rows()), 1)

    def test_a_previous_commit_that_is_not_in_the_repository_at_all_is_a_dash(self):
        self.add()
        gone = read(self.note).replace(self.head(), "deadbeef")
        with open(self.note, "w", encoding="utf-8") as f:
            f.write(gone)
        self.commit("next")
        self.add()
        self.assertEqual(self.cells(self.rows()[1])[2:4], ["–", "`next`"])

    def test_an_empty_subject_is_shown_as_such(self):
        self.assertEqual(s.cell(""), "`(no subject)`")

    def test_the_report_carries_the_row_it_wrote(self):
        self.assertTrue(self.add().row.startswith("| 2026-10-08 |"))


class Refusals(Base):
    def test_a_note_with_rows_but_no_generated_marker_gets_no_row(self):
        self.add()
        unmarked = read(self.note).replace("generated: true", "generated: false")
        with open(self.note, "w", encoding="utf-8") as f:
            f.write(unmarked)
        self.commit("next")
        report = self.add()
        self.assertEqual(read(self.note), unmarked)
        self.assertEqual([label for label, _ in report.refused], ["Projects/demo/demo - Stats.md"])

    def test_a_note_that_is_not_generated_is_left_alone(self):
        put(self.vault, "Projects/demo/demo - Stats.md", "---\ntype: reference\n---\nMine.\n")
        report = self.add()
        self.assertEqual(read(self.note), "---\ntype: reference\n---\nMine.\n")
        self.assertEqual([label for label, _ in report.refused], ["Projects/demo/demo - Stats.md"])
        self.assertIn("not marked generated", report.refused[0][1])  # said before anything about its rows

    def test_a_name_already_used_elsewhere_in_the_vault_is_refused(self):
        put(self.vault, "Elsewhere/demo - Stats.md", "---\ntype: reference\n---\nMine.\n")
        report = self.add()
        self.assertFalse(os.path.exists(self.note))
        self.assertEqual([label for label, _ in report.refused], ["demo - Stats"])

    def test_a_note_whose_last_line_is_not_a_row_is_refused_untouched(self):
        self.add()
        with open(self.note, "a", encoding="utf-8") as f:
            f.write("\nA remark the owner added.\n")
        before = read(self.note)
        self.commit("next")
        report = self.add()
        self.assertEqual(read(self.note), before)
        self.assertEqual(len(report.refused), 1)

    def test_an_empty_note_is_refused_not_a_crash(self):
        put(self.vault, "Projects/demo/demo - Stats.md", "")
        self.assertEqual(len(self.add().refused), 1)

    def test_bad_inputs_are_errors(self):
        with self.assertRaises(v.SyncError):
            s.add_row(self.repo, os.path.join(self.tmp.name, "nope"), "demo")
        with self.assertRaises(v.SyncError):
            s.add_row(self.repo, self.vault, "bad/name")
        with self.assertRaises(v.SyncError):
            s.add_row(self.vault, self.vault, "demo")


class Hub(Base):
    def hub(self, text):
        put(self.vault, "Projects/demo/demo.md", text)

    def test_an_existing_hub_is_never_edited_but_the_missing_link_is_hinted(self):
        self.hub("---\ntype: project\n---\nMine.\n")
        report = self.add()
        self.assertEqual(read(os.path.join(self.vault, "Projects", "demo", "demo.md")), "---\ntype: project\n---\nMine.\n")
        self.assertEqual(len(report.hints), 1)
        self.assertIn("[[demo - Stats]]", report.hints[0])

    def test_no_hint_when_the_hub_links_or_is_missing(self):
        self.assertEqual(self.add().hints, [])
        self.commit("next")
        self.hub("See [[demo - Stats]].\n")
        self.assertEqual(self.add().hints, [])


class Command(Base):
    def run_main(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = s.main([self.repo, self.vault, *argv])
            except SystemExit as e:
                code = e.code
        return code, out.getvalue(), err.getvalue()

    def test_exit_codes_and_report(self):
        code, out, _ = self.run_main("--context-tokens", "5")
        self.assertEqual(code, 0)
        self.assertIn("created 1, updated 0, unchanged 0, refused 0", out)
        self.assertIn("row: | ", out)
        code, out, _ = self.run_main()
        self.assertEqual((code, "row:" in out), (0, False))
        put(self.vault, "Projects/demo/demo - Stats.md", "---\ntype: reference\n---\nMine.\n")
        self.assertEqual(self.run_main()[0], 1)
        self.assertEqual(self.run_main("--context-tokens", "-1")[0], 2)
        self.assertEqual(self.run_main("--name", "bad/name")[0], 2)

    def test_the_project_name_defaults_to_the_folder_name_and_dry_run_says_would(self):
        code, out, _ = self.run_main("--dry-run")
        self.assertIn("would created 1", out)
        self.assertFalse(os.path.exists(self.note))

    def test_the_sync_leaves_the_stats_note_alone(self):
        put(self.repo, "docs/decisions/001-first.md", "# 001 — First\n\n## Decision\n\nText.\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "record")
        self.add()
        before = read(self.note)
        v.sync(self.repo, self.vault, "demo")
        self.assertEqual(read(self.note), before)


if __name__ == "__main__":
    unittest.main()
