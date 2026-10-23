"""generic — 照合に失敗したときの最小フォールバック。安全側に倒す"""
NAME = "generic"
DESC = "unknown device / 最小構成"
MATCH_MODEL = ()
MATCH_PLATFORM = ()

D_HARD = {"android", "com.android.systemui"}
C2_HARD = set()
L0_HARD = {"com.android.phone", "com.google.android.apps.messaging", "com.google.android.gms"}
IMPACT = {}

QUIRKS = {
    "proc_swaps_denied": True,
    "euicc_service": "euicc",
    "wallpaper_live_is_engine": False,
    "appops_query_op": True,
    "usagestats_bucket_dump": True,
    "protected_refuse_disable": [],
}
