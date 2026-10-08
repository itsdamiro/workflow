"""Run: python3 -m unittest discover -s adapters/claude/context-report"""

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(__file__))
import context_report as c  # noqa: E402


def message(mid, tokens, **extra):
    return {"type": "assistant", "message": {"id": mid, "usage": {"input_tokens": tokens}}, **extra}


def write(folder, name, events):
    with open(os.path.join(folder, name), "w", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")


class LoadSessions(unittest.TestCase):
    def test_counts_each_message_once_and_skips_subagents_and_short_sessions(self):
        with tempfile.TemporaryDirectory() as d:
            events = [message(f"m{i}", t) for i, t in enumerate([10, 20, 30, 40, 50])]
            events += [message("m1", 999), message("side", 999, isSidechain=True), {"type": "user", "message": {}}]
            write(d, "a.jsonl", events)
            write(d, "short.jsonl", [message(f"s{i}", 5) for i in range(4)])
            self.assertEqual(c.load_sessions(d), [[10, 20, 30, 40, 50]])

    def test_a_message_without_an_id_is_not_dropped(self):
        with tempfile.TemporaryDirectory() as d:
            write(d, "a.jsonl", [{"type": "assistant", "message": {"usage": {"input_tokens": t}}} for t in (1, 2, 3, 4, 5)])
            self.assertEqual(c.load_sessions(d), [[1, 2, 3, 4, 5]])


    def test_a_message_with_no_usage_is_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            events = [message(f"m{i}", t) for i, t in enumerate([10, 20, 30, 40, 50])]
            events.insert(2, {"type": "assistant", "message": {"id": "none"}})
            write(d, "a.jsonl", events)
            self.assertEqual(c.load_sessions(d), [[10, 20, 30, 40, 50]])


class Report(unittest.TestCase):
    def test_prints_the_aggregates_and_the_cap_line(self):
        with tempfile.TemporaryDirectory() as d:
            write(d, "a.jsonl", [message(f"m{i}", t) for i, t in enumerate([10, 20, 30, 40, 50])])
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = c.main([d, "--caps", "35", "--restart-extra", "0"])
            self.assertEqual(code, 0)
            self.assertIn("sessions 1, messages 5", out.getvalue())
            self.assertIn("re-read in all: 150;", out.getvalue())
            self.assertIn("110 (26% less), 1 restarts", out.getvalue())
            self.assertIn("the longest 20% of sessions account for 100%", out.getvalue())

    def test_restart_extra_raises_the_cost_of_a_restart(self):
        with tempfile.TemporaryDirectory() as d:
            write(d, "a.jsonl", [message(f"m{i}", t) for i, t in enumerate([10, 20, 30, 40, 50])])
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                c.main([d, "--caps", "35", "--restart-extra", "5"])
            self.assertIn("120 (20% less), 1 restarts", out.getvalue())  # restart at 10+5, then 25 and 35

    def test_an_empty_folder_is_reported_not_a_crash(self):
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(c.main([d]), 1)


class Simulate(unittest.TestCase):
    S = [[10, 20, 30, 40, 50]]

    def test_restart_when_over_the_cap(self):
        self.assertEqual(c.simulate(self.S, 35, 10), (110, 1))  # 10+20+30, restart at 10+10, then 30

    def test_a_context_equal_to_the_cap_does_not_restart(self):
        self.assertEqual(c.simulate(self.S, 40, 10), (120, 1))  # only 50 passes 40

    def test_a_drop_in_context_adds_nothing(self):
        self.assertEqual(c.simulate([[10, 40, 10, 20, 30]], 1000, 10), (200, 0))  # 10, 40, 40, 50, 60

    def test_no_restart_when_the_cap_is_never_reached(self):
        self.assertEqual(c.simulate(self.S, 1000, 10), (150, 0))


if __name__ == "__main__":
    unittest.main()
