"""plugin.json's defaults (what the host passes in) must equal the ones hooks/register.tsx falls back on; they once differed.
Run: python3 -m unittest discover -s adapters/claude/session-guard -p 'test_defaults.py'"""

import json
import os
import re
import sys
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))


def read(*parts):
    with open(os.path.join(HERE, *parts), encoding="utf-8") as f:
        return f.read()


def declared():
    return {key: row["default"] for key, row in json.loads(read(".claude-plugin", "plugin.json"))["userConfig"].items()}


def fallbacks():
    block = re.search(r"const DEFAULTS = \{(.*?)^\}", read("hooks", "register.tsx"), re.S | re.M).group(1)
    found = {}
    for line in block.splitlines():
        if not re.match(r"^\s*\w+:", line):
            continue
        literal = re.match(r"^\s*(\w+):\s*(?:'([^']*)'|(\d+))\s*,", line)
        if not literal:
            raise AssertionError(f"cannot read this line of DEFAULTS (use a quoted string or an integer, then a comma): {line.strip()}")
        key, text, number = literal.groups()
        found[key] = text if number is None else int(number)
    return found


class Defaults(unittest.TestCase):
    def test_plugin_json_and_the_code_declare_the_same_settings_with_the_same_defaults(self):
        self.assertEqual(declared(), fallbacks())

    def test_a_default_the_test_cannot_read_is_named_not_skipped(self):
        source = "const DEFAULTS = {\n  softTokens: 150 * 1000,\n}\n"
        with mock.patch.object(sys.modules[__name__], "read", return_value=source):
            with self.assertRaisesRegex(AssertionError, "150 \\* 1000"):
                fallbacks()

    def test_the_close_button_submits_the_handoff_command(self):  # ADR 005: one entry point, so a change of command is a recorded decision
        self.assertEqual(declared()["handoffPrompt"], "/handoff")
        self.assertNotIn("handoffCheckPrompt", declared())  # ADR 005, amendment of 2026-10-09: the checks are `/handoff full`, typed on purpose, never a second button


if __name__ == "__main__":
    unittest.main()
