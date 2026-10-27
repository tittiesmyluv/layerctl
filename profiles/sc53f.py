"""profile: SC-53F — docomo Galaxy A25 5G (Dimensity 6100+ / Android 16 / 4GB / 非root)

ro.product.model = SC-53F, ro.board.platform = mt6835 で照合される。
このファイルだけ書き換えれば他端末へ移植できる。"""
NAME = "sc53f"
DESC = "docomo SC-53F / Galaxy A25 5G / mt6835 / Android 16 / RAM 3.48GiB / 非root（rish/adb どちらでも）"
MATCH_MODEL = ("SC-53F",)
MATCH_PLATFORM = ("mt6835",)

D_HARD = {'system', 'com.ai.venice', 'android', 'com.android.systemui'}

C2_HARD = {'com.samsung.android.fmm',
 'com.samsung.android.kgclient',
 'com.samsung.android.themestore',
 'com.sec.enterprise.knox.cloudmdm.smdms'}

L0_HARD = {'com.android.phone',
 'com.google.android.apps.messaging',
 'com.google.android.gms',
 'jp.co.rakuten.mobile.rcs',
 'jp.naver.line.android'}

IMPACT = {'com.ai.venice': 'このアプリ',
 'com.android.stk': 'SIM Toolkit。docomo のSTKメニューが消える',
 'com.android.systemui': 'ステータスバー / 通知 / 壁紙描画',
 'com.android.vending': 'Playストア',
 'com.google.android.apps.messaging': 'SMSの受け皿。認証コードが届く',
 'com.google.android.gm': 'Gmail',
 'com.google.android.gms': 'FCM / 認証 / 位置。触るな',
 'com.google.android.googlequicksearchbox': 'Googleアプリ / 検索',
 'com.google.android.inputmethod.latin': 'Gboard。現在の既定IME',
 'com.hiya.star': '迷惑電話の識別が止まる',
 'com.instagram.android': 'Instagram。B1で通知が遅延する',
 'com.samsung.android.accessibility.talkback': 'TalkBack 停止',
 'com.samsung.android.app.dressroom': '壁紙とスタイル',
 'com.samsung.android.app.telephonyui': 'SIMマネージャ / APN編集UI',
 'com.samsung.android.app.telephonyui.esimclient': 'eSIM のDL/有効化',
 'com.samsung.android.fmm': 'Find My Mobile / 遠隔初期化。DeviceAdminで無効化不可',
 'com.samsung.android.incallui': '通話中画面（VoLTE）',
 'com.samsung.android.kgclient': 'KGクライアント。保護パッケージ',
 'com.samsung.android.lool': 'デバイスケア本体',
 'com.samsung.android.mapsagent': '連絡先/カレンダーの『地図』導線が消える',
 'com.samsung.android.samsungpass': 'Samsung Pass（パスワード生体認証）',
 'com.samsung.android.samsungpassautofill': 'Samsung Pass 自動入力',
 'com.samsung.android.simagent': 'SIM検出・状態通知',
 'com.samsung.android.sm.devicesecurity': 'McAfee モバイルセキュリティ停止',
 'com.samsung.android.themestore': 'Galaxy Themes。保護パッケージ',
 'com.samsung.android.wallpaper.live': 'レイヤード壁紙エンジン。殺すと壁紙が適用不能',
 'com.samsung.euicc': 'eSIM のLPA本体',
 'com.samsung.klmsagent': 'Knox ライセンス管理。Secure Folder が使う',
 'com.samsung.knox.securefolder': 'Secure Folder 本体',
 'com.sec.android.app.soundalive': 'SoundAlive/イコライザ設定が消える',
 'com.sec.android.sdhms': 'デバイスケアのバッテリー/温度統計',
 'com.sec.enterprise.knox.cloudmdm.smdms': 'Knox MDM。保護パッケージ',
 'com.whatsapp': 'WhatsApp',
 'jp.co.rakuten.mobile.rcs': 'Rakuten Link。着信。層0必須',
 'jp.naver.line.android': 'LINE。通知が生命線'}

QUIRKS = {
    "proc_swaps_denied": True,            # /proc/swaps は Permission denied。dumpsys meminfo で代用
    "euicc_service": "econtroller",       # dumpsys euicc は Can't find service。正は econtroller
    "wallpaper_live_is_engine": True,     # com.samsung.android.wallpaper.live はレイヤード壁紙エンジン。殺すと壁紙が壊れる
    "appops_query_op": True,              # cmd appops query-op が一括で返す
    "usagestats_bucket_dump": True,       # dumpsys usagestats に App Standby States がある
    "protected_refuse_disable": [         # pm disable-user を拒む。C2 へ回す
        "com.samsung.android.themestore",
        "com.samsung.android.kgclient",
        "com.samsung.android.fmm",
        "com.sec.enterprise.knox.cloudmdm.smdms",
    ],
    "c2_does_not_hold_bucket": [          # restricted を書き戻される実測済みの3本
        "com.samsung.android.fmm",
        "com.samsung.android.kgclient",
        "com.sec.enterprise.knox.cloudmdm.smdms",
    ],
    # 実測: 約10-25分おきに bucket30 へ降格される。whitelist に入れて状態を固定する
    "l0_force": ["moe.shizuku.privileged.api"],
    # 実測: restricted にしても必ず書き戻される。bucket を主張しない
    "no_bucket_hold": [
        "com.google.android.apps.tasks",
        "com.microsoft.office.outlook",
    ],
}
