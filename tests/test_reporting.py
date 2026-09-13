import unittest

from continuity.reporting.text import table


class ReportingTests(unittest.TestCase):
    def test_control_characters_are_escaped(self):
        text = table(("Name",), [("a\n\x1b[31m\t",)])
        self.assertNotIn("\x1b", text)
        self.assertIn(r"\n", text)
        self.assertEqual(len(text.splitlines()), 3)
