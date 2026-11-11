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
~/image-studio/.venv-imgcheck/bin/python scripts/check-grey-bars.py /path/to/generated/image.png
```

Returns exit code 0 if clean, 1 if grey bars detected. Reports exact bar height in pixels and percentage of canvas wasted. The system `python3` has no Pillow or numpy, so the script exits 2 with `ERROR: Pillow and numpy required`; create the venv once with `python3 -m venv ~/image-studio/.venv-imgcheck && ~/image-studio/.venv-imgcheck/bin/pip install Pillow numpy`.

### A full-frame vision pass can misread the margin as floor

`vision_analyze` on the whole PNG will happily call a bottom margin "the tiled floor, not a blank panel" and report the frame as "filled edge to edge". A full-frame pass cannot see that the floor's perspective lines stop short of the edge, so it reads the flat pale area as a receding surface.

**The script is right and the full-frame vision is wrong.** Settle it with two cheap checks, not by re-asking the same question:

1. Crop the bottom 150-200px and look at the crop. A real floor keeps its lines, shadows and objects in the crop; a margin is flat pale paper with the drawn objects cut off at the crop's top edge.
2. Print per-row colour stats. A drawn region has hundreds of distinct colours and a std of tens; a margin has ~100-230 distinct colours and a std under 3, with the mean sitting near 240,240,239:

```bash
~/image-studio/.venv-imgcheck/bin/python -c "
from PIL import Image
import numpy as np
im = Image.open(PATH).convert('RGB'); a = np.asarray(im).astype(int)
for y0 in range(600, im.size[1], 20):
    row = a[y0].reshape(-1, 3)
    print(y0, len(np.unique(row, axis=0)), row.mean(axis=0).round(1), round(row.std(), 2))
"
```

Report the margin's pixel height from the script's own number in the check note, not the vision pass's guess.

## A pale fill is not grey: measure the fill's share, not the band's colour

`check-grey-bars.py` matches grey margins (flat, RGB ~243, std≈0) at the top and bottom. A render can fail the same way on a **pale cream or near-white field** — the model draws the scene into part of the canvas and leaves the rest as flat `#F8FAFA` — and the grey-bar script reports "content fills the entire frame", because near-white is outside its grey match and because it reads only the two edges.

The question a blank margin answers is *how much of the frame is one flat fill, and where* — not *is the band grey*:

```bash
~/image-studio/.venv-imgcheck/bin/python ~/.hermes/profiles/matejko/skills/image-studio/scripts/check-blank-margin.py "$PNG"
```

It prints the dominant fill colour and its share of the whole frame, every run of rows and columns that is at least 80% that fill, the blank strip at each of the four edges, and the content bbox. One measured frame: fill `rgb(248,250,250)`, **49.5% of the frame**, 116 rows over 80% pale, and a **107 px right-edge strip 99.8% blank** — and the frame carried two pasted UI cards sitting on that field, which is what made the fill a defect rather than a background.

Read the numbers as a share, not a verdict:

