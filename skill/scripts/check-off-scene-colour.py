#!/usr/bin/env python3
"""check-off-scene-colour.py - measure colour a frame carries that its scene does not own.

A render's own scene has a hue axis. Wood, rope, cardboard, cloth and grey metal
all sit on the warm brown/grey axis, so a vivid green, blue or magenta pixel is
a colour the scene does not own - and that is the shape of a pasted banner, a
flat overlay and a colour-swatch block, which is why this is the numeric answer
to a "colorful artifacts in the middle" rejection.

A max-min channel spread test does NOT measure this. Wood, rope and cardboard
are all brown, and brown has a large channel spread, so a spread test flags a
third of a perfectly clean frame. Measure hue against the scene's axis.

The measurement is comparative, so pass the images together: the rejected
original, the candidate, and an image of the same series that Wojtek already
approved. A detail the approved image carries too is series texture, not a
defect in the candidate - and a colourful scene he approved can carry MORE
off-scene colour than the image he rejected, so no single image's number means
anything on its own.

Usage:
    check-off-scene-colour.py rejected.png candidate.png approved.png
    check-off-scene-colour.py --axis 15,55 candidate.png
    check-off-scene-colour.py --sat 0.45 candidate.png

Two ways this number misleads, both hit on 2026-10-26:
  - The default axis (15,55) is the warm brown/grey axis, so a blue-and-purple
    scene reads as 40-50% "off-scene" colour when it owns every one of those
    pixels. Pick the axis from the scene, not from the default: a cool scene
    wants --axis 15,280. Compare candidates and approved siblings at the SAME
    axis, and re-read the frame on a crop before calling any of it an artifact.
  - The largest-contiguous-region step is SKIPPED when the off-scene pixel
    count exceeds MAX_MASK_FOR_BLOBS (400000), and a busy frame is exactly the
    one where that number is high. The output then jumps from the histogram
    straight to the busiest 32x32 cell with no blob line at all, which reads
    like "no contiguous shape found" when it means "not measured". When the
    blob line is missing on a busy frame, measure the region another way
    (crop-probe.py on the busiest cell) rather than reading the silence.

Requires Pillow + numpy:
    ~/image-studio/.venv-imgcheck/bin/python check-off-scene-colour.py ...
"""

import argparse
import os
import sys

import numpy as np
from PIL import Image

MAX_MASK_FOR_BLOBS = 400000
BAND = 30  # histogram bin width in degrees
BIG_BLOB = 500  # px, a contiguous off-scene region this size is a shape, not a prop


def parse_axis(text):
    parts = [int(v) for v in text.split(",")]
    if len(parts) != 2 or parts[0] >= parts[1]:
        raise argparse.ArgumentError("axis must be lo,hi in degrees with lo<hi")
    return parts


def hue_sat(arr):
    """Hue in degrees and saturation in 0..1 for an RGB int array."""
    r = arr[:, :, 0]
    g = arr[:, :, 1]
    b = arr[:, :, 2]
    mx = arr.max(axis=2).astype(float)
    mn = arr.min(axis=2).astype(float)
    d = mx - mn
    sat = np.where(mx > 0, d / np.maximum(mx, 1e-6), 0.0)
    hue = np.zeros(mx.shape)
    nz = d > 1e-6
    mr = nz & (mx == r)
    mg = nz & (mx == g)
    mb = nz & (mx == b)
    with np.errstate(invalid="ignore", divide="ignore"):
        hue[mr] = (60 * ((g[mr] - b[mr]) / d[mr])) % 360
        hue[mg] = 60 * ((b[mg] - r[mg]) / d[mg]) + 120
        hue[mb] = 60 * ((r[mb] - g[mb]) / d[mb]) + 240
    return hue, sat


def in_axis(hue, lo, hi):
    """True where the hue is inside the scene's axis (lo,hi in degrees)."""
    if lo <= hi:
        return (hue >= lo) & (hue < hi)
    return (hue >= lo) | (hue < hi)


