# Grey Border Bars — Empty Canvas Margins

> 2026-07-14 session: regenerating the observability forklift blog header revealed a distinct artifact type not covered by the grey-box/safety-filter documentation.

## Symptom

The generated image (1216×832, file size >1.5 MB — so **not** a safety-filter grey-box) has uniform near-white bars at the top and/or bottom:

- **Top bar**: rows 0–159 (160px) with RGB ~243,243,240, std=0
- **Bottom bar**: rows 706–831 (126px) with RGB ~242,242,239, std=0
- **Content area**: only 546px of the 832px canvas (65%)

This is visually distinct from a safety-filter grey-box (entire image grey, file <300KB). Here the model rendered the scene correctly but left large empty margins.

## Root Causes

1. **Missing bboxes on all elements.** The original pre-v3.4.0 prompt used `position` strings ("left side", "center") instead of `bbox: [y1,x1,y2,x2]` coordinates. Without spatial guidance, the model placed content in the center and left the edges empty. (See pitfall #25.)

2. **Background description didn't demand full-frame fill.** The original prompt described a background but didn't explicitly say "fills the entire canvas" or "from the very top edge to the very bottom edge, no empty space." The model interpreted the background as a scene setting, not a spatial instruction.

3. **No elements with bboxes in the top/bottom margins.** All elements were clustered in the center vertical band. The top 20% and bottom 15% had no elements at all, so the model left them blank.

## Fix

### Prompt-level

1. **Add bbox to every element**, spanning the full canvas height where possible:
   - `bbox: [0, 0, 200, 1216]` for a left-edge server rack spanning top to bottom
   - `bbox: [650, 0, 1000, 250]` for dashboard panels in the upper region
   - `bbox: [550, 650, 1000, 1000]` for a storage server touching the bottom edge

2. **Explicitly state full-frame fill in the background description**:
   > "The scene fills the entire canvas with content from the very top edge to the very bottom edge, no empty space."

3. **Place at least one element with a bbox starting at y=0** (touching the top edge) and at least one with a bbox ending at y=1000 (touching the bottom edge).

### Diagnostic script

```bash
python3 scripts/check-grey-bars.py /path/to/generated/image.png
```

Returns exit code 0 if clean, 1 if grey bars detected. Reports exact bar height in pixels and percentage of canvas wasted.

## Distinction from Safety-Filter Grey-Box

| Feature | Grey Border Bars | Safety-Filter Grey-Box |
|---|---|---|
| File size | >1 MB (image rendered) | <300 KB (blocked) |
| Affected area | Top/bottom margins only | Entire image |
| Color | Near-white RGB ~243 | Grey RGB ~128 |
| Cause | Missing bboxes, no full-frame fill instruction | Prompt vocabulary triggered safety filter |
| Fix | Add bboxes, demand full-frame fill | Prompt hygiene, remove text elements, encoder swap |