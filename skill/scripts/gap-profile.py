#!/usr/bin/env python3
"""Measure a visible-gap claim across a part that sits in an opening.

Why this exists: when a picture's whole point is that a part does not fit -- a
block slack in a socket, a plank short of its stop, a door not meeting its
frame -- the gap IS the story, and no vision read settles it. The failure mode
is a read that confidently reports "seated in the socket" for a block passing
through it, or "a shadow" for a real gap on one side only. This prints the runs
and the flank/part luminance so the claim is a number.

It was hand-rolled as three separate scratch scripts in one session before
being promoted here; use it instead of writing it again.

Usage:
    gap-profile.py IMAGE --box x0,y0,x1,y1 [--row-step N] [--dark 75] [--bright 120]

--box is x0,y0,x1,y1 in PIXELS (crop-probe's order), covering the opening and
both flanks -- wider than the part, or a flank falls outside the box and the
claim is unmeasurable.

Read the output like this:
  * BOTH flanks dark and the part brighter than both = a real gap on both sides.
  * ONE dark side only = a shadow, not a gap. Do not write "the gap reads".
  * No dark run at all = the part fits (or passes through) and the picture has
    lost its point; the repair is to widen the opening, not to reword the prompt.

Quote the runs in the note ("dark runs at x 686-819 and x 917-1003 either side
of the brighter block at row 570"), never just the verdict.
"""

import argparse
import sys


def runs(mask, offset, min_width):
    idx = [i for i, v in enumerate(mask) if v]
    if not idx:
        return []
    out, start, prev = [], idx[0], idx[0]
    for i in idx[1:]:
        if i - prev > 4:
            out.append((start + offset, prev + offset, prev - start + 1))
            start = i
        prev = i
    out.append((start + offset, prev + offset, prev - start + 1))
    return [r for r in out if r[2] >= min_width]


def main():
    ap = argparse.ArgumentParser(description="Horizontal luminance profile across an opening.")
    ap.add_argument("image")
    ap.add_argument("--box", required=True, help="x0,y0,x1,y1 in pixels")
    ap.add_argument("--row-step", type=int, default=10)
    ap.add_argument("--dark", type=int, default=75, help="luminance below this counts as gap/shadow")
    ap.add_argument("--bright", type=int, default=120, help="luminance above this counts as the part")
    ap.add_argument("--min-width", type=int, default=8, help="ignore runs narrower than this")
    args = ap.parse_args()

    try:
        from PIL import Image
        import numpy as np
    except ImportError:
        sys.exit("ERROR: Pillow and numpy required. Run with ~/image-studio/.venv-imgcheck/bin/python")

    im = Image.open(args.image).convert("L")
    w, h = im.size
    arr = np.asarray(im).astype(float)

    try:
        x0, y0, x1, y1 = [int(v) for v in args.box.split(",")]
    except ValueError:
        sys.exit("ERROR: --box wants four comma-separated integers x0,y0,x1,y1")

    x0, x1 = max(0, x0), min(w, x1)
    y0, y1 = max(0, y0), min(h, y1)
    if x1 <= x0 or y1 <= y0:
        sys.exit("ERROR: empty region after clamping to the %dx%d image" % (w, h))

    print("image %s %dx%d" % (args.image, w, h))
    print("region x[%d-%d] y[%d-%d]  (x0,y0,x1,y1 order)" % (x0, x1, y0, y1))
    print()
    print("row  | dark(<%d) runs                      | bright(>%d) runs" % (args.dark, args.bright))

    any_gap_row = False
    for y in range(y0 + 2, y1 - 2, args.row_step):
        row = [int(v) for v in arr[y, x0:x1]]
        d = runs([v < args.dark for v in row], x0, args.min_width)
        b = runs([v > args.bright for v in row], x0, args.min_width)
        if len(d) >= 2:
            any_gap_row = True
        print("%4d | %-40s | %s" % (y, str(d) if d else "-", str(b) if b else "-"))

    print()
    if not any_gap_row:
        print("NO ROW SHOWS TWO DARK RUNS -- no gap on both sides of anything in this box.")
        print("Either the part fits, or the box does not hold both flanks. Widen the box")
        print("before concluding the part is seated.")
    else:
        print("Rows above with TWO dark runs are the gap claim. Read one such row in the note,")
        print("with the run coordinates, and sample the three segments (left flank, part,")
        print("right flank) to confirm the part is brighter than both.")


if __name__ == "__main__":
    main()
