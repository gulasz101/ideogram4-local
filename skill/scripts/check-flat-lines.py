#!/usr/bin/env python3
"""check-flat-lines.py - find horizontal and vertical FLAT LINES in a render.

Why this exists: each shipped band probe wants one particular signature.
check-flat-bands.py looks for hard-edged blocks carrying several distinct hues,
row-band.py for rows that are both flat AND saturated, check-palette-strip.py
only at the top and bottom edges, check-blank-margin.py only for the dominant
fill's own strips. A thin single-hue rule across the frame -- the near-white /
near-black / near-white lines of a drawn divider, for instance -- is none of
those, so it passes all of them while reading as a page gutter to one vision
pass and as a painted shelf lip to the next.

A row is reported when its luminance std is low AND one colour covers most of its
width. Consecutive such rows are grouped into one LINE with its row span,
thickness, fill colour, coverage and std range. The same scan runs over columns,
because the difference between a single drawn rule and a page frame that closes
on all four sides is whether the flat columns exist too.

Run it with the check venv:

    ~/image-studio/.venv-imgcheck/bin/python check-flat-lines.py IMAGE.png

Options:
    --std N       max luminance std for a line to count as flat (default 12)
    --cover F     min fraction of the line within --tol of its median (default 0.90)
    --tol N       luminance tolerance for the coverage count (default 18)
    --min-rows N  min thickness of a reported line, in px (default 2)
    --box x0,y0,x1,y1   restrict the scan to a region

The exit code is 0 whenever the scan ran: this is a detector, not a judge. A
painted shelf edge and a pasted graphic can both come back flat, so read a crop
of the rows it names before the note calls the line either one.
"""

import argparse
import sys

import numpy as np
from PIL import Image


def scan(lum, std_max, cover_min, tol, min_run):
    """Group consecutive flat lines. `lum` is 2D; each row of it is one line."""
    groups = []
    run_start = None
    run_stats = []
    for i in range(lum.shape[0]):
        line = lum[i]
        med = float(np.median(line))
        std = float(line.std())
        cover = float((np.abs(line - med) <= tol).mean())
        flat = std <= std_max and cover >= cover_min
        if flat:
            if run_start is None:
                run_start = i
                run_stats = []
            run_stats.append((i, std, cover, med))
        else:
            if run_start is not None:
                if len(run_stats) >= min_run:
                    groups.append(list(run_stats))
                run_start = None
                run_stats = []
    if run_start is not None and len(run_stats) >= min_run:
        groups.append(list(run_stats))
    return groups


def report(label, groups, rgb, total_lines, covered_word):
    if not groups:
        print(f"  {label}: no flat {covered_word} (none of {total_lines} is both "
              f"near-uniform and flat enough)")
        return False
    for g in groups:
        a, b = g[0][0], g[-1][0]
        stds = [s for _, s, _, _ in g]
        covers = [c for _, _, c, _ in g]
        band = rgb[a:b + 1] if rgb is not None else None
        colour = ""
        if band is not None and band.size:
            mean = band.reshape(-1, 3).mean(axis=0).round().astype(int)
            colour = f"  fill rgb({mean[0]},{mean[1]},{mean[2]})"
        print(f"  {label} {covered_word.upper()} {a}-{b} ({b - a + 1} px thick)"
              f"{colour}  std {min(stds):.1f}-{max(stds):.1f}"
              f"  coverage {min(covers):.0%}-{max(covers):.0%}")
    return True


def main():
    ap = argparse.ArgumentParser(description="find flat lines across a render")
    ap.add_argument("image")
    ap.add_argument("--std", type=float, default=12.0)
    ap.add_argument("--cover", type=float, default=0.90)
    ap.add_argument("--tol", type=float, default=18.0)
    ap.add_argument("--min-rows", type=int, default=2)
    ap.add_argument("--box", default=None,
                    help="x0,y0,x1,y1 subset to scan")
    args = ap.parse_args()

    im = np.array(Image.open(args.image).convert("RGB")).astype(float)
    if args.box:
        try:
            x0, y0, x1, y1 = [int(v) for v in args.box.split(",")]
        except ValueError:
            sys.exit("ERROR: --box is x0,y0,x1,y1")
        im = im[y0:y1, x0:x1]
        print(f"region x[{x0}-{x1}] y[{y0}-{y1}]")

    h, w = im.shape[0], im.shape[1]
    lum = im.mean(axis=2)
    print(f"image {args.image}  {w}x{h}")
    print(f"thresholds: std <= {args.std}, coverage >= {args.cover:.0%}, "
          f"tolerance {args.tol}, min thickness {args.min_rows} px")

    rows = scan(lum, args.std, args.cover, args.tol, args.min_rows)
    cols = scan(lum.T, args.std, args.cover, args.tol, args.min_rows)

    print("[ROWS]")
    has_rows = report("LINE", rows, im, h, "rows")
    print("[COLUMNS]")
    has_cols = report("LINE", cols, None, w, "columns")

    print("[VERDICT]")
    if has_rows and not has_cols:
        print("  flat horizontal line(s) only, no flat column: one drawn rule or "
              "band, NOT a page frame that closes on all four sides.")
    elif has_cols and not has_rows:
        print("  flat vertical line(s) only: a side panel or rule, no horizontal one.")
    elif has_rows and has_cols:
        print("  flat lines on BOTH axes: read a crop before deciding - a page frame "
              "or gutter looks like this, and so does a painted shelf against a wall.")
    else:
        print("  no flat lines: no thin drawn rule on either axis here.")
    print("  This is a detector, not a judge: read the rows it names before the note "
          "calls the line a graphic rule or a painted edge.")


if __name__ == "__main__":
    main()
