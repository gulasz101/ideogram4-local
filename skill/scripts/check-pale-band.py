#!/usr/bin/env python3
"""check-pale-band.py - settle a pale-band / fill-share flag numerically.

Requires Pillow + numpy. Run with the check venv:

    ~/image-studio/.venv-imgcheck/bin/python check-pale-band.py IMAGE.png --columns 912,1216

Why this exists: check-blank-margin.py reports a fill share and any row or
column band at >= 80% fill, and a painted pale wall, a paper-cream sky or a
white backdrop answers it with no defect present. A vision read of the same
band is not a tie-breaker -- two reads of one corner can return "blank paper
margin outside a panel border" and "full-bleed painted wall" and neither is
measurement. Ink is countable: a painted band carries dark pixels from
contours and hatching, a band with no drawing does not.

Read the output as a hint, and the numbers as the finding:
  dark% per column >= 3 with a region std well above 40  -> painted, the flag is scenery
  dark% ~0 with std under ~10                            -> a flat fill with nothing drawn on it

Examples
  # the right 300 px of a 1216-wide frame, per-column dark share
  check-pale-band.py IMAGE.png --columns 912,1216

  # the same over a row band instead of a column band
  check-pale-band.py IMAGE.png --rows 0,140

  # whole-frame baseline, to compare against the band
  check-pale-band.py IMAGE.png
"""

import argparse
import sys

import numpy as np
from PIL import Image

DARK = 120          # luminance below this counts as ink
STEP = 20           # sample every Nth column/row in the profile


def load(path):
    im = Image.open(path).convert("RGB")
    return np.asarray(im).astype(int)


def pct_dark(lum):
    return float((lum < DARK).mean() * 100.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--columns", help="x0,x1 column band to profile")
    ap.add_argument("--rows", help="y0,y1 row band to profile")
    ap.add_argument("--step", type=int, default=STEP)
    args = ap.parse_args()

    a = load(args.image)
    H, W, _ = a.shape
    lum = a.mean(axis=2)
    print(f"image {args.image} {W}x{H}")

    print(f"whole frame: mean {lum.mean():.1f}  std {lum.std():.1f}  dark% {pct_dark(lum):.2f}")

    if args.columns:
        x0, x1 = (int(v) for v in args.columns.split(","))
        x1 = min(x1, W)
        band = lum[:, x0:x1]
        print(f"band x[{x0}-{x1}] ({x1 - x0} px): mean {band.mean():.1f}  std {band.std():.1f}  dark% {pct_dark(band):.2f}")
        profile = []
        for x in range(x0, x1, args.step):
            col = lum[:, x:x + 1]
            profile.append((x, round(pct_dark(col), 1)))
        print("dark% per column:", profile)
        inked = sum(1 for _, v in profile if v >= 3.0)
        print(f"columns with >= 3% dark pixels: {inked} of {len(profile)}")

    if args.rows:
        y0, y1 = (int(v) for v in args.rows.split(","))
        y1 = min(y1, H)
        band = lum[y0:y1, :]
        print(f"band y[{y0}-{y1}] ({y1 - y0} px): mean {band.mean():.1f}  std {band.std():.1f}  dark% {pct_dark(band):.2f}")
        profile = []
        for y in range(y0, y1, args.step):
            row = lum[y:y + 1, :]
            profile.append((y, round(pct_dark(row), 1)))
        print("dark% per row:", profile)
        inked = sum(1 for _, v in profile if v >= 3.0)
        print(f"rows with >= 3% dark pixels: {inked} of {len(profile)}")

    print("verdict is the numbers: ink in the band means the fill flag was scenery, "
          "a flat near-zero-dark band means nothing is drawn there.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
