"""Tests for md_wrap_check.py. Usage: python3 -m unittest discover -s scripts -p 'test_md_wrap_check.py'"""

import contextlib
import io
import os
import tempfile
import unittest

import md_wrap_check as mw


def found(text: str) -> list[int]:
    return list(mw.continuation_lines(text.splitlines(keepends=True)))


class ContinuationLines(unittest.TestCase):
    def test_wrapped_paragraph_flags_each_continuation(self):
        self.assertEqual(found("one\ntwo\nthree\n"), [1, 2])

    def test_one_line_paragraphs_pass(self):
        self.assertEqual(found("one\n\ntwo\n"), [])

    def test_wrapped_list_item_is_flagged_but_a_new_item_is_not(self):
        self.assertEqual(found("- one\n  more\n- two\n1. three\n   more\n2. four\n"), [1, 4])

    def test_paren_numbered_and_star_items_start_a_block(self):
        self.assertEqual(found("1) a\n2) b\n* c\n+ d\n"), [])

    def test_item_directly_after_a_paragraph_starts_a_new_block(self):
        self.assertEqual(found("text\n- item\n"), [])

    def test_paragraph_after_an_item_continues_it(self):
        self.assertEqual(found("- item\ntext\n"), [1])

    def test_wrapped_quote_is_flagged_and_quoted_paragraphs_are_not(self):
        self.assertEqual(found("> one\n> two\n>\n> three\n"), [1])

    def test_quote_after_a_paragraph_is_not_its_continuation(self):
        self.assertEqual(found("text\n> quote\n"), [])

    def test_text_after_a_quote_continues_it_only_at_the_same_depth(self):
        self.assertEqual(found("> quote\nlazy\n"), [])
        self.assertEqual(found("> > deep\n> shallow\n"), [])

    def test_code_fences_are_skipped(self):
        self.assertEqual(found("```\na\nb\n```\n"), [])
        self.assertEqual(found("~~~\na\nb\n~~~\n"), [])

    def test_fence_closes_only_on_a_matching_marker(self):
        self.assertEqual(found("````\n```\nb\n````\nx\ny\n"), [5])
        self.assertEqual(found("```\n~~~\nb\n```\nx\ny\n"), [5])

    def test_text_after_a_closing_fence_starts_fresh(self):
        self.assertEqual(found("one\n```\ncode\n```\ntwo\n"), [])

    def test_a_fence_marker_with_text_does_not_close_a_fence(self):
        self.assertEqual(found("```\na\n``` not a close\nb\n```\nx\ny\n"), [6])

    def test_frontmatter_is_skipped_and_prose_after_it_is_checked(self):
        self.assertEqual(found("---\nsummary: a\n  b\n---\nx\ny\n"), [5])

    def test_a_rule_that_is_not_on_line_one_is_not_frontmatter(self):
        self.assertEqual(found("x\n\n---\n\na\nb\n"), [5])

    def test_tables_headings_rules_and_html_are_not_prose(self):
        text = "# Head\ntext\n| a | b |\n|---|---|\n| 1 | 2 |\ntext\n***\ntext\n<!-- c -->\ntext\n"
        self.assertEqual(found(text), [])

    def test_each_rule_style_ends_a_paragraph(self):
        for rule in ("---", "***", "___"):
            self.assertEqual(found(f"text\n{rule}\ntext\n"), [], rule)

    def test_text_directly_after_a_heading_or_table_is_not_a_continuation(self):
        self.assertEqual(found("# Head\ntext\n"), [])
        self.assertEqual(found("| a |\ntext\n"), [])

    def test_hard_break_allows_the_next_line(self):
        self.assertEqual(found("one  \ntwo\n"), [])
        self.assertEqual(found("one\\\ntwo\n"), [])
        self.assertEqual(found("one  \ntwo\nthree\n"), [2])

    def test_hard_break_on_a_list_item_allows_its_next_line(self):
        self.assertEqual(found("- one  \n  two\n"), [])
        self.assertEqual(found("- one\\\n  two\n"), [])

    def test_empty_text(self):
        self.assertEqual(found(""), [])


class Files(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = self.tmp.name

    def write(self, rel: str, text: str) -> str:
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path

    def run_main(self, paths: list[str]) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = mw.main(paths)
        return code, out.getvalue()

    def test_clean_files_exit_zero(self):
        self.write("a.md", "one\n\ntwo\n")
        self.assertEqual(self.run_main([self.root]), (0, ""))

    def test_a_wrapped_file_exits_one_and_names_file_and_line(self):
        path = self.write("a.md", "one\ntwo\n")
        code, out = self.run_main([self.root])
        self.assertEqual(code, 1)
        self.assertIn(f"{path}:2: continues the line above", out)
        self.assertIn("1 wrapped line(s)", out)

    def test_the_count_adds_up_across_lines_and_files(self):
        self.write("a.md", "one\ntwo\nthree\n")
        self.write("b.md", "one\ntwo\n")
        self.assertIn("3 wrapped line(s)", self.run_main([self.root])[1])

    def test_a_single_file_path_is_checked(self):
        path = self.write("a.md", "one\ntwo\n")
        self.assertEqual(self.run_main([path])[0], 1)

    def test_a_missing_path_is_an_error_not_a_pass(self):
        code, out = self.run_main([os.path.join(self.root, "nope")])
        self.assertEqual(code, 2)
        self.assertIn("no such file or folder", out)

    def test_a_missing_path_is_reported_even_beside_a_good_one(self):
        self.write("a.md", "one\n")
        self.assertEqual(self.run_main([self.root, os.path.join(self.root, "nope")])[0], 2)

    def test_only_markdown_is_checked(self):
        self.write("a.txt", "one\ntwo\n")
        self.assertEqual(self.run_main([self.root])[0], 0)

    def test_hidden_and_node_modules_folders_are_skipped(self):
        self.write(".hidden/a.md", "one\ntwo\n")
        self.write("node_modules/p/a.md", "one\ntwo\n")
        self.assertEqual(self.run_main([self.root])[0], 0)

    def test_symbolic_links_in_a_folder_are_not_reported_twice(self):
        target = self.write("a.md", "one\ntwo\n")
        os.symlink(target, os.path.join(self.root, "b.md"))
        code, out = self.run_main([self.root])
        self.assertEqual((code, out.count("continues the line above")), (1, 1))

    def test_nested_folders_are_searched(self):
        self.write("docs/sub/a.md", "one\ntwo\n")
        self.assertEqual(self.run_main([self.root])[0], 1)

    def test_default_path_is_the_current_folder(self):
        self.write("a.md", "one\ntwo\n")
        before = os.getcwd()
        os.chdir(self.root)
        try:
            self.assertEqual(self.run_main([])[0], 1)
        finally:
            os.chdir(before)


if __name__ == "__main__":
    unittest.main()
