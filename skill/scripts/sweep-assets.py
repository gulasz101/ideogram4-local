#!/usr/bin/env python3
"""Sweep every vault asset for the defects a script can settle, one JSONL line each.

Run this before building a review card from an existing draft: it answers the
two questions no judgement is needed for — grey bars and a palette strip at an
edge — over the whole library at once, so the repair work starts from a ranked
list instead of from the card the owner happens to open.

It deliberately does NOT run check-flat-bands.py as a verdict: that script fires
on every cel-shaded frame, including approved ones. Flat bands are a prompt to
look at a crop, never a finding (engine-pitfall #66).

Usage:
    sweep-assets.py [--root DIR] [--out FILE] [--workers N]

Then join the results to posts with scripts/audit-table.py.
"""
import argparse
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

DEFAULT_ROOT = "/Users/paperclip/vault/tech_blog/assets"
SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(SKILL, "scripts")
# The check venv: the system python3 has no Pillow/numpy and the edge scripts exit 2.
CHECK_PY = "/Users/paperclip/image-studio/.venv-imgcheck/bin/python"


def run(script, path):
    try:
        r = subprocess.run([CHECK_PY, os.path.join(SCRIPTS, script), path],
                           capture_output=True, text=True, timeout=120)
        return r.stdout + r.stderr
    except Exception as exc:                      # a timeout must not kill the sweep
        return f"ERROR {exc}"


def judge(root, path):
    rel = os.path.relpath(path, root)
    out = {"asset": rel}
    grey = run("check-grey-bars.py", path)
    out["grey_bars"] = "No grey bars" not in grey
    strip = run("check-palette-strip.py", path).lower()
    out["palette_strip"] = ("no palette strip" not in strip) and ("palette strip" in strip)
    out["bad"] = out["grey_bars"] or out["palette_strip"]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=DEFAULT_ROOT)
    ap.add_argument("--out", default="~/image-studio/backlog/audit/asset-sweep.jsonl")
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()

    out = os.path.expanduser(args.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)

    files = []
    for dirpath, _, names in os.walk(args.root):
        files.extend(os.path.join(dirpath, n) for n in names if n.lower().endswith(".png"))
    files.sort()
    print(f"{len(files)} PNGs under {args.root}", flush=True)

    done = flagged = 0
    with open(out, "w") as fh, ThreadPoolExecutor(max_workers=args.workers) as ex:
        for rec in ex.map(lambda p: judge(args.root, p), files):
            fh.write(json.dumps(rec) + "\n")
            fh.flush()
            done += 1
            flagged += 1 if rec["bad"] else 0
            if done % 50 == 0:
                print(f"  {done}/{len(files)} scanned, {flagged} flagged", flush=True)

    print(f"done: {len(files)} scanned, {flagged} flagged -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
