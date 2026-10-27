#!/usr/bin/env python3
"""venice/layers - A/B/C/D layer switchboard (non-root, rish backend)"""
import curses, os, subprocess, sys, time

HOME = os.path.expanduser("~")
DIR = os.path.dirname(os.path.abspath(__file__))
RISH = os.path.join(HOME, "rish")
TSV = os.path.join(DIR, "layers.tsv")
OBS = os.path.join(DIR, "layers.observed.tsv")

LAYERS = ["0", "A", "B1", "B2", "C1", "C2", "D"]
TITLE = {"0": "UNTOUCHABLE", "A": "DAILY", "B1": "THROTTLED", "B2": "FREQUENT",
         "C1": "DEAD", "C2": "PINNED", "D": "GREYOUT"}
DESC = {"0": "instant / doze-protected", "A": "resident allowed",
        "B1": "background cut / notif delayed", "B2": "notif kept",
        "C1": "disabled", "C2": "protected pkg / throttled", "D": "root required"}
ACTION = {"0": "protect", "A": "none", "B1": "restrict", "B2": "frequent",
          "C1": "disable", "C2": "restrict", "D": "none"}

# 端末固有データは profiles/ に分離。下の load_profile() で注入される

_T = None

def rish(cmd, timeout=300):
    if _T is None:
        return ""
    try:
        return _T.run(cmd, timeout=timeout)
    except Exception:
        return ""

sys.path.insert(0, DIR)
import core
_T = core.detect(os.environ.get("VENICE_TRANSPORT"))
from profiles import load_profile

PROFILE = load_profile(rish("getprop ro.product.model").strip(),
                       rish("getprop ro.board.platform").strip())
D_HARD = PROFILE.D_HARD
C2_HARD = PROFILE.C2_HARD
L0_HARD = PROFILE.L0_HARD
IMPACT = PROFILE.IMPACT

# bucket 値: 10=ACTIVE 20=WORKING_SET 30=FREQUENT 40=RARE 45=RESTRICTED 50=NEVER
BUCKET_RESTRICTIVE = ("30", "40", "45", "50")
BUCKET_NEUTRAL = "working_set"


def _quirks_list(key):
    """QUIRKS を呼び出し時に読む（プロファイル差し替えに追随させるため）"""
    return set(PROFILE.QUIRKS.get(key, ()))


def risk_of(L, p):
    if L in ("D", "0", "C2"):
        return 3
    if L == "C1" and p in IMPACT:
        return 2
    return 1

def probe():
    raw = rish("pm list packages")
    pkgs = sorted({l.strip()[8:] for l in raw.splitlines() if l.startswith("package:")})

    dis = set()
    for l in rish("pm list packages -d").splitlines():
        t = l.strip()
        if t.startswith("package:"):
            dis.add(t[8:])

    wht = set()
    for l in rish("dumpsys deviceidle whitelist").splitlines():
        f = l.strip().split(",")
        if len(f) >= 2 and f[1]:
            wht.add(f[1])

    # 能力検出: 一括取得が使えなければ個別に落ちる
    ops = set()
    if PROFILE.QUIRKS.get("appops_query_op", True):
        for l in rish("cmd appops query-op RUN_ANY_IN_BACKGROUND ignore").splitlines():
            t = l.strip()
            if t:
                ops.add(t.split()[0])
    else:
        for pk in pkgs:
            if "ignore" in rish("cmd appops get %s RUN_ANY_IN_BACKGROUND" % pk):
                ops.add(pk)

    bkt, rsn = {}, {}
    if PROFILE.QUIRKS.get("usagestats_bucket_dump", True):
        for l in rish("dumpsys usagestats").splitlines():
            t = l.strip()
            if not t.startswith("package="):
                continue
            f = t.split()
            try:
                pk = f[0][8:]; b = f[2].split("=")[1]; r = f[3].split("=")[1]
            except Exception:
                continue
            bkt[pk] = b; rsn[pk] = r
    else:
        for pk in pkgs:
            b = rish("am get-standby-bucket " + pk).strip()
            if b:
                bkt[pk] = b

    return pkgs, dis, wht, bkt, ops, rsn

