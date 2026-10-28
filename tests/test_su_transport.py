import os
import shutil
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import core


class SuTransport(unittest.TestCase):
    def test_local_when_forced(self):
        os.environ["VENICE_SU_LOCAL"] = "1"
        try:
            self.assertEqual(core.Su().argv("id"), ["su", "-c", "id"])
        finally:
            del os.environ["VENICE_SU_LOCAL"]

    def test_via_adb_when_adb_exists(self):
        if not shutil.which("adb"):
            self.skipTest("adb が無い")
        a = core.Su().argv("pm list packages")
        self.assertEqual(a[0], "adb")
        self.assertEqual(a[-1], "su -c 'pm list packages'")

    def test_via_adb_honours_serial(self):
        if not shutil.which("adb"):
            self.skipTest("adb が無い")
        os.environ["ANDROID_SERIAL"] = "SERIAL123"
        try:
            a = core.Su().argv("id")
            self.assertEqual(a[:3], ["adb", "-s", "SERIAL123"])
        finally:
            del os.environ["ANDROID_SERIAL"]

    def test_detect_prefers_su_when_asked(self):
        t = core.detect("su")
        self.assertIsNotNone(t)
        self.assertEqual(t.name, "su(root)")


if __name__ == "__main__":
    unittest.main()
