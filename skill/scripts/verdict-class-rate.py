#!/usr/bin/env python3
"""Measure a defect class's rejection rate in the image library.

Wojtek's verdicts are the only ground truth about his eye, and they are
countable: every library record carries a Verdicts table, and every row is
one decision with a reason. When a self-check has to decide whether a defect
is a hard one (costs a re-render) or a quirk (a line on the card), the
question is not how big the shape is but whether he has ever approved a
picture carrying that shape.

This script counts the distinct decisions whose reason mentions each defect
class's keywords, and prints what the library says about each class. A class
he has rejected and never confirmed approving is a class he rejects: that is
a re-render, not a note on the card. The count is a decision procedure, not
a taste judgement, so it also settles a disagreement with a brief's own
check note.

Four things the count has to get right, and each one is a way the number has
lied before:

* A slot's verdict history is copied into every later record of that slot,
  so the same rejection sits in several rows. Rows are collapsed to
  distinct decisions (slot, round, date, issue) before anything is
  counted, so one rejection counts once no matter how many records carry
  it forward.
* A row whose reason says the render was "held back at the self-check" is
  Matejko's own call, not Wojtek's. Those are counted separately and are
  never counted as his rejection.
* An approval only says something about a class when its reason names that
  class as something present in the picture. Most approval rows read
  "Approved on review." and name no defect at all, and a few describe a
  prompt revision instead of the picture -- neither is evidence that he
  tolerated the class. Those approvals are excluded from the class count
  and reported as silent, because the honest reading of "0 approvals" is
  "no approval row proves he accepted it", not "he never accepted it".
* A class that matches no row is a keyword miss, not an absence of
  history. Widen the class's keywords and count again before deciding
  anything on it.

Usage:
    verdict-class-rate.py                         # every class
    verdict-class-rate.py --class pasted-overlay
    verdict-class-rate.py --rows pasted-overlay   # print the matching rows
    verdict-class-rate.py --library /path/to/image-library

Exit codes:
    0 = ran and reported
    1 = bad arguments
    2 = the library directory is missing
"""
import argparse
import re
import sys
from pathlib import Path

DEFAULT_LIBRARY = (
    "~/wojtek.second.brain.obsidian.vault/3-resources/image-library"
)

# Keyword sets per defect class. A class is a shape the model invents, not a
# phrase: every entry is a way the class shows up in a verdict reason.
CLASSES = {
    "pasted-overlay": [
        "logo", "overlay", "icon", "collage", "paste", "pasted", "artifact",
        "cut-away", "cutaway", "inset", "banner", "plaque", "emblem", "badge",
        "picture-in-picture", "drop shadow", "flat rectangle", "swatch",
        "colorful blob", "colorfur blob", "colored blob", "graphic overlay",
    ],
    "unreadable-text": [
        "not readable", "nothing readable", "unreadable", "garbled",
        "not spelled", "misspell", "random letter", "pseudo-text", "illegible",
        "not explicit enough", "texts not explicit",
    ],
    "no-story": [
        "story", "logical connection", "items placed", "inventory",
        "disconnected", "no sense", "makes no sense", "no meaning",
    ],
    "concept-mismatch": [
        "concept", "does not fit", "doesn't fit", "fit into", "not fitting",
    ],
    "empty-margins": [
        "grey bar", "gray bar", "grey margin", "gray margin", "empty margin",
        "empty space", "blank band", "whitespace",
    ],
    "wrong-count": [
        "how many", "wrong number", "extra figure", "one more than",
        "too many", "not the number", "only one character", "one character",
        "main characters", "extra character", "extra characters",
        "second person", "second man", "second figure", "duplicate",
        "two of them",
    ],
}

# A row whose reason carries one of these is Matejko's own self-check call.
SELF_CHECK = re.compile(r"held back at the self-check|never shown", re.I)

# Approvals whose reason says nothing about a defect in the picture: the
# bare default, and a note describing a prompt revision.
SILENT_APPROVAL = re.compile(
    r"^approved on review\.?$"
    r"|^approved on the card with no reason given",
    re.I,
)
BOOKKEEPING_APPROVAL = re.compile(
    r"prompt revised|generated job", re.I
)


