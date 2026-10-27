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

## 掃除の分散サンプル (2026-10-27)

`--repeat 7` を実装して収束後に撃った。生ログ `~/work/artifacts/kill-sample-*.txt`。

- 前提: 差分0本（収束済み）
- 層コマンドのみ: −1.7 MB
- am kill-all x7: +77.4 / +6.9 / −2.7 / +14.3 / −5.3 / +1.6 / +1.2
- 中央値 +1.6 MB / 最小 −5.3 / 最大 +77.4

### 結論

- kill-all の効果は「前回からどれだけ溜まったか」の関数。定数ではない
- 長時間稼働後の初回 +1211.7 MB と、収束後の中央値 +1.6 MB は同じ操作
- 連続で撃つと減衰し、マイナスにもなる（殺したプロセスの再起動）
- 層コマンドは3回の実測すべてで −40.9 / −3.2 / −1.7 MB。即時解放はしない

### 未解決

- 「蓄積量」を定量して一緒に出すべき。procs の絶対数か、前回 kill からの経過
- `--wait` を入れて、蓄積させてから測る手順を自動化できるか

## 蓄積量の前提を出して2回測った (2026-10-27)

`baseline_line` を入れた後、収束済みの状態で2回測った。

| 回 | 前提 | 層コマンド | kill-all 中央値 | 最小/最大 |
|---|---|---|---|---|
| 1 | MemAvailable 8312/12288 MB (68%) / procs 704 / 前回から 0分21秒 | +3.0 MB | +4.1 MB | −4.0 / +89.8 |
| 2 | MemAvailable 8377/12288 MB (68%) / procs 699 / 前回から 0分09秒 | −2.7 MB | +4.2 MB | +0.6 / +11.8 |

### 結論

- RAM 12GB で空き 68%、procs 700 前後。**蓄積がほぼ無いので解放もほぼ無い**
- 同じ端末・同じ操作で、長時間稼働後の初回は +1211.7 MB、収束後は中央値 +4 MB。
  差は操作ではなく**前提**で説明できる
- 各回の1発目が最大（+89.8）。以降は減衰する。掃除は溜まっていたぶんだけ出る
- 層コマンドは両回ともほぼ 0（+3.0 / −2.7 MB）

### 未解決

- 12GB 端末では「掃除の効果」が小さく出る。4GB の SC-53F では +82〜486 MB
  出ていた。**RAM 容量と空き率で期待値を変える**べきか、単に前提として出すだけか
- `load_hint` の閾値(65%/40%)は経験則。実測が増えたら見直す

## SH-53D (wish3) での実測 — 層コマンドの中身依存 (2026-10-27)

誤って SH-53D に SC-53F の意志を入れて測った。結果的に3つの知見が出た。
生ログ `~/work/artifacts/sc53f-apply-*.txt`（ファイル名は sc53f だが中身は wish3）。

- 前提: MemAvailable 1042/3664 MB (28%) / procs 1257 / 前回から 6分24秒
- 差分333本（pm 167 / dumpsys 101 / am 35 / cmd 30）
- 層コマンドのみ: **+70.4 MB / SwapFree +316.3 MB / procs +16**
- am kill-all x5: +502.3 / +162.4 / +34.5 / −337.2 / +31.8 → 中央値 +34.5

### 知見

1. **層コマンドの効果は中身に依存する。** `pm disable-user` は即時解放する
   （167本で +70.4 MB / swap +316.3 MB）。`am set-standby-bucket` は政策のみ。
   raven の14本が ≈0 だったのは bucket だけだったから
2. 掃除の分散は 4GB でも同じ。最小 −337.2 / 最大 +502.3
3. **意志は端末固有。** 他機種の意志を使うと未インストール分が永久に差分に残る。
   333本適用しても 245本残った。`plan` を installed で絞る修正を入れた

### 未検証

- SC-53F 実機での C2 確認（`protected_refuse_disable` が4件あるので C2 が埋まるはず）
- wish3 の `protected_refuse_disable` は空なので C2=0 は正常だった
