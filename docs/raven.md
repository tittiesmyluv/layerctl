# Google Pixel 6 Pro (raven) — layerctl 実機検証記録

- 日付: 2026-10-25
- 端末: Pixel 6 Pro / Google Tensor GS101 / Android 17 (SDK 37) / build CP3A.261005.002.A1
- 状態: bootloader 解錠 (verifiedbootstate=orange, flash.locked=0) / root=Magisk / ro.debuggable=0
- 輸送層: su (VENICE_TRANSPORT=su)
- 結果: profile=raven 照合 / snapshot / diff / seed / plan / apply 全通過

## 実測した値
| 項目 | 値 |
|---|---|
| su | `su -c '<cmd>'` が uid=0 / u:r:magisk:s0 |
| `su 0 id` | 対話プロンプトに落ちて使えない（Magisk の su の癖） |
| adb root | 不可（`adbd cannot run as root in production builds`） |
| euicc サービス | `dumpsys econtroller` のみ応答。`dumpsys euicc` は Can't find service |
| /proc/swaps | root で読める（zram0 3.0GiB） |
| appops RUN_ANY_IN_BACKGROUND | Android 17 でも生存。set 後に query-op が拾う |
| pm disable-user | 検体3件すべて素直に disabled-user になった |
| usagestats | App Standby States を一括パース可（1456行） |
| deviceidle whitelist | 接頭辞は system / system-excidle / user の3種 |

## 適用の実測
- snapshot: 0:58 A:255 B1:34 B2:14 C1:20 C2:0 D:3（計384）
- plan: 97本（whitelist +30 / bucket restricted 34 / appops ignore 33）
- apply 後: whitelist 56 → 86 行（user +30）。youtube は bucket 45 / appops ignore を保持
- 45秒後も plan の残差は不変。bucket の書き戻しは観測されず
- 残差は `com.google.android.apps.photos` 2本のみ。再 apply で 0 に収束

## 端末固有の癖
- `com.android.egg` は bucket 10 (ACTIVE) から動かない。`am set-standby-bucket` を撃っても 10 のまま
- apply 直後の MemAvailable 差分は 0.0MB になりうる。手で `am kill-all` を撃つと
  MemAvailable +318MB / SwapFree +505MB 動く。metrics は健全で、故障ではない

## 触れると痛い層
- B1: `com.google.android.apps.walletnfcrel` / `com.felicanetworks.mfc|mfs|mfw.a.boot`（NFC決済）
- B1: `com.google.android.apps.pixel.nowplaying` / アクセシビリティ系 / `com.termux.api`

## 計測の2段化 実測 (2026-10-27)

`apply` を2段計測にした後、raven で実測した。生ログは
`~/work/artifacts/apply-cmd-*.txt` / `apply-kill-*.txt` / `kill-again-*.txt`。

- 前提: 差分14本（すべて `am set-standby-bucket`）。A層が制限bucketを戻す修正と
  名前規則の追加で、これまで残っていた差分が出た
- 適用後 `plan` は 0 に収束した（14 cmd -> 0）
- C2 は 0 本。raven の `protected_refuse_disable` が空のため

| 段 | MemAvailable | SwapFree | procs | load1 |
|---|---|---|---|---|
| 層コマンドのみ (14 cmd) | −40.9 MB | −84.2 MB | ±0 | +0.00 |
| 続けて am kill-all | +1211.7 MB | +655.2 MB | −92 | −0.09 |

差分0本の状態から am kill-all のみ:

| 回 | MemAvailable | procs | load1 |
|---|---|---|---|
| 1回目 | +335.7 MB | −6 | −2.14 |
| 2回目 | −268.1 MB | +7 | −4.04 |

### 結論

- 層コマンドは政策。即時解放ではない。−40.9 MB は誤差
- 制限を解除すると逆にメモリを使うことがある（SwapFree −84.2 MB）
- 即時解放は am kill-all が出す。桁が違う
- 掃除は単発で測れない。ばらつきが大きく、連続で撃つとマイナスにもなる
- 旧計測の +486 MB 等を「層変更の効果」と呼ぶのは誤り

### 未解決

- 掃除の効果は分散が大きい。`--repeat N` で複数回サンプルして中央値を出すべき
- 2回目の −268.1 MB は、殺したプロセスの再起動コスト。この再起動を抑えるには
  層コマンドで bucket/appops を締めてから撃つ順序が効くはず（未検証）
