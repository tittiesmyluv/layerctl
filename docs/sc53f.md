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
| shizuku_demoted | moe.shizuku.privileged.api が10-25分おきに bucket30 へ |

## 未検証

- C2 の4件が実際に restricted を保持しないこと（書き戻し）の直接観測。
  `c2_does_not_hold_bucket` に3件を記録済みだが、plan の残差で間接的にしか
  見えていない
- `shizuku_demoted` は QUIRKS にあるが `infer` に配線されていない
