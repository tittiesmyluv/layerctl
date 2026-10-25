#!/usr/bin/env python3
"""venice/core - transport + env + batched metrics. non-root first, portable."""
import os, shutil, subprocess, sys, time

HOME = os.path.expanduser("~")
RISH = os.path.join(HOME, "rish")

class _T:
    name = "?"
    def ok(self): return False
    def run(self, cmd, timeout=30):
        r = subprocess.run(self.argv(cmd), text=True,
                           stderr=subprocess.STDOUT, timeout=timeout, stdout=subprocess.PIPE,
                           stdin=subprocess.DEVNULL)
        return r.stdout

class Rish(_T):
    name = "rish(Shizuku)"
    def ok(self): return os.path.exists(RISH) and os.access(RISH, os.X_OK)
    def argv(self, c): return [RISH, "-c", c]

class Adb(_T):
    name = "adb"
    def ok(self): return shutil.which("adb") is not None
    def argv(self, c):
        a = ["adb"]
        dev = os.environ.get("ANDROID_SERIAL")
        if dev:
            a += ["-s", dev]
        return a + ["exec-out", c]
    def run(self, cmd, timeout=30):
        return super().run(cmd, timeout).replace("\r\n", "\n").replace("\r", "\n")

class Su(_T):
    name = "su(root)"
    def ok(self): return shutil.which("su") is not None
    def argv(self, c): return ["su", "-c", c]

def detect(prefer=None):
    prefer = prefer or os.environ.get("VENICE_TRANSPORT")
    order = [Rish, Adb, Su]
    if prefer == "adb": order = [Adb, Rish, Su]
    elif prefer == "su": order = [Su, Rish, Adb]
    for cls in order:
        t = cls()
        if t.ok(): return t
    return None

ENV_CMD = ("getprop ro.product.model; getprop ro.product.device; "
           "getprop ro.build.version.release; getprop ro.build.version.sdk; "
           "getprop ro.board.platform; "
           "settings get global development_settings_enabled; "
           "settings get global adb_enabled; settings get global adb_wifi_enabled; "
           "getprop init.svc.adbd; ps -A | grep -c shizuku; "
           "pm list features | grep -c euicc; getprop ro.build.version.oneui")
ENV_KEYS = ["model","device","android","sdk","platform","devmode","adb","adbwifi",
            "adbd","shizuku","euicc","oneui"]

def env(t):
    out = t.run(ENV_CMD).splitlines()
    out += [""] * (len(ENV_KEYS) - len(out))
    d = dict(zip(ENV_KEYS, [x.strip() for x in out]))
    d["root"] = "1" if t.run("command -v su || which su").strip() else "0"
    d["adb_bin"] = "1" if shutil.which("adb") else "0"
    d["rish"] = "1" if os.access(RISH, os.X_OK) else "0"
    d["transport"] = t.name
    return d

SNAP_CMD = ("cat /proc/meminfo; echo ==STAT==; head -1 /proc/stat; "
            "echo ==NET==; cat /proc/net/dev; echo ==DF==; df -k /data; "
            "echo ==LOAD==; cat /proc/loadavg; echo ==PROC==; ps -A | wc -l; "
            "echo ==BATT==; dumpsys battery; echo ==ZRAM==; cat /sys/block/zram0/mm_stat")
MARKS = ("==STAT==", "==NET==", "==DF==", "==LOAD==", "==PROC==", "==BATT==", "==ZRAM==")

def _mark(x):
    for m in MARKS:
        if m in x:
            return m
    return None

