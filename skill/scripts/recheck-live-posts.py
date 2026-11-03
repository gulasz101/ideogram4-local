#!/usr/bin/env python3
"""Measure the image backlog by the drafts, not by the assets folder.

A sweep of every PNG in the vault answers "how many files are broken", which is
not the question a reviewer or a campaign owner has. The question is what a
reader would actually see in the posts that are still to be reviewed. This walks
those drafts instead: read queue.json, take every post whose state is not `done`,
resolve each markdown image embed against the vault, and run the two checks that
need no judgement (grey bars, palette strip) on each distinct file.

Two things this finds that a folder walk cannot:

  * an embed that resolves to a file which does not exist -- a folder walk only
    ever sees files that are there, so a dead link is invisible to it;
  * the real remaining count -- a file replaced by an approved re-render stops
    being embedded, so it drops out of the answer without anyone maintaining it.

Output: an .md table and a .jsonl beside it, under backlog/audit/.

Read the result with references/campaign-state-check.md in hand: a flagged
image on a post that is holding an open card is usually one of the slots that
card replaces, and calls for a look at the card's items before it is reported
as a defect.
"""
import json
import os
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor

VAULT = "/Users/paperclip/vault"
QUEUE = "/Users/paperclip/image-studio/backlog/queue.json"
AUDIT = "/Users/paperclip/image-studio/backlog/audit"
S = "/Users/paperclip/.hermes/profiles/matejko/skills/image-studio/scripts"
PY = "/Users/paperclip/image-studio/.venv-imgcheck/bin/python"
OUT_MD = os.path.join(AUDIT, "recheck-of-live-posts.md")
OUT_JSONL = os.path.join(AUDIT, "recheck-of-live-posts.jsonl")

EMBED = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")


def run(script, path):
    r = subprocess.run([PY, os.path.join(S, script), path],
                       capture_output=True, text=True, timeout=120)
    return r.stdout + r.stderr


def judge(path):
    g = run("check-grey-bars.py", path)
    p = run("check-palette-strip.py", path).lower()
    return {
        "path": os.path.relpath(path, VAULT),
        "grey_bars": "no grey bars" not in g.lower(),
        "palette_strip": "no palette strip" not in p,
    }


q = json.load(open(QUEUE))
live = [p for p in q["posts"] if p["state"] != "done"]
posts = {p["n"]: p for p in live}

# The queue's draft path key is `post`, not `draft`/`path`/`file`.
drafts = {n: p["post"] for n, p in posts.items() if p.get("post")}

rows, missing, seen = [], [], {}
for n in sorted(posts):
    d = drafts.get(n)
    if not d:
        continue
    full = d if os.path.isabs(d) else os.path.join(VAULT, d)
    if not os.path.exists(full):
        missing.append((n, d, "draft not found"))
        continue
    txt = open(full, encoding="utf-8").read()
    for rel in EMBED.findall(txt):
        if rel.startswith(("http:", "https:")):
            continue
        p = rel if os.path.isabs(rel) else os.path.join(VAULT, "tech_blog", rel)
        if not os.path.exists(p):
            missing.append((n, rel, "embed does not resolve"))
            continue
        seen.setdefault(p, []).append(n)

targets = sorted(seen)
print(f"{len(posts)} live posts, {len(targets)} distinct embedded images", flush=True)

results = []
with ThreadPoolExecutor(max_workers=6) as ex:
    for rec in ex.map(judge, targets):
        rec["posts"] = sorted(set(seen[os.path.join(VAULT, rec["path"])]))
        rec["bad"] = rec["grey_bars"] or rec["palette_strip"]
        results.append(rec)

with open(OUT_JSONL, "w") as fh:
    for r in results:
        fh.write(json.dumps(r) + "\n")

bad = [r for r in results if r["bad"]]
with open(OUT_MD, "w") as fh:
    fh.write("# Live-post image re-check\n\n")
    fh.write(f"- posts not done in the queue: **{len(posts)}**\n")
    fh.write(f"- distinct images embedded in their drafts: **{len(targets)}**\n")
    fh.write(f"- fail grey bars or palette strip: **{len(bad)}**\n")
    fh.write(f"- embeds that do not resolve: **{len(missing)}**\n\n")
    fh.write("Checks are `check-grey-bars.py` and `check-palette-strip.py` only -- no model in the loop.\n")
    fh.write("`check-flat-bands.py` is left out on purpose: it fires on cel-shaded art including approved frames.\n\n")
    fh.write("## Failing\n\n")
    if bad:
        fh.write("| post(s) | image | why |\n| --- | --- | --- |\n")
        for r in bad:
            why = ", ".join(k for k in ("grey_bars", "palette_strip") if r[k])
            fh.write(f"| {', '.join(map(str, r['posts']))} | `{r['path']}` | {why} |\n")
    else:
        fh.write("None. Every image embedded in a live post passes both checks.\n")
    fh.write("\n## Unresolved embeds\n\n")
    if missing:
        for n, rel, why in missing:
            fh.write(f"- post {n}: `{rel}` -- {why}\n")
    else:
        fh.write("None.\n")

print(f"bad {len(bad)} / {len(targets)}, missing {len(missing)}", flush=True)
print(OUT_MD)
