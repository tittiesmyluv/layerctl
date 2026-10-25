"""sh53d — SHARP AQUOS wish3 (SH-53D)。実測で確定。非root。"""
NAME = "sh53d"
DESC = "SHARP AQUOS wish3 / SH-53D / mt6833 / Android 15 / RAM 3.57GiB / 非root"
MATCH_MODEL = ("SH-53D", "AQUOS wish3")
MATCH_PLATFORM = ("mt6833",)

D_HARD = {"android", "com.android.systemui"}
C2_HARD = set()
L0_HARD = {"com.android.phone", "com.google.android.apps.messaging", "com.google.android.gms"}
IMPACT = {"jp.co.sharp.android.launcher3.simple": "launcher"}

QUIRKS = {
    "proc_swaps_denied": True,          # 実測: cat /proc/swaps -> Permission denied
    "euicc_service": "euicc",           # 実測: dumpsys euicc も econtroller も在り
    "wallpaper_live_is_engine": False,  # 未検証
    "appops_query_op": True,            # 実測: cmd appops query-op が応答する
    "usagestats_bucket_dump": True,     # 実測: App Standby States を一括パース可能
    "protected_refuse_disable": [],     # 未検証
}