def library_records(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.md") if p.is_file())


def slot_of(path: Path) -> str:
    """The slot a record belongs to: its stem minus date, token and attempt."""
    stem = path.stem.split("--")[0]
    stem = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", stem)
    stem = re.sub(r"-[0-9a-f]{8}$", "", stem)
    stem = re.sub(r"-r\d+b?$", "", stem)
    return stem


def issue_id(raw: str) -> str:
    m = re.search(r"(GUL-\d+)", raw)
    return m.group(1) if m else raw


def verdict_rows(path: Path) -> list[dict]:
    """Return every Verdicts row of one record, with its decision fields."""
    rows = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [c.strip() for c in stripped.split("|")]
        # a row is | round | date | verdict | reason | issue |
        if len(cells) < 6 or not cells[1].isdigit():
            continue
        verdict = cells[3].lower()
        if verdict not in ("approved", "rejected", "deferred"):
            continue
        # a reason carrying a pipe would shift the columns, so fold the
        # middle back together rather than truncating the reason
        reason = " | ".join(cells[4:-2]) if len(cells) > 6 else cells[4]
        rows.append({
            "round": cells[1],
            "date": cells[2],
            "verdict": verdict,
            "reason": reason,
            "issue": issue_id(cells[-2]),
            "slot": slot_of(path),
        })
    return rows


def distinct_decisions(records: list[Path]) -> list[dict]:
    """Collapse a slot's carried-forward history into one row per decision.

    The same rejection is copied into every later record of the slot, so a
    naive row count multiplies it. The first record in sorted order holds
    the shortest (unprefixed) reason, so keeping the first hit keeps the
    cleanest wording.
    """
    seen: dict[tuple, dict] = {}
    for path in records:
        for row in verdict_rows(path):
            key = (row["slot"], row["round"], row["date"], row["issue"],
                   row["verdict"])
            seen.setdefault(key, row)
    return list(seen.values())


def is_silent_approval(row: dict) -> bool:
    """An approval whose reason says nothing about a defect in the picture."""
    if row["verdict"] != "approved":
        return False
    reason = row["reason"].strip()
    return bool(
        SILENT_APPROVAL.match(reason) or BOOKKEEPING_APPROVAL.search(reason)
    )


def matches(reason: str, keywords: list[str]) -> bool:
    low = reason.lower()
    return any(k in low for k in keywords)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--class", dest="cls", help="report only this class")
    ap.add_argument(
        "--rows", dest="rows",
        help="print the matching verdict rows for this class",
    )
    ap.add_argument("--library", default=DEFAULT_LIBRARY)
    args = ap.parse_args()

    for name in (args.cls, args.rows):
        if name and name not in CLASSES:
            sys.exit(
                f"error: unknown class {name}; known: {', '.join(CLASSES)}"
            )

    root = Path(args.library).expanduser()
    if not root.is_dir():
        sys.exit(f"error: library not found: {root}")

    records = library_records(root)
    if not records:
        sys.exit(f"error: no records under {root}")

    decisions = distinct_decisions(records)
    his = [d for d in decisions if not SELF_CHECK.search(d["reason"])]
    mine = [d for d in decisions if SELF_CHECK.search(d["reason"])]
    silent = [d for d in his if is_silent_approval(d)]
    spoken = [d for d in his if d["verdict"] == "approved" and not is_silent_approval(d)]

    if args.rows:
        keywords = CLASSES[args.rows]
        for d in his:
            if matches(d["reason"], keywords):
                mark = " [silent approval]" if is_silent_approval(d) else ""
                print(f"[{d['verdict']}]{mark} {d['slot']} (round {d['round']}, "
                      f"{d['issue']}): {d['reason']}")
        return 0

    names = [args.cls] if args.cls else list(CLASSES)
    print(f"library: {root}")
    print(f"records: {len(records)}   decisions: {len(decisions)}")
    print(f"  his decisions: {len(his)}   self-check holds (not his): {len(mine)}")
    print(f"  approvals naming no defect in the picture (silent): {len(silent)}")
    print()

    print(f"{'class':<18} {'rejected':>9} {'approved':>9} {'rate':>8}")
    empty = []
    for name in names:
        keywords = CLASSES[name]
        r = sum(1 for d in his
                if d["verdict"] == "rejected" and matches(d["reason"], keywords))
        a = sum(1 for d in spoken
                if matches(d["reason"], keywords))
        total = a + r
        rate = f"{(a / total * 100):.0f}%" if total else "no rows"
        if not total:
            empty.append(name)
        print(f"{name:<18} {r:>9} {a:>9} {rate:>8}")

    print()
    print(
        "A class he has rejected and never confirmed approving is a class he "
        "rejects:\nthat is a re-render, not a note on the card. Rows are the "
        "evidence: --rows <class>\nprints them, and it marks the approvals "
        "whose reason names no defect."
    )
    print(
        "Read the number with its limits. An approval only counts here when "
        "its reason names the\nclass as something present in the picture, so "
        "'0 approved' means 'no approval row proves he\naccepted it', not "
        "'he never accepted it'. Self-check holds are counted apart and are "
        "not his verdicts."
    )
    if empty:
        print(
            "No rows matched for: " + ", ".join(empty) +
            ". That is a keyword miss, not an absence of history:\n"
            "widen the class's keywords in this script and count again "
            "before deciding on it."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
