"""device profile loader — 端末固有データをコードから追い出す"""
import importlib

from . import generic

KNOWN = ("sc53f", "sh53d", "raven")


def load_profile(model="", platform=""):
    model = (model or "").strip()
    platform = (platform or "").strip()
    for name in KNOWN:
        mod = importlib.import_module("." + name, __package__)
        mm = getattr(mod, "MATCH_MODEL", ())
        mp = getattr(mod, "MATCH_PLATFORM", ())
        if model in mm or platform in mp:
            return mod
    return generic


def names():
    return [*KNOWN, "generic"]