- **A fill that is the wall behind a full scene is scenery.** Cel-shaded art has large flat surfaces; a 20-40% fill with props and figures crossing every edge is normal, and `check-flat-bands.py` fires on such frames by construction (engine-pitfall #66).
- **A fill that is most of the frame with the drawing squeezed into one corner or one half is an empty margin**, whatever its colour, and it is the same defect class as a grey band.
- **A blank vertical band is invisible to both edge scripts**, which scan rows — read the column runs too, because a strip down a side edge is the same empty margin as a band across the bottom.
- **Put the numbers in the note.** "49.5% of the frame is one flat pale fill, 116 rows over 80% pale, the right 107 px strip 99.8% blank" is re-runnable; "half the image is empty" is not.
- **The class vocabulary may have no rate for it.** `verdict-class-rate.py --class empty-margins` can come back `no rows` while the standing rule is well established across approved cards, so quote the rule and the measurement rather than an invented rate, and say the class has no verdict rows.

## A band that carries the frame's grain was painted, not left empty

The row/column stats above separate an unpainted digital margin (std under 3, ~100-230 distinct colours) from drawn content (std of tens, many hundreds of colours). There is a third case in the middle, and it decides a note rather than a defect: **a flat band whose noise is the frame's own grain**. One nano banana header carried a cream border about 16 px deep on all four edges: colour `#FEF7DD`, std 14-15 per row, and only 18-26 distinct colours per row. The low unique count says one colour; the std of 14 says that colour is textured, so the band was painted paper and not an empty canvas.

- **Compare the band's std against a large flat surface elsewhere in the same frame.** A wall or bench panel in the same picture carries the same std, because it is the same grain over a different colour. A band at std 0 beside surfaces at std 15 is empty canvas.
- **Check all four edges before naming the shape.** A print border wraps the frame; an empty margin usually sits on one or two edges and cuts the drawing off at its own boundary. `check-blank-margin.py` reporting band rows and band cols of the same colour on opposite edges is a border; one long band with the content bbox pressed against it is a margin.
- **Name the measurement, not a verdict.** "Cream `#FEF7DD` paper margin, about 16 px on every edge, flat with the frame's grain" is re-runnable; "has a border" invites a re-render of a file he has already accepted. A border that the scene's own drawing continues into costs nothing.

## Distinction from Safety-Filter Grey-Box

| Feature | Grey Border Bars | Safety-Filter Grey-Box |
|---|---|---|
| File size | >1 MB (image rendered) | <300 KB (blocked) |
| Affected area | Top/bottom margins only | Entire image |
## FLUX renders can carry empty margins despite full-frame bbox guidance

A prompt that passes `check-bboxes.py` clean and carries \"fills the entire canvas edge to edge, no empty space\" in its background still comes back with a near-white frame on FLUX.2-klein, where the same prompt on ideogram4 fills the frame. The flux model is less spatially compliant than ideogram4: full-frame bboxes and a single fill sentence are not enough to force content to every edge.

Fix: name the contact on each edge explicitly, in the same sentence as the fill demand — \"the couch touches the bottom edge, the wall lamp touches the left edge, the doorway frame touches the top and right edges\" — and add a hard negative (\"no empty margin, no border, no frame, no whitespace, no bare wall band anywhere\"). If the margin persists after that, the slot's passing engine (the one that filled the frame) is the render that ships; do not spend another flux attempt on the same composition. Record the held-back flux render with a `rejected` row naming the empty margin and its pixel height from `check-blank-margin.py`, and let the brief name the passing render as the one that ships.

| Color | Near-white RGB ~243 | Grey RGB ~128 |
| Cause | Missing bboxes, no full-frame fill instruction | Prompt vocabulary triggered safety filter |
| Fix | Add bboxes, demand full-frame fill | Prompt hygiene, remove text elements, encoder swap |

## Swatch strips and duplicate props that survive the edge clause on ideogram4

A render can come back with a **thin multi-colour calibration bar** on the top and bottom edges — a rainbow or greyscale swatch strip — plus a **baked-in transparency checkerboard** (grey-and-white squares at the border). Check the PNG mode before calling the checkerboard a viewer artefact: an `RGB` file is painted, so it is a render defect; only `RGBA` with a real alpha channel makes it a display mask.

- **The model treats a "no colour bar" clause as a palette hint, not a prohibition.** A slot that keeps producing the strip on ideogram4 across two attempts (the same shot, not the same prompt) is not fixed by another wording pass — the prompt already said no bars on any edge. Switch the slot to `flux2-klein` with the 1990s-anime register written into the prompt; on post 141 flux cleared the bar on the first flux attempt after ideogram4 had produced strips and a checkerboard on three.
- **A prompt naming one cloud/shield symbol can draw two.** Describe a single prop and place it with its own bbox; when a duplicate still appears, the flux render is the one that keeps one.
- **Measure the strip with `check-blank-margin.py` and the grain with `measure-grain.py`** and put the numbers in the check note, because the strip is often the only thing separating a modern flat render from a 1990s one.
- **Do not answer an edge strip with another ideogram attempt on the same slot.** The standing fix is the ideogram + flux pair, and the pair only needs one pass: if the ideogram fails on edges, the flux is the render that ships.