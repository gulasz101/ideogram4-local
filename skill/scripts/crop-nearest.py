#!/usr/bin/env python3
"""crop-nearest.py - cut a pixel-exact crop, and optionally its near-black ink mask.

Why this exists: `crop-probe.py` upscales with LANCZOS, which softens one-pixel ink
lines until a drawn finger separation reads as a smooth edge. A hand judged on a
LANCZOS upscale can be called a `fused mitten` when the drawing has separate fingers,
and that call is a hold-back, so the wrong upscale costs a render and a round. Use this
script for any judgement about articulation: fingers, digits, contact between a hand and
the prop it grips, thin prop outlines.

Locate the part before you cut it. Guessed pixel boxes land on the arm, the wall or the
hair and still read back as "a crop of the hand" - so cut a wide crop first, ask a reader
for the part's position as FRACTIONS of that crop, map the fractions back to original
pixels, print the box, then cut here.

Usage:
    ~/image-studio/.venv-imgcheck/bin/python crop-nearest.py <png> \
        --box x0,y0,x1,y1 --scale 8 --out <scratch>/hand.png [--ink]

`--ink` also writes `<out stem>-ink.png`: the same crop as a black-on-white mask of
everything darker than --ink-threshold (default 90 luminance), which shows the drawn
line structure without colours getting in the way of a reader.

Keep the box inside the frame and around the whole part: a crop that clips its subject
at its own edge answers nothing about that subject.
"""
import argparse
import sys

import numpy as np
from PIL import Image


def parse_box(value):
    parts = [int(p) for p in value.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("box is x0,y0,x1,y1 in pixels")
    return parts


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("image")
    ap.add_argument("--box", type=parse_box, required=True)
    ap.add_argument("--scale", type=int, default=8)
    ap.add_argument("--out", required=True)
    ap.add_argument("--ink", action="store_true")
    ap.add_argument("--ink-threshold", type=int, default=90)
    args = ap.parse_args(argv)

    im = Image.open(args.image).convert("RGB")
    width, height = im.size
    x0, y0, x1, y1 = args.box
    if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
        raise SystemExit(f"box {args.box} does not fit a {width}x{height} image")

    crop = im.crop((x0, y0, x1, y1))
    w, h = crop.size
    crop.resize((w * args.scale, h * args.scale), Image.NEAREST).save(args.out)
    print(f"{args.image} {width}x{height} -> box x[{x0}-{x1}] y[{y0}-{y1}] "
          f"{w}x{h} at {args.scale}x nearest -> {args.out}")

    if args.ink:
        lum = np.asarray(crop, dtype=np.int16).mean(axis=2)
        mask = Image.fromarray(((lum < args.ink_threshold) * 255).astype(np.uint8), "L")
        mask.resize((w * args.scale, h * args.scale), Image.NEAREST).save(
            args.out.replace(".png", "-ink.png"))
        print(f"ink mask < {args.ink_threshold} luminance -> "
              f"{args.out.replace('.png', '-ink.png')}")


if __name__ == "__main__":
    main(sys.argv[1:])
