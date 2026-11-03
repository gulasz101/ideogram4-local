#!/usr/bin/env python3
"""Emit a zoomed crop for counting hands or repeated objects in a render.

Usage:
  python3 crop-for-count.py IMAGE --size
  python3 crop-for-count.py IMAGE --box 0.55,0.24,1,1 --scale 2.5 --out /tmp/fig.png
  python3 crop-for-count.py IMAGE --box 420,120,1216,760 --scale 2 --out /tmp/wall.png --grid 8

--box accepts either fractions of width/height (all four values <= 1) or pixels.
--grid N overlays thin N x N rules to keep the eye on one object at a time (off by default:
rules over a photo-grain render can hide a thumb line).

Why: a full-frame vision read over-counts hands and drifts on repeated objects. A 2-3x crop of
one row or one figure is the measurement; see references/counting-checks.md.
"""
import argparse
import sys

from PIL import Image, ImageDraw


def parse_box(raw, w, h):
    parts = [float(p) for p in raw.split(",")]
    if len(parts) != 4:
        sys.exit("--box needs four values: x1,y1,x2,y2")
    if all(p <= 1.0 for p in parts):
        parts = [parts[0] * w, parts[1] * h, parts[2] * w, parts[3] * h]
    x1, y1, x2, y2 = [int(round(p)) for p in parts]
    x1, x2 = sorted((max(0, min(x1, w)), max(0, min(x2, w))))
    y1, y2 = sorted((max(0, min(y1, h)), max(0, min(y2, h))))
    if x2 - x1 < 20 or y2 - y1 < 20:
        sys.exit(f"box {x1},{y1},{x2},{y2} is too small to read")
    return x1, y1, x2, y2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--box", default=None, help="x1,y1,x2,y2 as fractions (<=1) or pixels")
    ap.add_argument("--scale", type=float, default=2.5)
    ap.add_argument("--out", default=None)
    ap.add_argument("--grid", type=int, default=0)
    ap.add_argument("--size", action="store_true", help="print the image size and exit")
    a = ap.parse_args()

    im = Image.open(a.image).convert("RGB")
    print(f"source {im.width}x{im.height}")
    if a.size:
        return
    if not a.box:
        sys.exit("--box is required unless --size is used")

    x1, y1, x2, y2 = parse_box(a.box, im.width, im.height)
    crop = im.crop((x1, y1, x2, y2))
    crop = crop.resize(
        (max(1, int(crop.width * a.scale)), max(1, int(crop.height * a.scale))),
        Image.LANCZOS,
    )
    if a.grid > 0:
        d = ImageDraw.Draw(crop)
        for i in range(1, a.grid):
            d.line([(crop.width * i / a.grid, 0), (crop.width * i / a.grid, crop.height)], fill=(0, 200, 255), width=2)
            d.line([(0, crop.height * i / a.grid), (crop.width, crop.height * i / a.grid)], fill=(0, 200, 255), width=2)

    out = a.out or (a.image.rsplit(".", 1)[0] + f"_crop_x{a.scale:g}.png")
    crop.save(out)
    print(f"box {x1},{y1},{x2},{y2} -> {crop.width}x{crop.height} at {a.scale:g}x")
    print(out)


if __name__ == "__main__":
    main()
