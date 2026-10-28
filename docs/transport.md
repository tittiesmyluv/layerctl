# 輸送層と計測の落とし穴

実機で踏んだものだけを載せる。推測は入れない。出典は各検証記録。

## 輸送層

| # | 症状 | 回避 | 出典 |
|---|---|---|---|
| 1 | `su 0 id` が返らず対話プロンプトに落ちる | `su -c '<cmd>'` を使う。`su 0` は使わない | raven.md |
| 2 | `adb root` が `cannot run as root in production builds` で失敗 | root は `su` 経路に任せる。adb は非root のまま使う | raven.md |
| 3 | `adb exec-out` の出力に `\r` が混じり解析が壊れる | 受信後に `\r\n`→`\n`、`\r`→空 に正規化する | core.py `Adb.run` |
| 4 | rish が Shizuku のログを stdout に混ぜる（`stderr=STDOUT` で融合） | 行単位で信用せず、`==STAT==` 等のマーカーで区切る | core.py `_T.run` |
| 5 | `dumpsys euicc` が `Can't find service` | `dumpsys econtroller` を使う（QUIRKS `euicc_service`） | raven.md / sc53f.md |
| 6 | `/proc/swaps` が非root で Permission denied | `dumpsys meminfo` で代用（QUIRKS `proc_swaps_denied`） | sc53f.md |
| 7 | 端末側 `su` が PATH に無く検出できない | `command -v su \|\| which su` で判定し、無ければ root=0 | core.py `env` |
| 8 | 複数端末接続時に別の端末へ飛ぶ | `ANDROID_SERIAL` を必ず渡す | core.py `Adb.argv` |
| 9 | Termux 同居時に PC 側の `su` を誤選択する | `VENICE_SU_LOCAL=1` で端末側 su を強制 | core.py `Su._via_adb` |
| 10 | `pm disable-user` が一部で拒否される | 拒否個体は QUIRKS `protected_refuse_disable` に入れて C2 に落とす | sc53f.md |

## 計測

| # | 罠 | 正しい読み方 | 出典 |
|---|---|---|---|
| 1 | apply 直後の差分 0.0MB を「無効」と判断する | 差分 0 は無効の証拠にならない。手で `am kill-all` を撃てば +318MB 動く | raven.md |
| 2 | 層コマンドを「解放」と読む | 層コマンドは政策。`am set-standby-bucket` は即時解放しない（−40.9MB は誤差） | raven.md |
| 3 | 3台を同じ土俵で比べる | 層コマンドの効き目は中身依存。`pm disable-user` は解放する（+70.4MB / swap +316.3MB）、bucket はしない | raven.md / sc53f.md |
| 4 | kill の効果を定数とみなす | 効果は「前回からどれだけ溜まったか」の関数。収束後は中央値 +1.6〜4MB | raven.md |
| 5 | 連続で kill を撃つ | 減衰し、マイナスにもなる（殺したプロセスの再起動コスト）。`--repeat` の中央値で見る | raven.md |
| 6 | 他機種の意志を当てて測る | 意志は端末固有。未インストール分が永久に差分へ残る。`plan` は `installed` で絞る | raven.md |
| 7 | 4GB 端末と 12GB 端末で同じ期待値を持つ | 解放量は空き率と蓄積量で決まる。前提（空き率・procs・前回からの経過）を毎回出す | raven.md |

## 運用

- 普段使い端末では `apply` の前に必ず `plan` を見る
- 端末が起動しない段（A202ZT の Preloader 等）は layerctl の対象外。切り分けは mtkclient 側で行う（a202zt.md）
