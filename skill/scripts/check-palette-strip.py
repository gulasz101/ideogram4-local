#!/usr/bin/env python3
"""Detect a rendered colour-palette strip along the top or bottom edge of an image.

A prompt that carries a `color_palette` array can come back with that array
drawn into the picture: a row of hard-edged, textureless colour chips laid
along an edge, one chip per palette entry, in palette order, ignoring the
scene's light and perspective. It is invisible to check-grey-bars.py, which
only looks for *grey* margins, and a vision read of the edge alone often
argues both ways ("is it floorboards or a swatch bar?").

This probe settles it with numbers instead of an opinion:

  * FLATNESS  - a chip strip has no vertical texture: its columns are flat
    over the edge rows, while a control band further into the scene is not.
    The scene band is the baseline; a strip collapses the ratio.
  * HUE SPREAD- a strip carries several distinct hues in sequence, one per
    palette entry. A painted floor band or a plank floor is a single hue.
    Hue groups are counted in 30-degree buckets, so a long run of near
    shades of one colour counts once.
  * PALETTE   - when the prompt JSON is supplied, every palette colour is
    counted in the band and in the whole frame. A colour that exists
    *only* in the band is the model rendering the list.

Usage:
    python3 check-palette-strip.py <image> [--prompt prompt.json]
    python3 check-palette-strip.py header.png --prompt records/prompt.json

Exit codes:
    0 = no strip on either edge
    1 = palette strip detected
    2 = flat band present but single-hue - read the crop before deciding
    3 = file not found, not an image, or missing Pillow/numpy

Run with the check venv: ~/image-studio/.venv-imgcheck/bin/python
(the system python3 has neither Pillow nor numpy).
"""

import argparse
import json
import sys
from pathlib import Path

try:
    from PIL import Image
    import numpy as np
except ImportError:
    print("ERROR: Pillow and numpy required.")
    sys.exit(3)

FLAT_STD = 1.0        # per-column vertical std below this counts as flat
FLAT_RATIO = 0.5      # share of flat columns that makes a band suspicious
CHIP_TOL = 24         # channel-sum difference that starts a new chip run
MIN_CHIP_PX = 6       # ignore chip runs narrower than this
HUE_BUCKET = 30       # degrees per hue group
HUE_SAT = 0.18        # min saturation for a colour to count as chromatic
PALETTE_TOL = 45      # channel-sum tolerance for a palette colour match


def modal_colors(band):
    """Per-column modal RGB of a band. band: (rows, w, 3) int array."""
    out = []
    for x in range(band.shape[1]):
        colors, counts = np.unique(band[:, x, :], axis=0, return_counts=True)
        out.append(tuple(int(v) for v in colors[int(np.argmax(counts))]))
    return out


def chip_runs(colors):
    """Split a per-column colour list into runs of near-constant colour."""
    runs = []
    start = 0
    for x in range(1, len(colors)):
        if max(abs(colors[x][i] - colors[start][i]) for i in range(3)) > CHIP_TOL:
            runs.append((start, x - 1, colors[start]))
            start = x
    runs.append((start, len(colors) - 1, colors[start]))
    return [r for r in runs if r[1] - r[0] + 1 >= MIN_CHIP_PX]


def hue_of(rgb):
    """Hue in degrees, or None for a near-grey."""
    r, g, b = rgb
    mx, mn = max(rgb), min(rgb)
    if mx == mn:
        return None
    sat = (mx - mn) / mx
    if sat < HUE_SAT:
        return None
    d = mx - mn
    if mx == r:
        h = 60 * (((g - b) / d) % 6)
    elif mx == g:
        h = 60 * (((b - r) / d) + 2)
    else:
        h = 60 * (((r - g) / d) + 4)
    return h % 360


def hue_groups(runs):
    buckets = set()
    for _, _, rgb in runs:
        h = hue_of(rgb)
        if h is not None:
            buckets.add(int(round(h / HUE_BUCKET)) % 12)
    return buckets


def edge_report(arr, edge, flat_rows, control_offset):
    """Flatness and chip sequence for the top or bottom edge band."""
    h, w, _ = arr.shape
    if edge == "bottom":
        band = arr[h - flat_rows:, :, :]
        control = arr[h - control_offset - flat_rows:h - control_offset, :, :]
    else:
        band = arr[0:flat_rows, :, :]
        control = arr[control_offset:control_offset + flat_rows, :, :]

    def flatness(region):
        if region.shape[0] < 2:
            return 0.0, 0.0
        per_col = region.astype(float).std(axis=0).mean(axis=1)
        flat = int((per_col < FLAT_STD).sum())
        return flat / float(w), float(per_col.mean())

    flat_ratio, band_vstd = flatness(band)
    control_ratio, control_vstd = flatness(control)

    runs = chip_runs(modal_colors(band))
    groups = hue_groups(runs)
    return {
        "edge": edge,
        "flat_ratio": flat_ratio,
        "band_vstd": band_vstd,
        "control_flat_ratio": control_ratio,
        "control_vstd": control_vstd,
        "runs": runs,
        "hue_groups": groups,
    }


