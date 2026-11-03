#!/usr/bin/env python3
"""Detect panel gutters: a grid of flat separator lines inside one frame.

An ideogram/flux render that comes back as several panels looks like a normal
illustration to every margin probe: check-grey-bars sees no grey bar, the content
bbox is the whole frame, and check-palette-strip may see nothing at an edge. The
one hard tell is a run of consecutive rows (or columns) that are flat in the
SAME fill, sitting in the interior of the frame: that is a gutter.

    python3 check-panel-gutters.py <png> [--min-run 6]

Prints every interior flat row/column run and a verdict. A frame with a run of
--min-run (default 6) or more flat rows AND a run of --min-run or more flat
columns is a panelled frame - a contact sheet of variants, or a comic page of
bordered panels on a pale canvas, and the read that follows says which. A single
axis alone is usually a painted edge (a table edge, a floor line) and is
reported as a note, not a verdict.
"""
import argparse
import sys

try:
    import numpy as np
    from PIL import Image
except ImportError:
    sys.exit("ERROR: Pillow and numpy required (~/image-studio/.venv-imgcheck/bin/python)")


def flat_runs(mat, axis, tol=6, colour_tol=14):
    """Return [(start, end, colour)] for runs of flat rows/cols.

    Two consecutive flat lines join one run when their fills agree to within
    `colour_tol` per channel: a gutter or a painted band is printed with a
    little grain and gradient, so an exact-colour test splits an 11 px gutter
    into eleven one-pixel runs and the grid stays invisible.
    """
    runs = []
    cur = None
    n = mat.shape[axis]
    for i in range(n):
        line = mat[i] if axis == 0 else mat[:, i]
        col = line.mean(axis=0)
        spread = np.abs(line - col).mean()
        if spread < tol:
            if cur is not None and np.abs(col - cur["mean"]).max() <= colour_tol:
                cur["end"] = i
                cur["mean"] = (cur["mean"] + col) / 2.0
                continue
            if cur:
                runs.append(cur)
            cur = {"start": i, "end": i, "mean": col.copy()}
        else:
            if cur:
                runs.append(cur)
            cur = None
    if cur:
        runs.append(cur)
    return runs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("png")
    ap.add_argument("--min-run", type=int, default=6)
    ap.add_argument("--tol", type=float, default=6.0)
    a = ap.parse_args()

    im = Image.open(a.png).convert("RGB")
    arr = np.asarray(im).astype(int)
    h, w, _ = arr.shape

    long_rows, long_cols = [], []
    for r in flat_runs(arr, 0, a.tol):
        length = r["end"] - r["start"] + 1
        # interior only: an edge band is check-blank-margin's job
        if length >= a.min_run and r["start"] > 0 and r["end"] < h - 1:
            long_rows.append((r["start"], r["end"], length, tuple(int(c) for c in r["mean"])))
    for c in flat_runs(arr, 1, a.tol):
        length = c["end"] - c["start"] + 1
        if length >= a.min_run and c["start"] > 0 and c["end"] < w - 1:
            long_cols.append((c["start"], c["end"], length, tuple(int(v) for v in c["mean"])))

    print(f"{a.png}: {w}x{h}, min-run {a.min_run} px at tol {a.tol}")
    for start, end, length, key in long_rows:
        print(f"  flat ROW run y{start}-{end} ({length} px) fill {key}")
    for start, end, length, key in long_cols:
        print(f"  flat COL run x{start}-{end} ({length} px) fill {key}")

    if long_rows and long_cols:
        print("PANELLED FRAME: flat gutter runs on both axes inside the frame -> a contact sheet or a comic page, not one scene; hold back, re-render as one scene")
        return 1
    if long_rows or long_cols:
        print("NOTE: one axis carries a flat run. A gutter grid needs both axes; confirm on a crop before calling it a panel edge.")
        return 0
    print("no interior gutter runs: reads as one continuous frame")
    return 0


if __name__ == "__main__":
    sys.exit(main())
