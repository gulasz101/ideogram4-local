#!/usr/bin/env python3
"""Find a flat colour band anywhere in a frame, not only along an edge.

A rendered `color_palette` swatch bar can cross the middle of the frame,
where the edge-only probe cannot see it (engine-pitfalls #33, #34, #34a).
This scans every row for the same signature check-palette-strip.py looks for
at the edges - a row covered by hard-edged, textureless colour blocks
carrying several distinct hues - and reports the rows, the blocks and their
widths, so the note carries a measurement instead of a read.

  * CHIP RUNS - a strip is a row of near-constant colour blocks. The blocks
    are counted and their widths measured, not merely the longest one: a
    strip is several blocks side by side, and the widest single block is
    often only half the row.
  * HUE GROUPS- one hue group per palette entry, bucketed at 30 degrees.
    A painted floor or a plain wall is a single hue.
  * FLATNESS  - a strip has no vertical texture: its columns are flat over
    the band rows, while a control band further into the scene is not.
  * PALETTE   - when the prompt JSON is supplied, every palette colour is
    counted in the band and in the whole frame. A colour that exists
    *only* in the band is the model rendering the list.

Usage:
    python3 check-flat-bands.py <image> [--prompt prompt.json]
    python3 check-flat-bands.py header.png --prompt records/prompt.json

Exit codes:
    0 = no multi-hue flat band anywhere in the frame
    1 = a palette-style band found
    2 = a flat single-hue band found - read the crop before deciding
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

CHIP_TOL = 24         # channel difference that starts a new chip run
MIN_CHIP_PX = 6       # ignore chip runs narrower than this
HUE_BUCKET = 30       # degrees per hue group
HUE_SAT = 0.18        # min saturation for a colour to count as chromatic
PALETTE_TOL = 45      # channel-sum tolerance for a palette colour match
COVERAGE_MIN = 0.75   # share of the row a band must cover
MIN_HUE_GROUPS = 3    # hue groups that make a band a swatch strip
FLAT_STD = 1.0        # per-column vertical std below this counts as flat
SINGLE_HUE_COVER = 0.9  # coverage that makes a one-hue band worth reporting


def hue_of(rgb):
    """Hue in degrees, or None for a near-grey."""
    r, g, b = rgb
    mx, mn = max(rgb), min(rgb)
    if mx == mn:
        return None
    if (mx - mn) / mx < HUE_SAT:
        return None
    d = mx - mn
    if mx == r:
        h = 60 * (((g - b) / d) % 6)
    elif mx == g:
        h = 60 * (((b - r) / d) + 2)
    else:
        h = 60 * (((r - g) / d) + 4)
    return h % 360


def runs_of_row(row):
    """Split one row of RGB pixels into runs of near-constant colour.

    row: (w, 3) int array. Returns (start, end, mean_rgb) inclusive.
    """
    w = row.shape[0]
    diff = np.abs(np.diff(row.astype(np.int16), axis=0)).max(axis=1)
    breaks = np.flatnonzero(diff > CHIP_TOL)
    starts = [0] + (breaks + 1).tolist()
    ends = breaks.tolist() + [w - 1]
    out = []
    for s, e in zip(starts, ends):
        if e - s + 1 < MIN_CHIP_PX:
            continue
        block = row[s : e + 1]
        out.append((s, e, tuple(int(v) for v in block.mean(axis=0))))
    return out


def hue_groups(runs):
    buckets = set()
    for _, _, rgb in runs:
        h = hue_of(rgb)
        if h is not None:
            buckets.add(int(round(h / HUE_BUCKET)) % 12)
    return buckets


def modal_colors(band):
    """Per-column modal RGB of a band. band: (rows, w, 3) int array."""
    out = []
    for x in range(band.shape[1]):
        colors, counts = np.unique(band[:, x, :], axis=0, return_counts=True)
        out.append(tuple(int(v) for v in colors[int(np.argmax(counts))]))
    return out


def band_runs(band):
    """Chip runs across a multi-row band, from its per-column modal colour."""
    runs = []
    start = 0
    colors = modal_colors(band)
    for x in range(1, len(colors)):
        if max(abs(colors[x][i] - colors[start][i]) for i in range(3)) > CHIP_TOL:
            runs.append((start, x - 1, colors[start]))
            start = x
    runs.append((start, len(colors) - 1, colors[start]))
    return [r for r in runs if r[1] - r[0] + 1 >= MIN_CHIP_PX]


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


def palette_report(arr, band, palette):
    """Per palette colour: pixels in the band vs in the whole frame."""
    flat_band = band.reshape(-1, 3)
    whole = arr.reshape(-1, 3)
    out = []
    for entry in palette:
        rgb = hex_to_rgb(entry)
        if rgb is None:
            continue
        target = np.array(rgb)
        d_band = np.abs(flat_band.astype(int) - target).sum(axis=1)
        d_whole = np.abs(whole.astype(int) - target).sum(axis=1)
        in_band = int((d_band < PALETTE_TOL).sum())
        in_whole = int((d_whole < PALETTE_TOL).sum())
        out.append((str(entry), in_band, in_whole))
    return out


def scan_rows(arr):
    """Per row: covered width, hue groups and the chip runs that made it."""
    h, w, _ = arr.shape
    rows = []
    for y in range(h):
        runs = runs_of_row(arr[y])
        if not runs:
            continue
        coverage = sum(e - s + 1 for s, e, _ in runs)
        groups = hue_groups(runs)
        rows.append({"y": y, "coverage": coverage / float(w),
                     "groups": len(groups), "runs": runs})
    return rows


def group_rows(rows, max_gap=2):
    """Merge consecutive candidate rows into bands, allowing a small gap."""
    bands = []
    for row in rows:
        if bands and row["y"] - bands[-1]["y2"] <= max_gap:
            bands[-1]["y2"] = row["y"]
            bands[-1]["rows"].append(row)
        else:
            bands.append({"y1": row["y"], "y2": row["y"], "rows": [row]})
    return bands


def flat_ratio(band):
    """Share of columns that are flat over the band's rows."""
    if band.shape[0] < 2:
        return 1.0
    per_col = band.astype(float).std(axis=0).mean(axis=1)
    return int((per_col < FLAT_STD).sum()) / float(band.shape[1])


