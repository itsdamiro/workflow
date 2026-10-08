"""Tests for vault_lint.py (ADR 010). Usage: python3 -m unittest discover -s scripts -p 'test_vault_lint.py'"""

import contextlib
import io
import os
import tempfile
import time
import unittest

import vault_lint as vl

TAGS = """---
type: project
status: accepted
created: 2026-10-08
tags: [type/project, topic/mind]
---
# Tags
Back to [[Garden]]. Topics: `topic/mind`.
## Namespaces
- `type/`: decision, concept, idea, project, folder-definition
- `status/`: proposed, accepted, draft, active
- `project/`: one per project, named as its folder
- `topic/`: the owner's own topics, added by hand
"""
GARDEN = "---\ntype: project\nstatus: active\ncreated: 2026-10-08\ntags: [type/project, topic/mind]\n---\n[[Tags]] [[Idea]]\n"
IDEA = "---\ntype: idea\nstatus: draft\ncreated: 2026-10-08\nprojects: [alpha]\ntags: [type/idea, status/draft, topic/mind]\n---\nBack to [[Garden]].\n"
DAY = 86400


def fm(**fields) -> str:
    """A note with the given frontmatter lines (None drops a field) and a link home."""
    base = {"type": "idea", "status": "draft", "created": "2026-10-08", "projects": "[alpha]",
            "tags": "[type/idea, status/draft, topic/mind]"}
    base.update(fields)
    return "---\n" + "".join(f"{k}: {v}\n" for k, v in base.items() if v is not None) + "---\nBack to [[Garden]].\n"


class Values(unittest.TestCase):
    def test_plain_quoted_and_empty_scalars(self):
        self.assertEqual(vl.parse_value(" accepted "), "accepted")
        self.assertEqual(vl.parse_value('"a: b"'), "a: b")
        self.assertEqual(vl.parse_value("'x'"), "x")
        self.assertEqual(vl.parse_value(""), "")

    def test_comments_are_dropped_but_a_hash_inside_a_word_is_kept(self):
        self.assertEqual(vl.parse_value("proposed   # proposed | accepted"), "proposed")
        self.assertEqual(vl.parse_value("# only a comment"), "")
        self.assertEqual(vl.parse_value("a#b"), "a#b")
        self.assertEqual(vl.parse_value('"x # y" # c'), "x # y")
        self.assertEqual(vl.parse_value("[a] # c"), ["a"])

    def test_flow_lists(self):
        self.assertEqual(vl.parse_value("[a, b/c , d-e]"), ["a", "b/c", "d-e"])
        self.assertEqual(vl.parse_value("[]"), [])
        self.assertEqual(vl.parse_value('["[[A]]", \'[[B|b]]\']'), ["[[A]]", "[[B|b]]"])
        self.assertEqual(vl.parse_value('["a, b", c]'), ["a, b", "c"])

    def test_an_apostrophe_inside_a_list_item_is_text_but_a_leading_quote_quotes(self):
        self.assertEqual(vl.parse_value("[Dan's note, b]"), ["Dan's note", "b"])
        self.assertEqual(vl.parse_value("['a, b', c]"), ["a, b", "c"])

    def test_unreadable_values_raise_with_a_reason(self):
        cases = {"[a, b": "not closed", "[[A]]": "must be quoted", "[a] b": "text after the list",
                 '"open': "not closed", '"a" b': "text after the quote", "[a, [b]]": "must be quoted",
                 "[a[b]": "must be quoted"}
        for bad, reason in cases.items():
            with self.assertRaisesRegex(ValueError, reason, msg=bad):
                vl.parse_value(bad)


