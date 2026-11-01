# docomo SC-53F (Galaxy A25 5G) — layerctl 実機検証記録

- 日付: 2026-10-27
- 端末: docomo SC-53F / Galaxy A25 5G / MediaTek MT6835 / Android 16 / RAM 3.48GiB / 非root
- 輸送層: adb
- 目的: `QUIRKS.protected_refuse_disable` の配線確認

## 結果: C2 が 4 本になった

これまで `C2_HARD` は全プロファイルで空だったため、C2層は TUI で手動巡回
しないと到達できなかった。`protected_refuse_disable` を `infer` に配線した
ことで、保護パッケージが自動で C2 に落ちるようになった。**その実機証明。**

snapshot: 0:127 A:174 B1:31 B2:1 C1:187 **C2:4** D:3（計525）

C2 に落ちた4件:
- `com.samsung.android.themestore`
- `com.samsung.android.kgclient`
- `com.samsung.android.fmm`
- `com.sec.enterprise.knox.cloudmdm.smdms`

diff: 22（正しい端末と意志の組み合わせ。他機種の意志だと 533 になる）

## 実測した QUIRKS

| 項目 | 値 |
|---|---|
| protected_refuse_disable | themestore / kgclient / fmm / knox.cloudmdm |
| c2_does_not_hold_bucket | fmm / kgclient / knox.cloudmdm（themostore は除く） |
| euicc_service | econtroller |
| proc_swaps_denied | True |
| l0_force | moe.shizuku.privileged.api |

### l0_force を入れた理由

このツールの輸送層（rish）は Shizuku に依存している。Doze に殺されたら
ツール自身が動かなくなる。だから自分の生命線は whitelist（層0）に入れる。

意志 `docs/layers.sc53f.tsv` は以前 `B2`（frequent で降格を受け入れる）だったが、
`l0_force` の配線に合わせて `0` に更新した。raven の意志は元から `0`。

## 未検証

- C2 の4件が実際に restricted を保持しないこと（書き戻し）の直接観測。
  `c2_does_not_hold_bucket` に3件を記録済みだが、plan の残差で間接的にしか
  見えていない
- ~~`shizuku_demoted` は未配線~~ → `l0_force` として infer に配線し、意志も `0` に更新した

## 普段使い端末としての実測 (2026-10-27)

リアルな条件（3.5GB / 空き25% / procs 827 / 前回の掃除から4分56秒）で計測。
生ログ `~/work/artifacts/sc53f-daily-*.txt`。

- 差分24本（am 18 / cmd 4 / pm 2）
- 層コマンドのみ: MemAvailable **+36.5 MB** / SwapFree **−60.2 MB** / procs +3
- am kill-all x5: +31.7 / +10.2 / +0.7 / −6.0 / +2.4 → 中央値 +2.4
- 収束: 24本 -> 2本（残差2本は揮発層の振動として既知）

### 知見

- 3台目のデータ。cmd-only は +36.5 MB で、`pm` が2本しかないのに Pixel より
  大きい。**±40 MB の範囲で向きが安定しない**
- kill の初回が +31.7 MB と小さいのは、前回の掃除から5分しか経っていなかったため。
  **kill の大きさは操作ではなく蓄積量が決める**という仮説を支持する
- 3台すべてで、連続 kill の中央値は数MB〜数十MBに落ちる

## 無効化を拒む5本 (2026-10-28)

`pm disable-user` が成功を返すのに、`pm list packages -d` に出てこない個体が5本あった。
Knox 系と端末管理系で、システムが有効へ戻す。

- `com.knox.vpn.proxyhandler`
- `com.samsung.android.knox.er`
- `com.samsung.android.themecenter`
- `com.samsung.klmsagent`
- `com.sec.android.sdhms`

`QUIRKS.protected_refuse_disable` に記録し、意志でも C2（無効化せず縛る）に置いた。
これで `plan` の `pm` は 0 になり、永続コマンドの失敗も 0 になった。

## 適用3日後の実測 (2026-11-01)

2026-10-28 の全適用（371 cmd）から3日、普段どおり使った後の値。生データは端末の
`/proc/meminfo` と `dumpsys meminfo`。

- MemAvailable 1,166,812K / 3,643,468K (**32%**)。適用前は 25%、直後は 28%
- Free RAM 1,416,098K (39%) うち cached 1.3GB、空き 116MB
- ZRAM 627,256K physical for 2,001,100K in swap（2GB を 627MB に圧縮。異常ではない）
- 残差 130 本、**すべて揮発**。永続コマンドの失敗は **0**
- 上位 RSS: instagram 276MB / system_server 268MB / gms 163MB

### 結論

- 永続側（`pm disable-user` / `deviceidle whitelist`）は3日経っても崩れない
- 揮発側（`am set-standby-bucket` / `cmd appops set`）は毎回書き戻る。130本。
  これは仕様で、`reapply` で再主張する対象
- 空き率は適用前より上がったが、**実利用（SNS の 276MB 等）の影響の方が大きい**。
  無効化は「蓄積を鈍らせる」効果であって、使用中のメモリを減らすものではない

## 書き戻される93本を no_bucket_hold に記録 (2026-11-01)

`reapply` 後も残った93本は、すべて `am set-standby-bucket` の書き戻しだった。
内訳は `com.android.*` の AOSP 中核、`com.google.android.gsf` / `webview` /
`networkstack` 系、Samsung の `providers.*` / `nfc` / `ims` / `knox` 系。
いずれもシステムが bucket を管理しており、外部から縛っても戻される。

`QUIRKS.no_bucket_hold` に93本を記録した。bucket は主張せず、`appops ignore` だけで
絞る。これで `plan` は 0 に収束し、`reapply` が空振りしなくなった。