def infer(pkgs, dis, wht, bkt, ops, rsn=None):
    # bucket: 5=EXEMPTED 10=ACTIVE 20=WORKING_SET 30=FREQUENT 40=RARE 45=RESTRICTED 50=NEVER
    B1_B, B2_B = ("45", "40", "50"), ("30",)
    # pm disable-user を拒む個体は C2 へ回す（profiles/*.py の QUIRKS に実測記録済み）
    c2_hard = C2_HARD | _quirks_list("protected_refuse_disable")
    recs = []
    for p in pkgs:
        b = bkt.get(p, "")
        if p in D_HARD:
            L = "D"
        elif p in c2_hard:
            L = "C2"
        elif p in L0_HARD:
            L = "0"
        elif p in dis:
            L = "C1"
        elif b == "5" or p in wht:
            L = "0"
        elif b in B1_B or p in ops:
            L = "B1"
        elif b in B2_B:
            L = "B2"
        else:
            L = "A"
        recs.append([L, p, ACTION[L], risk_of(L, p), IMPACT.get(p, "")])
    return recs

def current_state():
    pkgs, dis, wht, bkt, ops, rsn = probe()
    return dis, wht, bkt, ops


def plan_lines(recs, st):
    """recs と現在状態 st=(dis,wht,bkt,ops) の差分コマンドだけを返す"""
    dis, wht, bkt, ops = st
    out = []
    for L, p, a, r, imp in recs:
        if L == "C1":
            if p not in dis:
                out.append("pm disable-user --user 0 " + p)
        elif L == "0":
            if p not in wht:
                out.append("dumpsys deviceidle whitelist +" + p)
        elif L in ("B1", "C2"):
            if p not in ops:
                out.append("cmd appops set %s RUN_ANY_IN_BACKGROUND ignore" % p)
            # restricted を書き戻される個体は bucket を主張しない（実測）
            if L == "C2" and p in _quirks_list("c2_does_not_hold_bucket"):
                pass
            elif bkt.get(p) != "45":
                out.append("am set-standby-bucket %s restricted" % p)
        elif L == "B2":
            if p in ops:
                out.append("cmd appops set %s RUN_ANY_IN_BACKGROUND allow" % p)
            if bkt.get(p) != "30":
                out.append("am set-standby-bucket %s frequent" % p)
        elif L == "A":
            if p in ops:
                out.append("cmd appops set %s RUN_ANY_IN_BACKGROUND allow" % p)
            # 制限系 bucket から中立へ戻す。未観測(None)は触らない
            if bkt.get(p) in BUCKET_RESTRICTIVE:
                out.append("am set-standby-bucket %s %s" % (p, BUCKET_NEUTRAL))
    return out


def metrics():
    o = rish("grep -E 'MemAvailable|SwapFree' /proc/meminfo; "
             "echo procs $(ps -A | wc -l); cat /proc/loadavg")
    d = {"procs": 0, "load": 0.0}
    for l in o.splitlines():
        t = l.strip()
        if t.startswith("MemAvailable"):
            d["avail_kb"] = int(t.split()[1])
        elif t.startswith("SwapFree"):
            d["swapfree_kb"] = int(t.split()[1])
        elif t.startswith("procs"):
            d["procs"] = int(t.split()[1])
        else:
            f = t.split()
            if f:
                try:
                    d["load"] = float(f[0])
                except ValueError:
                    pass
    return d


