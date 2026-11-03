#!/usr/bin/env python3
"""check-prop-extent.py - is a prop ONE object in one place, or scattered across the frame?

Why this exists: two rejections in a row on one slot were both extent defects
and both were settled by the same measurement, which kept being hand-rolled in
scratch files. "The white/red things are all over the place" and "the barrier
runs across his neck" are the same question asked twice: where are the prop's
pixels, and do they overlap the figure's?

Three numbers answer it, and none of them is a read:

  * span, as a fraction of the frame on each axis - a prop that is one object
    occupies a compact region, and a prop the model scattered spans far more
    of the frame than the object could possibly be;
  * orientation - a span that is much taller than wide is a post, much wider
    than tall is a bar. Comparing that against what the prompt called the prop
    is how a shape-versus-bbox contradiction gets caught (engine-pitfall #69);
  * rows carrying both the prop colour and the figure colour - a prop that
    shares rows with the body is drawn across the body, whatever the read says.

Usage
    check-prop-extent.py IMAGE.png --colour 190,40,40 --tol 60
    check-prop-extent.py IMAGE.png --colour 190,40,40 --tol 60 \\
        --figure 235,190,150 --figure-tol 55

Painted props are textured, so a mask that is too tight finds nothing and one
that is too loose finds the whole room. The script says which happened rather
than leaving you to guess: a count of zero tells you to raise --tol, and a span
near the full frame under a loose --tol tells you the colour is not specific.
Calibrate on a known frame of the same series before trusting a verdict.

Requires Pillow + numpy (the check venv):
    ~/image-studio/.venv-imgcheck/bin/python check-prop-extent.py ...
"""

import argparse
import os
import sys

import numpy as np
from PIL import Image

# A span covering this much of the frame is reported as suspicious even before
# anyone compares it to the shape the prompt asked for.
WIDE_SPAN = 0.75
# Taller-or-wider by this factor is called an orientation rather than square.
ORIENT = 1.25


def parse_rgb(text):
    parts = [int(v) for v in text.split(",")]
    if len(parts) != 3 or any(v < 0 or v > 255 for v in parts):
        raise argparse.ArgumentTypeError(
            "colour must be three comma-separated 0-255 values, e.g. 190,40,40")
    return parts


def colour_mask(arr, rgb, tol):
    rgb = np.array(rgb).reshape((1, 1, 3))
    return (np.abs(arr - rgb) <= tol).all(axis=2)


def runs(index_list):
    """Contiguous runs in a sorted list of ints."""
    out = []
    start = prev = None
    for v in index_list:
        if start is None:
            start = prev = v
        elif v == prev + 1:
            prev = v
        else:
            out.append((start, prev))
            start = prev = v
    if start is not None:
        out.append((start, prev))
    return out


def report(path, colour, tol, figure, figure_tol):
    im = Image.open(path).convert("RGB")
    arr = np.asarray(im).astype(int)
    H, W = arr.shape[:2]
    print(f"=== {os.path.basename(path)}  {W}x{H} ===")

    m = colour_mask(arr, colour, tol)
    n = int(m.sum())
    print(f"  prop colour {colour} tol {tol}: {n} px")
    if n == 0:
        print("  -> nothing matched. The prop is textured; RAISE --tol and re-run."
              " Do not conclude the prop is absent from a zero count.")
        print()
        return

    ys, xs = np.where(m)
    x0, x1, y0, y1 = int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())
    xspan, yspan = x1 - x0 + 1, y1 - y0 + 1
    fx, fy = xspan / W, yspan / H
    print(f"  x range {x0}-{x1}  span {xspan} px ({fx:.0%} of width)")
    print(f"  y range {y0}-{y1}  span {yspan} px ({fy:.0%} of height)")

    ratio = yspan / max(xspan, 1)
    if ratio >= ORIENT:
        shape = f"TALLER than wide ({ratio:.2f}x) - reads as a post/column"
    elif ratio <= 1 / ORIENT:
        shape = f"WIDER than tall ({1/ratio:.2f}x) - reads as a bar/beam/banner"
    else:
        shape = "roughly square on both axes"
    print(f"  orientation: {shape}")

    if fx >= WIDE_SPAN or fy >= WIDE_SPAN:
        print(f"  -> a span at or over {WIDE_SPAN:.0%} of the frame rarely belongs to"
              " one prop. Either the mask is too loose (lower --tol) or the model"
              " scattered the prop.")

    # How the pixels are distributed, so a cluster and a scatter look different.
    occupied_rows = np.where(m.any(axis=1))[0]
    occupied_cols = np.where(m.any(axis=0))[0]
    print(f"  occupied rows: {len(occupied_rows)}"
          f" in {len(runs(list(occupied_rows)))} band(s)"
          f"  |  occupied cols: {len(occupied_cols)}"
          f" in {len(runs(list(occupied_cols)))} band(s)")

    if figure:
        fm = colour_mask(arr, figure, figure_tol)
        fn = int(fm.sum())
        if fn == 0:
            print(f"  figure colour {figure} tol {figure_tol}: nothing matched"
                  " - raise --figure-tol")
        else:
            shared = np.where(m.any(axis=1) & fm.any(axis=1))[0]
            print(f"  figure colour {figure} tol {figure_tol}: {fn} px")
            print(f"  rows carrying BOTH prop and figure: {len(shared)}"
                  f" in {len(runs(list(shared)))} band(s)")
            if len(shared):
                b0, b1 = int(shared.min()), int(shared.max())
                print(f"  -> the prop shares rows with the figure over y {b0}-{b1}."
                      " A prop that shares rows with the body is DRAWN ACROSS"
                      " the body; that is the defect, not a lighting detail.")
            else:
                print("  -> no row carries both. The prop and the figure are clear"
                      " of each other vertically.")
    print()


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("images", nargs="+")
    ap.add_argument("--colour", type=parse_rgb, required=True,
                    help="the prop's colour as r,g,b")
    ap.add_argument("--tol", type=int, default=60,
                    help="per-channel tolerance for the prop colour (default 60)")
    ap.add_argument("--figure", type=parse_rgb, default=None,
                    help="the figure's colour as r,g,b, to test for overlap")
    ap.add_argument("--figure-tol", type=int, default=55,
                    help="per-channel tolerance for the figure colour (default 55)")
    args = ap.parse_args()

    for path in args.images:
        if not os.path.exists(path):
            print(f"ERROR: no such file: {path}", file=sys.stderr)
            return 2
        report(path, args.colour, args.tol, args.figure, args.figure_tol)
    return 0


if __name__ == "__main__":
    sys.exit(main())
