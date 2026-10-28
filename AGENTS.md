# layerctl

## 応答
- 常に日本語。コード・コマンド・識別子・パスは原文のまま。
- 結論を先に。冗長な前置きを書かない。

## 前提
- 実機は adb 経由。Pixel 6 Pro (raven) / AQUOS wish3 (SH-53D) / Galaxy A25 (SC-53F)。
- SC-53F は普段使い。apply の前に必ず plan を見る。
- 意志は端末固有。layers.tsv は端末ごとに分ける。
- テストは先に赤を出してから直す。実行は `python3 -m unittest discover -s tests -v`。
- Python は /opt/local/Library/Frameworks/Python.framework/Versions/3.14/bin/python3.14。