def largest_blob(mask):
    """Size and bounding box of the largest 8-connected component, or None."""
    h, w = mask.shape
    seen = np.zeros(mask.shape, dtype=bool)
    best = (0, None)
    ys, xs = np.nonzero(mask)
    for sy, sx in zip(ys, xs):
        if seen[sy, sx]:
            continue
        stack = [(sy, sx)]
        seen[sy, sx] = True
        pts = []
        while stack:
            y, x = stack.pop()
            pts.append((y, x))
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ny, nx = y + dy, x + dx
                    if (0 <= ny < h and 0 <= nx < w and mask[ny, nx]
                            and not seen[ny, nx]):
                        seen[ny, nx] = True
                        stack.append((ny, nx))
        if len(pts) > best[0]:
            p = np.array(pts)
            best = (len(pts), (int(p[:, 1].min()), int(p[:, 0].min()),
                               int(p[:, 1].max()), int(p[:, 0].max())))
    return best


def measure(path, lo, hi, sat_thr):
    im = Image.open(path).convert("RGB")
    arr = np.asarray(im).astype(int)
    H, W = arr.shape[:2]
    hue, sat = hue_sat(arr)

    vivid = sat > sat_thr
    off = vivid & ~in_axis(hue, lo, hi)
    n_off = int(off.sum())

    print(f"  {os.path.basename(path)}  {W}x{H}")
    print(f"    off-scene vivid px: {n_off} ({100.0 * n_off / off.size:.3f}% of frame)"
          f"   [axis {lo}-{hi} deg, sat > {sat_thr}]")

    # hue histogram of the vivid pixels, so the reader sees where colour is
    hist = np.zeros(360 // BAND, dtype=int)
    vh = hue[vivid]
    if vh.size:
        idx = np.clip((vh // BAND).astype(int), 0, len(hist) - 1)
        hist += np.bincount(idx, minlength=len(hist))
    top = sorted(((int(c), i * BAND) for i, c in enumerate(hist)), reverse=True)[:5]
    print("    vivid hue bands: " + ", ".join(
        f"{a}-{a + BAND}deg:{c}" for c, a in top if c))

    if n_off:
        # largest contiguous off-scene region: a banner is one big shape,
        # scattered scene props are many small ones
        if n_off <= MAX_MASK_FOR_BLOBS:
            size, box = largest_blob(off)
            if size:
                print(f"    largest off-scene blob: {size} px "
                      f"({100.0 * size / off.size:.3f}% of frame) bbox={box}")
                if size >= BIG_BLOB:
                    print(f"      -> {size} px is a contiguous shape, not scattered "
                          "prop detail")
                else:
                    print("      -> no contiguous shape; the off-scene colour is "
                          "scattered prop detail")
        # busiest 32x32 cell: a flat banner fills cells entirely
        cell = 32
        worst = 0
        worst_at = None
        for gy in range(0, H - cell + 1, cell):
            for gx in range(0, W - cell + 1, cell):
                c = int(off[gy:gy + cell, gx:gx + cell].sum())
                if c > worst:
                    worst = c
                    worst_at = (gx, gy)
        print(f"    busiest 32x32 cell: {worst} px ({100.0 * worst / (cell * cell):.1f}%)"
              + (f" at {worst_at}" if worst_at else ""))
    return n_off


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("images", nargs="+")
    ap.add_argument("--axis", type=parse_axis, default=(15, 55),
                    help="the scene's own hue axis in degrees (default 15,55)")
    ap.add_argument("--sat", type=float, default=0.35,
                    help="saturation above which a pixel counts as vivid (default 0.35)")
    args = ap.parse_args()

    print("off-scene colour, scene axis "
          f"{args.axis[0]}-{args.axis[1]} deg, sat > {args.sat}")
    print("compare the rows: a candidate is only judged against the rejected "
          "original and an approved image of the same series\n")
    for path in args.images:
        if not os.path.exists(path):
            print(f"ERROR: no such file: {path}", file=sys.stderr)
            return 2
        measure(path, args.axis[0], args.axis[1], args.sat)
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
