# Reading the acceptance-bar scripts

The three edge scripts are the mechanical half of the bar: they cannot approve a picture, and they can hold one. The other half — hands, lettering, the beat — is a read. This file is only about getting an honest answer out of the scripts, because a misread flag costs a render and a misread pass puts a defect on a frozen card.

Run them with the profile's checking venv, from `~/image-studio`:

```bash
S=~/.hermes/profiles/matejko/skills/image-studio/scripts
.venv-imgcheck/bin/python $S/check-palette-strip.py <png>
.venv-imgcheck/bin/python $S/check-blank-margin.py <png>
.venv-imgcheck/bin/python $S/check-green-share.py <png>
```

`check-palette-strip.py` takes exactly one path (a second one is an argparse error, not a finding). `check-blank-margin.py` accepts several.

## Parse the verdict line, never a keyword grep

Every script prints its section headings whether or not it finds anything, so `grep -icE 'palette|edge|blank|green'` over the output matches the report's own vocabulary on a clean file. Nine shipped frames checked that way returned identical counts (`palette-hits=2 margin-hits=2 green-hits=1` each) and read like nine failures. Read the line each script ends on instead:

| script | pass line | failure shape |
| --- | --- | --- |
| `check-palette-strip` | `no palette strip on either edge` | names the edge (`[TOP EDGE]` / `[BOTTOM EDGE]`) with flat-share, `N distinct hue groups` and the colour runs |
| `check-blank-margin` | strips line at 98% fill plus `BLANK MARGIN: N band rows / M band cols` | a band at the fill threshold that also holds no ink |
| `check-green-share` | `no green blob of 2000 px or more` with `green pixels: N (x% of frame)` | a blob over 2000 px, or a frame-wide green cast |

`check-green-share` is the one number that is a measurement rather than a verdict: approved cel frames here run 0 to about 20 green pixels, 0.00 % of the frame. A cast is what matters — 6–27 % with blobs sitting on the subject is the series' old mascot body coming back, not clutter.

## The film-frame border trips two of them on every clean frame

The series' register includes a near-black print edge, roughly 17–18 px of `#010101` at the top and bottom of the frame. `check-palette-strip` reads it as a single-hue flat band on both edges and `check-blank-margin` reads it as `2 band rows / 2 band cols`. The palette report says as much in its own clause — *flat band on the top edge but a single hue, read the crop before deciding* — and the crop answers *the frame*.

So on a cel frame that carries the register:

- a single-hue flat edge is not a palette strip and does not hold a render;
- `2 band rows / 2 band cols` with a 5–7 % fill share is not a blank margin;
- `card-embed-coverage.py` runs the same check, so its `UNCOVERED` line on an already-approved header of this series is the same false positive. Confirm the card carries the slot's item and let the flag go.

The flag that *is* real: a pale or dark region with no ink, settled by a column profile (`scripts/check-pale-band.py <png> --columns …`) rather than by a second vision read, and a band the render left because the prompt named a shadow by location. Both cases are in `references/archive/hold-back-or-ship.md` under the pale-band section.

## `check-grey-bars` is a byte heuristic, not a read

It decides "full grey box" from a file size under 0.4 MB, and every frame from the nano banana engine comes back at 0.17–0.24 MB. It fires on all of them. Read the frame, pass a painted scene, and name the warning on the card in one line — never hold a render on it. `check-flat-bands` fires on all cel art by construction: it is a prompt to look, never a verdict.

## On a review card the edge profile is the gate, and a band at an edge is measured per row

`check-grey-bars` prints a pass line per file *and* a grey total for the frame. On cel art the total fires on painted skies and floors, so the pass line is the part to read — and neither line is a verdict about an edge. A full-width flat band that touches the frame edge is not scenery and has to be measured: a painted floor carries grain, shadow and an object crossing it, while an unrendered band is one colour from edge to edge with no ink at all.

Profile every existing draft image before it goes on a backlog-review card. PIL, `lum = a.mean(axis=2)`, `dark = (lum < 200).mean(axis=1)`, printed in 16-row bands: a run of rows at 0.0 % dark over a uniform colour is the defect, and a run at 0.5–15 % is a painted sky or a dark room. The two failure shapes are a flat colour from edge to edge with zero ink (a band the engine left unrendered, the desk and the crate ending well short of it) and ink only in the middle of the frame (a picture pasted on a white card). Both had passed the script's pass line, so the script's pass line is not clearance for an edge. Both slots were held back, the card that already carried one of them was withdrawn before the verdict, and both prompts were rewritten for a scene painted to all four edges.

The numbers belong in the check note beside the script's pass line, because the pass line alone reads as a clearance on a frame whose bottom fifth is empty. Write them as a per-row profile, never as a single overall percentage, which hides a full-width band behind an average that still looks healthy.

## `verify-slot.py --earlier` and `--post` are `append`, so repeat the flag

Both arguments are declared `action="append"`, not `nargs="+"`. Passing two records after one `--earlier` fails argparse with `unrecognized arguments: <second record>` before any check runs, which reads like a broken flag rather than a call shape. Repeat the flag once per earlier record, and repeat `--post` the same way when a slot names two.

## A wake on a card that is already pending

Read `unresolvedInteractionIds` in the wake payload first. If it names your card and the interaction comes back `status: pending` with `result: null`, there is nothing to apply: run the trio plus the hash/byte table read-only, confirm every attachment matches, leave the issue `in_review`, and post no comment — the card is the ask, and a "still waiting" comment only stands between the owner and the rows he is judging (a user comment on a targeted card can close it).

Do not spend a fresh vision read on frames whose check note already carries one. The note is frozen on the card, the verdict is the gate, and a reader that times out or errors has no decision to change — write up the scripts' numbers and stop there. Re-running the read is how an unavailable reader turns into a fake hold-back story.

## Tesseract can read noise from button-like shapes

`check-grey-bars` and the tesseract pass are two different things. Tesseract is a reader, and on a frame full of round lamps, buttons, or small painted marks it will emit short words ("Steers", "09 2 ak") that are not on the picture. In this session the flux companion's tesseract output read "Steers e" / "09 2 ak Cy QD" while a vread.py read of the same frame found no readable text at all — the words came from button shapes in the lamp grid and the robot's chest monitor, not from lettering.

Rule: when tesseract reports short words on a frame that is not supposed to carry text, do not put them on the card as a defect until a vision read (`vision_analyze` or `vread.py`) confirms them. A tesseract hit with no vision confirmation is a candidate, not a finding. Quote the vision read (and name the reader) in the check note either way, so a later round does not re-measure the same frame.

## Re-run them on the vault copy after the card closes

Staging was checked as a candidate; the vault copy is what the post serves, and the card's own run performs the copy. After the close, hash each vault file against its staging twin (`shasum -a 256`, `stat -f%z`) *and* read the verdict lines above on the file that is actually embedded. An approval names a job id; only the hash plus that check say the right picture went into the draft, and this is the cheapest place to catch a card run that copied one of two similar frames.
