# layerctl

![ci](https://github.com/tittiesmyluv/layerctl/actions/workflows/ci.yml/badge.svg)

**Non-root Android app-standby layer switchboard.** Re-map every installed
package into 7 tiers, then apply only the diff. No root required — rish(Shizuku) / adb / su(root) の3経路。No ROM.

非root Android のアプリ層スイッチボード。端末の全パッケージを7つの層に分類して
`layers.tsv` に固定し、**現在状態との差分だけ**を適用する。適用のたびに **層コマンドの効果と掃除(kill-all)の効果を分けて実測** して表示する。

輸送層は `core.detect()` が **rish(Shizuku) / adb / su** から自動選択する。
端末上の Termux でも、PC から USB 経由の adb でも、同じコマンドが等価に動く。

> **立ち位置**: 個々のコマンド（`pm disable-user` / `appops` / `set-standby-bucket`）は
> 既存ツールと重なっている。layerctl が他に無いのは **モデル** のほう — 全パッケージを
> 層に固定した「意志」を持ち、観測との差分だけを適用し、適用の効果を実測で報告する。
> 重なりの内訳は「既存ツールとの関係」節に正直に書いた。

![layerctl dashboard](assets/dashboard.svg)

## アーキテクチャ

~~~mermaid
flowchart LR
  subgraph host["ホスト: Termux / macOS / Linux"]
    TUI["tui.py<br/>層スイッチボード"]
    STAT["stat.py<br/>ライブダッシュボード"]
    CORE["core.py<br/>detect / snapshot / rates"]
    PROF["profiles/<br/>端末固有データ + QUIRKS"]
  end
  subgraph dev["Android 端末 (非root)"]
    RISH["rish (Shizuku)"]
    ADB["adbd (USB)"]
    SU["su (任意)"]
    SH["/system/bin/sh uid 2000"]
  end
  TUI --> CORE
  STAT --> CORE
  TUI --> PROF
  CORE -->|自動選択| RISH
  CORE -->|自動選択| ADB
  CORE -->|自動選択| SU
  RISH --> SH
  ADB --> SH
  SU --> SH
  SH --> API["pm / cmd appops / dumpsys / deviceidle"]
~~~

本体は端末を知らない。輸送層とプロファイルの両方が差し替え可能で、
`tui.py` と `stat.py` は `core` の口だけを見る。


## クイックスタート

~~~
git clone https://github.com/tittiesmyluv/layerctl
cd layerctl
./layers profile     # 端末が認識されるか確認（外れれば generic に落ちる）
./layers snapshot    # 現状を観測。意志は壊れない
./layers diff        # 同梱の layers.tsv とのズレを見る
./layers seed        # 自分の端末に合わせて意志を作り直す
./layers plan        # 差分コマンドを確認。実行はしない
./layers apply       # 適用。層コマンドと掃除を分けて計測し、適用後に検証する
~~~

同梱の `layers.tsv` は UAD (Universal Android Debloater) の公開リストから取り込んだ汎用の初期値だ。
端末の中核（`android` / `systemui` など）は `D`、`pm disable-user` を拒む個体は `C2` に固定してある。
作者が実機で詰めた端末別の意志は `docs/layers.sc53f.tsv` / `docs/layers.sh53d.tsv` / `docs/layers.raven.tsv` にある。
自分の端末に合わせるなら `seed` で観測に置き換えろ。`plan` は何も壊さないので、まずそれで
差分を眺めるのが安全だ。

## なぜ差分計測なのか、そしてなぜ2段なのか

非root では `dmesg` も LMKD のログも読めない。プロセスが何MB解放されたかを
知る手段が無い。**だから適用前後の差分が唯一の物証になる。**

ただし `am kill-all` を同じバッチに混ぜると、**解放が層変更のせいなのか
掃除のせいなのか区別できない。** そこで `apply` は2段で測る:

1. 層コマンドだけを適用 → 計測（層変更そのものの効果）
2. `am kill-all` → 計測（掃除の効果）

`--no-kill` で2段目を止められる。

### 実測: 3台で測った

**(a) 層コマンドのみ — 小さく、向きも一定しない**

| 端末 | RAM | 空き | procs | 中身 | MemAvailable | SwapFree |
|---|---|---|---|---|---|---|
| Pixel 6 Pro | 12.0 GB | 68% | 700 | am 14 | −40.9 / −3.2 / −1.7 MB | ±0 |
| AQUOS wish3 | 3.6 GB | 28% | 1257 | pm 167 他 | +70.4 MB | +316.3 MB |
| Galaxy A25 | 3.5 GB | 25% | 827 | am 18 / pm 2 | +36.5 MB | −60.2 MB |

`pm disable-user` が167本ある wish3 だけはっきりプラス（+70.4 MB）。
だが A25 は `pm` が2本でも +36.5 MB、Pixel は `pm` ゼロで −40.9 MB。
**±40 MB の範囲で、向きは安定しない。** 層コマンドを「解放装置」と呼ぶのは
無理がある。

**(b) am kill-all — 初回だけ大きく、あとは減衰する**

| 端末 | 前提 | 初回 | 中央値 | 最小 / 最大 |
|---|---|---|---|---|
| Pixel 6 Pro | 68% / procs 700 | **+1211.7 MB** | +1.6 MB | −5.3 / +77.4 |
| AQUOS wish3 | 28% / procs 1257 | **+502.3 MB** | +34.5 MB | −337.2 / +502.3 |
| Galaxy A25 | 25% / procs 827 | +31.7 MB | +2.4 MB | −6.0 / +31.7 |

**初回が最大で、以降は減衰する。** 殺すものが無くなれば中央値は数MBまで落ちる。
A25 の初回が小さいのは、前回の掃除から5分しか経っていなかったため。
**大きさを決めているのは操作ではなく蓄積量。**

**(c) 読み方**

- **「apply で◯MB 解放」は単独では意味を持たない。** 蓄積量を書かないと比較不能
- 旧計測の +486 MB は kill-all が稼いだぶん。層変更の寄与ではない
- `apply` は前提（空き率 / procs / 前回の掃除からの経過）を毎回表示するので、
  『なぜその数字か』が読める
- **差分ゼロは無効の証拠ではない。** 蓄積が無ければ解放も無い。それは正常
- 層コマンドの役割は**即時解放ではなく、今後の挙動を変えること**。
  `pm disable-user` だけはプロセスを止めるので即時に効く

旧計測（2段に分ける前。kill-all を混ぜている）:

| 端末 | 対象 | MemAvailable | procs |
|---|---|---|---|
| SC-53F | 全体 re-assert (5 cmd) | +82.1 MB | −2 |
| SC-53F | 仮想通貨アプリ1本を C1 へ | +276.3 MB | −10 |
| SC-53F | clone 直後の全適用 (7 cmd) | +486.7 MB | −2 |
| SH-53D (wish3) | clone 直後の全適用 (116 cmd) | +287.0 MB | −56 |

## 層モデル

| 層 | 名前 | 意味 | 適用コマンド | 持続性 |
|---|---|---|---|---|
| 0 | untouchable | 不可侵 / Doze 保護 | `dumpsys deviceidle whitelist +` | 持続 |
| A | daily | 常用 / 制限を解除 | `appops allow` + bucket を `working_set` へ戻す | 揮発 |
| B1 | throttled | 通知遅延可 | `appops ignore` + `bucket restricted` | 揮発 |
| B2 | frequent | 通知維持 | `appops allow` + `bucket frequent` | 揮発 |
| C1 | dead | 無効化 | `pm disable-user --user 0` | 持続 |
| C2 | pinned | 殺せないので縛る | `appops ignore` + `bucket restricted` | 揮発 |
| D | greyout | 手が届かない（root 必須） | — | 対象外 |

`0` と `C1` は `pm disable-user` と `deviceidle whitelist` で書かれるため
**OTA 以外で崩れない**。`A` `B1` `B2` `C2` は bucket 系で**揮発する**。
だから `--reapply` は収束演算ではなく**再主張**であり、残差は常に数本残って振動する。

`D` は root が要るため非rootでは1本もコマンドを出さない。**表示専用の層**として数え、
`plan` の対象からは外れる。

## 既存ツールとの関係

正直に書く。**個々の操作は重なっている。**

| 操作 | 既存の代表 | layerctl |
|---|---|---|
| `pm disable-user` で無効化 | Canta / Universal Android Debloater NG / App Manager / ADB AppControl | C1層 |
| standby bucket の get/set | ADB-Application-Manager / App Manager | A / B1 / B2 / C2層 |
| `RUN_ANY_IN_BACKGROUND` | AppOpsX / Brevent / Greenify / SuperFreezZ / Hail | A / B1 / C2層 |
| doze whitelist | Naptime / Battery Guru | 0層 |
| 安全度バッジ付き一覧 | Canta（UAD リスト参照） | `risk` 列 |

**重なっていないのはモデルのほう:**

| 性質 | 既存 | layerctl |
|---|---|---|
| 全パッケージを層に固定した「意志」を持つ | — | `layers.tsv` |
| 意志と観測を分離する | — | `layers.observed.tsv` |
| 差分だけを適用する | — | `plan` / `apply` |
| 適用の効果を実測で報告する | — | `apply` の2段計測 |
| 端末固有データをコードから追い出す | — | `profiles/` + `QUIRKS` |
| 輸送層を等価に抽象する | どれか1経路に固定 | rish / adb / su |

要するに **部品は既製品、組み立て方が新しい。** Greenify の代替ではなく
「Android のアプリ層を宣言的に管理する」道具として使え。

## 必要環境

- Android 11 以上
- `python3`（標準ライブラリのみ。依存なし）
- 輸送層のいずれか:
  - `rish`（Shizuku を起動し `~/rish` に配置 + `chmod +x`）— 端末上で完結
  - `adb`（USB デバッグ）— PC から。`ANDROID_SERIAL` でデバイスを固定
    - macOS: `brew install android-platform-tools` などで導入。初回は端末側で RSA 承認が要る
  - `su`（root 経由。adb があれば `adb -s <serial> exec-out "su -c '<cmd>'"`。Termux 同居で固定するなら `VENICE_SU_LOCAL=1`）
    - `su 0 id` は対話プロンプトに落ちる個体がある。`su -c` を使え
- root 不要

## 使い方

~~~
./layers profile     # 使用中のプロファイルと能力検出を表示
./layers snapshot    # 現状を走査して layers.observed.tsv に記録（layers.tsv は不変）
./layers seed        # 観測を layers.tsv（意志）へ昇格
./layers diff        # 意志と観測のズレだけ表示
./layers plan        # 差分コマンドだけ抽出。実行しない
./layers apply       # 差分を適用。層コマンドのみ / kill-all 後の2段で計測
./layers reapply     # 全件を再主張（OTA 後の復旧用）
./layers import f    # 外部の debloat リストを取り込む（UAD JSON / TSV / プレーン）
./layers             # TUI
~~~

`apply` は適用後に read-back して検証する。**揮発コマンドが書き戻されたのか、
永続コマンドが本当に効かなかったのかを分けて報告する**（揮発は異常ではない）。

~~~sh
./layers plan --json        # 差分を JSON で出す（他ツールから食える）
./layers apply --no-kill    # 掃除を撃たず、層コマンドだけ
./layers apply --repeat 7   # 掃除を7回サンプルして中央値・最小・最大を出す
./layers import f --as C1   # verdict を無視して全部 C1 として取り込む
./layers import f --dry     # プレビューのみ
~~~

`layers.tsv` は**意志**（望む層）、`layers.observed.tsv` は**観測**。`snapshot` は観測を
更新するだけで意志を壊さない。意志を観測へ合わせたい時だけ `seed` を打つ。

ライブダッシュボード:

~~~
python3 stat.py          # curses。メモリ / swap / CPU / RX / TX をスパークライン表示
python3 stat.py --dump   # 1フレームを素テキストで（CI / 検品用）
~~~

TUI の操作:

| キー | 動作 |
|---|---|
| `j` `k` | 上下移動 |
| `tab` | 層パネル / パッケージパネルの切替 |
| `space` | 層を巡回（0→A→B1→B2→C1→C2→D→0） |
| `a` | 選択中の1本を適用（risk>=3 は `y` 確認） |
| `A` | staged 全件を一括適用 |
| `w` | layers.tsv に保存 |
| `R` | 全件を再主張 |
| `q` | 保存して終了 |

## 移植

端末固有データは **`profiles/` の1ファイルだけ**に入っている。`tui.py` 本体は
端末を知らない。輸送層も `core.detect()` に閉じている。

同梱プロファイル: `sc53f` (Galaxy A25 5G) / `sh53d` (AQUOS wish3) / `generic`（未知機の受け皿）。

端末ごとの意志の実例は `docs/` に置いてある（`layers.sc53f.tsv` / `layers.sh53d.tsv`）。
**意志は端末固有**なので、他機種の意志で `apply` すると未インストール分が差分に
残る（`plan` は installed で絞るので実行は安全）。別機種ではまず `seed` を打て。

輸送層と計測の落とし穴は `docs/transport.md` に表でまとめてある。実機で踏んだものだけを載せた。触る前に一度読め。

~~~
cp profiles/generic.py profiles/pixel9.py
# NAME / MATCH_MODEL / MATCH_PLATFORM / D_HARD / C2_HARD / L0_HARD / IMPACT を書く
~~~

`ro.product.model` か `ro.board.platform` が一致すれば自動で選ばれる。外れれば
`generic` に落ちる。輸送層は `VENICE_TRANSPORT=adb` で明示固定できる。

## 実測で確定した地雷

| 症状 | 真因 | 対処 |
|---|---|---|
| 出力が全部空になる | `rish` が stdout/stderr を気まぐれに振り分ける | 常に `2>&1` |
| スクリプトが途中で止まる | `rish` が stdin を飲み尽くす | 常に `</dev/null` |
| `timeout` でハングする | 非前景プロセスグループで SIGTTOU | `timeout --foreground` |
| `adb shell` が `\r\n` を混ぜる | PTY 経由 | `adb exec-out` + `\r` 除去 |
| `dumpsys euicc` が無い | 正は `dumpsys econtroller` | QUIRKS に記録 |
| `/proc/swaps` が Permission denied | `dumpsys meminfo` の ZRAM 行で代用 | — |

## 既知の限界

- bucket 系の層は揮発する。システムが予測・時間切れ・利用検知で書き戻す
- 保護パッケージ（fmm / kgclient / knox.cloudmdm）は `restricted` を保持しない
- `EXEMPTED` は doze whitelist と同義ではない
- OTA は `appops` をリセットする。`--reapply` で復旧する
- `layers.tsv` は**意志**。`snapshot` は書き換えず、観測は `layers.observed.tsv` に隔離される
- `seed` 直後の初回 `plan` は、bucket5(EXEMPTED) を whitelist へ昇格させる一回性の
  正規化を含む。適用後は 0 に収束する（実測: 116 cmd → 0）

- `verify` の『揮発で書き戻された』は異常ではない。`am set-standby-bucket` と
  `cmd appops set` は Android が書き戻す。`pm disable-user` と
  `deviceidle whitelist` は持続するので、こちらが残ったときだけ本当の失敗
- 意志 `layers.tsv` は端末固有。他機種の意志を使うと未インストールのパッケージが
  差分に残り続ける。`plan` は installed で絞るようにした（`diff` は別枠で件数を出す）
- `A` 層は「制限を解除する層」。制限系の bucket（frequent/rare/restricted/never）を
  `working_set` へ戻す。bucket が未観測のアプリは触らない
- 2段計測の1段目は層変更そのものの効果、2段目は `am kill-all` の効果。
  合算して「この道具の効果」と呼ぶのは誤り

## License

MIT
