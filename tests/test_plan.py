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


class ApplyMeasure(unittest.TestCase):
    """apply_measure は層変更の効果と掃除(kill-all)の効果を分けて計測する。

    am kill-all を混ぜると、解放されたのが層変更のせいか掃除のせいか
    区別できない。README の実測表はここを分離していない。
    """

    def setUp(self):
        self.calls, self.seq = [], []
        self._rish, self._metrics, self._sleep = tui.rish, tui.metrics, tui.time.sleep
        tui.rish = lambda cmd, timeout=300: (self.calls.append(cmd), "")[1]
        tui.metrics = lambda: self.seq.pop(0)
        tui.time.sleep = lambda s: None

    def tearDown(self):
        tui.rish, tui.metrics, tui.time.sleep = self._rish, self._metrics, self._sleep

    def test_two_phase_separates_kill_from_commands(self):
        self.seq = [{"avail_kb": 1000}, {"avail_kb": 1000}, {"avail_kb": 1300}]
        b, m1, m2 = tui.apply_measure(["cmd x"], settle=0, cmd_settle=0)
        self.assertEqual(b["avail_kb"], 1000)
        self.assertEqual(m1["avail_kb"], 1000)   # コマンドだけでは動かない
        self.assertEqual(m2["avail_kb"], 1300)   # kill-all で初めて動く
        self.assertEqual(self.calls, ["cmd x", "am kill-all"])

    def test_no_kill_flag(self):
        self.seq = [{"avail_kb": 1000}, {"avail_kb": 1100}]
        b, m1, m2 = tui.apply_measure(["cmd x"], do_kill=False, settle=0, cmd_settle=0)
        self.assertEqual(m1["avail_kb"], 1100)
        self.assertIs(m1, m2)
        self.assertEqual(self.calls, ["cmd x"])

    def test_empty_lines_still_kills(self):
        self.seq = [{"avail_kb": 1000}, {"avail_kb": 1000}, {"avail_kb": 1200}]
        b, m1, m2 = tui.apply_measure([], settle=0, cmd_settle=0)
        self.assertEqual(self.calls, ["am kill-all"])
        self.assertEqual(m2["avail_kb"], 1200)


class PlanJson(unittest.TestCase):
    """plan_json は他ツールが食える形で差分を出す。相互運用の入口。"""

    def test_shape(self):
        recs = [["B1", "com.a", "restrict", 1, ""], ["A", "com.b", "none", 1, ""]]
        j = tui.plan_json(recs, (set(), set(), {}, set()), "raven", "su")
        self.assertEqual(j["schema"], 1)
        self.assertEqual(j["profile"], "raven")
        self.assertEqual(j["transport"], "su")
        self.assertEqual(j["counts"]["recs"], 2)
        self.assertEqual(j["counts"]["commands"], 2)   # B1で2本、Aは未観測bucketなので0本
        self.assertIn("cmd", j["by_command"])
        self.assertIsInstance(j["commands"], list)

    def test_is_json_serialisable(self):
        import json
        recs = [["C1", "com.a", "disable", 3, ""]]
        j = tui.plan_json(recs, (set(), set(), {}, set()))
        self.assertEqual(json.loads(json.dumps(j))["commands"],
                         ["pm disable-user --user 0 com.a"])

    def test_converged_is_empty(self):
        recs = [["0", "com.a", "protect", 3, ""]]
        j = tui.plan_json(recs, (set(), {"com.a"}, {}, set()))
        self.assertEqual(j["commands"], [])
        self.assertEqual(j["counts"]["commands"], 0)


