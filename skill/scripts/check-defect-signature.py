#!/usr/bin/env python3
"""Measure the signature of a pasted-overlay defect, against a baseline.

`check-flat-bands.py` answers "is there a band-shaped region", and on a
hand-painted cel-shaded scene the answer is yes for almost every picture -
including the ones Wojtek approved. It is a detector, not a judge
(engine-pitfalls #66). What separates a real overlay from the background is
the *signature* of the defect, measured as a number and compared with a
known-good frame from the same series.

Three signatures cover the blue-UI-panel family that broke rounds 1 and 2
of the `context-autofit-header` slot:

  1. BLUE   - pixels within tol 90 (sum of channel differences) of RGB
               40,90,200. A pasted UI panel is hundreds of thousands of
               these. Some blue is normal in this art style.
  2. WHITE  - near-white (every channel >= 255 - 26) connected components of
               400 px or more, 4-neighbour. A pasted panel or banner reads
               as a big white block. The check venv has no scipy, so the
               components are labelled with a union-find over runs.
  3. BAND   - rows that are both flat (few colour runs) and saturated
               (mean channel spread above the frame's median), which is a
               horizontal swatch strip (engine-pitfalls #34, #34a).

Run it on the candidate AND on a known-good image from the same series. The
question is never "is the number zero" but "is the candidate's signature at
zero while the known-bad frame's is not".

Usage:
    python3 check-defect-signature.py IMAGE.png [KNOWN_GOOD.png ...]
    python3 check-defect-signature.py r3.png --baseline plate-mountain.png

Exit codes:
    0 = measured, no verdict
    3 = file not found, not an image, or missing Pillow/numpy

Run with the check venv: ~/image-studio/.venv-imgcheck/bin/python
"""

import argparse
import sys
from pathlib import Path

try:
    from PIL import Image
    import numpy as np
except ImportError:
    print("ERROR: Pillow and numpy required.")
    sys.exit(3)

BLUE_RGB = np.array([40, 90, 200])
BLUE_TOL = 90
WHITE_TOL = 26
MIN_WHITE_BLOB = 400
RUN_BREAK = 12        # channel-sum difference that starts a new colour run
SAT_FACTOR = 1.35     # row saturation above this multiple of the median
FLAT_FACTOR = 0.35    # row run count below this multiple of the median


def blue_pixels(arr):
    """Pixels close to the pasted-UI-panel blue."""
    d = np.abs(arr - BLUE_RGB).sum(axis=2)
    return int((d < BLUE_TOL).sum())


def label_blobs(mask):
    """4-neighbour connected components. Returns the list of component sizes."""
    h, w = mask.shape
    labels = np.zeros((h, w), dtype=np.int32)
    parent = [0]

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            if ra < rb:
                parent[rb] = ra
            else:
                parent[ra] = rb

    nxt = 1
    for y in range(h):
        row = mask[y]
        for x in range(w):
            if not row[x]:
                continue
            up = labels[y - 1, x] if y > 0 and row[x] and mask[y - 1, x] else 0
            left = labels[y, x - 1] if x > 0 and row[x - 1] else 0
            if up and left:
                labels[y, x] = min(up, left)
                union(up, left)
            elif up:
                labels[y, x] = up
            elif left:
                labels[y, x] = left
            else:
                labels[y, x] = nxt
                parent.append(nxt)
                nxt += 1
    remap = {}
    sizes = {}
    ys, xs = np.nonzero(labels)
    for y, x in zip(ys, xs):
        r = find(labels[y, x])
        if r not in remap:
            remap[r] = len(remap) + 1
            sizes[remap[r]] = 0
        sizes[remap[r]] += 1
    return list(sizes.values())


def white_blobs(arr, min_blob=MIN_WHITE_BLOB):
    """Near-white flat components of min_blob px or more."""
    mask = arr.min(axis=2) >= 255 - WHITE_TOL
    if not mask.any():
        return 0, 0
    sizes = label_blobs(mask)
    big = sorted((s for s in sizes if s >= min_blob), reverse=True)
    return len(big), int(mask.sum())


def flat_saturated_band_rows(arr):
    """Longest run of consecutive rows that are flat and saturated."""
    h, w, _ = arr.shape
    runs = np.empty(h, dtype=np.int64)
    sat = np.empty(h, dtype=float)
    for y in range(h):
        row = arr[y]
        diffs = np.abs(np.diff(row, axis=0)).sum(axis=1)
        runs[y] = int((diffs > RUN_BREAK).sum()) + 1
        sat[y] = float(np.mean(row.max(axis=1) - row.min(axis=1)))
    med_runs = float(np.median(runs))
    med_sat = float(np.median(sat))
    band = [y for y in range(h)
            if runs[y] <= max(6, med_runs * FLAT_FACTOR)
            and sat[y] > med_sat * SAT_FACTOR]
    best = cur = 0
    prev = -2
    for y in band:
        cur = cur + 1 if y == prev + 1 else 1
        best = max(best, cur)
        prev = y
    return best


def measure(path):
    arr = np.asarray(Image.open(path).convert("RGB")).astype(int)
    h, w, _ = arr.shape
    blue = blue_pixels(arr)
    n_white, white_px = white_blobs(arr)
    band = flat_saturated_band_rows(arr)
    return {"name": Path(path).name, "size": f"{w}x{h}", "blue": blue,
            "white_blobs": n_white, "white_px": white_px, "band_rows": band}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("image", help="the candidate render")
    ap.add_argument("baseline", nargs="*",
                    help="known-good or known-bad frames from the same series")
    ap.add_argument("--min-blob", type=int, default=MIN_WHITE_BLOB)
    args = ap.parse_args()

    rows = []
    for path in [args.image] + args.baseline:
        p = Path(path)
        if not p.exists():
            print(f"ERROR: File not found: {path}")
            sys.exit(3)
        try:
            Image.open(p)
        except Exception:
            print(f"ERROR: Not an image: {path}")
            sys.exit(3)
        rows.append(measure(path))

    print(f"{'image':<50} {'size':<10} {'blue_px':>9} {'white_blobs':>12} "
          f"{'band_rows':>10}")
    for r in rows:
        print(f"{r['name']:<50} {r['size']:<10} {r['blue']:>9} "
              f"{r['white_blobs']:>12} {r['band_rows']:>10}")
    print("\nThe candidate is clean when its signature is at zero and the "
          "known-bad frame's is not.\nA nonzero number is only a finding when "
          "the same measurement on a picture Wojtek\napproved is much smaller.")


if __name__ == "__main__":
    main()