class Notes(unittest.TestCase):
    def parse(self, text):
        return vl.parse_note("p.md", "p", text, 0.0)

    def test_fields_and_body(self):
        note = self.parse("---\ntype: idea\n# a comment\n\ntags: [a, b]\nempty:\n---\nbody\n")
        self.assertEqual(note.fields, {"type": "idea", "tags": ["a", "b"], "empty": ""})
        self.assertEqual((note.problem, note.body), ("", "body\n"))

    def test_no_frontmatter_is_a_body(self):
        note = self.parse("just text\n---\nmore\n")
        self.assertEqual((note.fields, note.problem, note.body), ({}, "", "just text\n---\nmore\n"))

    def test_unclosed_fence(self):
        self.assertIn("not closed", self.parse("---\ntype: idea\nbody\n").problem)

    def test_unreadable_lines_are_a_problem_with_their_number(self):
        self.assertIn("line 3", self.parse("---\ntype: idea\n- item\n---\n").problem)
        self.assertIn("line 2", self.parse("---\ntags: [a\n---\n").problem)
        self.assertIn("line 2", self.parse("---\nkey:value\n---\n").problem)
        self.assertIn("line 2", self.parse("---\n  indented: x\n---\n").problem)

    def test_the_first_problem_is_kept(self):
        self.assertIn("line 2", self.parse("---\ntags: [a\n- x\n---\n").problem)

    def test_block_lists(self):
        note = self.parse('---\ntags:\n  - a\n  - "b c"\nother: x\nnone:\nmore:\n- u\n  -\n---\n')
        self.assertEqual((note.problem, note.fields["tags"], note.fields["other"]), ("", ["a", "b c"], "x"))
        self.assertEqual((note.fields["none"], note.fields["more"]), ("", ["u"]))

    def test_a_dash_line_needs_a_key_with_no_value_above_it(self):
        self.assertIn("line 3", self.parse("---\ntype: idea\n- bad\n---\n").problem)
        self.assertIn("line 2", self.parse("---\n- bad\n---\n").problem)
        self.assertIn("line 3", self.parse("---\ntags:\n  - [a, b]\n---\n").problem)

    def test_type_and_status_must_be_single_values(self):
        self.assertIn("type must be a single value", self.parse("---\ntype: [idea]\n---\n").problem)
        self.assertIn("status must be a single value", self.parse("---\nstatus:\n  - draft\n---\n").problem)
        self.assertEqual(self.parse("---\ntags: [a]\n---\n").problem, "")

    def test_crlf(self):
        note = self.parse("---\r\ntype: idea\r\n---\r\nbody\r\n")
        self.assertEqual((note.fields, note.problem), ({"type": "idea"}, ""))


class Prose(unittest.TestCase):
    def test_code_is_removed(self):
        text = "a [[Real]]\n```\n[[InFence]]\n```\nb `[[Inline]]` c\n~~~\n[[Tilde]]\n~~~\n[[After]]\n"
        links = [m.group(1) for m in vl.LINK.finditer(vl.prose(text))]
        self.assertEqual(links, ["Real", "After"])

    def test_a_longer_fence_is_not_closed_by_a_shorter_one(self):
        links = [m.group(1) for m in vl.LINK.finditer(vl.prose("````\n```\n[[X]]\n````\n[[Y]]\n"))]
        self.assertEqual(links, ["Y"])

    def test_backticks_do_not_pair_across_lines(self):
        self.assertIn("[[L]]", vl.prose("a `\n[[L]]\n` b"))

    def test_a_fence_of_the_other_kind_does_not_close(self):
        self.assertNotIn("[[X]]", vl.prose("```\n~~~\n[[X]]\n```\n"))

    def test_a_closing_fence_has_no_info_string(self):
        links = [m.group(1) for m in vl.LINK.finditer(vl.prose("```\n```python\n[[X]]\n```\n[[Y]]\n"))]
        self.assertEqual(links, ["Y"])

    def test_link_forms(self):
        found = [m.group(1) for m in vl.LINK.finditer("[[A]] [[B|b]] [[C#h]] [[D#h|d]] [[Dir/E]] [[F\\|f]] ![[G]]")]
        self.assertEqual(found, ["A", "B", "C", "D", "Dir/E", "F", "G"])
        self.assertEqual(vl.target_name(" Dir/Sub/E "), "e")
        self.assertEqual(vl.target_name("Note.MD"), "note")
        self.assertEqual(vl.target_name("Cafe\u0301"), "caf\u00e9")

    def test_concept_names(self):
        note = vl.parse_note("p.md", "p", '---\nconcepts: ["[[Foo Bar|x]]", plain, "[[Dir/Baz]]"]\n---\n', 0)
        self.assertEqual(vl.concept_names(note), ["foo bar", "plain", "baz"])
        self.assertEqual(vl.concept_names(vl.parse_note("p.md", "p", "---\ntype: idea\n---\n", 0)), [])


class VaultCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = self.tmp.name
        self.write("Tags.md", TAGS)
        self.write("Garden.md", GARDEN)
        self.write("Idea.md", IDEA)
        os.makedirs(os.path.join(self.root, "Projects", "alpha"))

    def write(self, rel, text, age_days=0):
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        stamp = 2_000_000_000 - age_days * DAY
        os.utime(path, (stamp, stamp))
        return path

    def lint(self, **kw):
        return vl.lint(self.root, now=2_000_000_000, **kw)

    def hits(self, rule, path=None):
        return [f for f in self.lint() if f.rule == rule and (path is None or f.path == path)]


