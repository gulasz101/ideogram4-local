#!/usr/bin/env python3
"""measure-bodies.py - is this ONE object broken in two, or SEVERAL objects?

Why this exists: a STRUCTURAL claim ("is this one plank cut in two, or two
planks stacked?", "is this one chain or three links?", "is this one wall with
a doorway, or a picture of a wall?") is not settled by a vision read. Two reads
of the SAME pixels at different zoom levels gave opposite answers about a
kerf, because a read completes the story it was asked about. The way out is to
count the bodies the pixels actually contain and measure how they touch:

  * BODIES      - connected components of the mask, each with area and bbox.
  * CONTINUITY  - for the largest body, the x ranges inside its own row span
                  where the MASK drops to zero. No interior absence means the
                  material runs continuously through that x range, however many
                  seams a read sees drawn across it. (It is a question about the
                  material, not about one object: a different body of the same
                  material filling the gap counts as continuous.)
  * SEPARATION  - for two bodies separated by a narrow horizontal gap: the gap
                  width, and whether their vertical spans are ALIGNED (same
                  top and bottom: one object broken in two) or NESTED/offset
                  (one board lying on another, a stack).

The component labelling is pure Python, so keep the region small: box the band
or the prop you are asking about rather than the whole frame.

Requires Pillow + numpy. Run it with the check venv:

    ~/image-studio/.venv-imgcheck/bin/python measure-bodies.py IMAGE.png --preset wood

Examples
  # how many separate pale-wood bodies sit in the plank band, and is the big
  # one broken anywhere?
  measure-bodies.py IMAGE.png --box 100,380,1216,560 --preset pale --min-px 300

  # the same for one specific colour
  measure-bodies.py IMAGE.png --find 40,90,200 --tol 60

  # a chain of links, to see whether the links are separate bodies
  measure-bodies.py IMAGE.png --box 200,300,900,500 --preset dark --min-px 200
"""

import argparse
import os
import sys
from collections import deque

import numpy as np
from PIL import Image

MIN_PX_DEFAULT = 300
MAX_GAP_DEFAULT = 40
ALIGN_TOL = 12          # px of vertical slack when calling two spans aligned
MAX_MASK_PX = 1500000   # above this the pure-Python labelling is too slow


def load(path):
    im = Image.open(path).convert("RGB")
    return im, np.asarray(im).astype(int)


def preset_mask(arr, name):
    """Boolean mask for a named material."""
    R = arr[:, :, 0]
    G = arr[:, :, 1]
    B = arr[:, :, 2]
    mx = arr.max(axis=2)
    mn = arr.min(axis=2)
    spread = mx - mn
    if name == "wood":
        # Warm wood, and NOT pink skin: skin carries a much larger R-G than G-B.
        return ((R > G) & (G > B) & ((R - B) > 45) & ((R - B) < 165)
                & ((R - G) < 60) & ((G - B) > 12))
    if name == "pale":
        # Bright, low-chroma, warm: a pale plank body.
        return ((mx > 145) & (spread > 0) & (spread < 105)
                & (G > B + 10) & ((R - G) < 70))
    if name == "dark":
        # Drawn ink strokes.
        return mx < 70
    raise ValueError("unknown preset: %s" % name)


def colour_mask(arr, rgb, tol):
    """True where the pixel is within a summed absolute distance of rgb."""
    return np.abs(arr - np.array(rgb, dtype=int)).sum(axis=2) < tol


def find_bodies(mask, min_px):
    """8-connected components of the mask, as dicts with area and bbox."""
    h, w = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    out = []
    for y in range(h):
        for x in np.nonzero(mask[y])[0]:
            if seen[y, x]:
                continue
            q = deque([(y, int(x))])
            seen[y, x] = True
            pts = []
            while q:
                cy, cx = q.popleft()
                pts.append((cy, cx))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ny, nx = cy + dy, cx + dx
                        if (0 <= ny < h and 0 <= nx < w
                                and mask[ny, nx] and not seen[ny, nx]):
                            seen[ny, nx] = True
                            q.append((ny, nx))
            if len(pts) >= min_px:
                ys = [p[0] for p in pts]
                xs = [p[1] for p in pts]
                out.append({"area": len(pts), "x0": min(xs), "x1": max(xs),
                            "y0": min(ys), "y1": max(ys)})
    out.sort(key=lambda b: b["area"], reverse=True)
    return out


