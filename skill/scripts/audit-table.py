#!/usr/bin/env python3
"""Join an asset sweep to the library records and print a per-post repair table.

The sweep (scripts/sweep-assets.py) keys assets relative to
`vault/tech_blog/assets/`. A library record's `asset:` field is spelled
`tech_blog/assets/<date>/<file>.png` — so the join needs BOTH prefixes stripped,
and a single `tech_blog/` strip silently matches nothing (0 of 70 flagged assets
joined until it was fixed).

Usage:
    audit-table.py [--sweep FILE] [--library DIR] [--out FILE]
"""
import argparse
import json
import os
import re
from collections import defaultdict

PREFIXES = ("tech_blog/assets/", "tech_blog/", "assets/")


def load_records(library):
    """asset path (vault-relative to tech_blog/) -> {record, post, superseded, verdict}"""
    index = {}
    for root, _, files in os.walk(library):
        for fn in files:
            if not fn.endswith(".md"):
                continue
            path = os.path.join(root, fn)
            body = open(path, encoding="utf-8", errors="replace").read()
            m = re.search(r'^asset: "(.*?)"', body, re.M)
            if not m:
                continue
            asset = m.group(1)
            for pre in PREFIXES:
                if asset.startswith(pre):
                    asset = asset[len(pre):]
                    break
            posts = re.search(r"^posts: \[(.*)\]", body, re.M)
            sup = re.search(r"^superseded_by: (.*)$", body, re.M)
            verdict = re.search(r'^verdict: "(.*?)"', body, re.M)
            index[asset] = {
                "record": os.path.relpath(path, library),
                "post": posts.group(1).strip('"') if posts else "?",
                "superseded": sup.group(1).strip() if sup else "",
                "verdict": verdict.group(1) if verdict else "?",
            }
    return index


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sweep", default="~/image-studio/backlog/audit/asset-sweep.jsonl")
    ap.add_argument("--library", default="/Users/paperclip/vault/3-resources/image-library")
    ap.add_argument("--out", default="~/image-studio/backlog/audit/asset-sweep-table.md")
    args = ap.parse_args()

    rows = [json.loads(l) for l in open(os.path.expanduser(args.sweep))]
    index = load_records(args.library)
    flagged = [r for r in rows if r.get("bad")]
    print(f"scanned {len(rows)} assets, {len(flagged)} flagged")

    by_post = defaultdict(list)
    unmatched = []
    for r in flagged:
        info = index.get(r["asset"])
        if not info:
            unmatched.append(r["asset"])
            continue
        by_post[info["post"]].append({**r, **info})

    live = {p: [x for x in rs if x["superseded"] == "null"] for p, rs in by_post.items()}
    live = {p: rs for p, rs in live.items() if rs}
    print(f"joined {sum(len(v) for v in live.values())} flagged assets to {len(live)} posts; "
          f"{len(unmatched)} have no library record")

    lines = ["| post | flagged images | why |", "| --- | --- | --- |"]
    for post, rs in sorted(live.items()):
        names = ", ".join(f"`{os.path.basename(x['asset'])}`" for x in rs)
        why = ", ".join(sorted({
            "grey bars, palette strip" if x["grey_bars"] and x["palette_strip"]
            else "grey bars" if x["grey_bars"] else "palette strip" for x in rs}))
        lines.append(f"| `{post}` | {names} | {why} |")

    out = os.path.expanduser(args.out)
    with open(out, "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nwrote {out}")
    for u in unmatched[:10]:
        print("  no record:", u)


if __name__ == "__main__":
    main()