class NameRules(unittest.TestCase):
    """profiles/base.py の名前規則。未知機の seed を実用にするための床。"""

    def setUp(self):
        self._saved = (tui.PROFILE, tui.D_HARD)

    def tearDown(self):
        tui.PROFILE, tui.D_HARD = self._saved

    def infer(self, pkg, dis=(), wht=(), bkt=None, ops=()):
        return tui.infer([pkg], set(dis), set(wht), dict(bkt or {}), set(ops))[0][0]

    def test_phone_is_l0(self):
        self.assertEqual(self.infer("com.android.phone"), "0")

    def test_dialer_is_l0(self):
        self.assertEqual(self.infer("com.google.android.dialer"), "0")

    def test_messaging_is_l0(self):
        self.assertEqual(self.infer("com.google.android.apps.messaging"), "0")

    def test_launcher_is_l0(self):
        self.assertEqual(self.infer("com.google.android.apps.nexuslauncher"), "0")

    def test_gmail_falls_to_a(self):
        # raven の実機検証で gm は A。通知は FCM 経由なので制限したくない
        self.assertEqual(self.infer("com.google.android.gm"), "A")

    def test_photos_is_b1(self):
        self.assertEqual(self.infer("com.google.android.apps.photos"), "B1")

    def test_docs_editors_is_b1(self):
        self.assertEqual(self.infer("com.google.android.apps.docs.editors.sheets"), "B1")

    def test_sdm_plugins_is_c1(self):
        self.assertEqual(self.infer("com.android.sdm.plugins.dcmo"), "C1")

    def test_carrier_is_c1(self):
        self.assertEqual(self.infer("com.verizon.services"), "C1")

    def test_wellbeing_is_c1(self):
        self.assertEqual(self.infer("com.google.android.apps.wellbeing"), "C1")

    def test_unknown_falls_to_a(self):
        self.assertEqual(self.infer("com.example.nothing"), "A")

    def test_observation_beats_name_rule(self):
        self.assertEqual(self.infer("com.google.android.videos",
                                    wht=["com.google.android.videos"]), "0")

    def test_disabled_beats_name_rule(self):
        self.assertEqual(self.infer("com.google.android.gm",
                                    dis=["com.google.android.gm"]), "C1")

    def test_d_hard_beats_name_rule(self):
        tui.D_HARD = {"com.android.phone"}
        self.assertEqual(self.infer("com.android.phone"), "D")

    def test_profile_override_wins(self):
        class Fake:
            QUIRKS = {}
            NAME_RULES = (("C1", r"^com\.google\.android\.gm$"),)
        tui.PROFILE = Fake()
        self.assertEqual(self.infer("com.google.android.gm"), "C1")


class SampleKill(unittest.TestCase):
    """掃除の効果は分散が大きい。単発でなく複数回サンプルして中央値で見る。"""

    def setUp(self):
        self.calls, self.seq = [], []
        self._rish, self._metrics, self._sleep = tui.rish, tui.metrics, tui.time.sleep
        tui.rish = lambda cmd, timeout=300: (self.calls.append(cmd), "")[1]
        tui.metrics = lambda: self.seq.pop(0)
        tui.time.sleep = lambda s: None

    def tearDown(self):
        tui.rish, tui.metrics, tui.time.sleep = self._rish, self._metrics, self._sleep

    def test_samples_n_times(self):
        self.seq = [{"avail_kb": 0}, {"avail_kb": 1024},
                    {"avail_kb": 0}, {"avail_kb": 2048},
                    {"avail_kb": 0}, {"avail_kb": 0}]
        ds = tui.sample_kill(3, settle=0)
        self.assertEqual(ds, [1.0, 2.0, 0.0])
        self.assertEqual(self.calls, ["am kill-all"] * 3)

    def test_median_odd(self):
        self.assertEqual(tui.median([3.0, 1.0, 2.0]), 2.0)

    def test_median_even(self):
        self.assertEqual(tui.median([1.0, 2.0, 3.0, 4.0]), 2.5)

    def test_median_empty(self):
        self.assertEqual(tui.median([]), 0.0)


class Baseline(unittest.TestCase):
    """計測の前提（蓄積量と前回の掃除からの経過）を数字で出す。"""

    def test_baseline_line(self):
        m = {"avail_kb": 1024 * 1183, "swapfree_kb": 1024 * 4201, "procs": 732}
        s = tui.baseline_line(m)
        self.assertIn("MemAvailable 1183 MB", s)
        self.assertIn("procs 732", s)

    def test_baseline_line_with_elapsed(self):
        m = {"avail_kb": 0, "swapfree_kb": 0, "procs": 1}
        self.assertIn("3分12秒", tui.baseline_line(m, since=192))

    def test_mark_and_since(self):
        import tempfile, os as _os
        saved = tui.STATE
        try:
            tui.STATE = _os.path.join(tempfile.mkdtemp(), "last-kill")
            self.assertIsNone(tui.since_last_kill())
            tui.mark_kill()
            self.assertLess(tui.since_last_kill(), 5)
        finally:
            tui.STATE = saved


if __name__ == "__main__":
    unittest.main()