class Clean(VaultCase):
    def test_a_valid_vault_has_no_findings(self):
        self.assertEqual(self.lint(), [])

    def test_hidden_folders_are_skipped(self):
        self.write(".obsidian/bad.md", "no frontmatter")
        self.assertEqual(self.lint(), [])

    def test_other_files_are_skipped(self):
        self.write("notes.txt", "[[Nope]]")
        self.assertEqual(self.lint(), [])


class Reading(VaultCase):
    def test_a_byte_order_mark_does_not_hide_the_frontmatter(self):
        with open(os.path.join(self.root, "Bom.md"), "wb") as f:
            f.write(b"\xef\xbb\xbf" + fm().encode("utf-8"))
        self.assertEqual([f for f in self.lint() if f.path == "Bom.md" and f.rule != "orphan"], [])

    def test_hidden_files_are_skipped(self):
        self.write(".hidden.md", "no frontmatter")
        self.assertEqual(self.lint(), [])

    def test_an_unreadable_entry_is_a_finding_not_a_crash(self):
        os.symlink(os.path.join(self.root, "nowhere"), os.path.join(self.root, "Broken.md"))
        found = [f for f in self.lint() if f.path == "Broken.md" and f.rule != "orphan"]
        self.assertEqual([(f.rule, f.severity) for f in found], [("bad-frontmatter", "error")])
        self.assertIn("cannot read the file: No such file", found[0].detail)

    @unittest.skipIf(os.geteuid() == 0, "root can read anything")
    def test_a_file_without_permission_is_a_finding(self):
        path = self.write("Locked.md", fm())
        os.chmod(path, 0)
        self.addCleanup(os.chmod, path, 0o644)
        self.assertEqual([f.rule for f in self.lint() if f.path == "Locked.md" and f.rule != "orphan"], ["bad-frontmatter"])

    def test_an_unreadable_inbox_note_gets_only_that_finding(self):
        os.makedirs(os.path.join(self.root, "Inbox"))
        with open(os.path.join(self.root, "Inbox", "B.md"), "wb") as f:
            f.write(b"\xff\xfe\x00")
        self.assertEqual([f.rule for f in self.lint() if f.path == "Inbox/B.md"], ["bad-frontmatter"])

    def test_a_note_with_bad_frontmatter_gets_no_link_nudge(self):
        self.write("A.md", "---\ntags: [a\n---\nplain text\n")
        self.assertEqual(self.hits("no-links", "A.md"), [])

    def test_a_list_for_type_is_reported_not_a_crash(self):
        self.write("A.md", fm(type="[idea]"))
        self.write("B.md", fm(status="[draft]"))
        for name in ("A.md", "B.md"):
            self.assertEqual([f.rule for f in self.lint() if f.path == name and f.rule != "orphan"], ["bad-frontmatter"])


class Frontmatter(VaultCase):
    def test_unreadable_frontmatter(self):
        self.write("A.md", "---\ntags: [a\n---\n[[Garden]]\n")
        found = self.hits("bad-frontmatter", "A.md")
        self.assertEqual([f.severity for f in found], ["error"])
        self.assertIn("line 2", found[0].detail)

    def test_an_unreadable_note_gets_no_field_or_tag_findings(self):
        self.write("A.md", "---\ntags: [a\n---\n[[Garden]]\n")
        self.assertEqual({f.rule for f in self.lint() if f.path == "A.md"} - {"orphan"}, {"bad-frontmatter"})

    def test_a_file_that_is_not_utf8(self):
        with open(os.path.join(self.root, "B.md"), "wb") as f:
            f.write(b"\xff\xfe\x00bad")
        self.assertIn("UTF-8", self.hits("bad-frontmatter", "B.md")[0].detail)

    def test_each_required_field_is_reported_by_name(self):
        self.write("A.md", fm(type=None, status=None, created=None))
        details = sorted(f.detail for f in self.hits("missing-field", "A.md"))
        self.assertEqual(details, ["created", "status", "type"])
        self.assertEqual({f.severity for f in self.hits("missing-field", "A.md")}, {"error"})

    def test_an_empty_value_counts_as_missing(self):
        self.write("A.md", fm(status=""))
        self.assertEqual([f.detail for f in self.hits("missing-field", "A.md")], ["status"])

    def test_a_generated_note_without_a_date_is_a_warning(self):
        self.write("A.md", fm(created=None, generated="true"))
        found = self.hits("missing-field", "A.md")
        self.assertEqual([(f.severity, f.detail) for f in found], [("warning", "created")])

    def test_only_created_is_softened_for_generated_notes(self):
        self.write("A.md", fm(status=None, generated="true"))
        self.assertEqual([f.severity for f in self.hits("missing-field", "A.md")], ["error"])

    def test_a_note_with_no_frontmatter_lacks_all_three(self):
        self.write("A.md", "text [[Garden]]\n")
        self.assertEqual(len(self.hits("missing-field", "A.md")), 3)

    def test_projects_is_required_for_some_types_only(self):
        self.write("A.md", fm(projects=None))
        self.write("B.md", fm(projects=None, type="concept", tags="[type/concept, status/draft, topic/mind]"))
        self.write("C.md", fm(projects="[]"))
        self.assertEqual([f.detail for f in self.hits("missing-field", "A.md")], ["projects"])
        self.assertEqual(self.hits("missing-field", "B.md"), [])
        self.assertEqual(self.hits("missing-field", "C.md"), [])

    def test_every_type_that_needs_projects_is_checked(self):
        for kind in ("decision", "idea", "pattern", "source"):
            self.write("A.md", fm(projects=None, type=kind))
            self.assertEqual([f.detail for f in self.hits("missing-field", "A.md")], ["projects"], kind)

    def test_unknown_type_and_status(self):
        self.write("A.md", fm(type="gizmo", tags="[status/draft, topic/mind]", status="odd"))
        self.assertEqual(len(self.hits("unknown-type", "A.md")), 1)
        self.assertEqual(len(self.hits("unknown-status", "A.md")), 1)
        self.assertEqual(self.hits("unknown-type", "Idea.md"), [])


