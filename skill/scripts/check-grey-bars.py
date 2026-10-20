#!/usr/bin/env python3
"""Check an image for grey border bars (uniform light-grey margins on top/bottom).

This is a DISTINCT defect from safety-filter grey-boxing:
- Safety-filter grey-box: entire image is grey, file ~252KB, RGB ~103,103,101
- Grey border bars: only top/bottom margins are grey, file is normal (1.5-2.5MB),
  content is present in the center, margins are uniform ~RGB 243,243,240, std≈0

Cause: element bboxes cluster in the vertical center, so the model fills
the top and bottom with empty grey. Fix: spread bboxes across the full
y-range (0-1000) and describe the background as filling the entire frame.

Usage:
    python3 check-grey-bars.py <image_path> [--threshold N]
    python3 check-grey-bars.py assets/2026-06-26/header.png

Exit codes:
    0 = no grey bars detected
    1 = grey bars detected (prints details)
    2 = file not found / not an image
"""
import sys
import argparse
from pathlib import Path


def check_grey_bars(image_path: str, grey_threshold: int = 200, std_threshold: int = 5, match_tolerance: int = 5) -> dict:
    """Scan an image for uniform grey bars on top and bottom.

    Returns dict with keys: width, height, top_bar_px, bottom_bar_px,
    has_grey_bars (bool), file_size_mb (float).
    """
    try:
        from PIL import Image
        import numpy as np
    except ImportError:
        print("ERROR: Pillow and numpy required. Install with: pip install Pillow numpy")
        sys.exit(2)

    p = Path(image_path)
    if not p.exists():
        print(f"ERROR: File not found: {image_path}")
        sys.exit(2)

    file_size_mb = p.stat().st_size / (1024 * 1024)

    img = Image.open(p)
    arr = np.array(img.convert("RGB"))
    h, w = arr.shape[:2]

    # Scan from top — find first row that is NOT uniform grey
    top_bar_px = 0
    for y in range(h):
        row = arr[y]
        r_m = int(row[:, 0].mean())
        g_m = int(row[:, 1].mean())
        b_m = int(row[:, 2].mean())
        std = int(row.std())
        is_grey = (
            abs(r_m - g_m) < match_tolerance
            and abs(g_m - b_m) < match_tolerance
            and r_m > grey_threshold
            and std < std_threshold
        )
        if not is_grey:
            top_bar_px = y
            break

    # Scan from bottom
    bottom_bar_px = 0
    for y in range(h - 1, -1, -1):
        row = arr[y]
        r_m = int(row[:, 0].mean())
        g_m = int(row[:, 1].mean())
        b_m = int(row[:, 2].mean())
        std = int(row.std())
        is_grey = (
            abs(r_m - g_m) < match_tolerance
            and abs(g_m - b_m) < match_tolerance
            and r_m > grey_threshold
            and std < std_threshold
        )
        if not is_grey:
            bottom_bar_px = h - 1 - y
            break

    has_grey_bars = top_bar_px > 0 or bottom_bar_px > 0

    # Also check if the entire image is a safety-filter grey-box
    is_full_grey_box = file_size_mb < 0.4 and top_bar_px == 0 and bottom_bar_px == 0

    return {
        "width": w,
        "height": h,
        "file_size_mb": round(file_size_mb, 2),
        "top_bar_px": top_bar_px,
        "bottom_bar_px": bottom_bar_px,
        "has_grey_bars": has_grey_bars,
        "is_full_grey_box": is_full_grey_box,
    }


def main():
    parser = argparse.ArgumentParser(description="Check image for grey border bars")
    parser.add_argument("image", help="Path to the image file")
    parser.add_argument("--threshold", type=int, default=200, help="RGB threshold for grey detection (default 200)")
    args = parser.parse_args()

    result = check_grey_bars(args.image, grey_threshold=args.threshold)

    print(f"Image: {result['width']}x{result['height']}, {result['file_size_mb']} MB")

    if result["is_full_grey_box"]:
        print(f"⚠️  FULL GREY-BOX (safety filter): file {result['file_size_mb']} MB < 0.4 MB threshold")
        sys.exit(1)

    if result["has_grey_bars"]:
        print(f"❌ Grey bar TOP: {result['top_bar_px']}px")
        print(f"❌ Grey bar BOTTOM: {result['bottom_bar_px']}px")
        total_grey = result["top_bar_px"] + result["bottom_bar_px"]
        pct = round(100 * total_grey / result["height"], 1)
        print(f"   Total grey: {total_grey}px ({pct}% of height)")
        print(f"   Fix: spread element bboxes across full y-range (0-1000),")
        print(f"   describe background as 'filling the entire frame edge to edge'")
        sys.exit(1)
    else:
        print("✅ No grey bars — content fills the entire frame")
        sys.exit(0)


if __name__ == "__main__":
    main()