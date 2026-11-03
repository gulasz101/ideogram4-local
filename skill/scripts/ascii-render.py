#!/usr/bin/env python3
"""ascii-render.py - print a pixel region as text, so a tiny prop can be read directly.

Why this exists: a zoomed vision read of a small prop is not stable. Upscaling
a 20x12 px label with LANCZOS adds moire, and the same region then reads as
"blank" on one crop and "dash-lines standing for words" on the next, at 12x
and 16x. Two reads of one crop disagreed outright.

Printing the pixels removes the model from the loop: what is on the box face is
what the text shows. It is the tie-breaker for the claims a zoomed read cannot
settle - is this label flat, or does it carry strokes; is this a shape or a
texture.

Two modes:
  shade  - every pixel, darkness mapped to a character ramp
  ink    - only pixels below a luminance threshold, so texture washes out and
           the drawn strokes are all that remain

Usage:
  ascii-render.py IMAGE.png --box 1105,595,1135,630 --mode ink
  ascii-render.py IMAGE.png --box 1105,595,1135,630 --mode shade
  ascii-render.py IMAGE.png --box 0,0,1216,832 --mode ink --cell 32

Requires Pillow + numpy:
  ~/image-studio/.venv-imgcheck/bin/python ascii-render.py ...
"""

import argparse
import os
import sys

import numpy as np
from PIL import Image

RAMP = " .:-=+*#%@"


def parse_box(text):
    parts = [int(v) for v in text.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentError("box must be x0,y0,x1,y1")
    x0, y0, x1, y1 = parts
    if x1 <= x0 or y1 <= y0:
        raise argparse.ArgumentError("box must be x1>x0 and y1>y0")
    return (x0, y0, x1, y1)


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image")
    ap.add_argument("--box", type=parse_box, help="x0,y0,x1,y1 in pixel coords")
    ap.add_argument("--mode", choices=("shade", "ink"), default="shade")
    ap.add_argument("--threshold", type=int, default=70,
                    help="ink mode: pixels darker than this count as ink (default 70)")
    ap.add_argument("--cell", type=int, default=0,
                    help="also report a per-cell ink count over this grid size")
    args = ap.parse_args()

    if not os.path.exists(args.image):
        print(f"ERROR: no such file: {args.image}", file=sys.stderr)
        return 2

    im = Image.open(args.image).convert("L")
    arr = np.asarray(im).astype(int)
    H, W = arr.shape
    if args.box:
        x0, y0, x1, y1 = args.box
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(W, x1), min(H, y1)
        if x1 <= x0 or y1 <= y0:
            print("ERROR: box is outside the image", file=sys.stderr)
            return 2
    else:
        x0, y0, x1, y1 = 0, 0, W, H
    reg = arr[y0:y1, x0:x1]
    h, w = reg.shape

    print(f"image {args.image} {W}x{H}  region x[{x0}-{x1}] y[{y0}-{y1}]  {w}x{h}px")
    if args.mode == "ink":
        print(f"  ink mode: '#' where luminance < {args.threshold}, '.' elsewhere")
    else:
        print(f"  shade mode: {RAMP[0]}=brightest, {RAMP[-1]}=darkest")
    print()

    for yy in range(h):
        if args.mode == "ink":
            line = "".join("#" if v < args.threshold else "." for v in reg[yy])
        else:
            line = "".join(RAMP[min(len(RAMP) - 1, int(v) * len(RAMP) // 256)]
                           for v in reg[yy])
        print(f"{y0 + yy:4d} |{line}|")

    print("     " + "".join(str((x0 + xx) // 10 % 10) for xx in range(w)))
    print("     " + "".join(str((x0 + xx) % 10) for xx in range(w)))

    if args.cell:
        cell = args.cell
        print(f"\n  ink per {cell}x{cell} cell (threshold {args.threshold}):")
        for gy in range(0, h - cell + 1, cell):
            row = []
            for gx in range(0, w - cell + 1, cell):
                c = int((reg[gy:gy + cell, gx:gx + cell] < args.threshold).sum())
                row.append(f"{c:5d}")
            print(f"    y{y0 + gy:4d} |" + "".join(row))
    return 0


if __name__ == "__main__":
    sys.exit(main())
