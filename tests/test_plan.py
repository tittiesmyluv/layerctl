"""plan_lines / infer の回帰テスト。

これまで core と profile 照合しかテストが無く、
一番バグが出るこの2関数が無検証だった。
"""
import os, sys, unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tui


class PlanLines(unittest.TestCase):
    """plan_lines(recs, st) は差分コマンドだけを返す。st=(dis,wht,bkt,ops)"""

    def plan(self, layer, pkg, st):
        return tui.plan_lines([[layer, pkg, "x", 1, ""]], st)

    # --- 収束 ---
    def test_b1_converged_is_empty(self):
        st = (set(), set(), {"com.a": "45"}, {"com.a"})
        self.assertEqual(self.plan("B1", "com.a", st), [])

    def test_a_converged_is_empty(self):
        st = (set(), set(), {"com.a": "10"}, set())
        self.assertEqual(self.plan("A", "com.a", st), [])

    # --- 基本動作 ---
    def test_b1_from_scratch(self):
        out = self.plan("B1", "com.a", (set(), set(), {}, set()))
        self.assertIn("cmd appops set com.a RUN_ANY_IN_BACKGROUND ignore", out)
        self.assertIn("am set-standby-bucket com.a restricted", out)

    def test_c1_disables(self):
        out = self.plan("C1", "com.a", (set(), set(), {}, set()))
        self.assertEqual(out, ["pm disable-user --user 0 com.a"])

    def test_l0_whitelists(self):
        out = self.plan("0", "com.a", (set(), set(), {}, set()))
        self.assertEqual(out, ["dumpsys deviceidle whitelist +com.a"])

    def test_a_restores_appops(self):
        out = self.plan("A", "com.a", (set(), set(), {}, {"com.a"}))
        self.assertIn("cmd appops set com.a RUN_ANY_IN_BACKGROUND allow", out)

    # ★ 穴: B1/C2 -> A に移しても bucket が restricted のまま残る
    def test_a_clears_restricted_bucket(self):
        st = (set(), set(), {"com.a": "45"}, set())
        out = self.plan("A", "com.a", st)
        self.assertIn("am set-standby-bucket com.a working_set", out)

    # ★ 穴: B2 -> A に移しても bucket が frequent のまま残る
    def test_a_clears_frequent_bucket(self):
        st = (set(), set(), {"com.a": "30"}, set())
        out = self.plan("A", "com.a", st)
        self.assertIn("am set-standby-bucket com.a working_set", out)


class Infer(unittest.TestCase):
    def setUp(self):
        self._saved = (tui.D_HARD, tui.C2_HARD, tui.L0_HARD, tui.IMPACT, tui.PROFILE)

    def tearDown(self):
        (tui.D_HARD, tui.C2_HARD, tui.L0_HARD, tui.IMPACT, tui.PROFILE) = self._saved

    def infer(self, pkg, dis=(), wht=(), bkt=None, ops=()):
        return tui.infer([pkg], set(dis), set(wht), dict(bkt or {}), set(ops))[0][0]

    def test_default_is_a(self):
        self.assertEqual(self.infer("com.a"), "A")

    def test_disabled_is_c1(self):
        self.assertEqual(self.infer("com.a", dis=["com.a"]), "C1")

    def test_whitelist_is_l0(self):
        self.assertEqual(self.infer("com.a", wht=["com.a"]), "0")

    def test_exempted_bucket_is_l0(self):
        self.assertEqual(self.infer("com.a", bkt={"com.a": "5"}), "0")

    def test_appops_ignore_is_b1(self):
        self.assertEqual(self.infer("com.a", ops=["com.a"]), "B1")

    def test_frequent_bucket_is_b2(self):
        self.assertEqual(self.infer("com.a", bkt={"com.a": "30"}), "B2")

    def test_d_hard_wins(self):
        tui.D_HARD = {"com.a"}
        self.assertEqual(self.infer("com.a"), "D")

    def test_l0_hard_wins(self):
        tui.L0_HARD = {"com.a"}
        self.assertEqual(self.infer("com.a"), "0")

    # ★ 穴: sc53f の QUIRKS.protected_refuse_disable が tui.py から読まれていない
    def test_protected_refuse_disable_goes_c2(self):
        class FakeProfile:
            QUIRKS = {"protected_refuse_disable": ["com.a"]}
        tui.PROFILE = FakeProfile()
        tui.C2_HARD = set()
        self.assertEqual(self.infer("com.a"), "C2")


    def test_c2_skips_bucket_when_quirk_says_so(self):
        class FakeProfile:
            QUIRKS = {"c2_does_not_hold_bucket": ["com.a"]}
        tui.PROFILE = FakeProfile()
        st = (set(), set(), {"com.a": "10"}, set())
        out = tui.plan_lines([["C2", "com.a", "restrict", 3, ""]], st)
        self.assertIn("cmd appops set com.a RUN_ANY_IN_BACKGROUND ignore", out)
        self.assertNotIn("am set-standby-bucket com.a restricted", out)


if __name__ == "__main__":
    unittest.main()
