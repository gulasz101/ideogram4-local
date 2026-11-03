#!/usr/bin/env python3
"""Measure how much of a render is one flat fill, and where the blank bands are.

`check-grey-bars.py` looks for grey margins at the top and bottom. A render can
fail the same way without any grey in it: the model draws the scene on a pale
cream or near-white field and leaves half the canvas empty. One measured frame
carried 49.5% of its pixels in a single #F8FAFA fill, 116 rows over 80% pale,
and a 107 px strip down the right edge that was 99.8% blank — and the grey-bar
script passed it, because 248,250,250 is not grey.

This probe answers the empty-margin question for any fill colour:

  * the dominant fill's share of the whole frame,
  * every run of rows that is mostly that fill (a blank horizontal band),
  * every run of columns that is mostly that fill (a blank vertical band),
  * the blank strip running in from each of the four edges,
  * the bounding box of the content, so a wide margin is a number.

A flat fill is not automatically a defect — cel-shaded art has flat surfaces,
and a wall or a floor legitimately carries one. Read the numbers with the crop:
a fill that covers half the frame with the drawing squeezed into the other half
is an empty margin; a fill that is the wall behind a full scene is scenery.
The share, the runs and the edge strips are what separate the two.

Usage:
    check-blank-margin.py IMAGE [IMAGE ...]
    check-blank-margin.py IMAGE --tol 6 --fill 248,250,250
    check-blank-margin.py IMAGE --edge-frac 0.98 --band-frac 0.80

Exit codes:
    0 = no blank margin at any edge and no band over the threshold
    1 = a blank strip at an edge, or a band of fill over the band threshold
    2 = Pillow or numpy is missing

The check venv is ~/image-studio/.venv-imgcheck: the system python3 has no
Pillow or numpy. See references/review-loop.md step 6 for the one-time setup.
"""
import argparse
import sys
from collections import Counter

try:
    from PIL import Image
    import numpy as np
except ImportError:  # pragma: no cover - the documented failure mode
    sys.exit("ERROR: Pillow and numpy required")


def runs(idx):
    """Collapse sorted indices into inclusive runs."""
    if len(idx) == 0:
        return []
    out, start, prev = [], idx[0], idx[0]
    for i in idx[1:]:
        if i != prev + 1:
            out.append((int(start), int(prev)))
            start = i
        prev = i
    out.append((int(start), int(prev)))
    return out


def dominant_fill(a):
    """The frame's most common quantised colour, as an exact RGB triple."""
    q = (a // 4) * 4
    flat = q.reshape(-1, 3)
    counts = Counter(map(tuple, flat))
    common, _ = counts.most_common(1)[0]
    # return the mean of the pixels actually inside that quantised bucket, so
    # the reported fill is the real colour and not the bucket corner
    mask = np.all(np.abs(a - np.array(common)) <= 4, axis=2)
    if not mask.any():
        return tuple(int(c) for c in common)
    return tuple(int(round(v)) for v in a[mask].mean(axis=0))


def edge_strip(mask, frac, axis):
    """Consecutive lines from each end that are at least `frac` fill."""
    cover = mask.mean(axis=axis)
    lo = 0
    while lo < len(cover) and cover[lo] >= frac:
        lo += 1
    hi = 0
    while hi < len(cover) and cover[len(cover) - 1 - hi] >= frac:
        hi += 1
    return lo, hi


def check(path, tol, fill, band_frac, edge_frac):
    im = Image.open(path).convert("RGB")
    a = np.asarray(im).astype(int)
    h, w, _ = a.shape

    if fill is None:
        fill = dominant_fill(a)
    mask = np.all(np.abs(a - np.array(fill)) <= tol, axis=2)
    share = mask.sum() / (h * w) * 100

    row_cover = mask.mean(axis=1)
    col_cover = mask.mean(axis=0)
    band_rows = runs(np.where(row_cover >= band_frac)[0])
    band_cols = runs(np.where(col_cover >= band_frac)[0])

    top, bottom = edge_strip(mask, edge_frac, 1)
    left, right = edge_strip(mask, edge_frac, 0)

    ys, xs = np.where(~mask)
    if len(xs):
        content = f"x {xs.min()}-{xs.max()}  y {ys.min()}-{ys.max()}"
    else:
        content = "none — the whole frame is one fill"

    print(f"image {path}  {w}x{h}")
    print(f"fill  rgb{tuple(fill)}  tol {tol}  "
          f"share {share:.1f}% of the frame")
    print(f"blank strips: top {top}  bottom {bottom}  "
          f"left {left}  right {right}  (px, at >= {edge_frac:.0%} fill)")
    print(f"rows at least {band_frac:.0%} fill: {len(band_rows)}"
          + (f" -> {band_rows[:8]}" + (" ..." if len(band_rows) > 8 else "")
             if band_rows else ""))
    print(f"cols at least {band_frac:.0%} fill: {len(band_cols)}"
          + (f" -> {band_cols[:8]}" + (" ..." if len(band_cols) > 8 else "")
             if band_cols else ""))
    print(f"content bbox: {content}")

    flagged = []
    for name, px in (("top", top), ("bottom", bottom),
                     ("left", left), ("right", right)):
        if px >= 40:
            flagged.append(f"{name} strip {px}px")
    if band_rows or band_cols:
        flagged.append(f"{len(band_rows)} band rows / {len(band_cols)} band cols")

    if flagged:
        print("BLANK MARGIN: " + ", ".join(flagged))
        print("  A flat fill is a defect only when the drawing is pushed off the "
              "frame by it:\n  crop the edge and read it before the note calls it "
              "empty space.")
        return 1

    print("NO BLANK MARGIN: no edge strip of 40 px or more, no band of fill")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("images", nargs="+")
    ap.add_argument("--tol", type=int, default=10,
                    help="per-channel tolerance around the fill colour")
    ap.add_argument("--fill", default=None,
                    help="r,g,b of the fill; default is the frame's dominant colour")
    ap.add_argument("--band-frac", type=float, default=0.80,
                    help="fraction of a line that must be fill to count as a band")
    ap.add_argument("--edge-frac", type=float, default=0.98,
                    help="fraction of a line that must be fill for an edge strip")
    args = ap.parse_args()

    fill = None
    if args.fill:
        try:
            fill = tuple(int(v) for v in args.fill.split(","))
        except ValueError:
            sys.exit("error: --fill wants r,g,b as three integers")
        if len(fill) != 3:
            sys.exit("error: --fill wants exactly three values")

    rc = 0
    for i, path in enumerate(args.images):
        if i:
            print()
        rc |= check(path, args.tol, fill, args.band_frac, args.edge_frac)
    return rc


if __name__ == "__main__":
    sys.exit(main())
