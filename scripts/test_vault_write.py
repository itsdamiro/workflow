"""Tests for vault_write.py (ADR 017). Usage: python3 -m unittest discover -s scripts -p 'test_vault_write.py'
All sentences are synthetic."""

import contextlib
import io
import os
import sys
import tempfile
import unittest
from unittest import mock

import vault_lint as vl
import vault_write as vw

TAGS = """---
type: project
status: accepted
created: 2026-10-08
tags: [type/project, topic/mind]
---
# Tags
Back to [[Garden]]. Topics: `topic/mind`, `topic/consent`.
## Namespaces
- `type/`: decision, concept, idea, project, folder-definition, capture
- `status/`: proposed, accepted, draft, active
- `project/`: one per project, named as its folder
- `topic/`: the owner's own topics, added by hand
"""
GARDEN = "---\ntype: project\nstatus: active\ncreated: 2026-10-08\ntags: [type/project, topic/mind]\n---\n[[Tags]] [[Idea]] [[alpha]] [[Notes]]\n"
IDEA = "---\ntype: idea\nstatus: draft\ncreated: 2026-10-08\nprojects: [alpha]\ntags: [type/idea, status/draft, topic/mind]\n---\nBack to [[Garden]].\n"
HUB = "---\ntype: project\nstatus: active\ncreated: 2026-10-08\ntags: [type/project, status/active, project/alpha, topic/mind]\n---\nBack to [[Garden]].\n"
SOURCE = "First message here.\fI want the report\nto list every write, because nobody reads\n\na hidden one.\fThird message, with Some Capitals."
QUOTE = "I want the report to list every write, because nobody reads a hidden one."
CONCEPT = "---\ntype: concept\nstatus: draft\ncreated: 2026-10-09\ntags: [type/concept, status/draft, topic/mind]\n---\nA made-up term. See [[Garden]].\n"
NOTES = "---\ntype: idea\nstatus: accepted\ncreated: 2026-10-08\nprojects: [alpha]\ntags: [type/idea, status/accepted, topic/mind]\n---\n# Notes\nintro [[Garden]]\n\n## Topics\n- one\n- two\n\n## Other\ntext\n"


