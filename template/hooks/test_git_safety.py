"""Both paths of every rule: the block and the allow. Run: python3 -m unittest discover -s hooks"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(__file__))
import git_safety as g  # noqa: E402

BLOCK = [
    "git checkout -- src/app.py", "git checkout .", "git -C repo checkout -- a.txt", "git restore src/a.py", "git reset --hard HEAD~1",
    "git clean -fd", "git clean -f", "git clean --force", "git add .", "git add -A", "git add --all", "git add -u", "git add src/a.py .",
    "FOO=1 git add .", "GIT_AUTHOR_NAME=x git commit -s -m x", "env git add .", "env -i git add .", "sudo -n git clean -fd", "env FOO=1 git reset --hard", "command git add -A", "sudo git clean -fd",
    "bash -c 'git add .'", 'sh -c "git reset --hard HEAD"', "zsh -lc 'git status && git add -A'", "git commit -sm x", "git commit -asm x",
    "git push -fu origin main", "(git add .)", "{ git add .; }", "cd repo && FOO=1 git add .", 'eval "git add ."',
    "git commit -s -m x", "git commit --signoff -m x", 'git commit -m "x\n\nCo-Authored-By: A <a@b.c>"',
    'git commit -m "$(cat <<\'EOF\'\nfix\n\nCo-authored-by: X\nEOF\n)"', "git status && git add .", "git push --force", "git push -f origin main",
]
ALLOW = [
    "git status", "git diff", "git log --oneline -5", "git checkout main", "git checkout -b feature", "git switch main", "git restore --staged a.py",
    "git add src/a.py tests/test_a.py", "git add -p", 'git commit -m "Fix the thing"', "git commit --amend --no-edit", "git reset --soft HEAD~1",
    "git clean -n", "ls -la && echo git add .", "git stash", "git diff --stat | head",
    "FOO=1 git status", "env git status", "bash -c 'git status'", "bash -c 'echo hi'", "bash script.sh", "git commit -am 'Fix the thing'",
    "git commit -m 'x' -q", "grep -n 'git add .' notes.txt", "git commit -m 'fix: env git add . broke'", "sudo ls", "git add -p src/a.py",
]
ASK = ["git push -u origin main", "FOO=1 git push", "bash -c 'git push'", "git push --force-with-lease", "git push", "git push origin main", "git commit -m x && git push"]


class GitSafety(unittest.TestCase):
    def test_blocked(self):
        for command in BLOCK:
            with self.subTest(command=command):
                self.assertEqual(g.verdict(command)[0], "block")
                self.assertTrue(g.verdict(command)[1])

    def test_allowed(self):
        for command in ALLOW:
            with self.subTest(command=command):
                self.assertEqual(g.verdict(command)[0], "allow")

    def test_push_asks(self):
        for command in ASK:
            with self.subTest(command=command):
                self.assertEqual(g.verdict(command)[0], "ask")

    def test_a_message_file_with_a_trailer_is_blocked(self):
        with tempfile.TemporaryDirectory() as repo:
            for name, body in (("bad.txt", "fix\n\nCo-authored-by: A <a@b.c>\n"), ("gen.txt", "fix\n\nGenerated with a tool\n"), ("ok.txt", "fix a thing\n\nbody\n")):
                with open(os.path.join(repo, name), "w") as f:
                    f.write(body)
            for form in ("git commit -F {}", "git commit -F{}", "git commit --file={}", "git commit --file {}", "git commit -q -F {} --no-edit"):
                with self.subTest(form=form):
                    self.assertEqual(g.verdict(form.format("bad.txt"), repo)[0], "block")
                    self.assertEqual(g.verdict(form.format("gen.txt"), repo)[0], "block")
                    self.assertEqual(g.verdict(form.format("ok.txt"), repo)[0], "allow")
                    self.assertEqual(g.verdict(form.format("missing.txt"), repo)[0], "allow")  # unreadable: the git hook is the backstop
            self.assertEqual(g.verdict("git commit -F -", repo)[0], "allow")
            home = os.environ.get("HOME")
            os.environ["HOME"] = repo
            try:
                self.assertEqual(g.verdict("git commit -F ~/bad.txt", "/")[0], "block")  # the shell expands ~; the hook sees it raw
            finally:
                os.environ["HOME"] = home
            self.assertEqual(g.verdict("git commit -F " + os.path.join(repo, "bad.txt"), ".")[0], "block")

    def test_a_denied_directory_is_not_added_as_a_directory_but_its_files_are(self):
        with tempfile.TemporaryDirectory() as repo:
            os.makedirs(os.path.join(repo, ".claude"))
            with open(os.path.join(repo, ".claude", "git-safety.deny-add"), "w") as f:
                f.write("# generated output\nsympose/webui\n")
            self.assertEqual(g.verdict("git add sympose/webui", repo)[0], "block")
            self.assertEqual(g.verdict("git add sympose/webui/", repo)[0], "block")
            self.assertEqual(g.verdict("git add sympose/webui/index.html", repo)[0], "allow")
            self.assertEqual(g.verdict("git add src", repo)[0], "allow")

    def test_the_script_blocks_with_exit_2_and_a_message_and_ignores_other_tools(self):
        def run(event):
            return subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "git_safety.py")], input=json.dumps(event), capture_output=True, text=True)

        blocked = run({"tool_name": "Bash", "tool_input": {"command": "git add ."}, "cwd": "."})
        self.assertEqual(blocked.returncode, 2)
        self.assertIn("named files", blocked.stderr)
        self.assertEqual(run({"tool_name": "Bash", "tool_input": {"command": "git status"}}).returncode, 0)
        self.assertEqual(run({"tool_name": "Edit", "tool_input": {"command": "git add ."}}).returncode, 0)
        asked = run({"tool_name": "Bash", "tool_input": {"command": "git push"}})
        self.assertEqual(asked.returncode, 0)
        self.assertEqual(json.loads(asked.stdout)["hookSpecificOutput"]["permissionDecision"], "ask")
        self.assertEqual(subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "git_safety.py")], input="not json", capture_output=True, text=True).returncode, 0)


if __name__ == "__main__":
    unittest.main()
