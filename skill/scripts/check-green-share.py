#!/usr/bin/env python3
"""check-green-share.py — measure how much green a render actually carries.

Wojtek's rejection clause "green stuff is not fitting generally the full concept"
turned the green band into a defect class for this series, and a vision read calls
an olive-grey robot "green" as easily as it calls a real green prop green. This
prints the number instead: the share of the frame whose hue sits in the green band
at usable saturation, the largest connected green blob and its bounding box, and
the busiest 32x32 cell — so "there is a green robot" becomes a measurement.

Usage (check venv):
    ~/image-studio/.venv-imgcheck/bin/python check-green-share.py IMAGE.png [--baseline OTHER.png]

Read it against a baseline: a clean cel-painted frame with no green prop still
carries a percent or two in the green band from wood and shadow hues, so the
comparison is what tells a prop from the paint. A blob that is several percent of
the frame and sits in one place is a prop; a scattered one or two percent is the
palette's own drift.

Exit code is always 0: this is a measurement, not a verdict.
"""
import argparse
import sys

import numpy as np
from PIL import Image


def load(path):
    im = Image.open(path).convert("RGB")
    return np.asarray(im).astype(float) / 255.0


def hsv(arr):
    import colorsys  # noqa: F401  (documented dependency, not used directly)
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    mx = arr.max(axis=2)
    mn = arr.min(axis=2)
    diff = mx - mn
    h = np.zeros_like(mx)
    mask = diff > 1e-6
    idx = (mx == r) & mask
    h[idx] = (60 * ((g[idx] - b[idx]) / diff[idx])) % 360
    idx = (mx == g) & mask
    h[idx] = 60 * ((b[idx] - r[idx]) / diff[idx]) + 120
    idx = (mx == b) & mask
    h[idx] = 60 * ((r[idx] - g[idx]) / diff[idx]) + 240
    s = np.where(mx > 1e-6, diff / np.maximum(mx, 1e-6), 0)
    return h, s, mx


def components(mask, min_px):
    """8-connected blob labelling without scipy."""
    h, w = mask.shape
    lab = np.zeros((h, w), dtype=np.int32)
    visited = np.zeros((h, w), dtype=bool)
    ys, xs = np.nonzero(mask)
    cur = 0
    blobs = []
    for sy, sx in zip(ys, xs):
        if visited[sy, sx]:
            continue
        cur += 1
        stack = [(sy, sx)]
        visited[sy, sx] = True
        pts = []
        while stack:
            y, x = stack.pop()
            pts.append((y, x))
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not visited[ny, nx]:
                        visited[ny, nx] = True
                        stack.append((ny, nx))
        if len(pts) >= min_px:
            ys_ = [p[0] for p in pts]
            xs_ = [p[1] for p in pts]
            blobs.append((len(pts), min(xs_), min(ys_), max(xs_), max(ys_)))
    blobs.sort(reverse=True)
    return blobs


def report(path, hue_lo=70, hue_hi=170, sat_min=0.20, val_min=0.10, min_blob=2000):
    arr = load(path)
    hh, ww = arr.shape[0], arr.shape[1]
    hue, sat, val = hsv(arr)
    mask = (hue >= hue_lo) & (hue <= hue_hi) & (sat >= sat_min) & (val >= val_min)
    total = hh * ww
    share = 100.0 * mask.sum() / total
    print(f"{path}  {ww}x{hh}")
    print(f"  green band hue {hue_lo}-{hue_hi} deg, sat >= {sat_min}, val >= {val_min}")
    print(f"  green pixels: {int(mask.sum())} ({share:.2f}% of frame)")
    blobs = components(mask, min_blob)
    if blobs:
        for n, x0, y0, x1, y1 in blobs[:3]:
            print(f"  blob {n} px ({100.0*n/total:.2f}%)  bbox x{x0}-{x1} y{y0}-{y1}")
    else:
        print(f"  no green blob of {min_blob} px or more")
    cell = 32
    best = (0, 0, 0)
    for y in range(0, hh - cell, cell):
        for x in range(0, ww - cell, cell):
            c = int(mask[y:y + cell, x:x + cell].sum())
            if c > best[0]:
                best = (c, x, y)
    if best[0]:
        print(f"  busiest {cell}x{cell} cell: {best[0]} px "
              f"({100.0*best[0]/(cell*cell):.1f}%) at ({best[1]}, {best[2]})")
    return share


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("images", nargs="+")
    ap.add_argument("--baseline", help="a frame from the same series with no green prop")
    ap.add_argument("--min-blob", type=int, default=2000)
    args = ap.parse_args()
    for p in args.images:
        report(p, min_blob=args.min_blob)
    if args.baseline:
        print("--- baseline ---")
        report(args.baseline, min_blob=args.min_blob)
    return 0


if __name__ == "__main__":
    sys.exit(main())
