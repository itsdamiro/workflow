"""Run: python3 -m unittest discover -s adapters/claude/capture   (synthetic sentences only)"""

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import owner_messages as om  # noqa: E402

SID = "0c6a8571-151c-47b9-88aa-e230728893bd"
HUMAN = {"kind": "human"}


def user(content, **extra):
    return {"type": "user", "message": {"role": "user", "content": content}, "origin": HUMAN, **extra}


class Typed(unittest.TestCase):
    def test_a_typed_string_and_the_text_blocks_of_a_typed_list_are_kept(self):
        self.assertEqual(om.typed_text(user("  say it plainly \n")), "say it plainly")
        blocks = [{"type": "text", "text": "first"}, {"type": "image", "source": {}}, {"type": "text", "text": "second"}]
        self.assertEqual(om.typed_text(user(blocks)), "first\nsecond")

    def test_tool_results_assistant_text_and_other_kinds_of_user_events_are_not(self):
        result = {"type": "user", "message": {"role": "user", "content": [{"type": "tool_result", "content": "a file"}]}}
        for event in (result, {**result, "toolUseResult": {"x": 1}},
                      {"type": "user", "message": {"role": "user", "content": "text"}, "toolUseResult": {}},
                      {"type": "assistant", "message": {"role": "assistant", "content": "I said so"}},
                      user("subagent", isSidechain=True), user("injected", isMeta=True),
                      user("plugin", origin={"kind": "plugin", "name": "x"}), user("peer", origin={"kind": "peer", "from": "a"}),
                      user("odd", origin="human"), {"type": "attachment", "message": {"content": "x"}}, user(""), user(5), user(None)):
            self.assertEqual(om.typed_text(event), "", event)

    def test_a_message_sent_while_the_assistant_worked_is_kept_as_a_queued_command(self):
        def queued(**extra):
            a = {"type": "queued_command", "prompt": "sent mid-turn", "origin": HUMAN, "commandMode": "prompt", **extra}
            return {"type": "attachment", "attachment": a}
        self.assertEqual(om.typed_text(queued()), "sent mid-turn")
        self.assertEqual(om.typed_text(queued(prompt="a\fb")), "a b")
        self.assertEqual(om.typed_text({**queued(), "isSidechain": True}), "")
        for bad in (queued(origin={"kind": "peer"}), queued(origin=None), queued(origin="human"), queued(type="other"), queued(prompt=None),
                    {"type": "attachment", "attachment": "queued_command"}, {"type": "attachment"},
                    {"type": "attachment", "attachment": {"type": "hook_success", "prompt": "x", "origin": HUMAN}}):
            self.assertEqual(om.typed_text(bad), "", bad)

    def test_an_event_with_no_origin_is_kept_as_older_transcripts_have_none(self):
        self.assertEqual(om.typed_text({"type": "user", "message": {"content": "old style"}}), "old style")

    def test_a_form_feed_typed_by_the_owner_cannot_forge_a_message_break(self):
        self.assertEqual(om.typed_text(user("a\fb")), "a b")


class Command(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        os.makedirs(os.path.join(self.tmp.name, "-proj"))

    def transcript(self, events, session=SID, raw=()):
        path = os.path.join(self.tmp.name, "-proj", session + ".jsonl")
        with open(path, "w", encoding="utf-8") as f:
            for e in events:
                f.write(json.dumps(e) + "\n")
            for line in raw:
                f.write(line + "\n")

    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = om.main([*args, "--projects-dir", self.tmp.name])
        return code, out.getvalue(), err.getvalue()

    def test_messages_come_out_in_order_split_by_a_form_feed_line_and_only_the_owners(self):
        self.transcript([user("one"), {"type": "assistant", "message": {"content": [{"type": "text", "text": "assistant words"}]}},
                         {"type": "user", "message": {"content": [{"type": "tool_result", "content": "tool words"}]}},
                         user("two\n\nstill two"), user("three")], raw=["not json", "[1]"])
        code, out, err = self.run_cli(SID)
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(out, "one\n\f\ntwo\n\nstill two\n\f\nthree\n")
        self.assertNotIn("assistant words", out)
        self.assertNotIn("tool words", out)

    def test_a_queued_message_comes_out_in_its_place(self):
        queued = {"type": "attachment", "attachment": {"type": "queued_command", "prompt": "mid", "origin": HUMAN}}
        self.transcript([user("one"), {"type": "queue-operation", "operation": "enqueue", "content": "mid"}, queued, user("two")])
        self.assertEqual(self.run_cli(SID)[:2], (0, "one\n\f\nmid\n\f\ntwo\n"))

    def test_no_session_id_a_bad_one_or_an_unknown_one_gives_exit_one_and_no_output(self):
        self.transcript([user("one")])
        for args in ((), ("not-a-uuid",), ("11111111-1111-1111-1111-111111111111",)):
            code, out, err = self.run_cli(*args)
            self.assertEqual((code, out), (1, ""), args)
            self.assertTrue(err.startswith("owner_messages: "), err)

    def test_the_newest_file_is_never_guessed(self):
        self.transcript([user("other session")], session="22222222-2222-2222-2222-222222222222")
        self.assertEqual(self.run_cli(SID)[:2], (1, ""))

    def test_the_session_id_comes_from_the_environment_when_not_given(self):
        self.transcript([user("one")])
        os.environ["CLAUDE_CODE_SESSION_ID"] = SID
        self.addCleanup(os.environ.pop, "CLAUDE_CODE_SESSION_ID")
        self.assertEqual(self.run_cli()[:2], (0, "one\n"))

    def test_an_unreadable_transcript_gives_exit_one(self):
        self.transcript([user("one")])
        path = os.path.join(self.tmp.name, "-proj", SID + ".jsonl")
        os.chmod(path, 0)
        self.addCleanup(os.chmod, path, 0o644)
        self.assertEqual(self.run_cli(SID)[:2], (1, ""))


if __name__ == "__main__":
    unittest.main()
