#!/usr/bin/env python3
"""venice/stat - live dashboard. rish/adb/su."""
import curses, os, sys
sys.path.insert(0, os.path.expanduser("~/venice"))
import core

SPARK = "▁▂▃▄▅▆▇█"

def put(std, y, x, s, at=0):
    try:
        h, w = std.getmaxyx()
        if y < 0 or y >= h or x >= w:
            return
        std.addstr(y, x, s[:max(0, w - x - 1)], at)
    except curses.error:
        pass

def spark(v, w):
    if not v or w < 2:
        return ""
    v = v[-w:]
    lo, hi = min(v), max(v)
    if hi == lo:
        hi = lo + 1
    return "".join(SPARK[min(7, int((x - lo) / (hi - lo) * 7.99))] for x in v)

def bar(f, w):
    n = int(max(0.0, min(1.0, f)) * w)
    return "█" * n + "░" * (w - n)

def tone(f):
    return 3 if f < 0.7 else (4 if f < 0.88 else 5)

def loop(std, t, iv):
    curses.start_color(); curses.use_default_colors(); curses.curs_set(0)
    for i, c in enumerate([curses.COLOR_MAGENTA, curses.COLOR_CYAN, curses.COLOR_GREEN,
                           curses.COLOR_YELLOW, curses.COLOR_RED, curses.COLOR_WHITE], 1):
        curses.init_pair(i, c, -1)
    prev = core.snapshot(t)
    env = core.env(t)
    hist = {"rx": [], "tx": [], "cpu": [], "av": []}
    std.timeout(int(iv * 1000))
    while True:
        cur = core.snapshot(t)
        r = core.rates(prev, cur)
        prev = cur
        std.erase()
        h, w = std.getmaxyx()
        y = 0
        put(std, y, 1, "DEVICE %s / %s  android %s sdk %s  via %s"
            % (env["model"], env["platform"], env["android"], env["sdk"], env["transport"]),
            curses.A_BOLD)
        y += 1
        flags = [("devmode", env["devmode"] == "1"), ("usb-debug", env["adb"] == "1"),
                 ("wifi-debug", env["adbwifi"] == "1"), ("adbd", env["adbd"] == "running"),
                 ("shizuku", env["shizuku"].isdigit() and int(env["shizuku"]) > 0),
                 ("rish", env["rish"] == "1"), ("adb-bin", env["adb_bin"] == "1"),
                 ("root", env["root"] == "1"),
                 ("esim", env["euicc"].isdigit() and int(env["euicc"]) > 0)]
        x = 1
        for name, on in flags:
            if x + len(name) + 4 > w - 1:
                x = 1; y += 1
            put(std, y, x, "[%s]" % name, curses.color_pair(3 if on else 4))
            x += len(name) + 4
        y += 2
        mt = cur["mem"].get("MemTotal", 1) or 1
        av = cur["mem"].get("MemAvailable", 0)
        st = cur["mem"].get("SwapTotal", 0)
        sf = cur["mem"].get("SwapFree", 0)
        used = max(0, st - sf)
        gw = max(8, min(40, w - 30))
        put(std, y, 1, "MemAvailable", curses.A_BOLD)
        put(std, y, 16, "%6d MB  %s" % (core.mb(av), bar(1 - av / mt, gw)),
            curses.color_pair(tone(1 - av / mt)))
        put(std, y + 1, 1, "Swap used", curses.A_BOLD)
        put(std, y + 1, 16, "%6d MB  %s" % (core.mb(used), bar(used / st if st else 0, gw)),
            curses.color_pair(tone(used / st if st else 0)))
        if cur["df"]:
            tot, free = cur["df"]
            put(std, y + 2, 1, "/data free", curses.A_BOLD)
            put(std, y + 2, 16, "%6d MB  %s" % (core.mb(free), bar(1 - free / tot, gw)),
                curses.color_pair(tone(1 - free / tot)))
        cpu = r["cpu"] or 0
        put(std, y + 3, 1, "CPU", curses.A_BOLD)
        put(std, y + 3, 16, "%5.1f %%  %s" % (cpu, bar(cpu / 100.0, gw)),
            curses.color_pair(tone(cpu / 100.0)))
        put(std, y + 4, 1, "RX / TX", curses.A_BOLD)
        put(std, y + 4, 16, "%8.1f / %-8.1f kbps" % (r["rx_kbps"], r["tx_kbps"]),
            curses.color_pair(2))
        put(std, y + 5, 1, "procs %d   load %s" % (cur["procs"], cur["load"][:20]))
        if cur.get("zram"):
            o, c, m = cur["zram"]
            put(std, y + 6, 1, "zram stored %dMB -> %dMB  ratio %.2f:1  RAM cost %dMB"
                % (o / 1048576, c / 1048576, (o / c if c else 0), m / 1048576))
        y += 8
        bw = max(8, min(80, w - 14))
        hist["rx"].append(r["rx_kbps"]); hist["tx"].append(r["tx_kbps"])
        hist["cpu"].append(cpu); hist["av"].append(core.mb(av))
        for k in hist:
            hist[k] = hist[k][-160:]
        if y < h - 4:
            put(std, y, 1, "rx   " + spark(hist["rx"], bw), curses.color_pair(2))
            put(std, y + 1, 1, "tx   " + spark(hist["tx"], bw), curses.color_pair(6))
            put(std, y + 2, 1, "cpu  " + spark(hist["cpu"], bw), curses.color_pair(4))
            put(std, y + 3, 1, "avail" + spark(hist["av"], bw), curses.color_pair(3))
        put(std, h - 1, 1, "q=quit  +/-=interval(%ds)  r=reset" % int(iv), curses.A_DIM)
        std.refresh()
        ch = std.getch()
        if ch in (ord("q"), 27):
            return
        elif ch == ord("r"):
            for k in hist:
                hist[k] = []
        elif ch in (ord("+"), ord("=")):
            iv = min(10.0, iv + 1); std.timeout(int(iv * 1000))
        elif ch == ord("-"):
            iv = max(1.0, iv - 1); std.timeout(int(iv * 1000))

def main():
    t = core.detect()
    if t is None:
        print("no transport"); return
    curses.wrapper(loop, t, 3.0)

if __name__ == "__main__":
    main()