class Tagging(VaultCase):
    def bad(self, tags, **fields):
        self.write("A.md", fm(tags=tags, **fields))
        return [f.detail for f in self.hits("bad-tag", "A.md")]

    def test_valid_tags_pass(self):
        self.assertEqual(self.bad("[type/idea, status/draft, topic/mind, project/alpha]"), [])

    def test_not_namespaced_or_not_kebab_case(self):
        self.assertEqual(len(self.bad("[idea]")), 1)
        self.assertEqual(len(self.bad("[Topic/mind]")), 1)
        self.assertEqual(len(self.bad("[topic/Mind]")), 1)
        self.assertEqual(len(self.bad("[topic/mind_map]")), 1)
        self.assertEqual(len(self.bad("[topic/a/b]")), 1)

    def test_unknown_namespace(self):
        self.assertIn("namespace", self.bad("[colour/red]")[0])

    def test_closed_namespaces_check_their_values(self):
        self.assertIn("type/", self.bad("[type/gizmo]", type="gizmo")[0])
        self.assertIn("status/", self.bad("[status/odd]", status="odd")[0])

    def test_a_tag_that_disagrees_with_its_field(self):
        self.assertIn("disagrees", self.bad("[type/concept]")[0])
        self.assertIn("disagrees", self.bad("[status/active]")[0])

    def test_an_open_namespace_value_is_free(self):
        self.assertEqual(self.bad("[topic/anything-at-all]"), [])

    def test_project_needs_a_folder(self):
        self.assertIn("project", self.bad("[project/beta]")[0])
        self.assertEqual(self.bad("[project/alpha]"), [])

    def test_a_project_file_is_not_a_project_folder(self):
        self.write("Projects/beta.md", fm())
        self.assertEqual(len(self.bad("[project/beta]")), 1)

    def test_a_file_with_a_project_name_is_not_a_project_folder_either(self):
        self.write("Projects/gamma", "not a folder")
        self.assertEqual(len(self.bad("[project/gamma]")), 1)

    def test_a_project_folder_matches_whatever_its_case(self):
        os.makedirs(os.path.join(self.root, "Projects", "Beta"))
        self.assertEqual(self.bad("[project/beta]"), [])

    def test_block_style_tags_are_read(self):
        self.write("A.md", fm(tags="\n  - type/idea\n  - topic/mind"))
        self.assertEqual(self.hits("bad-frontmatter", "A.md"), [])
        self.assertEqual(self.hits("no-tags", "A.md"), [])

    def test_a_scalar_tags_value_is_read_as_one_tag(self):
        self.assertEqual(len(self.bad("idea")), 1)


