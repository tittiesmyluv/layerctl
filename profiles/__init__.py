"""device profile loader — 端末固有データをコードから追い出す"""
import importlib

from . import generic

KNOWN = ("sc53f",)


def load_profile(model="", platform=""):
    model = (model or "").strip()
    platform = (platform or "").strip()
    for name in KNOWN:
        mod = importlib.import_module("." + name, __package__)
        if model in getattr(mod, "MATCH_MODEL", ()) or platform in getattr(mod, "MATCH_PLATFORM", ()):
            return mod
    return generic


def names():
    return list(KNOWN) + ["generic"]
