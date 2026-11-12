# Reading the mechanical probes

Every card's check note is a frozen claim, so the `scripts/check-*.py` probes guard it. A probe reports a *shape*, not a verdict, and two probes can point opposite ways. Read them in this order and arbitrate before any defect reaches a note.

## The pair to run on every render

One call, staging PNG, keep the printed numbers for the note:

```bash
cd ~/.hermes/profiles/matejko/skills/image-studio/scripts
python3 check-grey-bars.py "$IMG"; python3 check-palette-strip.py "$IMG" --prompt "$PROMPT_JSON"
python3 check-blank-margin.py "$IMG"; python3 check-green-share.py "$IMG"; python3 check-grain.py "$IMG"
```

- `check-palette-strip.py` wants `--prompt` to use its third argument (a colour that exists only in the band is the model rendering the list). Without it you get flatness and hue groups only.
- `check-green-share.py` gives a hard number for the no-green preference; quote the percentage, not an adjective.
- `check-grain.py` prints `hf_residual` with **no baseline**. Quote it as measured and let the visual read say whether grain is visible; a lone number is not "grain on".

## A flat-bands flag is not a strip

`check-flat-bands.py` prints `PALETTE-STYLE BAND FOUND: flat colour blocks mid-frame` for ordinary painted scene texture: one or two rows at the very top edge carrying the wall's own warm cream, or a near-black run of blocks that is the deep-indigo shadow side of the palette. A swatch strip is a row of hard-edged, textureless chips in palette order that ignores the scene's light.

A concrete instance that looked like a defect and was not: rows 129-139 of a cel-shaded workshop frame flagged `PALETTE-STYLE BAND FOUND`, and the rows were the deep-indigo shadow side of the pegboard/wall junction — scene texture, not a pasted strip. The crop read settled it as painted wall, and the strip probe printed `no palette strip on either edge`. The flag alone never reaches a note; the rows get cropped and read first.

**Arbitrate with `check-palette-strip.py` and `check-blank-margin.py`; one probe's flag alone never becomes a defect note.** The strip probe is the authoritative one because it measures the edge band's flatness against a control band inside the same scene and counts hue groups. If it prints `no palette strip on either edge`, say so in the note and move on — do not spend a render on a flag from the weaker probe. The reverse holds too: a strip the eye argues both ways on is settled by the strip probe's numbers, not by a read of the edge.

## Locate the prop before you crop it

A prompt's `bbox` is in the prompt's own 0-1000 space and is **not** a frame pixel box, and an element bbox is not even a reliable region: crop from a guessed box and the read answers confidently about the neighbouring object — a crop that overlapped the padlock came back as "there is no padlock in this crop, just a hand wiping a hinge", and other reads invented a franchise character the figure half-resembles.

Find the prop by colour signature first, then crop exactly it (full procedure: `references/verifying-image-details.md`). The cheap locator needs only PIL and numpy — no labelling library — so it works anywhere: print a coarse ASCII map of an HSV mask and read the prop's band off it.

```python
hsv = np.asarray(im.convert("HSV")).astype(int); H, S, V = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
mask = (S > 140) & (V > 110) & (H > 14) & (H < 42)   # saturated brass-gold
# print 26 rows x 64 cols of the mask as '#/o/.' and read the block where the prop sits
```

Then crop that block at 4-6x. A mask that is too loose (thresholds that let the whole warm palette through) prints a full frame of `#` and tells you nothing — tighten saturation before believing it.

## A prose read is a claim; the probe is the measurement

A read that reports a blank margin, a grey bar or a colour strip has made a *claim*, and the probe for that claim is one call. On a batch of flux renders the read answered "a flat pasted panel with a stark white margin" on every frame while `check-blank-margin.py` measured no blank rows on any of them: the pasted panel was real and the margin was invented. Write only the half the number supports, and never hold a render back on the strength of the unmeasured half.

The same read can be wrong about the scene itself — a basement workshop came back as "an artist's studio" twice in one hop — and a wrong scene description reads exactly like a render defect. Before a hold-back, re-read once with the second reader (`references/vision-route-fallbacks.md`) and ask a narrow question instead of "describe this": the misread is the model's, but the hold-back and the card note are yours.

## Two reads that agree on the crops outrank one full-frame read

A full-frame read sees the whole composition and is the right tool for "what does this picture say"; it is weak on a small state (open or shut, seated or lifted) because it reads the shape at thumbnail scale. When a full-frame read and a zoomed crop disagree on a state that decides the verdict, the crop wins — and the card says the crops settled it, in one clause, so the reader knows the note was measured rather than assumed.