class Case(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = os.path.join(self.tmp.name, "vault")
        for rel, text in (("Tags.md", TAGS), ("Garden.md", GARDEN), ("Idea.md", IDEA), ("Projects/alpha/alpha.md", HUB),
                          ("Ideas/Notes.md", NOTES)):
            self.put(rel, text)

    def put(self, rel, text):
        path = os.path.join(self.root, *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        return path

    def read(self, rel):
        with open(os.path.join(self.root, *rel.split("/")), encoding="utf-8", newline="") as f:
            return f.read()

    def exists(self, rel):
        return os.path.exists(os.path.join(self.root, *rel.split("/")))

    def run_cli(self, *args, stdin=""):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), mock.patch.object(sys, "stdin", io.StringIO(stdin)):
            code = vw.main([self.root, *args])
        return code, out.getvalue(), err.getvalue()

    def source(self, text=SOURCE):
        path = os.path.join(self.tmp.name, "source.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path

    def capture(self, quote=QUOTE, title="Every write is listed", about=("Idea",), topic=("mind",), project="alpha", source=None, extra=()):
        args = ["capture", "--project", project, "--source", source or self.source(), "--quote", quote, "--title", title,
                "--created", "2026-10-09", *extra]
        for a in about:
            args += ["--about", a]
        for t in topic:
            args += ["--topic", t]
        return self.run_cli(*args)

    def refused(self, result, *words):
        code, out, err = result
        self.assertEqual((code, out), (1, ""), err)
        self.assertTrue(err.startswith("refused: "), err)
        for w in words:
            self.assertIn(w, err)

    def test_the_fixture_vault_is_clean(self):
        self.assertEqual(vl.lint(self.root), [])


class Capture(Case):
    def test_an_exact_quote_is_written_and_the_vault_stays_clean(self):
        code, out, err = self.capture()
        self.assertEqual((code, out.strip(), err), (0, "Projects/alpha/Captured/Every write is listed.md", ""))
        self.assertEqual(self.read("Projects/alpha/Captured/Every write is listed.md"),
                         "---\ntype: capture\nstatus: draft\ncreated: 2026-10-09\nprojects: [alpha]\n"
                         "tags: [type/capture, status/draft, project/alpha, topic/mind]\n---\n"
                         f"> {QUOTE}\n\nAbout: [[Idea]]\n")
        self.assertEqual(vl.lint(self.root), [])

    def test_a_difference_in_whitespace_only_is_allowed(self):
        self.assertEqual(self.capture(quote="I want  the report to list every write,\nbecause nobody reads a hidden one.")[0], 0)

    def test_the_quote_may_come_from_standard_input_and_the_hub_and_two_notes_and_topics_are_fine(self):
        code = self.run_cli("capture", "--project", "alpha", "--source", "-", "--quote", QUOTE, "--title", "T", "--about", "alpha",
                            "--about", "Garden", "--topic", "mind", "--topic", "consent", stdin=SOURCE)[0]
        self.assertEqual(code, 0)
        self.assertIn("About: [[alpha]], [[Garden]]", self.read("Projects/alpha/Captured/T.md"))
        self.assertIn("topic/mind, topic/consent", self.read("Projects/alpha/Captured/T.md"))

    def test_any_change_to_the_words_is_refused_and_nothing_is_written(self):
        for quote in (QUOTE.replace("every", "each"), QUOTE.replace("I want", "i want"), QUOTE.replace("one.", "one!"),
                      "I want the report ... a hidden one.", "I want the report to list every write. Third message, with Some Capitals.",
                      "", "   "):
            self.refused(self.capture(quote=quote), "quote")
            self.assertFalse(self.exists("Projects/alpha/Captured/Every write is listed.md"), quote)

    def test_a_quote_across_two_messages_is_refused(self):
        self.refused(self.capture(quote="First message here. I want the report"), "quote")

    def test_about_and_topic_are_required_and_must_exist(self):
        self.refused(self.capture(about=()), "--about")
        self.refused(self.capture(about=("Nowhere",)), "Nowhere")
        self.refused(self.capture(about=("Idea", "Nowhere")), "Nowhere")
        self.refused(self.capture(topic=()), "--topic")
        self.refused(self.capture(topic=("mind", "gardening")), "gardening")

    def test_the_title_must_be_a_new_plain_note_name(self):
        self.refused(self.capture(title="Idea"), "exists")
        self.refused(self.capture(title="idea"), "exists")
        for bad in ("a/b", "a|b", "[x]", "a#b", "", "  ", ".hidden", "a:b"):
            self.refused(self.capture(title=bad), "note name")
        self.assertEqual(self.capture(title="Same")[0], 0)
        self.refused(self.capture(title="Same"), "exists")

    def test_the_project_needs_a_folder(self):
        self.refused(self.capture(project="beta"), "Projects/beta")
        self.refused(self.capture(project="../x"), "Projects")

    def test_a_missing_source_or_vault_is_refused(self):
        self.refused(self.capture(source=os.path.join(self.tmp.name, "none.txt")), "cannot read")
        os.remove(os.path.join(self.root, "Tags.md"))
        self.refused(self.capture(), "Tags.md")

    def test_a_quote_whose_link_does_not_resolve_is_refused_by_the_lint(self):
        self.refused(self.capture(quote="see [[Nope]]", source=self.source("Third message, see [[Nope]]")), "broken-link")


class New(Case):
    def new(self, text=CONCEPT, path="Concepts/Capture.md"):
        src = os.path.join(self.tmp.name, "text.md")
        with open(src, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        return self.run_cli("new", "--path", path, "--text-file", src)

    def test_the_approved_text_is_written_byte_for_byte_and_passes_the_lint(self):
        self.assertEqual(self.new(), (0, "Concepts/Capture.md\n", ""))
        self.assertEqual(self.read("Concepts/Capture.md"), CONCEPT)
        self.assertEqual(vl.lint(self.root), [])

    def test_the_text_may_come_from_standard_input(self):
        code = self.run_cli("new", "--path", "Concepts/Capture.md", "--text-file", "-", stdin=CONCEPT)[0]
        self.assertEqual(code, 0)

    def test_an_existing_name_anywhere_is_refused(self):
        self.refused(self.new(path="Concepts/Idea.md"), "exists")
        self.refused(self.new(path="Concepts/IDEA.md"), "exists")
        self.assertEqual(self.new()[0], 0)
        self.refused(self.new(), "exists")

    def test_a_path_outside_the_vault_or_in_a_hidden_folder_is_refused(self):
        for path in ("../Out.md", "/tmp/Out.md", ".obsidian/Out.md", "Concepts/.Out.md", "Concepts/Out.txt", "a//b.md", "Concepts/../../Out.md"):
            self.refused(self.new(path=path), "path")
        self.assertFalse(os.path.exists(os.path.join(self.tmp.name, "Out.md")))

    def test_a_symlink_out_of_the_vault_is_refused(self):
        outside = os.path.join(self.tmp.name, "outside")
        os.makedirs(outside)
        os.symlink(outside, os.path.join(self.root, "Link"))
        self.refused(self.new(path="Link/Out.md"), "leaves the vault")
        self.assertEqual(os.listdir(outside), [])

    def test_generated_and_non_draft_notes_are_refused(self):
        self.refused(self.new(text=CONCEPT.replace("topic/mind]", "topic/mind]\ngenerated: true")), "generated")
        self.refused(self.new(text=CONCEPT.replace("status: draft", "status: accepted").replace("status/draft", "status/accepted")), "draft")

    def test_a_hidden_folder_is_not_copied_for_the_lint(self):
        secret = self.put(".git/objects/secret.md", "x")
        os.chmod(secret, 0)
        self.addCleanup(os.chmod, secret, 0o644)
        self.assertEqual(self.new()[0], 0)

    def test_what_the_lint_rejects_is_refused(self):
        self.refused(self.new(text=CONCEPT.replace("type: concept", "type: gizmo")), "unknown-type")
        self.refused(self.new(text=CONCEPT.replace("topic/mind", "colour/red")), "bad-tag")
        self.refused(self.new(text=CONCEPT.replace("[[Garden]]", "[[Nowhere]]")), "broken-link")
        self.refused(self.new(text=CONCEPT.replace("See [[Garden]].", "No link.")), "no-links")
        self.refused(self.new(text=CONCEPT.replace("created: 2026-10-09\n", "")), "missing-field")
        self.refused(self.new(text="no frontmatter [[Garden]]"), "draft")
        self.refused(self.new(text="---\ntype: concept\nnot a field\n---\n[[Garden]]"), "frontmatter")

    def test_a_missing_text_file_is_refused(self):
        self.refused(self.run_cli("new", "--path", "Concepts/X.md", "--text-file", os.path.join(self.tmp.name, "none")), "cannot read")

    def test_nothing_is_left_behind_when_refused(self):
        self.refused(self.new(text=CONCEPT.replace("[[Garden]]", "[[Nowhere]]")), "lint")
        self.assertFalse(self.exists("Concepts"))


class AddLine(Case):
    def add(self, line="- three", under=None, path="Ideas/Notes.md"):
        args = ["add-line", "--path", path, "--line", line]
        return self.run_cli(*args, *(["--under", under] if under else []))

    def test_a_line_is_appended_at_the_end(self):
        self.assertEqual(self.add(), (0, "Ideas/Notes.md\n", ""))
        self.assertEqual(self.read("Ideas/Notes.md"), NOTES + "- three\n")

    def test_a_line_goes_to_the_end_of_the_named_section_after_its_last_content(self):
        self.add(under="Topics")
        self.assertEqual(self.read("Ideas/Notes.md"), NOTES.replace("- two\n", "- two\n- three\n"))

    def test_the_last_section_and_a_nested_one(self):
        self.add(under="Other")
        self.assertEqual(self.read("Ideas/Notes.md"), NOTES.replace("text\n", "text\n- three\n"))
        self.put("Ideas/Deep.md", NOTES + "### Deeper\nd\n\n## After\n")
        self.add(under="Other", path="Ideas/Deep.md")
        self.assertIn("text\n### Deeper\nd\n- three\n\n## After\n", self.read("Ideas/Deep.md"))

    def test_a_note_without_a_final_newline_gets_one_before_the_line(self):
        self.put("Ideas/Bare.md", NOTES.rstrip("\n"))
        self.add(path="Ideas/Bare.md")
        self.assertEqual(self.read("Ideas/Bare.md"), NOTES + "- three\n")

    def test_a_note_with_windows_line_ends_keeps_them(self):
        self.put("Ideas/Win.md", NOTES.replace("\n", "\r\n"))
        self.add(path="Ideas/Win.md", under="Topics")
        self.assertEqual(self.read("Ideas/Win.md"), NOTES.replace("- two\n", "- two\n- three\n").replace("\n", "\r\n"))

    def test_a_heading_in_a_code_fence_or_the_frontmatter_is_not_a_heading(self):
        self.put("Ideas/Fence.md", "---\ntype: idea\nstatus: accepted\ncreated: 2026-10-08\n# Topics\n---\n```\n## Topics\n```\n## Real\nx\n")
        self.refused(self.add(path="Ideas/Fence.md", under="Topics"), "heading")
        self.add(path="Ideas/Fence.md", under="Real")
        self.assertTrue(self.read("Ideas/Fence.md").endswith("## Real\nx\n- three\n"))

    def test_a_missing_heading_file_or_a_generated_or_unreadable_note_is_refused(self):
        self.refused(self.add(under="Nope"), "heading")
        self.refused(self.add(under="topics"), "heading")
        self.refused(self.add(path="Ideas/None.md"), "does not exist")
        self.put("Ideas/Gen.md", NOTES.replace("topic/mind]", "topic/mind]\ngenerated: true"))
        self.refused(self.add(path="Ideas/Gen.md"), "generated")
        self.put("Ideas/Bad.md", "---\nnot a field\n---\n")
        self.refused(self.add(path="Ideas/Bad.md"), "unreadable")
        self.assertEqual(self.read("Ideas/Notes.md"), NOTES)

    def test_a_repeated_line_or_one_with_a_line_break_is_refused(self):
        self.refused(self.add(line="- two"), "already")
        self.refused(self.add(line="a\nb"), "line break")
        self.refused(self.add(line="a\rb"), "line break")
        self.refused(self.add(line="  "), "empty")
        self.assertEqual(self.read("Ideas/Notes.md"), NOTES)

    def test_a_hidden_folder_or_a_path_outside_the_vault_is_refused(self):
        self.put(".obsidian/Hidden.md", NOTES)
        self.refused(self.add(path=".obsidian/Hidden.md"), "path")
        self.refused(self.add(path="../x.md"), "path")

    def test_a_write_that_does_not_read_back_puts_the_old_content_back(self):
        def damaged(full, text):
            with open(full, "w", encoding="utf-8") as f:
                f.write(text[: len(text) // 2])
        with mock.patch.object(vw, "_replace", damaged):
            self.refused(self.add(), "put back")
        self.assertEqual(self.read("Ideas/Notes.md"), NOTES)


class AddValue(Case):
    NO_CAPTURE = TAGS.replace(", capture", "")

    def add(self, value="capture", namespace="type"):
        return self.run_cli("add-value", "--namespace", namespace, "--value", value)

    def test_a_value_goes_to_the_end_of_the_one_line_list_and_nothing_else_changes(self):
        self.put("Tags.md", self.NO_CAPTURE)
        self.assertEqual(self.add(), (0, "Tags.md\n", ""))
        self.assertEqual(self.read("Tags.md"), TAGS)
        self.put("Tags.md", self.NO_CAPTURE)
        self.assertEqual(self.add("review", "status")[0], 0)
        self.assertEqual(self.read("Tags.md"), self.NO_CAPTURE.replace("active\n", "active, review\n"))

    def test_windows_line_ends_and_a_missing_final_newline_are_kept(self):
        self.put("Tags.md", self.NO_CAPTURE.replace("\n", "\r\n"))
        self.add()
        self.assertEqual(self.read("Tags.md"), TAGS.replace("\n", "\r\n"))
        self.put("Tags.md", self.NO_CAPTURE.replace("- `topic/`: the owner's own topics, added by hand\n", "")
                 .replace("active\n- `project/`", "active\n- `project/`").rstrip("\n") + "\n- `type/`: x")
        self.refused(self.add(), "exactly one")

    def test_a_listed_value_a_bad_word_a_missing_or_doubled_line_or_a_punctuated_line_is_refused(self):
        self.refused(self.add("idea"), "already listed")
        for bad in ("Capture", "two words", "a/b", "x-", ""):
            self.refused(self.add(bad), "kebab-case")
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):  # argparse rejects any namespace but type and status
            self.add(namespace="topic")
        self.put("Tags.md", self.NO_CAPTURE.replace("- `status/`: proposed, accepted, draft, active\n", ""))
        self.refused(self.add("review", "status"), "no values for status")
        self.put("Tags.md", self.NO_CAPTURE + "- `type/`: more\n")
        self.refused(self.add(), "exactly one")
        self.put("Tags.md", self.NO_CAPTURE.replace("folder-definition\n", "folder-definition.\n"))
        self.refused(self.add(), "punctuation")
        self.assertEqual(self.read("Tags.md"), self.NO_CAPTURE.replace("folder-definition\n", "folder-definition.\n"))

    def test_a_vault_without_tags_md_is_refused(self):
        os.remove(os.path.join(self.root, "Tags.md"))
        self.refused(self.add(), "Tags.md")

    def test_a_write_that_does_not_read_back_puts_the_old_content_back(self):
        self.put("Tags.md", self.NO_CAPTURE)
        def damaged(full, text):
            with open(full, "w", encoding="utf-8") as f:
                f.write(text[: len(text) // 2])
        with mock.patch.object(vw, "_replace", damaged):
            self.refused(self.add(), "put back")

    def test_missing_values_names_what_the_writer_needs(self):
        self.assertEqual(vw.missing_values(self.root), [])
        self.put("Tags.md", self.NO_CAPTURE)
        self.assertEqual(vw.missing_values(self.root), [("type", "capture")])
        self.put("Tags.md", self.NO_CAPTURE.replace("draft, ", ""))
        self.assertEqual(vw.missing_values(self.root), [("type", "capture"), ("status", "draft")])

    def test_the_capture_that_failed_for_the_unlisted_type_works_after_the_value_is_added(self):
        self.put("Tags.md", self.NO_CAPTURE)
        self.refused(self.run_cli("capture", "--project", "alpha", "--source", self.source(), "--quote", QUOTE, "--title", "T",
                                  "--about", "Idea", "--topic", "mind"), "unknown-type")
        self.add()
        self.assertEqual(self.run_cli("capture", "--project", "alpha", "--source", self.source(), "--quote", QUOTE, "--title", "T",
                                      "--about", "Idea", "--topic", "mind")[0], 0)


if __name__ == "__main__":
    unittest.main()
