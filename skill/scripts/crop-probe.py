#!/usr/bin/env python3
"""crop-probe.py - crop and pixel-probe an image for the image-studio self-check.

Requires Pillow + numpy. Run it with the check venv:

    ~/image-studio/.venv-imgcheck/bin/python crop-probe.py IMAGE.png --box ...

Why this exists: a `vision_analyze` region crop is not a measurement. The
region parameter can resolve to different content between two reads of the
same box, so two reads of one PNG can contradict each other. The reliable
tie-breaker is a crop written to disk and analysed as a file, plus a numeric
count for claims that are countable.

Examples
  # 4x upscaled crop of a region -> /tmp/clock.png
  crop-probe.py IMAGE.png --box 210,250,410,450 --scale 4 --out /tmp/clock.png

  # largest blobs of a colour and their bounding boxes
  crop-probe.py IMAGE.png --find 245,240,225 --tol 55

  # does colour A really overlap colour B in that region, or sit behind it?
  crop-probe.py IMAGE.png --box 210,250,410,450 --overlap 106,102,106 200,160,60
"""

import argparse
import os
import sys

import numpy as np
from PIL import Image

MAX_MASK_FOR_BLOBS = 300000  # above this, labelling is too slow to be useful


def load(path):
    im = Image.open(path).convert("RGB")
    return im, np.asarray(im).astype(int)


def color_mask(arr, rgb, tol):
    """True where the pixel is within a summed absolute distance of rgb."""
    return np.abs(arr - np.array(rgb, dtype=int)).sum(axis=2) < tol


def components(mask, min_px):
    """Label 8-connected blobs of a boolean mask; return (labels, count)."""
    h, w = mask.shape
    lab = np.zeros((h, w), dtype=np.int32)
    visited = np.zeros((h, w), dtype=bool)
    ys, xs = np.nonzero(mask)
    cur = 0
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
            p = np.array(pts)
            lab[p[:, 0], p[:, 1]] = cur
    return lab, cur


def parse_rgb(text):
    parts = [int(p) for p in text.split(",")]
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("colour must be r,g,b")
    return parts


def parse_box(text):
    parts = [int(p) for p in text.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("box must be x0,y0,x1,y1")
    x0, y0, x1, y1 = parts
    if x1 <= x0 or y1 <= y0:
        raise argparse.ArgumentTypeError("box must be x1>x0 and y1>y0")
    return (x0, y0, x1, y1)


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image")
    ap.add_argument("--box", type=parse_box, help="x0,y0,x1,y1 in pixel coords")
    ap.add_argument("--scale", type=float, default=4.0, help="upscale factor for --out")
    ap.add_argument("--out", help="write the crop here")
    ap.add_argument("--find", type=parse_rgb, help="r,g,b of a colour to locate")
    ap.add_argument("--tol", type=int, default=40, help="summed absolute colour tolerance")
    ap.add_argument("--min-px", type=int, default=400, help="smallest blob reported by --find")
    ap.add_argument("--overlap", nargs=2, type=parse_rgb, metavar=("A", "B"),
                    help="two r,g,b colours to cross-count in the region")
    args = ap.parse_args()

    if not os.path.exists(args.image):
        print(f"ERROR: no such image: {args.image}", file=sys.stderr)
        return 2

    im, arr = load(args.image)
    H, W = arr.shape[0], arr.shape[1]
    print(f"image {args.image} {W}x{H}")

    region = arr
    if args.box:
        x0, y0, x1, y1 = args.box
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(W, x1), min(H, y1)
        if x1 <= x0 or y1 <= y0:
            print("ERROR: box is outside the image", file=sys.stderr)
            return 2
        print(f"region x[{x0}-{x1}] y[{y0}-{y1}]")
        region = arr[y0:y1, x0:x1]

    if args.find:
        mask = color_mask(region, args.find, args.tol)
        total = int(mask.sum())
        print(f"colour {args.find} tol={args.tol}: {total} px in region")
        if total > MAX_MASK_FOR_BLOBS:
            print(f"WARNING: mask too large to label ({total} px); narrow --box or raise --tol")
        else:
            lab, n = components(mask, args.min_px)
            blobs = []
            for i in range(1, n + 1):
                ys, xs = np.nonzero(lab == i)
                if len(ys) == 0:
                    continue
                blobs.append((len(ys), (int(xs.min()), int(ys.min()),
                                        int(xs.max()), int(ys.max()))))
            blobs.sort(reverse=True)
            print(f"blobs >= {args.min_px} px: {len(blobs)}")
            for cnt, box in blobs[:8]:
                if args.box:
                    box = (box[0] + args.box[0], box[1] + args.box[1],
                           box[2] + args.box[0], box[3] + args.box[1])
                print(f"  {cnt:7d} px  bbox={box}")

    if args.overlap:
        a, b = args.overlap
        ma = color_mask(region, a, args.tol)
        mb = color_mask(region, b, args.tol)
        inter = int((ma & mb).sum())
        print(f"overlap A={a} B={b}: A={int(ma.sum())} B={int(mb.sum())} A&B={inter}")
        if inter == 0:
            print("  -> B does not overlap A: B is behind or beside A, not draped over it")
        else:
            print(f"  -> {inter} px of B sit on top of A")

    if args.out:
        if not args.box:
            print("ERROR: --out needs --box", file=sys.stderr)
            return 2
        x0, y0, x1, y1 = args.box
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(W, x1), min(H, y1)
        w, h = x1 - x0, y1 - y0
        crop = im.crop((x0, y0, x1, y1)).resize(
            (max(1, int(w * args.scale)), max(1, int(h * args.scale))), Image.LANCZOS)
        crop.save(args.out)
        print(f"wrote {args.out} ({crop.size[0]}x{crop.size[1]}, {args.scale}x)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
