"""Tests for close_slice.py on throwaway repositories and vaults. Run: python3 -m unittest discover -s scripts -p 'test_close_slice.py'"""

import contextlib
import io
import os
import re
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(__file__))
import close_slice as c  # noqa: E402
import test_vault_lint as tl  # noqa: E402
import test_vault_sync as ts  # noqa: E402

TAGS = tl.TAGS.replace("folder-definition", "folder-definition, reference, index, pattern")
FRONT = "---\ntype: {}\nstatus: {}\ncreated: 2026-10-08\ntags: [type/{}, status/{}, topic/mind]\n---\n"
GARDEN = FRONT.format("project", "active", "project", "active") + "[[Tags]] [[demo]]\n"
HUB = FRONT.format("project", "active", "project", "active") + "Back to [[Garden]]. [[demo - Rejected ideas]]\n"
CONCEPT = FRONT.format("concept", "accepted", "concept", "accepted") + "Back to [[Garden]]. [[002 - Second decision]]\n"


class Close(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo, self.vault = os.path.join(self.tmp.name, "demo"), os.path.join(self.tmp.name, "vault")
        os.makedirs(self.vault)
        ts.git(self.tmp.name, "init", "-q", "-b", "main", self.repo)
        ts.git(self.repo, "config", "user.name", "t")
        ts.git(self.repo, "config", "user.email", "t@example.com")
        ts.put(self.repo, "docs/decisions/002-second-decision.md", ts.NEW)
        ts.put(self.repo, "docs/decisions/README.md", "| # | Decision | Status |\n|---|---|---|\n")
        ts.commit(self.repo, "records")
        for rel, text in (("Tags.md", TAGS), ("Garden.md", GARDEN), ("Projects/demo/demo.md", HUB)):
            ts.put(self.vault, rel, text)

    def close(self, *extra):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = c.main([self.repo, self.vault, *extra])
        return code, out.getvalue(), err.getvalue()

    def test_a_clean_close_exits_0_and_shows_the_three_results(self):
        ts.put(self.vault, "Concepts/round-trip-frugality.md", CONCEPT)
        code, out, _ = self.close("--context-tokens", "1234")
        self.assertEqual(code, 0, out)
        self.assertRegex(out, r"(?m)^sync:  created 2, ")
        self.assertRegex(out, r"(?m)^stats: created 1, ")
        self.assertIn("| 1234 |", out)  # the row carries the context size
        self.assertRegex(out, r"(?m)^lint:  0 error\(s\), \d+ warning\(s\)$")
        self.assertNotIn("do not push", out)

    def test_a_lint_error_exits_1_lists_the_error_and_says_not_to_push(self):
        code, out, _ = self.close()  # the record names a concept that has no note
        self.assertEqual(code, 1)
        self.assertIn("missing-concept", out)
        self.assertIn("do not push", out)

    def test_the_lint_reads_the_stats_note_the_close_just_wrote(self):
        ts.put(self.vault, "Concepts/round-trip-frugality.md", CONCEPT)
        ts.put(self.vault, "Projects/demo/demo.md", HUB.replace("[[demo - Rejected ideas]]", "[[demo - Rejected ideas]] [[demo - Stats]]"))
        code, out, _ = self.close()
        self.assertEqual(code, 0, out)  # a link to the stats note resolves only if the stats step ran first

    def test_the_lint_is_given_the_repo_so_a_pattern_citation_is_checked(self):
        ts.put(self.vault, "Concepts/round-trip-frugality.md", CONCEPT)
        draft = ("---\ntype: pattern\nstatus: draft\ncreated: 2026-10-08\nprojects: [demo]\ncode: {}\n"
                 "tags: [type/pattern, status/draft, project/demo, topic/mind]\n---\nBack to [[Garden]].\n")
        ts.put(self.vault, "Patterns/Cites.md", draft.format("docs/gone.md:1-2"))
        _, missing, _ = self.close()
        ts.put(self.vault, "Patterns/Cites.md", draft.format("docs/decisions/README.md:1-2"))
        _, present, _ = self.close()
        count = lambda out: int(re.search(r"(\d+) warning\(s\)", out).group(1))  # noqa: E731
        self.assertEqual(count(missing), count(present) + 1)

    def test_a_dry_run_writes_nothing(self):
        ts.put(self.vault, "Concepts/round-trip-frugality.md", CONCEPT)
        code, out, _ = self.close("--dry-run")
        self.assertIn("would created", out)
        self.assertFalse(os.path.exists(os.path.join(self.vault, "Projects", "demo", "decisions")))

    def test_a_failing_script_exits_2_and_says_which(self):
        os.remove(os.path.join(self.vault, "Tags.md"))
        code, _, err = self.close()
        self.assertEqual(code, 2)
        self.assertIn("close_slice: the lint failed", err)

    def test_a_project_with_no_records_exits_2_from_the_sync(self):
        empty = os.path.join(self.tmp.name, "empty")
        ts.git(self.tmp.name, "init", "-q", "-b", "main", empty)
        ts.git(empty, "config", "user.name", "t")
        ts.git(empty, "config", "user.email", "t@example.com")
        ts.put(empty, "a.txt", "x\n")
        ts.commit(empty, "first")
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = c.main([empty, self.vault])
        self.assertEqual(code, 2)
        self.assertIn("close_slice: the sync failed", err.getvalue())


if __name__ == "__main__":
    unittest.main()
