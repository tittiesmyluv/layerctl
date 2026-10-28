"""端末非依存の名前規則。未知機でも seed が実用になるようにする。

方針:
  - 作者の実機3台 (sc53f / sh53d / raven) で実際にそう分類されていたものだけを入れる
  - 迷ったら A（触らない）に倒す
  - プロファイルは NAME_RULES を定義して上書きできる（プロファイル側が優先）
  - 正規表現は re.search で評価する

infer() は観測 (disabled / bucket / appops / whitelist) を先に見て、
どれにも当たらなかったものだけをここに落とす。
だから名前規則が観測を上書きすることはない。
"""

# (層, 正規表現) 上から順に評価。最初に当たった層を返す。
NAME_RULES = (
    # --- 0: 通知・着信・システムの生命線 ---
    ("0", r"^com\.android\.(phone|server\.telecom)$"),
    ("0", r"^com\.android\.providers\.(telephony|contacts|calendar|downloads|settings)$"),
    ("0", r"^com\.google\.android\.(gms|dialer|apps\.messaging|inputmethod\.latin)$"),
    ("0", r"(nexuslauncher|launcher3(\.\w+)?)$"),
    ("0", r"^com\.samsung\.android\.(dialer|messaging|honeyboard)$"),
    ("0", r"^com\.samsung\.android\.app\.contacts$"),
    ("0", r"^com\.sec\.android\.app\.launcher$"),

    # --- B1: 背景同期で足りる。通知が数分遅れても困らない ---
    ("B1", r"^com\.google\.android\.youtube$"),
    ("B1",
     (r"^com\.google\.android\.apps\."
     r"(docs|docs\.editors\.\w+|photos|nbu\.files|tips"
     r"|subscriptions\.red|pixel\.nowplaying)$")),

    # --- B1: 同梱の標準アプリ。無効化すると困るので絞るだけ ---
    ("B1", r"^com\.sec\.android\.app\.(camera|myfiles|clockpackage)$"),
    ("B1", r"^com\.sec\.android\.gallery3d$"),
    ("B1", r"^com\.android\.(camera2?|gallery3d|deskclock)$"),

    # --- C1: 同梱物。ほぼ誰も開かない ---
    ("C1", r"^com\.android\.sdm\.plugins\."),
    ("C1", r"^com\.android\.omadm\.service$"),
    ("C1", r"^com\.google\.android\.(videos|apps\.wellbeing)$"),
    ("C1", r"^com\.(verizon|vzw)\."),
)
