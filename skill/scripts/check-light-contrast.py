#!/usr/bin/env python3
"""Does the light land on the object, or on the wall beside it?

A beat carried by light (a lamp turned onto the shelf it is meant to watch, its
counterpart turned onto bare brick; a lit lamp against a dark one) is settled by
measuring two bands, not by reading the frame. A full-frame read can MISS a lit
object as easily as it invents a defect, so the number comes first and the crop
is what explains the number.

Usage
  check-light-contrast.py IMAGE [IMAGE ...] \
      --object x0,y0,x1,y1 --wall x0,y0,x1,y1 [--frac] [--pair]

  --object / --wall  one box shared by every image: pixels (x0,y0,x1,y1 from
                     the top-left of the frame), or 0..1 fractions
  --pair             add the pair verdict: a set of frames can only argue a
                     contrast if their signs differ

Prints mean luminance and spread per region, then the signed difference
(object minus wall). Positive = the object band is the brighter one.

Run it with the image-check venv:
  /Users/paperclip/image-studio/.venv-imgcheck/bin/python \
      check-light-contrast.py a.png b.png --object .70,.42,.98,.72 --wall .05,.36,.32,.70 --pair
"""

import argparse
import sys

from PIL import Image, ImageStat


def parse_box(text):
    parts = [p.strip() for p in text.split(",")]
    if len(parts) != 4:
        raise SystemExit("box must be x0,y0,x1,y1: %r" % text)
    return [float(p) for p in parts]


def scale_box(box, size):
    w, h = size
    x0, y0, x1, y1 = box
    if max(abs(v) for v in box) <= 1.0:
        x0, x1 = x0 * w, x1 * w
        y0, y1 = y0 * h, y1 * h
    x0, x1 = sorted((int(round(x0)), int(round(x1))))
    y0, y1 = sorted((int(round(y0)), int(round(y1))))
    x0 = max(0, min(w - 1, x0))
    y0 = max(0, min(h - 1, y0))
    x1 = max(x0 + 1, min(w, x1))
    y1 = max(y0 + 1, min(h, y1))
    return (x0, y0, x1, y1)


def measure(path, box):
    with Image.open(path) as im:
        grey = im.convert("L")
        region = grey.crop(scale_box(box, im.size))
    stat = ImageStat.Stat(region)
    return round(stat.mean[0], 1), round(stat.stddev[0], 1)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Measure object-band against wall-band luminance.")
    ap.add_argument("images", nargs="+")
    ap.add_argument("--object", required=True, help="x0,y0,x1,y1 of the object's band")
    ap.add_argument("--wall", required=True, help="x0,y0,x1,y1 of the wall or ground band beside it")
    ap.add_argument("--pair", action="store_true", help="add the pair verdict across the images")
    args = ap.parse_args(argv)

    object_box = parse_box(args.object)
    wall_box = parse_box(args.wall)

    print("%-46s %8s %8s %10s" % ("frame", "object", "wall", "object-wall"))
    signs = []
    for path in args.images:
        name = path.rsplit("/", 1)[-1]
        obj_mean, obj_sd = measure(path, object_box)
        wall_mean, wall_sd = measure(path, wall_box)
        diff = round(obj_mean - wall_mean, 1)
        signs.append("+" if diff > 0 else "-")
        print("%-46s %8.1f %8.1f %+10.1f" % (name[:46], obj_mean, wall_mean, diff))
        print("%-46s %8.1f %8.1f %10s" % ("   spread (sd)", obj_sd, wall_sd, ""))

    print()
    print("signs: %s  (+ = the object band is brighter)" % " ".join(signs))
    if args.pair and len(args.images) > 1:
        if len(set(signs)) == 1:
            print("PAIR FAILS: every frame sits in the same state, so the set cannot argue a contrast.")
            print("    The frame whose purpose was the contrast is the one to hold back.")
        else:
            print("PAIR ARGUES: the frames differ in sign across the contrast.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
