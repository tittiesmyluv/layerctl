"""raven — Google Pixel 6 Pro (Tensor GS101 / Android 17 / root=Magisk)。

ro.product.model="Pixel 6 Pro", ro.board.platform="gs101" で照合。
QUIRKS は実測値のみ。未検証は「未検証」と明記する。"""
NAME = "raven"
DESC = "Google Pixel 6 Pro / gs101 / Android 17 (SDK 37) / root(Magisk) / CP3A.261005.002.A1"
MATCH_MODEL = ("Pixel 6 Pro",)
MATCH_PLATFORM = ("gs101",)

D_HARD = {"android", "com.android.systemui", "system", "com.ai.venice"}

C2_HARD = set()          # 未検証。DeviceAdmin 実測後に詰める

L0_HARD = {
    "com.android.phone",
    "com.google.android.apps.messaging",
    "com.google.android.gms",
    "com.google.android.dialer",
    "com.google.android.apps.nexuslauncher",
    "com.google.android.inputmethod.latin",
    "com.google.android.apps.wallpaper",
}

IMPACT = {
    "com.android.systemui": "ステータスバー / 通知 / 壁紙描画",
    "com.android.vending": "Playストア",
    "com.google.android.gms": "FCM / 認証 / 位置。触るな",
    "com.google.android.apps.messaging": "SMSの受け皿。認証コードが届く",
    "com.google.android.dialer": "電話。着信",
    "com.google.android.apps.nexuslauncher": "Pixel Launcher。ホーム",
    "com.google.android.inputmethod.latin": "Gboard。既定IME",
    "com.google.android.apps.wallpaper": "壁紙ピッカー",
    "com.google.android.apps.turbo": "Adaptive Battery。bucket を書き戻す",
    "com.google.android.gm": "Gmail",
    "com.google.android.googlequicksearchbox": "Googleアプリ / 検索",
    "com.google.android.apps.photos": "Googleフォト",
    "com.google.android.youtube": "YouTube",
    "com.google.android.apps.subscriptions.red": "Google One",
}

QUIRKS = {
    "proc_swaps_denied": False,          # 実測: root で cat /proc/swaps が読める (zram0)
    "euicc_service": "econtroller",      # 実測: dumpsys euicc は Can't find service
    "wallpaper_live_is_engine": False,   # 実測: 該当パッケージ無し
    "appops_query_op": True,             # 実測: set 後に query-op が拾う (Android 17 でも生存)
    "usagestats_bucket_dump": True,      # 実測: App Standby States を一括パース可能
    "protected_refuse_disable": [],      # 実測: egg/turbo/wallpaper は素直に disable できた
}