class Links(VaultCase):
    def test_broken_link_in_the_body(self):
        self.write("A.md", fm() + "See [[Nowhere]].\n")
        found = self.hits("broken-link", "A.md")
        self.assertEqual([(f.severity, f.detail) for f in found], [("error", "[[nowhere]] is not a note")])

    def test_broken_link_in_frontmatter(self):
        self.write("A.md", fm(see='"[[Nowhere]]"'))
        self.assertEqual(len(self.hits("broken-link", "A.md")), 1)

    def test_links_resolve_by_name_with_alias_heading_path_and_case(self):
        self.write("A.md", fm() + "[[idea|x]] [[Idea#Head]] [[Some/Dir/IDEA]]\n")
        self.assertEqual(self.hits("broken-link", "A.md"), [])

    def test_a_heading_link_inside_the_same_note_is_fine(self):
        self.write("A.md", fm() + "[[#Section]] [[#^block]]\n")
        self.assertEqual(self.hits("broken-link", "A.md"), [])

    def test_embeds_of_files_and_note_file_names_are_fine(self):
        self.write("A.md", fm() + "![[pic.png]] [[Garden.md]] [[doc.pdf]] ![[Idea]]\n")
        self.assertEqual(self.hits("broken-link", "A.md"), [])

    def test_an_escaped_pipe_in_a_table_is_an_alias(self):
        self.write("A.md", fm().replace("Back to [[Garden]].", "| a |\n|---|\n| [[Garden\\|home]] |"))
        self.assertEqual(self.hits("broken-link", "A.md"), [])
        self.assertEqual(self.hits("no-links", "A.md"), [])

    def test_a_note_with_a_dot_in_its_name_is_still_a_note(self):
        self.write("Node.js.md", fm())
        self.write("A.md", fm() + "[[Node.js]]\n")
        self.assertEqual(self.hits("broken-link", "A.md"), [])
        self.assertEqual(self.hits("orphan", "Node.js.md"), [])

    def test_a_dotted_target_that_does_not_look_like_a_file_is_still_broken(self):
        for target in ("v1.2", "v1.23", "a.abcdefgh", "a.b"):
            self.write("A.md", fm() + f"[[{target}]]\n")
            self.assertEqual(len(self.hits("broken-link", "A.md")), 1, target)

    def test_names_match_across_unicode_forms(self):
        self.write("Cafe\u0301.md", fm())
        self.write("A.md", fm() + "[[Caf\u00e9]]\n")
        self.assertEqual(self.hits("broken-link", "A.md"), [])
        self.assertEqual(self.hits("orphan", "Cafe\u0301.md"), [])

    def test_links_in_code_are_not_links(self):
        self.write("A.md", fm() + "`[[Nope]]`\n```\n[[Nope]]\n```\n")
        self.assertEqual(self.hits("broken-link", "A.md"), [])

    def test_a_missing_concept_is_not_also_a_broken_link(self):
        self.write("A.md", fm(concepts='["[[ghost]]"]'))
        self.assertEqual(self.hits("broken-link", "A.md"), [])
        self.assertEqual(len(self.hits("missing-concept", "A.md")), 1)

    def test_missing_concept_forms(self):
        self.write("Concepts/Real.md", fm(type="concept", tags="[type/concept, topic/mind]"))
        self.write("A.md", fm(concepts='["[[Real]]", real, ghost, "[[Other/Ghost2|g]]"]'))
        self.assertEqual(sorted(f.detail for f in self.hits("missing-concept", "A.md")),
                         ["ghost has no note in Concepts/", "ghost2 has no note in Concepts/"])

    def test_a_note_outside_concepts_does_not_make_a_concept(self):
        self.write("A.md", fm(concepts="[idea]"))
        self.assertEqual(len(self.hits("missing-concept", "A.md")), 1)

    def test_a_concept_note_is_linked_through_the_concepts_field(self):
        self.write("Concepts/Real.md", fm(type="concept", tags="[type/concept, topic/mind]") + "[[Idea]]\n")
        self.write("A.md", fm(concepts='["[[Real]]"]'))
        self.assertEqual(self.hits("orphan", "Concepts/Real.md"), [])

    def test_duplicate_names_are_reported_once_on_the_later_file(self):
        self.write("X/Same.md", fm())
        self.write("Y/same.md", fm())
        found = self.hits("duplicate-name")
        self.assertEqual([(f.path, f.severity) for f in found], [("Y/same.md", "error")])
        self.assertIn("X/Same.md", found[0].detail)

    def test_three_copies_report_two(self):
        for folder in "XYZ":
            self.write(f"{folder}/Same.md", fm())
        self.assertEqual(len(self.hits("duplicate-name")), 2)


