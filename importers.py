"""外部の debloat リストを取り込む。パースだけを担い、層への写像は tui 側。

対応形式（中身で自動判定）:
  - UAD JSON  : universal-android-debloater-next-generation の uad_lists.json
  - 簡易 TSV  : 'pkg<TAB>verdict'。verdict は recommended/advanced/expert/unsafe
  - プレーン  : 1行1パッケージ。'#' から行末までコメント

外部ツールの語彙をそのまま持ち込まず、'verdict' という1つの語に正規化する。
"""
import json
import re

PKG = re.compile(r"^\w+(\.\w+)+$")


def _clean(line):
    return line.split("#", 1)[0].strip()


def parse_plain(text):
    out = {}
    for line in text.splitlines():
        line = _clean(line)
        if not line:
            continue
        pkg = line.split()[0]
        if PKG.match(pkg):
            out[pkg] = ""
    return out


def parse_tsv(text):
    out = {}
    for line in text.splitlines():
        line = _clean(line)
        if not line:
            continue
        c = line.split("\t")
        pkg = c[0].strip()
        if not PKG.match(pkg):
            continue
        out[pkg] = (c[1].strip().lower() if len(c) > 1 else "")
    return out


def parse_uad_json(text):
    d = json.loads(text)
    out = {}
    for pkg, v in d.items():
        if not isinstance(v, dict) or not PKG.match(pkg):
            continue
        out[pkg] = str(v.get("removal", "")).strip().lower()
    return out


def load(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    if path.endswith(".json") or text.lstrip()[:1] == "{":
        return parse_uad_json(text)
    if "\t" in text:
        return parse_tsv(text)
    return parse_plain(text)
