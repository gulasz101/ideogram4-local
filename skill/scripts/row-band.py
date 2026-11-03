#!/usr/bin/env python3
"""Whole-frame row measurement for a horizontal swatch band.

The shipped check-palette-strip.py only looks at the top and bottom edge. A
swatch bar can cross the middle of the frame, where that script cannot see
it (engine-pitfalls #34, #34a). This measures every row of the frame and
reports any row that is flat (few colour runs) and saturated (mean channel
spread above the frame's median), with the run count and the wide blocks.

`check-defect-signature.py` reports the same band count next to the blue and
white signatures and against a baseline. Use this one when you want the block
layout of a band.

Usage: row-band.py IMAGE.png

Run with the check venv: ~/image-studio/.venv-imgcheck/bin/python
"""

import sys

import numpy as np
from PIL import Image

RUN_BREAK = 12        # channel-sum difference that starts a new colour run
SAT_FACTOR = 1.35     # row saturation above this multiple of the median
FLAT_FACTOR = 0.35    # row run count below this multiple of the median
MIN_BLOCK_PX = 20     # a block narrower than this is not worth printing


def main(path):
    arr = np.asarray(Image.open(path).convert("RGB")).astype(int)
    H, W, _ = arr.shape
    print(f"image {path} {W}x{H}")

    runs, sat = [], []
    for y in range(H):
        row = arr[y]
        diffs = np.abs(np.diff(row, axis=0)).sum(axis=1)
        runs.append(int((diffs > RUN_BREAK).sum()) + 1)
        sat.append(float(np.mean(row.max(axis=1) - row.min(axis=1))))

    runs = np.array(runs)
    sat = np.array(sat)
    med_runs = float(np.median(runs))
    med_sat = float(np.median(sat))
    print(f"control: median runs/row {med_runs:.0f}, median saturation {med_sat:.1f}")

    band_rows = [y for y in range(H)
                 if runs[y] <= max(6, med_runs * FLAT_FACTOR)
                 and sat[y] > med_sat * SAT_FACTOR]
    print(f"rows that are both flat and saturated: {len(band_rows)}")

    best = cur = 0
    best_end = cur_end = -1
    prev = -2
    for y in band_rows:
        if y == prev + 1:
            cur += 1
        else:
            cur = 1
        if cur > best:
            best, best_end = cur, y
        prev = y
    print(f"longest consecutive flat+saturated band: {best} rows"
          + (f" (y {best_end - best + 1}-{best_end})" if best else ""))
    if best >= 6:
        print("  -> a horizontal flat band of that height is a swatch strip")
        for y in range(best_end - best + 1, best_end + 1, max(1, best // 4)):
            row = arr[y]
            blocks = []
            start = 0
            for x in range(1, W):
                if abs(int(row[x].sum()) - int(row[x - 1].sum())) > RUN_BREAK:
                    if x - start > MIN_BLOCK_PX:
                        blocks.append((start, x - 1, tuple(row[(start + x) // 2])))
                    start = x
            if W - start > MIN_BLOCK_PX:
                blocks.append((start, W - 1, tuple(row[(start + W) // 2])))
            print(f"  row {y}: {len(blocks)} wide blocks: {blocks[:8]}")
    else:
        print("  -> no swatch strip anywhere in the frame")
    print("A painted scene can trip this. Compare the number with a picture "
          "Wojtek approved\nfrom the same series before calling it a defect "
          "(engine-pitfall #66).")


if __name__ == "__main__":
    main(sys.argv[1])