class Nudges(VaultCase):
    def test_a_note_with_no_links_is_a_warning_with_hints(self):
        self.write("A.md", fm().replace("Back to [[Garden]].", "This mentions Idea and garden in plain text."))
        found = self.hits("no-links", "A.md")
        self.assertEqual([f.severity for f in found], ["warning"])
        self.assertTrue(found[0].detail.endswith("could link: Garden, Idea"), found[0].detail)

    def test_no_hint_when_nothing_is_mentioned(self):
        self.write("A.md", fm().replace("Back to [[Garden]].", "Nothing here."))
        self.assertEqual(self.hits("no-links", "A.md")[0].detail, "links to no other note")

    def test_a_name_inside_a_longer_word_is_not_a_hint(self):
        self.write("A.md", fm().replace("Back to [[Garden]].", "Gardener and Idea-like and ideas."))
        self.assertEqual(self.hits("no-links", "A.md")[0].detail, "links to no other note")

    def test_hints_are_limited(self):
        names = [f"Name{c}" for c in "ABCDEFG"]
        for n in names:
            self.write(f"{n}.md", fm())
        self.write("A.md", fm().replace("Back to [[Garden]].", " ".join(names)))
        detail = self.hits("no-links", "A.md")[0].detail
        self.assertEqual(detail.count("Name"), 5)

    def test_a_link_to_itself_or_to_nothing_does_not_count(self):
        self.write("A.md", fm().replace("Back to [[Garden]].", "[[A]] [[Nowhere]]"))
        self.assertEqual(len(self.hits("no-links", "A.md")), 1)

    def test_a_link_in_frontmatter_counts(self):
        self.write("A.md", fm(see='"[[Garden]]"').replace("Back to [[Garden]].", "x"))
        self.assertEqual(self.hits("no-links", "A.md"), [])

    def test_a_new_inbox_note_may_wait_and_an_old_one_may_not(self):
        self.write("Inbox/New.md", fm().replace("Back to [[Garden]].", "x"), age_days=3)
        self.write("Inbox/Old.md", fm().replace("Back to [[Garden]].", "x"), age_days=30)
        self.assertEqual([f.path for f in self.hits("no-links")], ["Inbox/Old.md"])

    def test_the_inbox_period_is_the_option(self):
        self.write("Inbox/New.md", fm().replace("Back to [[Garden]].", "x"), age_days=3)
        self.assertEqual([f.path for f in vl.lint(self.root, inbox_days=2, now=2_000_000_000) if f.rule == "no-links"],
                         ["Inbox/New.md"])
        self.assertEqual(self.hits("no-links"), [])

    def test_the_inbox_boundary_day_still_waits(self):
        self.write("Inbox/Edge.md", fm().replace("Back to [[Garden]].", "x"), age_days=14)
        self.assertEqual(self.hits("no-links"), [])

    def test_orphans_are_warnings_and_inbox_is_exempt(self):
        self.write("A.md", fm())
        self.write("Inbox/I.md", fm())
        found = self.hits("orphan")
        self.assertEqual([(f.path, f.severity) for f in found], [("A.md", "warning")])

    def test_garden_is_exempt_even_when_nothing_links_to_it(self):
        self.write("Tags.md", TAGS.replace("[[Garden]]", "home"))
        self.write("Idea.md", fm().replace("[[Garden]]", "[[Tags]]"))
        self.assertEqual(self.hits("orphan", "Garden.md"), [])

    def test_a_folder_that_only_starts_like_inbox_is_not_exempt(self):
        self.write("Inboxes/I.md", fm())
        self.assertEqual(len(self.hits("orphan", "Inboxes/I.md")), 1)
        self.write("Inboxes/J.md", fm().replace("Back to [[Garden]].", "x"), age_days=1)
        self.assertEqual(len(self.hits("no-links", "Inboxes/J.md")), 1)

    def test_hints_are_sorted_and_never_name_the_note_itself(self):
        self.write("Zed.md", fm())
        self.write("X/Aardvark.md", fm())
        self.write("A.md", fm().replace("Back to [[Garden]].", "Zed Aardvark A"))
        self.assertTrue(self.hits("no-links", "A.md")[0].detail.endswith("could link: Aardvark, Zed"))

    def test_a_link_from_another_note_ends_the_orphan_state_but_a_self_link_does_not(self):
        self.write("A.md", fm() + "[[A]]\n")
        self.assertEqual(len(self.hits("orphan", "A.md")), 1)
        self.write("B.md", fm() + "[[A]]\n")
        self.assertEqual(self.hits("orphan", "A.md"), [])

    def test_no_tags(self):
        self.write("A.md", fm(tags="[]"))
        self.write("B.md", fm(tags=None))
        self.assertEqual([f.detail for f in self.hits("no-tags", "A.md")], ["no tags"])
        self.assertEqual([f.detail for f in self.hits("no-tags", "B.md")], ["no tags"])

    def test_every_type_that_wants_a_topic_is_checked(self):
        for kind in ("decision", "concept", "pattern", "idea", "source"):
            self.write("A.md", fm(type=kind, tags=f"[type/{kind}]"))
            self.assertEqual([f.detail for f in self.hits("no-tags", "A.md")], ["no topic/ tag"], kind)

    def test_another_namespace_is_not_a_topic(self):
        self.write("A.md", fm(tags="[type/idea, topical/x]"))
        self.assertEqual([f.detail for f in self.hits("no-tags", "A.md")], ["no topic/ tag"])

    def test_a_note_with_unreadable_frontmatter_gets_no_tag_nudge(self):
        self.write("A.md", "---\ntype: idea\n- bad\n---\n[[Garden]]\n")
        self.assertEqual(self.hits("no-tags", "A.md"), [])

    def test_a_topic_is_expected_on_some_types_only(self):
        self.write("A.md", fm(tags="[type/idea]"))
        self.write("B.md", fm(type="project", tags="[type/project]"))
        self.assertEqual([f.detail for f in self.hits("no-tags", "A.md")], ["no topic/ tag"])
        self.assertEqual(self.hits("no-tags", "B.md"), [])
        self.assertEqual({f.severity for f in self.hits("no-tags")}, {"warning"})

    def test_unlisted_topics_name_the_tag_and_its_notes(self):
        self.write("A.md", fm(tags="[type/idea, topic/sympose]"))
        self.write("B.md", fm(tags="[type/idea, topic/sympose]"))
        found = self.hits("unlisted-topic")
        self.assertEqual([(f.path, f.severity) for f in found], [("Tags.md", "warning")])
        self.assertIn("topic/sympose", found[0].detail)
        self.assertIn("A.md, B.md", found[0].detail)

    def test_a_note_named_with_hyphens_makes_a_topic_known(self):
        self.write("Prompt-caching.md", fm())
        self.write("A.md", fm(tags="[type/idea, topic/mind, topic/prompt-caching]"))
        self.assertEqual(self.hits("unlisted-topic"), [])

    def test_a_tag_twice_in_one_note_names_the_note_once(self):
        self.write("A.md", fm(tags="[type/idea, topic/zzz, topic/zzz]"))
        self.assertTrue(self.hits("unlisted-topic")[0].detail.endswith("used by A.md"))

    def test_a_badly_written_topic_is_only_a_bad_tag(self):
        self.write("A.md", fm(tags="[type/idea, topic/Zzz]"))
        self.assertEqual(self.hits("unlisted-topic"), [])
        self.assertEqual(len(self.hits("bad-tag", "A.md")), 1)

    def test_only_the_topic_namespace_makes_topics(self):
        self.write("A.md", fm(tags="[type/idea, topical/zzz, topic/mind]"))
        self.assertEqual(self.hits("unlisted-topic"), [])

    def test_exactly_the_shown_limit_of_users_adds_no_more(self):
        for i in range(5):
            self.write(f"N{i}.md", fm(tags="[type/idea, topic/zzz]"))
        self.assertTrue(self.hits("unlisted-topic")[0].detail.endswith("N4.md"))

    def test_listed_or_noted_topics_are_fine(self):
        self.write("Prompt caching.md", fm())
        self.write("Stylo.md", fm())
        self.write("A.md", fm(tags="[type/idea, topic/mind, topic/prompt-caching, topic/stylo]"))
        self.assertEqual(self.hits("unlisted-topic"), [])

    def test_users_of_a_topic_are_cut_off(self):
        for i in range(7):
            self.write(f"N{i}.md", fm(tags="[type/idea, topic/zzz]"))
        detail = self.hits("unlisted-topic")[0].detail
        self.assertIn("and 2 more", detail)
        self.assertNotIn("N5.md", detail)