def main():
    parser = argparse.ArgumentParser(description="Check a frame for a flat colour band anywhere in it")
    parser.add_argument("image", help="Path to the image file")
    parser.add_argument("--prompt", help="Prompt JSON, to compare against its color_palette")
    parser.add_argument("--control-offset", type=int, default=100,
                        help="Rows inward for the control band (default 100)")
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

    rows = scan_rows(arr)
    multi = [r for r in rows if r["groups"] >= MIN_HUE_GROUPS
             and r["coverage"] >= COVERAGE_MIN]
    single = [r for r in rows if r["groups"] < MIN_HUE_GROUPS
              and r["coverage"] >= SINGLE_HUE_COVER]

    if not multi and not single:
        print("\nCLEAN: no flat multi-hue band anywhere in the frame")
        sys.exit(0)

    verdict = 0
    for band in group_rows(multi):
        region = arr[band["y1"] : band["y2"] + 1]
        runs = band_runs(region)
        groups = hue_groups(runs)
        covered = sum(e - s + 1 for s, e, _ in runs)
        fr = flat_ratio(region)
        print(f"\n[MULTI-HUE BAND] rows {band['y1']}-{band['y2']} "
              f"({band['y2'] - band['y1'] + 1} rows), "
              f"{len(runs)} blocks covering {covered}/{w} px "
              f"({100.0 * covered / w:.1f}%), {len(groups)} hue groups, "
              f"{fr * 100:.0f}% flat columns")
        for (x0, x1, rgb) in runs[:14]:
            print(f"    x[{x0:4d}-{x1:4d}] w={x1 - x0 + 1:4d}  "
                  f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}")
        if len(runs) > 14:
            print(f"    ... {len(runs) - 14} more blocks")
        if palette:
            for (name, in_band, in_whole) in palette_report(arr, region, palette):
                share = (in_band / in_whole * 100) if in_whole else 0.0
                mark = "  <-- only in the band" if in_whole and share >= 80 else ""
                print(f"    palette {name}: band={in_band} frame={in_whole} "
                      f"({share:.1f}% in band){mark}")
        verdict = 1

    for band in group_rows(single):
        region = arr[band["y1"] : band["y2"] + 1]
        runs = band_runs(region)
        covered = sum(e - s + 1 for s, e, _ in runs)
        fr = flat_ratio(region)
        print(f"\n[SINGLE-HUE BAND] rows {band['y1']}-{band['y2']}, "
              f"{len(runs)} block(s) covering {covered}/{w} px "
              f"({100.0 * covered / w:.1f}%), {fr * 100:.0f}% flat columns")
        for (x0, x1, rgb) in runs[:14]:
            print(f"    x[{x0:4d}-{x1:4d}] w={x1 - x0 + 1:4d}  "
                  f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}")
        if verdict == 0:
            verdict = 2

    if verdict == 1:
        print("\nPALETTE-STYLE BAND FOUND: flat colour blocks mid-frame. "
              "Read a crop of it before deciding.")
    else:
        print("\nFlat single-hue band found - read the crop before deciding "
              "(a painted floor or a plain wall looks the same by these numbers).")
    sys.exit(verdict)


if __name__ == "__main__":
    main()
