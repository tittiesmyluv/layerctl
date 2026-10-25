import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import core
from profiles import load_profile

SAMPLE = """MemTotal:        3643468 kB
MemAvailable:    1100548 kB
SwapTotal:       4194300 kB
SwapFree:        2605408 kB
==STAT==
cpu  1000 200 300 4000 500 0 0 0 0 0
==LOAD==
1.00 2.00 3.00 1/100 999
==PROC==
42
==BATT==
  level: 77
"""

class FakeT:
    name = "fake"
    def __init__(self, out): self.out = out
    def run(self, cmd, timeout=30): return self.out

class TestCore(unittest.TestCase):
    def test_mb(self):
        self.assertAlmostEqual(core.mb(1024), 1.0)

    def test_snapshot_parse(self):
        s = core.snapshot(FakeT(SAMPLE))
        self.assertEqual(s["mem"]["MemTotal"], 3643468)
        self.assertEqual(s["mem"]["MemAvailable"], 1100548)
        self.assertEqual(s["procs"], 42)
        self.assertEqual(s["batt"]["level"], "77")
        self.assertEqual(s["load"], "1.00 2.00 3.00 1/100 999")
        self.assertIsNotNone(s["stat"])

    def test_rates_cpu_zero(self):
        p = {"ts": 0, "net": {}, "stat": (1000, 500)}
        c = {"ts": 1, "net": {}, "stat": (2000, 1500)}
        self.assertAlmostEqual(core.rates(p, c)["cpu"], 0.0)

    def test_rates_net(self):
        p = {"ts": 0, "net": {"wlan0": (0, 0)}, "stat": None}
        c = {"ts": 1, "net": {"wlan0": (1000, 0)}, "stat": None}
        self.assertAlmostEqual(core.rates(p, c)["rx_kbps"], 8.0)

class TestProfiles(unittest.TestCase):
    def test_match(self):
        self.assertEqual(load_profile("SC-53F", "mt6835").__name__.split(".")[-1], "sc53f")

    def test_fallback(self):
        self.assertEqual(load_profile("Nonexistent", "zzz").__name__.split(".")[-1], "generic")

class TestStore(unittest.TestCase):
    def test_roundtrip(self):
        import tempfile
        import tui
        d = tempfile.mkdtemp()
        p = os.path.join(d, "x.tsv")
        recs = [["A", "com.a", "none", 1, ""], ["C1", "com.b", "disable", 2, "note"]]
        tui.save(recs, p)
        self.assertEqual(tui.load(p), recs)

if __name__ == "__main__":
    unittest.main()

class TestProfilesSh53d(unittest.TestCase):
    def test_match(self):
        self.assertEqual(load_profile("SH-53D", "mt6833").__name__.split(".")[-1], "sh53d")

    def test_generic_not_shadowed(self):
        self.assertEqual(load_profile("Pixel", "tensor").__name__.split(".")[-1], "generic")