def show_delta(b, a):
    print("  MemAvailable  %+8.1f MB" % ((a.get("avail_kb", 0) - b.get("avail_kb", 0)) / 1024.0))
    print("  SwapFree      %+8.1f MB" % ((a.get("swapfree_kb", 0) - b.get("swapfree_kb", 0)) / 1024.0))
    print("  procs         %+8d" % (a.get("procs", 0) - b.get("procs", 0)))
    print("  load1         %+8.2f" % (a.get("load", 0.0) - b.get("load", 0.0)))


def save(recs, path=None):
    path = path or TSV
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        f.write("# layer\tpkg\taction\trisk\timpact\n")
        for L, p, a, r, imp in recs:
            f.write("%s\t%s\t%s\t%d\t%s\n" % (L, p, a, r, imp))

def load(path=None):
    path = path or TSV
    if not os.path.exists(path):
        return None
    with open(path) as fh:
        raw = fh.read().splitlines()
    recs = []
    for line in raw:
        if not line or line.startswith("#"):
            continue
        c = line.split("\t")
        while len(c) < 5:
            c.append("")
        recs.append([c[0], c[1], c[2], int(c[3] or 1), c[4]])
    return recs

def ui(recs, orig):
    curses.wrapper(_ui, recs, orig)

def _ui(std, recs, orig):
    curses.start_color()
    curses.use_default_colors()
    curses.curs_set(0)
    for i, c in enumerate([curses.COLOR_MAGENTA, curses.COLOR_CYAN, curses.COLOR_YELLOW,
                           curses.COLOR_GREEN, curses.COLOR_RED, curses.COLOR_RED,
                           curses.COLOR_WHITE]):
        curses.init_pair(i + 1, c, -1)
    LP = {L: i + 1 for i, L in enumerate(LAYERS)}
    cur_l, cur_p, focus = 0, 0, 0
    status = "space=cycle  a=apply  A=apply all staged  w=save  R=re-assert  tab=panel  q=quit"
    while True:
        std.erase()
        h, w = std.getmaxyx()
        grp = {L: [] for L in LAYERS}
        for i, (L, p, a, r, imp) in enumerate(recs):
            grp.setdefault(L, []).append(i)
        std.addstr(0, 1, "LAYERS", curses.A_BOLD)
        for i, L in enumerate(LAYERS):
            at = curses.color_pair(LP[L])
            if L == "D":
                at |= curses.A_DIM
            if i == cur_l:
                at |= curses.A_REVERSE if focus == 0 else curses.A_BOLD
            std.addstr(2 + i, 1, "%-3s %-12s %4d" % (L, TITLE[L], len(grp.get(L, []))), at)
        staged = sum(1 for L, p, a, r, imp in recs if orig.get(p) != L)
        std.addstr(3 + len(LAYERS), 1, "staged: %d" % staged, curses.A_BOLD)
        cl = LAYERS[cur_l]
        lst = grp.get(cl, [])
        if lst and cur_p >= len(lst):
            cur_p = len(lst) - 1
        std.addstr(0, 34, "%s  %s  (%d)" % (cl, TITLE[cl], len(lst)), curses.A_BOLD)
        std.addstr(1, 34, DESC[cl], curses.A_DIM)
        vis = max(1, h - 5)
        top = max(0, min(cur_p - vis // 2, max(0, len(lst) - vis)))
        mark = "!"
        for k in range(vis):
            if top + k >= len(lst):
                break
            idx = lst[top + k]
            L, p, a, r, imp = recs[idx]
            mark = "!!!" if r >= 3 else ("!!" if r == 2 else "!")
            at = curses.color_pair(LP[L])
            if L == "D":
                at |= curses.A_DIM
            if orig.get(p) != L:
                at |= curses.A_UNDERLINE
            if top + k == cur_p and focus == 1:
                at |= curses.A_REVERSE
            std.addstr(2 + k, 34, "%-3s %s" % (mark, p[:max(1, w - 40)]), at)
        if lst:
            L, p, a, r, imp = recs[lst[cur_p]]
            std.addstr(h - 3, 1, ("IMPACT: " + (imp or "-"))[:w - 2], curses.A_BOLD)
            std.addstr(h - 2, 1, ("pkg=%s layer=%s action=%s risk=%s" % (p, L, a, mark))[:w - 2])
        std.addstr(h - 1, 1, status[:w - 2], curses.A_DIM)
        std.refresh()
        ch = std.getch()
        if ch in (ord("q"), 27):
            save(recs)
            return
        elif ch in (curses.KEY_UP, ord("k")):
            if focus == 0:
                cur_l = (cur_l - 1) % len(LAYERS)
                cur_p = 0
            else:
                cur_p = max(0, cur_p - 1)
        elif ch in (curses.KEY_DOWN, ord("j")):
            if focus == 0:
                cur_l = (cur_l + 1) % len(LAYERS)
                cur_p = 0
            else:
                cur_p = min(max(0, len(lst) - 1), cur_p + 1)
        elif ch == 9:
            focus = 1 - focus
        elif ch == curses.KEY_LEFT:
            focus = 0
        elif ch == curses.KEY_RIGHT:
            focus = 1
        elif ch == ord(" "):
            if focus == 1 and lst:
                idx = lst[cur_p]
                nxt = LAYERS[(LAYERS.index(recs[idx][0]) + 1) % len(LAYERS)]
                recs[idx][0] = nxt
                recs[idx][2] = ACTION[nxt]
                recs[idx][3] = risk_of(nxt, recs[idx][1])
                nl = [i for i, r2 in enumerate(recs) if r2[0] == nxt]
                cur_l = LAYERS.index(nxt)
                cur_p = nl.index(idx) if idx in nl else 0
                status = "staged %s -> %s   (space=cycle  a=apply)" % (recs[idx][1], nxt)
        elif ch == ord("a"):
            if focus == 1 and lst and orig.get(recs[lst[cur_p]][1]) != recs[lst[cur_p]][0]:
                idx = lst[cur_p]
                if recs[idx][3] >= 3:
                    std.addstr(h - 1, 1, "DANGER risk>=3 - press y to confirm"[:w - 2], curses.A_REVERSE)
                    std.refresh()
                    if std.getch() not in (ord("y"), ord("Y")):
                        continue
                std.addstr(h - 1, 1, "working..."[:w - 2], curses.A_REVERSE)
                std.refresh()
                st = current_state()
                pl = plan_lines([recs[idx]], st)
                b = metrics()
                if pl:
                    rish("; ".join(pl + ["am kill-all"]))
                    time.sleep(3)
                a2 = metrics()
                orig[recs[idx][1]] = recs[idx][0]
                if pl:
                    status = "%s -> %s  %dcmd  MemAvail %+.1fMB procs %+d" % (
                        recs[idx][1], recs[idx][0], len(pl),
                        (a2.get("avail_kb", 0) - b.get("avail_kb", 0)) / 1024.0,
                        a2.get("procs", 0) - b.get("procs", 0))
                else:
                    status = "%s already at %s (no command needed)" % (recs[idx][1], recs[idx][0])
                save(recs)
        elif ch == ord("w"):
            save(recs)
            status = "saved -> " + TSV
        elif ch == ord("A"):
            staged = [r for r in recs if orig.get(r[1]) != r[0]]
            if staged:
                std.addstr(h - 1, 1, ("applying %d staged..." % len(staged))[:w - 2], curses.A_REVERSE)
                std.refresh()
                st = current_state()
                pl = plan_lines(staged, st)
                b = metrics()
                if pl:
                    rish("; ".join(pl + ["am kill-all"]))
                    time.sleep(3)
                a2 = metrics()
                for r in staged:
                    orig[r[1]] = r[0]
                save(recs)
                status = "applied %d staged  %dcmd  MemAvail %+.1fMB procs %+d" % (
                    len(staged), len(pl),
                    (a2.get("avail_kb", 0) - b.get("avail_kb", 0)) / 1024.0,
                    a2.get("procs", 0) - b.get("procs", 0))
        elif ch == ord("R"):
            std.addstr(h - 1, 1, "re-asserting..."[:w - 2], curses.A_REVERSE)
            std.refresh()
            st = current_state()
            pl = plan_lines(recs, st)
            b = metrics()
            if pl:
                rish("; ".join(pl + ["am kill-all"]))
            a2 = metrics()
            for L, p, a, r, imp in recs:
                orig[p] = L
            status = "re-asserted %d cmd  MemAvail %+.1fMB" % (
                len(pl), (a2.get("avail_kb", 0) - b.get("avail_kb", 0)) / 1024.0)
            save(recs)

def main():
    if "--help" in sys.argv or "-h" in sys.argv:
        print("usage: tui.py [--profile|--snapshot|--seed|--diff|--plan|--apply|--reapply]")
        return
    if "--profile" in sys.argv:
        from profiles import names
        print("active profile : %s" % PROFILE.NAME)
        print("desc           : %s" % PROFILE.DESC)
        print("available      : %s" % ", ".join(names()))
        print("quirks:")
        for k, v in sorted(PROFILE.QUIRKS.items()):
            print("  %-28s %s" % (k, v))
        return
    if "--snapshot" in sys.argv or "--seed" in sys.argv:
        pkgs, dis, wht, bkt, ops, rsn = probe()
        recs = infer(pkgs, dis, wht, bkt, ops, rsn)
        if "--seed" in sys.argv:
            save(recs, TSV)
            print("seed -> " + TSV)
            return
        save(recs, OBS)
        seeded = False
        if not os.path.exists(TSV):
            save(recs, TSV)
            seeded = True
        print("observed -> " + OBS + ("   (seeded " + TSV + ")" if seeded else ""))
        n = {L: 0 for L in LAYERS}
        for L, p, a, r, imp in recs:
            n[L] += 1
        for L in LAYERS:
            print("  %-3s %-12s %4d" % (L, TITLE[L], n[L]))
        return
    if "--diff" in sys.argv:
        recs = load()
        if recs is None:
            print("no " + TSV); return
        pkgs, dis, wht, bkt, ops, rsn = probe()
        now = {r[1]: r[0] for r in infer(pkgs, dis, wht, bkt, ops, rsn)}
        will = {r[1]: r[0] for r in recs}
        ch = [(p, will.get(p, "-"), now.get(p, "-"))
              for p in sorted(set(will) | set(now)) if will.get(p) != now.get(p)]
        print("diff: %d" % len(ch))
        for p, a, b in ch:
            print("  %-3s -> %-3s  %s" % (a, b, p))
        return
    if "--plan" in sys.argv or "--reapply" in sys.argv or "--apply" in sys.argv:
        recs = load()
        if recs is None:
            print("no " + TSV)
            return
        import collections
        pkgs, dis, wht, bkt, ops, rsn = probe()
        lines = plan_lines(recs, (dis, wht, bkt, ops))
        print("planned: %d commands (recs=%d)" % (len(lines), len(recs)))
        c = collections.Counter(x.split()[0] for x in lines)
        for k, v in c.most_common():
            print("  %-10s %d" % (k, v))
        open(os.path.join(DIR, "plan.txt"), "w").write("\n".join(lines) + "\n")
        print("plan -> " + os.path.join(DIR, "plan.txt"))
        if "--plan" in sys.argv:
            return
        b = metrics()
        if lines:
            rish("; ".join(lines + ["am kill-all"]))
        print("applied %d commands" % len(lines))
        time.sleep(8)
        print("--- delta after 8s (MemAvailable + = freed) ---")
        show_delta(b, metrics())
        return
    recs = load()
    if recs is None:
        print("run: python3 %s --snapshot" % os.path.basename(__file__))
        return
    orig = {p: L for L, p, a, r, imp in recs}
    ui(recs, orig)

if __name__ == "__main__":
    main()