def interior_absence(mask, body, margin=8):
    """x ranges inside a body's own row span where the mask drops to zero."""
    sub = mask[body["y0"]:body["y1"] + 1, body["x0"]:body["x1"] + 1]
    counts = sub.sum(axis=0)
    lo, hi = margin, len(counts) - margin
    gaps = []
    run = None
    for i in range(lo, hi):
        if counts[i] == 0:
            if run is None:
                run = [i, i]
            else:
                run[1] = i
        elif run is not None:
            gaps.append(tuple(run))
            run = None
    if run is not None:
        gaps.append(tuple(run))
    return [(body["x0"] + a, body["x0"] + b) for a, b in gaps]


def mean_lum(arr, x0, y0, x1, y1):
    if x1 <= x0 or y1 <= y0:
        return 0.0
    reg = arr[y0:y1, x0:x1]
    if reg.size == 0:
        return 0.0
    return float(reg.mean(axis=2).mean())


def parse_rgb(text):
    parts = [int(p) for p in text.split(",")]
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("colour must be r,g,b")
    return parts


def parse_box(text):
    parts = [int(p) for p in text.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("box must be x0,y0,x1,y1")
    x0, y0, x1, y1 = parts
    if x1 <= x0 or y1 <= y0:
        raise argparse.ArgumentTypeError("box must be x1>x0 and y1>y0")
    return (x0, y0, x1, y1)


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image")
    ap.add_argument("--box", type=parse_box, help="x0,y0,x1,y1 in pixel coords")
    ap.add_argument("--find", type=parse_rgb, help="r,g,b of one colour to mask")
    ap.add_argument("--preset", choices=("wood", "pale", "dark"),
                    help="named material mask")
    ap.add_argument("--tol", type=int, default=40,
                    help="summed absolute colour tolerance for --find")
    ap.add_argument("--min-px", type=int, default=MIN_PX_DEFAULT,
                    help="smallest body reported (default %d)" % MIN_PX_DEFAULT)
    ap.add_argument("--max-gap", type=int, default=MAX_GAP_DEFAULT,
                    help="widest gap treated as a separation (default %d)" % MAX_GAP_DEFAULT)
    args = ap.parse_args()

    if not os.path.exists(args.image):
        print("ERROR: no such image: %s" % args.image, file=sys.stderr)
        return 2
    if not args.find and not args.preset:
        print("ERROR: give --find r,g,b or --preset wood|pale|dark", file=sys.stderr)
        return 2

    im, arr = load(args.image)
    H, W = arr.shape[0], arr.shape[1]
    print("image %s %dx%d" % (args.image, W, H))

    x0, y0, x1, y1 = 0, 0, W, H
    if args.box:
        x0, y0, x1, y1 = args.box
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(W, x1), min(H, y1)
        if x1 <= x0 or y1 <= y0:
            print("ERROR: box is outside the image", file=sys.stderr)
            return 2
    print("region x[%d-%d] y[%d-%d]" % (x0, x1, y0, y1))
    region = arr[y0:y1, x0:x1]

    if args.preset:
        mask = preset_mask(region, args.preset)
        print("preset %s" % args.preset)
    else:
        mask = colour_mask(region, args.find, args.tol)
        print("colour %s tol=%d" % (args.find, args.tol))
    print("mask: %d px (%.2f%% of region)" % (
        int(mask.sum()), 100.0 * mask.sum() / max(1, region.shape[0] * region.shape[1])))
    if int(mask.sum()) > MAX_MASK_PX:
        print("WARNING: mask too large to label (%d px); narrow --box or raise --tol"
              % int(mask.sum()))
        return 2

    bodies = find_bodies(mask, args.min_px)
    print("\nbodies >= %d px: %d" % (args.min_px, len(bodies)))
    for b in bodies[:12]:
        print("  area=%7d  x %4d-%4d (w=%4d)  y %4d-%4d (h=%4d)" % (
            b["area"], b["x0"] + x0, b["x1"] + x0, b["x1"] - b["x0"] + 1,
            b["y0"] + y0, b["y1"] + y0, b["y1"] - b["y0"] + 1))
    if not bodies:
        print("  (no body reached the threshold: the material is not there)")
        return 0

    big = bodies[0]
    gaps = interior_absence(mask, big)
    print("\nlargest body (area %d, x %d-%d, y %d-%d):" % (
        big["area"], big["x0"] + x0, big["x1"] + x0, big["y0"] + y0, big["y1"] + y0))
    if not gaps:
        print("  CONTINUOUS: no interior absence across its whole width")
    else:
        for a, b in gaps:
            print("  INTERIOR ABSENCE x %d-%d (w=%d): the body is broken here" % (
                a + x0, b + x0, b - a + 1))

    print("\nseparations (narrow gap between two bodies):")
    found = False
    for i in range(len(bodies)):
        for j in range(i + 1, len(bodies)):
            a, b = bodies[i], bodies[j]
            # Skip pairs that overlap horizontally; keep the ones that sit side
            # by side, and order them left to right.
            if not (a["x1"] < b["x0"] or b["x1"] < a["x0"]):
                continue
            if a["x1"] < b["x0"]:
                left, right = a, b
            else:
                left, right = b, a
            gap = right["x0"] - left["x1"] - 1
            if gap <= 0:
                # The two bodies touch: that is one mass, not a separation.
                continue
            if gap > args.max_gap:
                continue
            found = True
            ov_top = max(left["y0"], right["y0"])
            ov_bot = min(left["y1"], right["y1"])
            overlap = ov_bot - ov_top + 1
            aligned = (abs(left["y0"] - right["y0"]) <= ALIGN_TOL
                       and abs(left["y1"] - right["y1"]) <= ALIGN_TOL)
            gap_lum = mean_lum(arr, left["x1"] + 1 + x0, ov_top + y0,
                               right["x0"] + x0, ov_bot + 1 + y0)
            flank = 0.5 * (mean_lum(arr, max(left["x0"], left["x1"] - 5) + x0,
                                    ov_top + y0, left["x1"] + 1 + x0, ov_bot + 1 + y0)
                           + mean_lum(arr, right["x0"] + x0, ov_top + y0,
                                      min(right["x1"], right["x0"] + 5) + 1 + x0,
                                      ov_bot + 1 + y0))
            gap_x0 = left["x1"] + 1 + x0
            gap_x1 = right["x0"] - 1 + x0
            print("  gap x %d-%d (w=%d)  left body x %d-%d y %d-%d  right body x %d-%d y %d-%d  overlap %d px"
                  % (gap_x0, gap_x1, gap,
                     left["x0"] + x0, left["x1"] + x0, left["y0"] + y0, left["y1"] + y0,
                     right["x0"] + x0, right["x1"] + x0, right["y0"] + y0, right["y1"] + y0,
                     overlap))
            if overlap <= 0:
                print("    spans do not overlap vertically: two objects at different "
                      "heights, not one object broken in two")
            elif aligned:
                print("    ALIGNED spans (same top and bottom): one object broken in two")
            else:
                print("    OFFSET spans: two different objects, one lying on/against the other")
            if flank > 0:
                print("    gap luminance %.0f vs flanking %.0f (%.0f%%): %s" % (
                    gap_lum, flank, 100.0 * gap_lum / flank,
                    "the background shows through" if gap_lum < 0.8 * flank
                    else "no dip, a seam or shadow line on a continuous surface"))
    if not found:
        print("  (no pair of bodies separated by a gap of %d px or less)" % args.max_gap)

    return 0


if __name__ == "__main__":
    sys.exit(main())
