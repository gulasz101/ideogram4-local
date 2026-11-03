#!/usr/bin/env python3
"""check-grain.py - measure the film-grain floor of a render, with an optional baseline.

Run it with the check venv (Pillow + numpy):

    ~/image-studio/.venv-imgcheck/bin/python check-grain.py IMG.png
    ~/image-studio/.venv-imgcheck/bin/python check-grain.py IMG.png --baseline REJECTED.png

The series brief asks for "fine photographic grain across the whole frame", and a
vision read answers that with an adjective ("clean digital art with a noise filter",
"the grain is subtle") either way. This prints numbers instead.

Two measures, and they answer different questions:

  hf_residual   mean absolute difference between the image and a 3x3 median filter.
                This is the grain floor: grain is per-pixel noise, so a frame with
                real grain always sits above ~2.5 on an 8-bit render. Content edges
                raise it too, which is why the number is read against a baseline
                rather than against an absolute threshold.
  flat_std      median standard deviation of 32x32 patches whose mean is not black.
                This is dominated by content, so it says more about how busy the
                picture is than about grain. Do not quote it as grain.

So the check is comparative: run the candidate and the picture the same owner
rejected with --baseline, and quote both hf_residual values. A candidate that is
below the rejected frame's number has less grain than the frame he called
"photo graining is not here", whatever the prompt asked for.

Exit code: 0 always unless the file cannot be read. It is a probe, not a verdict.
"""

import argparse
import sys


def measure(path):
    from PIL import Image, ImageFilter
    import numpy as np

    im = Image.open(path).convert('RGB')
    arr = np.asarray(im).astype(float)
    med = np.asarray(im.filter(ImageFilter.MedianFilter(size=3))).astype(float)
    hf = float(np.abs(arr - med).mean())

    g = np.asarray(im.convert('L')).astype(float)
    stds = []
    for y in range(0, g.shape[0] - 32, 32):
        for x in range(0, g.shape[1] - 32, 32):
            patch = g[y:y + 32, x:x + 32]
            if patch.mean() > 40:
                stds.append(float(patch.std()))
    flat = float(np.median(stds)) if stds else 0.0
    return hf, flat, im.size


def main():
    ap = argparse.ArgumentParser(description='Measure the film-grain floor of a render.')
    ap.add_argument('image')
    ap.add_argument('--baseline', help='a picture from the same series to compare against'
                                       ' (typically the frame the owner rejected)')
    args = ap.parse_args()

    try:
        hf, flat, size = measure(args.image)
    except Exception as exc:                        # noqa: BLE001 - probe reports, never crashes
        print(f'ERROR: {exc}')
        return 2

    print(f'{args.image}  {size[0]}x{size[1]}')
    print(f'  hf_residual  {hf:.2f}   <- the grain floor; read it against a baseline')
    print(f'  flat_std     {flat:.2f}   <- content busyness, not grain')

    if args.baseline:
        try:
            bhf, bflat, bsize = measure(args.baseline)
        except Exception as exc:                    # noqa: BLE001
            print(f'ERROR reading baseline: {exc}')
            return 2
        print(f'{args.baseline}  {bsize[0]}x{bsize[1]}')
        print(f'  hf_residual  {bhf:.2f}')
        print(f'  flat_std     {bflat:.2f}')
        delta = hf - bhf
        verdict = 'MORE grain than' if delta > 0.15 else ('LESS grain than' if delta < -0.15 else 'the same grain as')
        print(f'\n  candidate carries {verdict} the baseline ({delta:+.2f} hf_residual)')

    return 0


if __name__ == '__main__':
    sys.exit(main())
