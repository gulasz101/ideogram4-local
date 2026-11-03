#!/usr/bin/env python3
"""Check a prompt's bboxes against the words in their own element descriptions.

The schema's bbox order is [y1, x1, y2, x2]. A prompt written as
[x1, y1, x2, y2] swaps every element's width and height, and the model follows
the boxes rather than the prose. `lint` cannot catch it: the schema only
requires four numbers.

This prints each box as "y a-b (h), x c-d (w)" and flags the boxes whose
geometry contradicts the spatial words in the same element's desc.

Usage:
    check-bboxes.py prompt.json
    check-bboxes.py prompt.json --verbose   # also print every element
"""
import json
import re
import sys
from pathlib import Path

# Spatial phrase -> the axis it constrains and the direction it means.
# "left" constrains x to the low end, "top" constrains y to the low end, etc.
#
# The patterns are deliberately narrow. A loose "top" matches "stacked on top of
# one another", which says nothing about where the object sits in the frame, and
# a false positive makes the check worthless.
RULES = [
    (r"\bleft third\b|\bleft half\b|\bleft side\b|\bthe left\b", "x", "low"),
    (r"\bright third\b|\bright half\b|\bright side\b|\bthe right\b", "x", "high"),
    (r"\btop left\b", "both", "low"),
    (r"\btop right\b", "both", "high"),
    (r"\bbottom left\b", "x", "low"),
    (r"\bbottom right\b", "x", "high"),
    (r"\btop edge\b|\bat the top\b|\bupper (?:part|half|corner|left|right)\b", "y", "low"),
    (r"\bbottom edge\b|\bat the bottom\b|\bin the lower\b", "y", "high"),
    (r"\bfull[- ]width\b|\bacross the whole\b|\bfull width\b", "x", "full"),
    (r"\bfull[- ]height\b|\bfull height\b", "y", "full"),
    (r"\bnarrow\b|\bthin\b|\bslim\b", "axis", "thin"),
]

# "bottom" as a position word, not as part of "leaning against the bottom of".
BOTTOM_POSITION = re.compile(
    r"\bbottom (?:left|right|corner|edge)\b|\bat the bottom\b|\bin the lower\b"
)
# "top" as a position word: the frame's top edge, not "on top of".
TOP_POSITION = re.compile(
    r"\btop (?:left|right|edge)\b|\bat the top\b|\bupper (?:part|half|corner|left|right)\b"
)


def axes(desc: str) -> set:
    """Which axes the desc constrains, and in which direction."""
    low = set()
    text = desc.lower()
    for pattern, axis, direction in RULES:
        if not re.search(pattern, text):
            continue
        if axis == "both":
            low.add("x")
            low.add("y")
        elif axis == "axis":
            low.add("thin")
        else:
            low.add(axis)
    return low


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    verbose = "--verbose" in sys.argv
    if not args:
        print(__doc__)
        return 2

    path = Path(args[0]).expanduser()
    prompt = json.loads(path.read_text())
    elements = prompt.get("compositional_deconstruction", {}).get("elements", [])

    if not elements:
        print("no elements in the prompt")
        return 0

    problems = []
    print(f"{path.name}: {len(elements)} elements, bbox order [y1, x1, y2, x2]")
    for index, element in enumerate(elements):
        bbox = element.get("bbox")
        desc = element.get("desc", "")
        if not bbox or len(bbox) != 4:
            print(f"  [{index}] no bbox: {desc[:50]}")
            continue
        y1, x1, y2, x2 = bbox
        height = y2 - y1
        width = x2 - x1
        print(f"  [{index}] y {y1}-{y2} (h={height}), x {x1}-{x2} (w={width}) | {desc[:60]}")

        # A "left" or "right" element must not be a full-width band.
        if re.search(r"\bleft\b", desc.lower()) and width > 600 and height < 600:
            problems.append(
                f"[{index}] desc says LEFT but the box is {width}px wide and {height}px tall - "
                "a full-width band, not a left region"
            )
        if re.search(r"\bright\b", desc.lower()) and width > 600 and height < 600:
            problems.append(
                f"[{index}] desc says RIGHT but the box is {width}px wide and {height}px tall - "
                "a full-width band, not a right region"
            )
        if re.search(r"\bnarrow\b|\bthin\b", desc.lower()) and width > 400 and height > 400:
            problems.append(
                f"[{index}] desc says NARROW but the box is {width}x{height} - not a narrow strip"
            )
        if BOTTOM_POSITION.search(desc.lower()) and y1 < 400 and height < 600:
            problems.append(
                f"[{index}] desc says BOTTOM but the box starts at y={y1} - it is in the top half"
            )
        if TOP_POSITION.search(desc.lower()) and y1 > 600:
            problems.append(
                f"[{index}] desc says TOP but the box starts at y={y1} - it is in the bottom half"
            )

    if problems:
        print("\nBBOX PROBLEMS:")
        for problem in problems:
            print(f"  - {problem}")
        print(
            "\nThe schema's order is [y1, x1, y2, x2]. A box written [x1, y1, x2, y2] swaps "
            "width and height, and the model follows the box, not the prose."
        )
        return 1

    print("\nno bbox contradicts its own desc")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
