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
