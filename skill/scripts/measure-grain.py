#!/usr/bin/env python3
"""measure-grain.py - print a grain number for one or more PNGs.

Why this exists: a vision read and a brief disagree about film grain often
("grain present" against "flat digital cartoon"), and neither is a
measurement. High-frequency energy in the FLATTEST parts of the frame is:
film grain raises it, smooth digital fills do not, and edges and props do not
disturb it because the flattest fifth of the tiles is what gets averaged.

Usage:
    ~/image-studio/.venv-imgcheck/bin/python measure-grain.py A.png [B.png ...]

It prints, per file, `flat` (mean |laplacian| over the flattest fifth of
32x32 tiles), `flat_med` (the same tiles' median) and `overall` (the laplacian
std across the whole frame, which edges dominate and grain barely moves). With
several files it also prints the ratio to the first, so a card can say
`6.1 against the ideogram's 7.5` instead of "grain looks lighter".

Read it as a comparison, never as a pass/fail: a cel render with clean inking
legitimately sits lower than a photo-backed one, and the number that decides
anything is the same number on two files measured with the same mask.

The system python has no numpy or Pillow (PEP 668), so run it with the studio
venv: ~/image-studio/.venv-imgcheck/bin/python.
"""
import sys

import numpy as np
from PIL import Image

TILE = 32


def measure(path):
    gray = np.asarray(Image.open(path).convert("L"), dtype=np.float32)
    lap = (gray[1:-1, 1:-1] * 4
           - gray[:-2, 1:-1] - gray[2:, 1:-1]
           - gray[1:-1, :-2] - gray[1:-1, 2:])
    h, w = lap.shape
    tiles = []
    for y in range(0, h - TILE + 1, TILE):
        for x in range(0, w - TILE + 1, TILE):
            t = lap[y:y + TILE, x:x + TILE]
            tiles.append((float(t.std()), float(np.abs(t).mean())))
    if not tiles:
        raise SystemExit(f"{path}: image is smaller than one {TILE}x{TILE} tile")
    tiles.sort()
    flat = tiles[:max(1, len(tiles) // 5)]
    return {
        "path": path,
        "size": f"{w + 2}x{h + 2}",
        "flat": float(np.mean([f[1] for f in flat])),
        "flat_med": float(np.median([f[1] for f in flat])),
        "overall": float(lap.std()),
    }


def main(argv):
    if not argv:
        raise SystemExit(__doc__)
    rows = [measure(p) for p in argv]
    for r in rows:
        print(f"{r['flat']:7.2f} flat  {r['flat_med']:7.2f} flat_med  "
              f"{r['overall']:7.2f} overall  {r['size']}  {r['path']}")
    if len(rows) > 1:
        base = rows[0]["flat"] or 1.0
        for r in rows[1:]:
            print(f"  {r['path']}: flat is {r['flat'] / base:.2f}x the first file")


if __name__ == "__main__":
    main(sys.argv[1:])
