#!/usr/bin/env python3
"""Extract an author's finished prompt JSONs out of a composition document, and prove
the boxes in the files are the boxes he wrote.

The authoring hand-off often comes back as an issue document whose fenced json blocks
ARE the prompts, one per slot under a heading that names it, with the element sets also
written out as markdown tables of [y1, x1, y2, x2]. Retyping those prompts is how a box
reaches the render at a value nobody asked for: a skipped row or a transposed digit
passes both lint and check-bboxes.py, because the file you wrote is internally
consistent, and the render then places an element where the author never put it.

So this writes the blocks out byte for byte and then compares every element's bbox
against the table row for the same slot. A mismatch fails here instead of on a card.

Usage
-----
  python3 extract-author-prompts.py <composition.md> \
      --out-dir ~/image-studio/backlog/prompts --prefix 038 --round 2

Writes <prefix>-<name>-r<round>.json, skipping the suffix when the heading already
carries it. Omit --out-dir to verify without writing. Exits non-zero on invalid JSON,
a slot with no table, or any bbox mismatch, so it can gate a submit.

Prompt file names are prefixed with the post number because the prompts directory is
shared by every post of the backlog and a bare `header-r2.json` already belongs to
some other post's round 2. The render's --name stays the card's item id.
"""

import argparse
import json
import os
import re
import sys

BLOCK_RE = re.compile(r"#{3,}\s+`([^`]+?)\.json`\s*\n+\s*```json\s*\n(.*?)\n```", re.S)
SLOT_HEAD_RE = re.compile(r"^#{2,}\s+\d+[.)]\s+`([A-Za-z0-9._-]+)`")
ROW_RE = re.compile(r"^\|\s*(\d+)\s*\|")


def parse_tables(doc):
    """{slot: [[y1, x1, y2, x2], ...]} from the markdown element tables."""
    tables, cur = {}, None
    for line in doc.splitlines():
        head = SLOT_HEAD_RE.match(line.strip())
        if head:
            cur = head.group(1)
            tables.setdefault(cur, [])
            continue
        if cur is None or not ROW_RE.match(line.strip()):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 6:
            continue
        try:
            nums = [int(cells[i]) for i in range(2, 6)]
        except ValueError:
            continue
        tables[cur].append(nums)
    return tables


def out_name(name, prefix, round_no):
    stem = name
    if round_no is not None and not re.search(r"-r%d$" % round_no, stem):
        stem = "%s-r%d" % (stem, round_no)
    return "%s-%s.json" % (prefix, stem) if prefix else "%s.json" % stem


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("doc", help="the author's composition markdown (e.g. from jq -j '.body')")
    ap.add_argument("--out-dir", help="directory for the prompt files; omit to verify only")
    ap.add_argument("--prefix", default="", help="post number, e.g. 038")
    ap.add_argument("--round", type=int, default=None, help="round number, e.g. 2")
    args = ap.parse_args()

    doc = open(args.doc, encoding="utf-8").read()
    blocks = BLOCK_RE.findall(doc)
    if not blocks:
        print("no fenced json block under a `### `<slot>.json`` heading — nothing extracted")
        return 2

    tables = parse_tables(doc)
    problems = []

    for name, body in blocks:
        try:
            data = json.loads(body)
        except json.JSONDecodeError as exc:
            problems.append("%s: invalid JSON (%s)" % (name, exc))
            continue
        boxes = [el.get("bbox") for el in data.get("compositional_deconstruction", {}).get("elements", [])]
        tbl = tables.get(name)
        verdict = "no table found"
        if tbl is not None:
            if boxes == tbl:
                verdict = "boxes match table (%d)" % len(tbl)
            else:
                verdict = "MISMATCH"
                problems.append("%s: %d json boxes vs %d table rows" % (name, len(boxes), len(tbl)))
                for i, (a, b) in enumerate(zip(boxes, tbl)):
                    if a != b:
                        problems.append("  element %d: json=%s table=%s" % (i, a, b))
        if tbl is None:
            problems.append("%s: no element table in the document to check against" % name)

        written = ""
        if args.out_dir:
            os.makedirs(args.out_dir, exist_ok=True)
            path = os.path.join(args.out_dir, out_name(name, args.prefix, args.round))
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2, ensure_ascii=False)
                fh.write("\n")
            written = " -> %s" % path
        print("%-28s %s%s" % (name, verdict, written))

    if problems:
        print("\nPROBLEMS")
        for p in problems:
            print("  " + p)
        print("\nRun lint and check-bboxes.py on the written files before submitting either way.")
        return 1

    print("\nOK: every block parsed and every bbox matches its table.")
    print("Next: python3 ~/.local/share/ideogram4-local/ideogram4_local.py lint <file>")
    print("      python3 .../scripts/check-bboxes.py <file>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
