# Verifying a small image detail before it goes on a card

A self-check note is a claim about a picture Wojtek will judge from, and the card's
`items[].description` and `detailsMarkdown` are **frozen at the POST** — there is no
PATCH for an interaction. A note you later disprove is a defect he would judge from,
so a small claim has to be settled before the card goes up, not after.

## Why a region crop is not enough

`vision_analyze` takes a `region` box, and the read answers about whatever the region
parameter actually resolved to. Across calls on one image, the same box came back as
the alarm clock in one pass, as a pegboard wall in the next, and as a magnified glass
in a third. Two reads of the identical box on one PNG gave opposite answers, and a
third read of a 4x crop of that same box gave a third answer.

So: **a region crop is a prompt to the model about an area, not a measurement of it.**
It is fine for scoping a question ("read every character on the clipboard verbatim")
and useless for settling a countable fact.

## The procedure

1. **Locate the subject by pixel signature, not by eye.** Find it by colour mask and
   print the bounding box — a cream dial, a gold clock body, a red question mark. A
   crop of the wrong region reads confidently and wrongly, so the box must come from
   the pixels.
2. **Write the crop to disk and analyse the file.** An upscaled crop of the exact
   subject (3-4x, LANCZOS) is a stable input: the same file always reads the same way.
3. **Count the claim when it is countable.** Tick marks go in an angular histogram
   around the detected centre, one bucket per hour position. Overlap goes in a pixel
   cross-count. A veil that drapes a subject has veil-coloured pixels **on** the
   subject's pixels; a shape behind it has none, and the count of zero is the answer.
4. **Cross-check the read against the count.** A read that says "twelve tick marks"
   and a histogram that finds eleven do not both get to stand. Re-crop wider, re-read,
   and let the number settle the fact.
5. **Only then write the note**, and say which check it rests on.

## The tool

```bash
~/image-studio/.venv-imgcheck/bin/python ~/.hermes/profiles/matejko/skills/image-studio/scripts/crop-probe.py \
  "$PNG" --box 210,250,410,450 --scale 4 --out /tmp/prop.png
```

- `--box x0,y0,x1,y1` — the region, in pixel coordinates.
- `--out` — where the upscaled crop is written; analyse this file, not the region.
- `--find r,g,b` — locate the largest blobs of a colour and print their bounding
  boxes, so the crop box comes from the pixels.
- `--overlap r,g,b r,g,b` — cross-count two colours in the region: how much of the
  second lies on the first. Zero means "behind or beside", not "draped over".
- `--tol` — summed absolute colour tolerance; raise it when a subject is textured.

The venv is `~/image-studio/.venv-imgcheck` — the system `python3` has no Pillow or
numpy. `references/review-loop.md` step 6 carries the one-time setup.

## When the note turns out wrong after the card is live

Withdraw and re-post. `POST /api/issues/<id>/interactions/<id>/withdraw` with a
reason naming what was wrong settles the card as `cancelled`; a new card under a new
idempotency key (`verdicts:<issueId>:round-<k>-corrected`) carries the corrected text.
The cancelled card is not a pending card, so exactly one card stays open for the
round — verify with `GET /interactions` that one is `pending` and the other
`cancelled`.

Post an issue comment saying what was wrong and what the correction is: the
withdrawn card's wording stays in the thread, and a wrong note that vanishes without
explanation looks like a quiet mistake rather than a correction.

The one-card-at-a-time rule counts **pending** cards, not cards already retracted.
