#!python3
"""Print a render's frame layout as a coarse colour map of text.

Why this exists: the vision tool can rate-limit or go down mid-card, and a
run still has to say what the frame holds before it writes a check note. This
prints an approximate painter's thumbnail - one letter per cell, classified by
mean colour - so the layout, the big shapes and where a flat block sits can be
read straight off the terminal with no model in the loop.

It is a layout view, NOT a defect judge. A flat fill is normal in cel-shaded
art; use crop-probe.py for a prop and check-flat-bands.py for a band.

Usage:
  frame-map.py IMAGE.png                # 32 px cells
  frame-map.py IMAGE.png --cell 16      # finer, noisier
  frame-map.py IMAGE.png --box 400,300,900,700
  frame-map.py A.png B.png --cell 48    # several frames, shorter view

Requires Pillow + numpy:
  ~/image-studio/.venv-imgcheck/bin/python frame-map.py ...
"""
import argparse

import numpy as np
from PIL import Image

# First match wins, so the saturated colours are tested before the greys.
RULES = [
    ('G', lambda r, g, b: g > r + 20 and g > b + 20 and g > 80),
    ('B', lambda r, g, b: b > r + 25 and b > g + 15 and b > 90),
    ('Y', lambda r, g, b: r > 150 and g > 140 and b < 110),
    ('O', lambda r, g, b: r > 150 and 70 < g < 150 and b < 90),
    ('R', lambda r, g, b: r > 120 and g < 80 and b < 80),
    ('P', lambda r, g, b: r > 90 and b > 90 and g < 90),
    ('#', lambda r, g, b: r < 60 and g < 60 and b < 60),
    ('+', lambda r, g, b: r < 110 and g < 110 and b < 110),
    ('.', lambda r, g, b: r > 200 and g > 200 and b > 200),
    ('-', lambda r, g, b: True),
]

KEY = ('G green  B blue  Y yellow  O orange  R red  P purple  ' '# near-black  + dark grey  . near-white  - mid tone')


def classify(block):
    r, g, b = block.reshape(-1, 3).mean(axis=0)
    for char, test in RULES:
        if test(r, g, b):
            return char
    return '-'


def draw(path, cell, box):
    im = np.array(Image.open(path).convert('RGB'))
    h, w, _ = im.shape
    x0, y0, x1, y1 = box if box else (0, 0, w, h)
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(w, x1), min(h, y1)
    print('%s  %dx%d  cell=%d  region x[%d-%d] y[%d-%d]'
          % (path, w, h, cell, x0, x1, y0, y1))
    cols = list(range(x0, x1, cell))
    # Column ruler: one digit per ten cells, so a coordinate can be read off.
    print('      ' + ''.join(str(((x - x0) // cell // 5) % 10) for x in cols))
    for y in range(y0, y1, cell):
        line = ''.join(classify(im[y:y + cell, x:x + cell]) for x in cols)
        print('%5d %s' % (y, line))
    print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('images', nargs='+')
    ap.add_argument('--cell', type=int, default=32)
    ap.add_argument('--box', default=None,
                    help='x0,y0,x1,y1 in pixel coords')
    args = ap.parse_args()

    box = None
    if args.box:
        box = tuple(int(v) for v in args.box.split(','))
        if len(box) != 4:
            raise SystemExit('--box needs four numbers: x0,y0,x1,y1')

    print(KEY)
    for path in args.images:
        draw(path, args.cell, box)


if __name__ == '__main__':
    main()