def snapshot(t):
    out = t.run(SNAP_CMD)
    sec = "==MEM=="
    s = {"mem": {}, "net": {}, "df": None, "load": "", "procs": 0,
         "batt": {}, "stat": None, "zram": None, "misc": {}, "noise": [], "ts": time.time()}
    for line in out.splitlines():
        x = line.strip()
        if not x:
            continue
        m = _mark(x)
        if m:
            sec = m
            continue
        if sec == "==MEM==":
            if ":" in x:
                k, v = x.split(":", 1)
                f = v.split()
                if f and f[0].isdigit():
                    s["mem"][k.strip()] = int(f[0])
                elif f:
                    s["misc"][k.strip()] = f[0]
            else:
                s["noise"].append(x)
        elif sec == "==STAT==":
            f = x.split()
            if f and f[0] == "cpu" and len(f) >= 6:
                v = [int(i) for i in f[1:] if i.isdigit()]
                if len(v) >= 5:
                    s["stat"] = (sum(v), v[3] + v[4])
            else:
                s["noise"].append(x)
        elif sec == "==NET==":
            if ":" in x:
                k, rest = x.split(":", 1)
                f = rest.split()
                if len(f) >= 9 and f[0].isdigit() and f[8].isdigit():
                    s["net"][k.strip()] = (int(f[0]), int(f[8]))
        elif sec == "==DF==":
            f = x.split()
            if len(f) >= 4 and f[0].startswith("/") and f[1].isdigit() and f[3].isdigit():
                s["df"] = (int(f[1]), int(f[3]))
        elif sec == "==LOAD==":
            s["load"] = x
        elif sec == "==PROC==":
            if x.isdigit():
                s["procs"] = int(x)
        elif sec == "==BATT==":
            if ":" in x:
                k, v = x.split(":", 1)
                s["batt"][k.strip()] = v.strip()
        elif sec == "==ZRAM==":
            f = x.split()
            if len(f) >= 3 and all(i.isdigit() for i in f[:3]):
                s["zram"] = (int(f[0]), int(f[1]), int(f[2]))
    return s

def rates(p, c):
    dt = max(0.001, c["ts"] - p["ts"])
    rx = tx = 0
    for i, (r, t) in c["net"].items():
        if i in p["net"]:
            pr, pt = p["net"][i]
            if r >= pr: rx += r - pr
            if t >= pt: tx += t - pt
    cpu = None
    if p.get("stat") and c.get("stat"):
        dtot = c["stat"][0] - p["stat"][0]
        didle = c["stat"][1] - p["stat"][1]
        if dtot > 0:
            cpu = 100.0 * (dtot - didle) / dtot
    return {"rx_kbps": rx / dt * 8 / 1000.0, "tx_kbps": tx / dt * 8 / 1000.0, "cpu": cpu}

def mb(kb): return kb / 1024.0

PROBES = [
    ("meminfo", "cat /proc/meminfo | wc -l"),
    ("stat",    "head -1 /proc/stat | wc -c"),
    ("netdev",  "cat /proc/net/dev | wc -l"),
    ("df",      "df -k /data | wc -l"),
    ("loadavg", "cat /proc/loadavg"),
    ("ps",      "ps -A | wc -l"),
    ("battery", "dumpsys battery | wc -l"),
    ("zram",    "cat /sys/block/zram0/mm_stat | wc -c"),
    ("which",   "which cat grep head df ps dumpsys sed"),
]

def probe_all(t):
    for name, c in PROBES:
        try:
            o = t.run(c, timeout=20).strip().replace("\n", " | ")
        except Exception as e:
            o = "EXC " + repr(e)
        print("%-9s %s" % (name, o[:80]))

if __name__ == "__main__":
    t = detect()
    if t is None:
        print("no transport"); raise SystemExit(1)
    if "--probe" in sys.argv:
        probe_all(t)
    elif "--raw" in sys.argv:
        for i, l in enumerate(t.run(SNAP_CMD).splitlines()):
            print("%3d %s" % (i, repr(l)))
    elif "--json" in sys.argv:
        import json
        print(json.dumps({"env": env(t), "snap": snapshot(t)}, default=str, indent=2))
    else:
        print(t.name)
        for k, v in env(t).items():
            print("  %-10s %s" % (k, v))
        s = snapshot(t)
        print("  mem", s["mem"])
        print("  misc", s["misc"])
        print("  noise", s["noise"][:5])
