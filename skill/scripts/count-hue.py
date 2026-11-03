#!/usr/bin/env python3
"""Count pixels inside a hue/saturation/value window, on one or many images.

The comparative proof that a rejected colour artefact is gone: run it on the
candidate and on the render he rejected, with the same window, and put both
numbers on the card ("0 px against 5836 px") instead of "the blob is gone".

Unlike the other check scripts in this directory this one takes MORE THAN ONE
image path on purpose: the comparison is the measurement.

Usage:
    ~/image-studio/.venv-imgcheck/bin/python count-hue.py \
        --hue 33-58 --sat 0.55 --val 0.45 candidate.png rejected.png

The defaults are the amber/gold window that the "yellow/black blob growing out
of his back" and a pasted gold badge both land in. Widen or move --hue for a
red or green artefact, and state the window in the check note: a tighter mask
reports a smaller number on the same file, and both renders have to be measured
with the same one.

Exit codes: 0 every image measured, 2 bad arguments, 3 an image could not be
read.
"""
import argparse
import sys

try:
    from PIL import Image
    import numpy as np
except ImportError:  # pragma: no cover
    sys.exit(
        "Pillow and numpy required: run with "
        "~/image-studio/.venv-imgcheck/bin/python"
    )


def hue_range(text):
    lo, _, hi = text.partition("-")
    try:
        lo, hi = float(lo), float(hi)
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected LO-HI, got {text!r}")
    if not (0 <= lo <= 360 and 0 <= hi <= 360):
        raise argparse.ArgumentTypeError("hue is 0-360 degrees")
    return lo, hi


def hsv_arrays(img):
    """Return (hue in degrees, saturation, value) as float arrays in 0..1."""
    a = np.asarray(img.convert("RGB"), dtype=np.float32) / 255.0
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    mx = a.max(axis=2)
    mn = a.min(axis=2)
    diff = mx - mn
    safe = np.maximum(diff, 1e-6)
    sat = np.where(mx > 0, diff / np.maximum(mx, 1e-6), 0.0)

    hue = np.zeros_like(mx)
    chroma = diff > 1e-6
    red = chroma & (mx == r)
    green = chroma & (mx == g) & ~(mx == r)
    blue = chroma & (mx == b) & ~(mx == r) & ~(mx == g)
    hue[red] = (60.0 * ((g - b) / safe))[red] % 360.0
    hue[green] = (60.0 * ((b - r) / safe) + 120.0)[green] % 360.0
    hue[blue] = (60.0 * ((r - g) / safe) + 240.0)[blue] % 360.0
    return hue, sat, mx


def count(path, lo, hi, sat_floor, val_floor):
    img = Image.open(path)
    width, height = img.size
    hue, sat, val = hsv_arrays(img)
    if lo <= hi:
        in_hue = (hue >= lo) & (hue <= hi)
    else:  # window wraps the 0/360 seam
        in_hue = (hue >= lo) | (hue <= hi)
    mask = in_hue & (sat >= sat_floor) & (val >= val_floor)
    px = int(mask.sum())
    total = width * height
    return width, height, px, 100.0 * px / total if total else 0.0


def main():
    parser = argparse.ArgumentParser(
        description="Count pixels in a hue/saturation/value window, per image."
    )
    parser.add_argument("--hue", type=hue_range, default=(33.0, 58.0),
                        metavar="LO-HI", help="hue window in degrees (default 33-58, amber)")
    parser.add_argument("--sat", type=float, default=0.55,
                        metavar="F", help="saturation floor 0-1 (default 0.55)")
    parser.add_argument("--val", type=float, default=0.45,
                        metavar="F", help="value floor 0-1 (default 0.45)")
    parser.add_argument("images", nargs="+", help="one image path per render compared")
    args = parser.parse_args()

    lo, hi = args.hue
    failed = False
    for path in args.images:
        try:
            width, height, px, pct = count(path, lo, hi, args.sat, args.val)
        except Exception as exc:  # a missing or unreadable file is not a zero
            print(f"{path}  ERROR {exc}")
            failed = True
            continue
        print(
            f"{path}  {width}x{height}  "
            f"hue={lo:g}-{hi:g} sat>={args.sat:g} val>={args.val:g}  "
            f"px={px} ({pct:.2f}%)"
        )
        if len(args.images) > 1:
            print("  (both renders must be measured with this same window)")
    return 3 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
