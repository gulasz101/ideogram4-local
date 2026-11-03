#!/usr/bin/env python3
"""Screen every vault asset for the two defects a script can settle.

Walks <assets>/**/*.png, runs check-grey-bars.py and check-palette-strip.py on
each, and writes a per-asset JSONL plus a per-post markdown table of failures.
The post is found through the library record's `asset:` field, so the join is
what turns a pile of filenames into a repair list.

Deliberately NOT included: check-flat-bands.py. It fires on nearly every
cel-shaded frame (a full sweep hit all 566 assets) because flat colour blocks are
the art style, so it is a prompt to crop and look, never a verdict.

Usage:
    audit-assets.py [--assets DIR] [--library DIR] [--out JSONL] [--table MD]
                    [--threads N]
"""
import argparse
import json
import os
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor

DEFAULT_VAULT = "/Users/paperclip/vault"
SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(SKILL, "scripts")
PY = "/Users/paperclip/image-studio/.venv-imgcheck/bin/python"


def run_check(script, path):
    try:
        r = subprocess.run([PY, os.path.join(SCRIPTS, script), path],
                           capture_output=True, text=True, timeout=180)
        return r.stdout + r.stderr
    except Exception as exc:  # a timeout is a row, not a crash
        return f"ERROR {exc}"


def judge(path, assets_root):
    rec = {"asset": os.path.relpath(path, assets_root)}
    grey = run_check("check-grey-bars.py", path)
    rec["grey_bars"] = "No grey bars" not in grey
    pal = run_check("check-palette-strip.py", path).lower()
    rec["palette_strip"] = "palette strip on" in pal and "no palette strip" not in pal
    rec["bad"] = rec["grey_bars"] or rec["palette_strip"]
    return rec


def load_records(library):
    """asset path (prefix-stripped) -> record info.

    The prefix strip is load-bearing: records spell the asset
    `tech_blog/assets/...`, a filesystem walk yields `YYYY-MM-DD/...`, and without
    normalising the join matches nothing and the report reads clean.
    """
    index = {}
    for root, _, files in os.walk(library):
        for fn in files:
            if not fn.endswith(".md"):
                continue
            p = os.path.join(root, fn)
            body = open(p, encoding="utf-8", errors="replace").read()
            m = re.search(r'^asset: "(.*?)"', body, re.M)
            if not m:
                continue
            asset = m.group(1)
            for prefix in ("tech_blog/assets/", "tech_blog/", "assets/"):
                if asset.startswith(prefix):
                    asset = asset[len(prefix):]
                    break
            posts = re.search(r"^posts: \[(.*)\]", body, re.M)
            sup = re.search(r"^superseded_by: (.*)$", body, re.M)
            verd = re.search(r'^verdict: "(.*?)"', body, re.M)
            index[asset] = {
                "record": os.path.relpath(p, library),
                "post": posts.group(1).strip('"') if posts else "?",
                "superseded": sup.group(1).strip() if sup else "",
                "verdict": verd.group(1) if verd else "?",
            }
    return index


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--assets", default=os.path.join(DEFAULT_VAULT, "tech_blog/assets"))
    ap.add_argument("--library", default=os.path.join(DEFAULT_VAULT, "3-resources/image-library"))
    ap.add_argument("--out", default="asset-sweep.jsonl")
    ap.add_argument("--table", default="asset-sweep-table.md")
    ap.add_argument("--threads", type=int, default=6)
    args = ap.parse_args()

    pngs = sorted(
        os.path.join(root, fn)
        for root, _, fns in os.walk(args.assets)
        for fn in fns
        if fn.lower().endswith(".png")
    )
    print(f"{len(pngs)} PNGs under {args.assets}", flush=True)

    rows, done = [], 0
    with open(args.out, "w") as fh, ThreadPoolExecutor(max_workers=args.threads) as ex:
        for rec in ex.map(lambda p: judge(p, args.assets), pngs):
            fh.write(json.dumps(rec) + "\n")
            fh.flush()
            rows.append(rec)
            done += 1
            if done % 50 == 0:
                print(f"  {done}/{len(pngs)}", flush=True)

    index = load_records(args.library)
    flagged = [r for r in rows if r["bad"]]
    by_post, unmatched = {}, []
    for r in flagged:
        info = index.get(r["asset"])
        if not info:
            unmatched.append(r["asset"])
            continue
        by_post.setdefault(info["post"], []).append({**r, **info})

    live = {p: rs for p, rs in by_post.items() if any(x["superseded"] == "null" for x in rs)}
    lines = ["| post | flagged images | why |", "| --- | --- | --- |"]
    for post, rs in sorted(live.items()):
        names = ", ".join(f"`{os.path.basename(x['asset'])}`" for x in rs if x["superseded"] == "null")
        if not names:
            continue
        why = ", ".join(sorted(
            " + ".join(w for w in ("grey bars" if x["grey_bars"] else "",
                                   "palette strip" if x["palette_strip"] else "") if w)
            for x in rs if x["superseded"] == "null"))
        lines.append(f"| `{post}` | {names} | {why} |")
    open(args.table, "w").write("\n".join(lines) + "\n")

    print(f"scanned {len(rows)}, flagged {len(flagged)}, in a post {sum(len(v) for v in by_post.values())}"
          f" across {len(by_post)} posts ({len(live)} with a live record)")
    print(f"unmatched (no library record): {len(unmatched)}")
    print(f"wrote {args.out} and {args.table}")


if __name__ == "__main__":
    main()