class Command(VaultCase):
    def run_cli(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = vl.main(list(args))
        return code, out.getvalue()

    def test_clean_exits_zero(self):
        code, out = self.run_cli(self.root)
        self.assertEqual((code, out), (0, "0 error(s), 0 warning(s)\n"))

    def test_errors_exit_one_and_are_printed_with_counts(self):
        self.write("A.md", fm(type=None))
        code, out = self.run_cli(self.root)
        self.assertEqual(code, 1)
        self.assertIn("A.md: error: missing-field: type\n", out)
        self.assertIn("\n\n  missing-field: 1\n", out)
        self.assertTrue(out.endswith("1 error(s), 1 warning(s)\n"), out)

    def test_warnings_alone_exit_zero(self):
        self.write("A.md", fm())
        code, out = self.run_cli(self.root)
        self.assertEqual(code, 0)
        self.assertIn("A.md: warning: orphan: no note links here", out)
        self.assertTrue(out.endswith("0 error(s), 1 warning(s)\n"), out)

    def test_counts_are_listed_by_rule_name(self):
        self.write("A.md", fm(type=None))
        self.write("B.md", fm(tags="[colour/red, type/idea, topic/mind]"))
        counts = [line.split(":")[0].strip() for line in self.run_cli(self.root)[1].splitlines() if line.startswith("  ")]
        self.assertEqual(counts, sorted(counts))
        self.assertGreater(len(counts), 1)

    def test_the_default_inbox_period_is_two_weeks(self):
        path = self.write("Inbox/I.md", fm().replace("Back to [[Garden]].", "x"))
        for days, reported in ((10, False), (20, True)):
            stamp = time.time() - days * DAY
            os.utime(path, (stamp, stamp))
            self.assertEqual("no-links" in self.run_cli(self.root)[1], reported, days)

    def test_findings_come_back_sorted_even_when_found_late(self):
        self.write("Z.md", fm(type=None))
        self.write("A.md", fm())
        found = self.lint()
        self.assertEqual(found, sorted(found))
        self.assertLess([f.path for f in found].index("A.md"), [f.path for f in found].index("Z.md"))

    def test_findings_are_sorted(self):
        self.write("B.md", fm(type=None))
        self.write("A.md", fm(status=None))
        lines = [line for line in self.run_cli(self.root)[1].splitlines() if ": error:" in line]
        self.assertEqual(lines, sorted(lines))

    def test_a_vault_without_tags_is_a_usage_error(self):
        os.remove(os.path.join(self.root, "Tags.md"))
        code, out = self.run_cli(self.root)
        self.assertEqual(code, 2)
        self.assertIn("no Tags.md", out)

    def test_a_tags_note_without_type_values_is_a_usage_error(self):
        self.write("Tags.md", TAGS.replace("- `type/`: decision, concept, idea, project, folder-definition\n", ""))
        code, out = self.run_cli(self.root)
        self.assertEqual(code, 2)
        self.assertIn("no values for type/", out)

    def test_a_missing_folder_is_a_usage_error(self):
        self.assertEqual(self.run_cli(os.path.join(self.root, "nope"))[0], 2)

    def test_the_inbox_option_is_read(self):
        path = self.write("Inbox/I.md", fm().replace("Back to [[Garden]].", "x"))
        five_days_ago = time.time() - 5 * DAY
        os.utime(path, (five_days_ago, five_days_ago))
        self.assertNotIn("no-links", self.run_cli(self.root)[1])
        self.assertIn("Inbox/I.md: warning: no-links", self.run_cli(self.root, "--inbox-days", "2")[1])

    def test_read_only(self):
        self.write("A.md", fm(type=None))
        names = ("A.md", "Tags.md", "Idea.md")

        def snapshot():
            out = {}
            for name in names:
                with open(os.path.join(self.root, name), "rb") as f:
                    out[name] = f.read()
            return out

        before = snapshot()
        self.run_cli(self.root)
        self.assertEqual(before, snapshot())


class TagsNote(unittest.TestCase):
    def test_namespaces_closed_values_and_topics(self):
        tags = vl.read_tags(TAGS)
        self.assertEqual(tags.namespaces, {"type", "status", "project", "topic"})
        self.assertEqual(tags.closed["type"], {"decision", "concept", "idea", "project", "folder-definition"})
        self.assertEqual(tags.closed["status"], {"proposed", "accepted", "draft", "active"})
        self.assertNotIn("project", tags.closed)
        self.assertEqual(tags.topics, {"mind"})

    def test_a_bare_topic_namespace_is_not_a_topic(self):
        text = "- `type/`: a\n- `status/`: b\n- `topic/`: x\n"
        self.assertEqual(vl.read_tags(text).topics, set())

    def test_an_empty_list_does_not_swallow_the_next_line(self):
        with self.assertRaisesRegex(ValueError, "status/"):
            vl.read_tags("- `type/`: a\n- `status/`: \n- `topic/`: x\n")

    def test_type_and_status_values_are_required(self):
        for text, missing in (("- `status/`: b\n", "type/"), ("- `type/`: a\n", "status/"),
                              ("- `type/`: a\n- `status/`: \n", "status/")):
            with self.assertRaisesRegex(ValueError, missing):
                vl.read_tags(text)


if __name__ == "__main__":
    unittest.main()