def find_palette(obj):
    """Find a color_palette list anywhere in a prompt JSON."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == "color_palette" and isinstance(value, list):
                return value
            found = find_palette(value)
            if found:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = find_palette(item)
            if found:
                return found
    return None


def hex_to_rgb(value):
    text = str(value).strip().lstrip("#")
    if len(text) == 3:
        text = "".join(c * 2 for c in text)
    if len(text) != 6:
        return None
    try:
        return (int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16))
    except ValueError:
        return None


def palette_report(arr, band_rows, palette):
    """Per palette colour: pixels in the edge band vs in the whole frame."""
    h, w, _ = arr.shape
    band = arr[h - band_rows:, :, :].reshape(-1, 3)
    whole = arr.reshape(-1, 3)
    out = []
    for entry in palette:
        rgb = hex_to_rgb(entry)
        if rgb is None:
            continue
        target = np.array(rgb)
        d_band = np.abs(band.astype(int) - target).sum(axis=1)
        d_whole = np.abs(whole.astype(int) - target).sum(axis=1)
        in_band = int((d_band < PALETTE_TOL).sum())
        in_whole = int((d_whole < PALETTE_TOL).sum())
        out.append((str(entry), in_band, in_whole))
    return out


def main():
    parser = argparse.ArgumentParser(description="Check an image for a rendered colour-palette strip")
    parser.add_argument("image", help="Path to the image file")
    parser.add_argument("--prompt", help="Prompt JSON, to compare against its color_palette")
    parser.add_argument("--flat-rows", type=int, default=12, help="Edge rows measured for flatness (default 12)")
    parser.add_argument("--band-rows", type=int, default=40, help="Edge rows used for the palette count (default 40)")
    parser.add_argument("--control-offset", type=int, default=100, help="Rows inward for the control band (default 100)")
    args = parser.parse_args()

    path = Path(args.image)
    if not path.exists():
        print(f"ERROR: File not found: {path}")
        sys.exit(3)
    try:
        img = Image.open(path)
    except Exception:
        print(f"ERROR: Not an image: {path}")
        sys.exit(3)
    arr = np.array(img.convert("RGB")).astype(int)
    h, w, _ = arr.shape
    if h < args.flat_rows * 3:
        print(f"ERROR: Image too small for an edge check: {w}x{h}")
        sys.exit(3)

    print(f"Image: {w}x{h}, {path.stat().st_size / 1048576:.2f} MB")

    palette = None
    if args.prompt:
        try:
            with open(args.prompt) as handle:
                palette = find_palette(json.load(handle))
        except Exception as exc:
            print(f"WARNING: could not read prompt JSON ({exc}); continuing without a palette")
        if palette:
            print(f"Prompt palette: {', '.join(str(c) for c in palette)}")

    reports = [edge_report(arr, edge, args.flat_rows, args.control_offset)
               for edge in ("top", "bottom")]

    for rep in reports:
        print(f"\n[{rep['edge'].upper()} EDGE]  flat columns {rep['flat_ratio'] * 100:.0f}% "
              f"(control {rep['control_flat_ratio'] * 100:.0f}%)  "
              f"vstd {rep['band_vstd']:.2f} vs control {rep['control_vstd']:.2f}")
        if rep["runs"]:
            print(f"  {len(rep['runs'])} colour runs, {len(rep['hue_groups'])} distinct hue groups")
            for (x0, x1, rgb) in rep["runs"][:14]:
                print(f"    x[{x0:4d}-{x1:4d}] w={x1 - x0 + 1:4d}  #{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}")
            if len(rep["runs"]) > 14:
                print(f"    ... {len(rep['runs']) - 14} more runs")
        else:
            print("  no flat chip runs")

    if palette:
        print("\n[PALETTE]  edge band vs whole frame")
        for (name, in_band, in_whole) in palette_report(arr, args.band_rows, palette):
            share = (in_band / in_whole * 100) if in_whole else 0.0
            mark = "  <-- only in the band" if in_whole and share >= 80 else ""
            print(f"  {name}  band={in_band:6d}  frame={in_whole:6d}  {share:5.1f}% in band{mark}")

    verdict = 0
    message = "no palette strip on either edge"
    for rep in reports:
        if rep["flat_ratio"] < FLAT_RATIO:
            continue
        if len(rep["hue_groups"]) >= 3:
            verdict = 1
            message = (f"PALETTE STRIP on the {rep['edge']} edge: {rep['flat_ratio'] * 100:.0f}% flat columns "
                       f"and {len(rep['hue_groups'])} hue groups in one row")
            break
        if verdict == 0:
            verdict = 2
            message = (f"flat band on the {rep['edge']} edge but a single hue - read the crop before deciding "
                       f"(a painted floor band looks the same by these numbers)")

    print(f"\n{message}")
    sys.exit(verdict)


if __name__ == "__main__":
    main()
