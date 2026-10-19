"""Run: python3 -m unittest discover -s adapters/claude/context-report"""

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
import unittest.mock

sys.path.insert(0, os.path.dirname(__file__))
import last_context as lc  # noqa: E402


def message(mid, tokens, **extra):
    return {"type": "assistant", "message": {"id": mid, "usage": {"input_tokens": tokens}}, **extra}


def write(folder, name, events):
    with open(os.path.join(folder, name), "w", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")


class SessionContexts(unittest.TestCase):
    def test_counts_each_message_once_and_skips_subagents(self):
        with tempfile.TemporaryDirectory() as d:
            events = [message(f"m{i}", t) for i, t in enumerate([10, 20, 30])]
            events += [message("m1", 999), message("side", 999, isSidechain=True), {"type": "user", "message": {}}]
            write(d, "a.jsonl", events)
            self.assertEqual(lc.session_contexts(os.path.join(d, "a.jsonl")), [10, 20, 30])

    def test_a_message_without_an_id_is_not_dropped(self):
        with tempfile.TemporaryDirectory() as d:
            write(d, "a.jsonl", [{"type": "assistant", "message": {"usage": {"input_tokens": t}}} for t in (1, 2, 3)])
            self.assertEqual(lc.session_contexts(os.path.join(d, "a.jsonl")), [1, 2, 3])

    def test_a_message_with_no_usage_is_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            events = [message("a", 10), {"type": "assistant", "message": {"id": "none"}}, message("b", 20)]
            write(d, "a.jsonl", events)
            self.assertEqual(lc.session_contexts(os.path.join(d, "a.jsonl")), [10, 20])


ID = "123e4567-e89b-42d3-a456-426614174000"
OTHER = "223e4567-e89b-42d3-a456-426614174000"


def run_last(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = lc.main(list(argv))
    return code, out.getvalue(), err.getvalue()


def project(root, folder, session, events):
    os.makedirs(os.path.join(root, folder), exist_ok=True)
    write(os.path.join(root, folder), session + ".jsonl", events)


class LastContext(unittest.TestCase):
    def test_prints_the_last_main_thread_answer_with_usage(self):
        with tempfile.TemporaryDirectory() as d:
            events = [message("a", 10), message("b", 20), message("side", 999, isSidechain=True),
                      {"type": "assistant", "message": {"id": "none"}}, {"type": "user", "message": {}}]
            project(d, "-proj", ID, events)
            self.assertEqual(run_last(ID, "--projects-dir", d), (0, "20\n", ""))

    def test_a_short_session_still_has_a_size(self):
        with tempfile.TemporaryDirectory() as d:
            project(d, "-proj", ID, [message("a", 7)])
            self.assertEqual(run_last(ID, "--projects-dir", d)[1], "7\n")

    def test_the_context_adds_new_cached_and_cache_written_tokens(self):
        with tempfile.TemporaryDirectory() as d:
            usage = {"input_tokens": 1, "cache_read_input_tokens": 20, "cache_creation_input_tokens": 300, "output_tokens": 9000}
            project(d, "-proj", ID, [{"type": "assistant", "message": {"id": "a", "usage": usage}}])
            self.assertEqual(run_last(ID, "--projects-dir", d)[1], "321\n")

    def test_the_id_defaults_to_the_environment_variable(self):
        with tempfile.TemporaryDirectory() as d:
            project(d, "-proj", ID, [message("a", 5)])
            with unittest.mock.patch.dict(os.environ, {"CLAUDE_CODE_SESSION_ID": ID}):
                self.assertEqual(run_last("--projects-dir", d)[1], "5\n")

    def test_another_sessions_file_is_never_read(self):
        with tempfile.TemporaryDirectory() as d:
            project(d, "-proj", OTHER, [message("a", 5)])  # the newest file, but not this session
            code, out, err = run_last(ID, "--projects-dir", d)
            self.assertEqual((code, out), (1, ""))
            self.assertIn("no transcript", err)

    def test_the_same_id_in_two_folders_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            project(d, "-one", ID, [message("a", 5)])
            project(d, "-two", ID, [message("a", 6)])
            code, out, err = run_last(ID, "--projects-dir", d)
            self.assertEqual((code, out), (1, ""))
            self.assertIn("more than one", err)

    def test_no_id_is_refused(self):
        with tempfile.TemporaryDirectory() as d, unittest.mock.patch.dict(os.environ, clear=True):
            code, out, err = run_last("--projects-dir", d)
            self.assertEqual((code, out), (1, ""))
            self.assertIn("no session id", err)

    def test_an_id_that_is_not_a_uuid_is_refused_before_it_reaches_a_path(self):
        with tempfile.TemporaryDirectory() as d:
            project(d, "-proj", "x", [message("a", 5)])
            for bad in ("*", "../x", "x", ID + "x"):
                code, out, err = run_last(bad, "--projects-dir", d)
                self.assertEqual((code, out), (1, ""), bad)
                self.assertIn("not a UUID", err)

    def test_a_transcript_with_no_usage_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            project(d, "-proj", ID, [{"type": "user", "message": {}}, {"type": "assistant", "message": {"id": "a"}}])
            code, out, err = run_last(ID, "--projects-dir", d)
            self.assertEqual((code, out), (1, ""))
            self.assertIn("no answer with usage", err)

    def test_a_projects_dir_with_glob_characters_is_taken_literally(self):
        with tempfile.TemporaryDirectory(prefix="p[1]*") as d:
            project(d, "-proj", ID, [message("a", 5)])
            self.assertEqual(run_last(ID, "--projects-dir", d)[1], "5\n")

    def test_a_transcript_that_cannot_be_read_is_refused_not_a_crash(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "-proj", ID + ".jsonl"))  # a directory where the file should be
            code, out, _ = run_last(ID, "--projects-dir", d)
            self.assertEqual((code, out), (1, ""))


if __name__ == "__main__":
    unittest.main()
