"""Tests for close_slice.py on throwaway repositories and vaults. Run: python3 -m unittest discover -s scripts -p 'test_close_slice.py'"""

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
import close_slice as c  # noqa: E402
import test_vault_lint as tl  # noqa: E402
import test_vault_sync as ts  # noqa: E402

TAGS = tl.TAGS.replace("folder-definition", "folder-definition, reference, index, pattern")
FRONT = "---\ntype: {}\nstatus: {}\ncreated: 2026-10-08\ntags: [type/{}, status/{}, topic/mind]\n---\n"
GARDEN = FRONT.format("project", "active", "project", "active") + "[[Tags]] [[demo]]\n"
HUB = FRONT.format("project", "active", "project", "active") + "Back to [[Garden]]. [[demo - Rejected ideas]]\n"
GENERATED = "---\ntype: decision\nstatus: accepted\ncreated: 2026-10-08\nprojects: [demo]\ngenerated: true\ntags: [type/decision, status/accepted, project/demo, topic/mind]\n---\nBack to [[Garden]].\n{}"
DRAFT = ("---\ntype: pattern\nstatus: draft\ncreated: 2026-10-08\nprojects: [demo]\n"
         "tags: [type/pattern, status/draft, project/demo, topic/mind]\n---\nBack to [[Garden]].\n")
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
        return self.close_at(self.vault, *extra)

    def close_at(self, vault, *extra):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = c.main([self.repo, vault, *extra])
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

    def test_a_hint_names_a_value_tags_md_lacks_that_the_writer_needs_and_stops_when_it_is_listed(self):
        ts.put(self.vault, "Concepts/round-trip-frugality.md", CONCEPT)
        code, out, _ = self.close()
        self.assertEqual(code, 0, out)
        self.assertIn("hint: Tags.md does not list type/capture", out)
        self.assertNotIn("status/draft", out)
        ts.put(self.vault, "Tags.md", TAGS.replace("folder-definition", "folder-definition, capture", 1))
        self.assertNotIn("hint: Tags.md", self.close()[1])

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

    def test_the_block_lists_the_vault_notes_created_then_updated_and_never_a_note_it_did_not_touch(self):
        ts.put(self.vault, "Concepts/round-trip-frugality.md", CONCEPT)
        code, first, _ = self.close()
        self.assertEqual(code, 0, first)
        self.assertRegex(first, r"(?m)^vault: 3 note\(s\) created, 0 updated$")
        self.assertIn("created: Projects/demo/decisions/002 - Second decision.md", first)
        self.assertIn("created: Projects/demo/demo - Stats.md", first)
        ts.put(self.repo, "notes.txt", "x\n")
        ts.commit(self.repo, "another")  # a new commit makes the stats note gain a row
        _, second, _ = self.close()
        self.assertRegex(second, r"(?m)^vault: 0 note\(s\) created, 1 updated$")
        self.assertIn("updated: Projects/demo/demo - Stats.md", second)
        self.assertNotIn("Garden.md", first + second)  # the owner's notes were not written, so they are not listed

    def test_a_close_that_writes_nothing_says_so(self):
        ts.put(self.vault, "Concepts/round-trip-frugality.md", CONCEPT)
        self.close()
        _, again, _ = self.close()
        self.assertNotIn("created:", again)
        self.assertRegex(again, r"(?m)^vault: no note changed$")

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

    def vault_repo(self, remote=False):
        """Make the vault a git repository of its own with its concept note committed; with a remote, level with it."""
        ts.put(self.vault, "Concepts/round-trip-frugality.md", CONCEPT)
        ts.git(self.tmp.name, "init", "-q", "-b", "main", self.vault)
        ts.git(self.vault, "config", "user.name", "vault-owner")
        ts.git(self.vault, "config", "user.email", "vault@example.com")
        ts.put(self.vault, "Projects/demo/Old.md", GENERATED.format("old\n"))
        ts.put(self.vault, "Projects/demo/[x] a*.md", GENERATED.format("one\n"))
        ts.put(self.vault, "Projects/demo/x a1.md", FRONT.format("project", "active", "project", "active") + "Back to [[Garden]].\n")
        ts.put(self.vault, "Projects/demo/Moved.md", GENERATED.format("moved\n"))
        ts.commit(self.vault, "the owner's vault")
        if remote:
            bare = os.path.join(self.tmp.name, "remote.git")
            ts.git(self.tmp.name, "init", "-q", "--bare", bare)
            ts.git(self.vault, "remote", "add", "origin", bare)
            ts.git(self.vault, "push", "-q", "-u", "origin", "main")

    def committed(self, rev="HEAD"):
        return set(ts.git(self.vault, "show", "--name-only", "--format=", rev).splitlines())

    def test_the_close_commits_the_changed_generated_notes_by_path_and_leaves_everything_else(self):
        self.vault_repo()
        os.remove(os.path.join(self.vault, "Projects/demo/Old.md"))  # a deletion is the owner's act
        ts.put(self.vault, "Projects/demo/[x] a*.md", GENERATED.format("two\n"))  # a generated note whose name holds glob characters
        ts.put(self.vault, "Projects/demo/x a1.md", FRONT.format("project", "active", "project", "active") + "Back to [[Garden]]. Edited.\n")
        ts.put(self.vault, "Garden.md", GARDEN + "A line the owner staged.\n")
        ts.git(self.vault, "add", "Garden.md")
        ts.put(self.vault, "Patterns/Draft.md", DRAFT)  # a model draft
        ts.put(self.vault, ".trash/Old.md", GENERATED.format("trash\n"))  # generated, but in a hidden folder
        ts.put(self.vault, "Board/demo/pic.png", "x")
        ts.put(self.vault, "notes.txt", GENERATED.format("not Markdown\n"))  # generated, but not a Markdown file
        ts.git(self.vault, "mv", "Projects/demo/Moved.md", "Projects/demo/Moved2.md")  # a rename the owner staged
        code, out, _ = self.close()
        self.assertEqual(code, 0, out)
        self.assertEqual(self.committed(), {"Projects/demo/[x] a*.md", "Projects/demo/demo - Rejected ideas.md", "Projects/demo/demo - Stats.md",
                                            "Projects/demo/decisions/002 - Second decision.md"})
        self.assertRegex(out, r"(?m)^vault git: committed 4 note\(s\) as [0-9a-f]+$")
        status = ts.git(self.vault, "status", "--porcelain", "--untracked-files=all").splitlines()
        self.assertEqual(sorted(status), sorted([" D Projects/demo/Old.md", ' M "Projects/demo/x a1.md"', "M  Garden.md", "R  Projects/demo/Moved.md -> Projects/demo/Moved2.md", "?? Patterns/Draft.md", "?? notes.txt",
                                                 "?? Board/demo/pic.png", "?? .trash/Old.md"]))

    def test_the_commit_message_names_the_project_and_the_count_with_no_trailer_and_the_vaults_own_identity(self):
        self.vault_repo()
        self.close()
        short = ts.git(self.repo, "rev-parse", "--short", "HEAD").strip()
        self.assertEqual(ts.git(self.vault, "log", "-1", "--format=%B").strip(), f"Close demo at {short}: 3 generated note(s)")
        self.assertEqual(ts.git(self.vault, "log", "-1", "--format=%an <%ae>").strip(), "vault-owner <vault@example.com>")

    def test_a_second_close_with_nothing_new_commits_nothing(self):
        self.vault_repo()
        self.close()
        before = ts.git(self.vault, "rev-parse", "HEAD")
        _, again, _ = self.close()
        self.assertIn("vault git: nothing to commit", again)
        self.assertEqual(ts.git(self.vault, "rev-parse", "HEAD"), before)

    def test_a_vault_that_is_not_its_own_repository_is_left_alone(self):
        ts.put(self.vault, "Concepts/round-trip-frugality.md", CONCEPT)
        _, plain, _ = self.close()
        self.assertIn("vault git: not committed (the vault is not a git repository of its own)", plain)
        ts.git(self.tmp.name, "init", "-q", "-b", "main", self.tmp.name)  # now the vault sits inside another repository
        _, nested, _ = self.close()
        self.assertIn("vault git: not committed (the vault is not a git repository of its own)", nested)
        self.assertEqual(subprocess.run(["git", "-C", self.tmp.name, "rev-parse", "HEAD"], capture_output=True).returncode, 128)  # no commit was made

    def test_a_merge_a_rebase_or_a_held_lock_stops_the_commit(self):
        self.vault_repo()
        for marker, what in (("MERGE_HEAD", "a merge"), ("rebase-merge", "a rebase"), ("index.lock", "another git command")):
            with self.subTest(marker):
                path = os.path.join(self.vault, ".git", marker)
                if marker == "rebase-merge":
                    os.makedirs(path)
                else:
                    ts.put(self.vault, os.path.join(".git", marker), "x\n")
                before = ts.git(self.vault, "rev-parse", "HEAD")
                _, out, _ = self.close()
                self.assertIn(f"vault git: not committed ({what}", out)
                self.assertEqual(ts.git(self.vault, "rev-parse", "HEAD"), before)
                (os.rmdir if marker == "rebase-merge" else os.remove)(path)

    def test_unmerged_paths_stop_the_commit(self):
        self.vault_repo()
        note = "Projects/demo/[x] a*.md"
        ts.put(self.vault, note, GENERATED.format("stashed\n"))
        ts.git(self.vault, "stash", "-q")
        ts.put(self.vault, note, GENERATED.format("committed\n"))
        ts.commit(self.vault, "a different change")
        subprocess.run(["git", "-C", self.vault, "stash", "pop", "-q"], capture_output=True)  # conflicts, leaving the note unmerged without a MERGE_HEAD
        self.assertFalse(os.path.exists(os.path.join(self.vault, ".git", "MERGE_HEAD")))
        before = ts.git(self.vault, "rev-parse", "HEAD")
        _, out, _ = self.close()
        self.assertIn("vault git: not committed (the vault has unmerged paths)", out)
        self.assertEqual(ts.git(self.vault, "rev-parse", "HEAD"), before)

    def test_a_detached_head_is_not_committed_to(self):
        self.vault_repo()
        ts.git(self.vault, "checkout", "-q", "--detach")
        before = ts.git(self.vault, "rev-parse", "HEAD")
        _, out, _ = self.close()
        self.assertIn("vault git: not committed (the vault's HEAD is detached)", out)
        self.assertEqual(ts.git(self.vault, "rev-parse", "HEAD"), before)

    def test_a_commit_that_fails_leaves_nothing_staged(self):
        self.vault_repo()
        hook = os.path.join(self.vault, ".git", "hooks", "pre-commit")
        ts.put(self.vault, os.path.join(".git", "hooks", "pre-commit"), "#!/bin/sh\necho refused by a hook >&2\nexit 1\n")
        os.chmod(hook, 0o755)
        _, out, _ = self.close()
        self.assertIn("vault git: not committed (", out)
        self.assertNotIn("committed 3", out)
        self.assertEqual(ts.git(self.vault, "diff", "--cached", "--name-only"), "")
        self.assertIn('?? "Projects/demo/demo - Stats.md"', ts.git(self.vault, "status", "--porcelain", "--untracked-files=all"))

    def test_a_note_the_owner_untracked_is_not_committed_back(self):
        self.vault_repo()
        ts.git(self.vault, "rm", "-q", "--cached", "Projects/demo/Moved.md")  # staged deletion; the file stays in the work tree
        _, out, _ = self.close()
        self.assertRegex(out, r"(?m)^vault git: committed 3 note\(s\) as ")
        self.assertNotIn("Projects/demo/Moved.md", self.committed())
        self.assertIn("D  Projects/demo/Moved.md", ts.git(self.vault, "status", "--porcelain"))

    def test_a_vault_path_spelled_in_another_case_is_still_its_repository(self):
        self.vault_repo()
        other = os.path.join(self.tmp.name, "VAULT")
        if not os.path.exists(other):
            self.skipTest("a case-sensitive file system")
        code, out, _ = self.close_at(other)
        self.assertRegex(out, r"(?m)^vault git: committed 3 note\(s\) as ")

    def test_generated_true_is_read_as_the_sync_reads_it(self):
        self.vault_repo()
        ts.put(self.vault, "Projects/demo/Old.md", GENERATED.format("shout\n").replace("generated: true", "generated: True"))
        _, out, _ = self.close()
        self.assertIn("Projects/demo/Old.md", self.committed())

    def test_a_git_status_that_fails_is_not_reported_as_nothing_to_commit(self):
        self.vault_repo()
        ts.put(self.vault, os.path.join(".git", "index"), "garbage")
        code, out, _ = self.close()
        self.assertEqual(code, 0, out)
        self.assertRegex(out, r"(?m)^vault git: not committed \(")
        self.assertNotIn("nothing to commit", out)

    def test_a_git_that_cannot_run_is_reported_and_does_not_change_the_exit_code(self):
        self.vault_repo()
        real = c.git

        def refuse_add(vault, *args):
            if args[0] == "add":
                raise OSError("Argument list too long")
            return real(vault, *args)
        with mock.patch.object(c, "git", side_effect=refuse_add):
            code, out, _ = self.close()
        self.assertEqual(code, 0, out)
        self.assertIn("vault git: not committed (Argument list too long)", out)

    def test_a_symlink_is_not_committed(self):
        self.vault_repo()
        outside = os.path.join(self.tmp.name, "outside.md")
        ts.put(self.tmp.name, "outside.md", GENERATED.format("elsewhere\n"))
        os.symlink(outside, os.path.join(self.vault, "Projects/demo/Link.md"))
        _, out, _ = self.close()
        self.assertNotIn("Projects/demo/Link.md", self.committed())
        self.assertIn("?? Projects/demo/Link.md", ts.git(self.vault, "status", "--porcelain"))

    def test_a_lint_error_commits_nothing(self):
        self.vault_repo()
        os.remove(os.path.join(self.vault, "Concepts/round-trip-frugality.md"))  # the record's concept now has no note: a lint error
        before = ts.git(self.vault, "rev-parse", "HEAD")
        code, out, _ = self.close()
        self.assertEqual(code, 1)
        self.assertIn("vault git: not committed (the lint has an error)", out)
        self.assertEqual(ts.git(self.vault, "rev-parse", "HEAD"), before)

    def test_a_dry_run_commits_nothing(self):
        self.vault_repo()
        before = ts.git(self.vault, "rev-parse", "HEAD")
        _, out, _ = self.close("--dry-run")
        self.assertIn("vault git: not committed (dry run)", out)
        self.assertEqual(ts.git(self.vault, "rev-parse", "HEAD"), before)

    def test_a_vault_ahead_of_its_remote_is_committed_to_but_reported_as_not_to_be_pushed(self):
        self.vault_repo(remote=True)
        _, level, _ = self.close()
        self.assertNotIn("ahead", level)
        ts.git(self.vault, "push", "-q")
        ts.put(self.vault, "Inbox/Mine.md", FRONT.format("project", "active", "project", "active") + "Back to [[Garden]].\n")
        ts.git(self.vault, "add", "Inbox/Mine.md")
        ts.git(self.vault, "commit", "-q", "-m", "the owner's own commit")
        ts.put(self.repo, "notes.txt", "x\n")
        ts.commit(self.repo, "another")  # the stats note gains a row
        _, ahead, _ = self.close()
        self.assertIn("vault git: the vault was already 1 commit(s) ahead of its remote, so do not push it", ahead)
        self.assertRegex(ahead, r"(?m)^vault git: committed 1 note\(s\) as ")

    def test_a_vault_with_no_upstream_is_reported(self):
        self.vault_repo()
        _, out, _ = self.close()
        self.assertIn("vault git: the vault has no upstream branch or no commit", out)


if __name__ == "__main__":
    unittest.main()
