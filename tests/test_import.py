import os
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import importers as imp
import tui


class ParsePlain(unittest.TestCase):
    def test_basic(self):
        d = imp.parse_plain("com.a\n# comment\ncom.b\n\n   com.c   \n")
        self.assertEqual(sorted(d), ["com.a", "com.b", "com.c"])

    def test_ignores_junk(self):
        d = imp.parse_plain("notapackage\ncom.a\n")
        self.assertNotIn("notapackage", d)
        self.assertIn("com.a", d)


class ParseTsv(unittest.TestCase):
    def test_verdict(self):
        d = imp.parse_tsv("com.a\trecommended\ncom.b\tunsafe\n")
        self.assertEqual(d["com.a"], "recommended")
        self.assertEqual(d["com.b"], "unsafe")

    def test_missing_verdict(self):
        self.assertEqual(imp.parse_tsv("com.a\n"), {"com.a": ""})


class ParseUad(unittest.TestCase):
    def test_removal(self):
        t = '{"com.a": {"removal": "recommended", "list": "Oem"}}'
        self.assertEqual(imp.parse_uad_json(t), {"com.a": "recommended"})

    def test_skips_non_dict(self):
        t = '{"com.a": "x", "com.b": {"removal": "expert"}}'
        self.assertEqual(imp.parse_uad_json(t), {"com.b": "expert"})


class LoadDispatch(unittest.TestCase):
    def _write(self, name, text):
        p = os.path.join(tempfile.mkdtemp(), name)
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
        return p

    def test_json_by_content(self):
        p = self._write("x.txt", '{"com.a": {"removal": "expert"}}')
        self.assertEqual(imp.load(p), {"com.a": "expert"})

    def test_tsv_by_tab(self):
        p = self._write("x.txt", "com.a\trecommended\n")
        self.assertEqual(imp.load(p), {"com.a": "recommended"})

    def test_plain_fallback(self):
        p = self._write("x.txt", "com.a\ncom.b\n")
        self.assertEqual(sorted(imp.load(p)), ["com.a", "com.b"])


class Mapping(unittest.TestCase):
    def test_verdict_to_layer(self):
        self.assertEqual(tui.VERDICT_LAYER["recommended"], "C1")
        self.assertEqual(tui.VERDICT_LAYER["expert"], "B1")
        self.assertEqual(tui.VERDICT_LAYER["unsafe"], "A")

    def test_merge_overwrites_and_sorts(self):
        old = [["A", "com.b", "none", 1, ""]]
        new = [["C1", "com.b", "disable", 1, ""], ["C1", "com.a", "disable", 1, ""]]
        m = tui.merge_recs(old, new)
        self.assertEqual([r[1] for r in m], ["com.a", "com.b"])
        self.assertEqual({r[1]: r[0] for r in m}["com.b"], "C1")

    def test_as_layer_overrides(self):
        p = os.path.join(tempfile.mkdtemp(), "l.txt")
        pathlib.Path(p).write_text("com.a\ncom.b\n")
        recs = tui.import_recs(p, as_layer="B1")
        self.assertEqual({r[0] for r in recs}, {"B1"})


if __name__ == "__main__":
    unittest.main()
