#!/usr/bin/env python3
"""Rebuild the backlog runner's `queue` issue document from live state.

The runner holds no card, so the board shows one open review issue at a time
and the whole list of posts has to live in one document. `backlog.py status`
cannot build that document: it prints only the posts that are not `todo`, so it
cannot produce the full table. This script reads `queue.json` plus every brief
and prints the document body as markdown, ready to PUT to the runner's issue
document (see references/paperclip-api.md for the PUT).

Usage:
    python3 build-queue-doc.py [--backlog-dir DIR] [--out FILE]

Prints the body on stdout; --out also writes it to a file for the PUT.
"""
import argparse
import datetime
import json
import os
import re

FIELD_STATUS = re.compile(r"\*\*Status:\*\*\s*(.+)")
FIELD_IMAGES = re.compile(r"\*\*Images:\*\*\s*(\d+)")
# A brief's Notes block marks a slot that was never rendered.
MISSING = re.compile(r"\*\*Missing image\.\*\*")


def read_brief(path):
    try:
        with open(path) as f:
            return f.read()
    except OSError:
        return ""


def brief_facts(text):
    status = FIELD_STATUS.search(text)
    images = FIELD_IMAGES.search(text)
    return (
        status.group(1).strip().replace("`", "") if status else "unknown",
        int(images.group(1)) if images else 0,
        len(MISSING.findall(text)),
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--backlog-dir", default=os.path.expanduser("~/image-studio/backlog"))
    ap.add_argument("--out", help="also write the body to this file")
    args = ap.parse_args()

    with open(os.path.join(args.backlog_dir, "queue.json")) as f:
        q = json.load(f)

    briefs = os.path.join(args.backlog_dir, "briefs")
    rows = []
    total_images = 0
    needs_render = []

    for p in q["posts"]:
        status_field, images, missing = brief_facts(read_brief(os.path.join(briefs, p["brief"])))
        total_images += images
        if missing:
            needs_render.append((p["n"], missing, p["title"]))

        issues = " ".join(p.get("issues") or []) or "—"
        state = p["state"]
        if p.get("issues"):
            state = f"{state} ({issues})"
        note = "; ".join(p.get("notes") or [])
        if note:
            state = f"{state} — {note}"

        rows.append(
            f"| {p['n']:03d} | {p['title']} | {status_field} | {images} | "
            f"{missing or '—'} | {state} |"
        )

    counts = {}
    for p in q["posts"]:
        counts[p["state"]] = counts.get(p["state"], 0) + 1
    count_line = ", ".join(f"{v} {k}" for k, v in sorted(counts.items()))

    slot = q.get("slot") or {}
    if slot:
        ident = slot.get("issue") or ""
        prefix = ident.split("-")[0] if "-" in ident else ""
        link = f"[{ident}](/{prefix}/issues/{ident})" if prefix else ident
        if ident:
            slot_line = (
                f"**Live slot:** post {slot['n']:03d}, round {slot['round']}, card issue {link} "
                "— one card at a time; the next post starts when this one carries a verdict "
                "for every one of its items. Wojtek's verdicts land on that card, not here."
            )
        else:
            slot_line = (
                f"**Live slot:** post {slot['n']:03d}, round {slot['round']}, card issue not "
                "created yet — the runner creates it on the next Advance."
            )
    else:
        slot_line = "**Live slot:** free."

    batch = q.get("batch") or []
    if batch:
        lines = []
        for b in batch:
            ident = b.get("issue") or ""
            prefix = ident.split("-")[0] if "-" in ident else ""
            link = f"[{ident}](/{prefix}/issues/{ident})" if prefix else "not created yet"
            lines.append(f"post {b['n']:03d} round {b['round']} — {link}")
        batch_line = (
            "**Batch cards in flight:** "
            + "; ".join(lines)
            + ". Wojtek asked for more than one card at a time so there is work to do "
            "overnight. The live slot above is still the runner's own next card."
        )
    else:
        batch_line = "**Batch cards in flight:** none."

    if needs_render:
        render_line = "; ".join(f"{n:03d} ({m} missing)" for n, m, _ in needs_render)
        render_line = f"**Needs a render before its card:** {render_line}."
    else:
        render_line = "**Needs a render before its card:** none."

    skipped = q.get("skipped") or []
    skip_txt = ", ".join(f"`{s['post']}` ({s['why']})" for s in skipped) or "none"
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    body = f"""# Backlog review queue

The order Wojtek sees the cards in: newest draft first. The live state is `~/image-studio/backlog/queue.json` on the Air; Matejko rebuilds this document from it and from the briefs on every watchdog wake.

**{q['total']} posts, {total_images} images.** Skipped: {skip_txt}.

Snapshot {now}. Counts: {count_line}.

**Where the rest of the work lives.** Every post has a brief in `~/image-studio/backlog/briefs/`, one file per post, each listing every image, the section it sits in, its live library record and its job id. The runner opens them **one at a time**: `backlog.py next` hands out exactly one card, and the next post starts only when the previous card carries a verdict for every one of its items. That is why the board shows a single open review issue at a time — the rest of the list is this table, and each finished card creates the next.

{slot_line}

{batch_line}

{render_line}

| # | post | status field | images | needs render | state |
| --- | --- | --- | --- | --- | --- |
""" + "\n".join(rows) + "\n"

    if args.out:
        with open(args.out, "w") as f:
            f.write(body)
    print(body)


if __name__ == "__main__":
    main()
