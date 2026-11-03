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
   A crop of the wrong region reads confidently and wrongly, so the box must come from the pixels. **A read that says the crop holds none of the subject is a claim about the crop, not about the render.** The model answers the region it was handed, so a box a few hundred pixels off comes back described as a hinge, a doorknob or a bare wall — sometimes with a cast from a completely different film — and the tempting conclusion is a missing prop that is right there in the frame. Re-locate on the mask and crop again before any note says a prop is absent; the give-away is a read whose subject list has nothing in common with the prompt.
   the pixels.
   - **Some subjects have no colour signature — a wall of openings does not.** Then
     crop a *band* wide enough to contain the subject and its neighbours, read the
     band, and re-crop the exact thing. On the port80 header a crop of the right
     wall of server racks answered "there are no doorways here, these are cabinet
     fronts" while the back wall next to it held two hangar doorways, one open and
     one a closed roller shutter. A tight crop of the wrong half of a room gives a
     confident, false inventory. Read the band first, then the subject.
2. **Write the crop to disk and analyse the file.** An upscaled crop of the exact
   subject (3-4x, LANCZOS) is a stable input: the same file always reads the same way.
3. **Count the claim when it is countable.** Tick marks go in an angular histogram
   around the detected centre, one bucket per hour position. Overlap goes in a pixel
   cross-count. A veil that drapes a subject has veil-coloured pixels **on** the
   subject's pixels; a shape behind it has none, and the count of zero is the answer.
   - **A number in the note must come from the count, not from the read.** A note that
     says "one glare" or "two bars" is a countable claim, and a vision read of a prop
     routinely undercounts it: a read of a lens said "one curved white glare" where a
     blob count found **two** white marks, the larger a filled shape at 42% of its own
     bounding box rather than a thin streak. The card's text is frozen at the POST, so
     a count that a `--find` blob sweep contradicts has to be fixed before the card
     goes up, not after. Count the blobs (`--find <colour> --min-px <small>`), and for
     each one compare its pixel count with the area of its own bounding box: a thin
     streak fills a small fraction of its box, a filled blob fills a large one, and
     that ratio is what tells "a highlight" from "a solid shape".
   - **Count every mark on the prop, not just the one that draws the eye.** A prop can
     carry a small second mark that the read folds into the background. Sweep the
     whole prop region for the colour and enumerate the blobs, rather than reporting
     what the read happened to single out.
   - **When the claim is a number of instances in the frame, the box has to come from a
     frame-wide sweep.** A crop of a band you picked answers about that band: a 3x crop
     of the middle of a wall reported one red cross where a frame-wide `--find` found
     **two**, the second sitting well outside the crop. So a count read off a chosen
     region is not a frame count, and the note either names the region it counts or
     rests on the sweep.
   - **A pasted overlay is counted the same way, and its cards are the unit.** On a frame with flat UI panels pasted over a painting, count the panels per fill colour (`--find <r,g,b> --tol 45 --min-px 2000`) and name the unit in the note — "two green cards (x195-546 y573-731, x733-1035 y133-270), three blue badges, one yellow badge". The full-frame vision read is not a count: it lists what it happened to notice, and a note written from the impression of "it looked busy" put **eight** pasted panels on a frozen card where the sweep finds **six**. Sample one pixel of each panel to get its fill colour first (a panel's fill is rarely the prompt's palette hex), and drop the number entirely rather than guess if the sweep cannot separate a panel from painted scenery of the same hue.
   - **A crop also undercounts a stack of overlapping identical objects**, because it
     sees only the sheets that reach into its band. A fan of six paper slips read as
     **three** in a 2x crop of the right side and as **six** in a frame-wide blob
     sweep, and the six matched both the prompt and the post's alt text. So when the
     objects overlap each other, the count comes from the sweep with the fill colour
     and a tolerance wide enough to catch every sheet, and a crop's lower number never
     becomes the note.
   - **When the count and the read disagree, check they counted the same objects
     before you pick a side.** A read of a ring of keys said "four keys" where a disk
     crop of the hand showed three: the fourth round shape was the master ring the
     fingers grip, not a key. That is not an off-by-one, it is a different object
     counted in, and a bare "three keys" leaves the disagreement open on a card
     Wojtek reads. Write the unit into the note — "three keys (a round bow plus a
     shaft with teeth each; the extra round shape is the master ring)" — because a
     bare number is a claim he cannot check.
4. **Cross-check the read against the count.** A read that says "twelve tick marks"
   and a histogram that finds eleven do not both get to stand. Re-crop wider, re-read,
   and let the number settle the fact. **When the count and the read disagree, the
   count wins** and the note is rewritten — the image did not change, the note did.
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

**Use this script; do not hand-roll a cropper in a scratch directory.** Writing a
throwaway PIL script to do the same job costs a write and a run, and it drifts from
the shipped one: `--box` is `x0,y0,x1,y1`, the script prints the region it actually
cropped, and that printed box is the record of what was read. A one-off script in
scratch keeps neither, so a later reader cannot tell which pixels a claim rested on.
When the shipped script cannot do what a check needs, extend it — that keeps the
procedure in one place for every later card.

Four more shipped probes cover the questions this script cannot:

- `scripts/ascii-render.py` — prints a region as text, `--mode shade` for a whole
  region and `--mode ink` for the drawn strokes alone. This is the tie-breaker when a
  zoomed read of a small prop is unstable; see the section above.
- `scripts/check-off-scene-colour.py` — measures colour a frame carries that its own
  scene does not own, per image, so a "colorful artifacts" clause is answered
  comparatively against the rejected original and an approved sibling.
- `scripts/measure-bodies.py` — counts the separate bodies a material mask holds and
  measures whether the largest one is continuous and whether two bodies sit aligned
  (one object broken in two) or offset (a stack). This is the probe for a
  **structural** claim, which no read settles; see the section above.
- `scripts/check-defect-signature.py` — measures the pasted-overlay signature
  (saturated blue pixels, near-white flat blobs of 400 px or more, rows that are both
  flat and saturated) on a candidate **and** on baseline frames, so the verdict is
  "the candidate is at zero and the known-bad frame is not". **Every comparison probe
  in this skill takes positional image paths with the candidate FIRST and no flags**
  — `check-defect-signature.py candidate.png approved.png bad.png`,
  `check-off-scene-colour.py rejected.png candidate.png approved.png`. There is no
  `--baseline` and no `--compare`; inventing one costs a call and returns a usage
  error that reads like the script is broken. Read `--help` on a probe you have not
  called in this session rather than guessing its flag names.

**A flat-band report on a wooden scene is expected, not an alarm.** The flat-band
heuristic cannot tell a painted board from a rendered swatch strip, so a frame whose
middle is a plank, a bench top or a wall of boards trips it by construction. Its own
output says so — *"Read a crop of it before deciding"* — and the crop decides (this is
engine-pitfall #66: a detector, not a judge). Do not re-render a frame because a
wooden scene has a band of wood in it.

**Settle the band with the same rows measured on an approved sibling, because the crop
can be argued and the number cannot.** Read the report's row span, then measure those
exact rows' luminance standard deviation on the candidate **and** on an approved frame
of the same series. Painted wall and lamplight carry the same texture the approved frame
carries — a flagged strip measured std 46.67 against 45.86 on the approved header of the
same post, and a 2x crop of it showed wall, a wall corner, a shelf edge and a pendant
lamp, so it was scenery and the strip reading was the false positive. A rendered
`color_palette` strip is the opposite shape: near-uniform rows whose std is in single
digits. Quote both std values in the note; "it looks like wall" is a read, and the pair
of numbers is the measurement.

**Quote the whole row list, not the first row.** A painted concrete wall trips the
same probe on a score of separate single rows — one render reported rows 65, 79,
103-105, 112, 166-168, 186, 190-192, 195-197, 200-204 and onward past 290 — so a note
saying "fired on one row" under-counts the detector by an order of magnitude and reads
as a single strip where the frame has scenery. Run the probe, count the bands, and
write either the count or "fires on many separate rows of the painted wall". A brief
inherited from an earlier run can carry the under-count, so re-run the probe rather
than copying its number onto the card.

**A scratch script is a last resort, and a fleet of them is a smell.** Six
throwaway probes written in one session to settle one small claim is a signal that
the question needs a shipped probe instead, because the next card will ask it again
and the fleet will have drifted apart. When two or more scratch scripts answer
neighbouring questions, promote the one that works into `scripts/` and delete the
rest.

**A zoomed read of a small prop is not stable, and the way out is to print the pixels**

**A figure's gaze is a geometric claim, and a read gets it wrong by looking at the head.** Which way a character looks is not settled by "the head is turned left" — it is settled by where the iris sits inside the eye opening, against a reference the crop itself provides. **Establish the nose first**: in a profile or three-quarter view the nose bridge lies on one side of the eye, and that side is the direction the face points. Then read the iris against it: an iris pushed toward the nose side means the eye is rotated the way the face looks, and an iris pushed toward the lower lid means it is looking down. A downward gaze and a leftward gaze look the same in a small crop until the nose is located, which is why a read of a head can report "looking down" for a figure that is plainly looking sideways. Check "is the iris displaced toward the lower eyelid?" as a separate question, because that is the one that decides it. On 2026-10-26 the `header-docs-mcp-transport` r6 render was reported by a brief's check note as having its eyes down on a tablet; five disk crops at 4x to 16x found the nose to the LEFT of the eye, the iris in the LEFT part of the eye opening and no displacement toward the lower lid, so the gaze was on the chained door — and Wojtek approved that render. **A brief's check note is one run's read, so a figure's gaze in it is a read like any other, and the crop decides.** A note that survives on a card is a note Wojtek judges from, so a gaze claim belongs on the card only after a crop has settled it; and a "deviation" copied out of a brief into a lesson becomes a rule that sends the next render after a defect the picture does not have.

A vision read of a *large* prop settles a question. A vision read of a **small** one
often does not, and the failure is specific: upscaling a 20x12 px label with LANCZOS
adds moire, so the same region reads as "blank" on one crop and "two rows of dash-lines
standing for words" on the next. Two reads of the *identical* file disagreed outright,
one at 12x and one at 16x, and a third read of a wider crop of the same boxes reversed
the answer again. The cardboard texture is not text; the interpolation invents it.

So when the claim is about a prop only a few pixels across, **print the pixels instead
of asking the model about them**:

```bash
~/image-studio/.venv-imgcheck/bin/python ~/.hermes/profiles/matejko/skills/image-studio/scripts/ascii-render.py \
  "$PNG" --box 1105,595,1135,630 --mode ink
```

- `--mode shade` maps every pixel's darkness to a character ramp, so the whole region is
  legible as a picture.
- `--mode ink` prints only pixels below `--threshold`, so texture washes out and the
  **drawn strokes** are all that remain. A flat label shows a plain rectangle; a label
  with dash-lines shows the horizontal bars. This is the mode that settles the claim.
- `--cell N` adds a per-cell ink count over an NxN grid, which locates the strokes
  without reading them.

The output is the evidence: what is in the note is what the text shows, and a later
reader can re-run the same command and get the same characters.

**Do not hand-roll a detector for this.** A hand-written "find the label rectangles"
pass over a 1216x832 render reported **7242 candidate rectangles** and 48 "labels with
dash-like strokes" — it was matching wood grain and rope edges, not labels. A detector
that finds thousands of candidates in one frame is measuring the wrong thing; a
detector's output magnitude is a health check on the detector, not a fact about the
image. Detect the prop by a property it actually has (a light fill, a local contrast
against its surroundings), and when the numbers stay implausible, go to the pixels
rather than tuning the threshold. `scripts/crop-probe.py` is the shipped probe; when
it cannot answer a question, extend it rather than starting a new one.

## A structural claim ("one object broken in two, or several objects?") is not settled by a read

A read settles what a thing **shows**. It does not settle what a thing **is** — whether
the pale board running across the frame is one plank cut in two, or two boards lying
together; whether a chain is one chain or three links; whether a wall is a wall with a
doorway in it. Those are structural claims, and the evidence is the **arrangement of
the bodies**, not their appearance.

This is the one claim type where the read is not merely unreliable but **biased by the
question**: ask a crop "is there a visible saw cut with sawdust in the gap?" and it
finds a cut; ask the overlapping region "is this a continuous board with a shadow
line?" and it finds a continuous board. Two reads of the *same* pixels at 7x and 8x
answered opposite ways, and the wrong one was the confident one. A read asked about a
specific mechanism will supply that mechanism, because a model completes the story it
was handed.

So the structural claim is settled by counting the bodies and measuring how they touch:

```bash
~/image-studio/.venv-imgcheck/bin/python ~/.hermes/profiles/matejko/skills/image-studio/scripts/measure-bodies.py \
  "$PNG" --box 100,380,1216,560 --preset pale --min-px 300
```

- **Bodies** — connected components of a material mask, each with area and bbox. How
  many separate objects the pixels actually contain.
- **Continuity** — for the largest body, the x ranges inside its own row span where
  the mask drops to zero. **No interior absence means the body is one unbroken piece**,
  however many seams a read sees drawn across it. This is the measurement that
  settles "cut in two" outright: a cut leaves an interior absence, a seam does not.
- **Separation** — for two bodies divided by a narrow horizontal gap: the gap width,
  and whether their vertical spans are **ALIGNED** (same top and bottom, so one object
  broken in two) or **offset/nested** (one board lying on another, a stack). A cut
  gives two aligned pieces; a stack gives one piece sitting on another.

**The gap's own pixels confirm it.** An open gap shows the background through it and
dips in luminance against the flanking surfaces; a drawn seam or shadow line on a
continuous surface does not dip. The script prints the gap luminance against the
flank, so the difference is a number rather than a read.

**A "gap" in a mask is not always a gap in the object.** A mask that includes skin
splits at the man's face and at his hands, and the component analysis then reports
what looks like a break in the wood. Use the `wood` preset, which excludes skin
(skin is pinker: a much larger R-G than G-B), before concluding that a body is
broken. Reading the crop of the supposed gap settles which it was — in one case the
"gap" was a face and the plank was continuous.

**Name the reading that won.** When the inherited note says the cut is legible and
the measurement says the body is continuous, the note goes up with the measurement
and says which reading won — the alternative is a card whose text Wojtek judges from
a claim the pixels contradict.

**Two box orders live in this skill, and transposing between them is the easy
mistake.** A prompt's element `bbox` is `[y1, x1, y2, x2]`; `crop-probe.py --box` and
`measure-bodies.py --box` are `x0,y0,x1,y1`. An agent that has just been reading
prompt boxes will transpose the first call it makes. **The guard is the printed
line**: both scripts print the region they actually used (`region x[300-1216]
y[300-560]`), so a transposed box is visible in the output and the call is free to
redo. Read that line before trusting any crop of it.

## A visible-gap claim is measured across the gap, and the picture's whole point can rest on it

When the picture exists to show that a part does not fit — a block slack in a socket, a
plank short of its stop, a door not meeting its frame — the gap **is** the story, so the
self-check has to answer "is the gap visible" with a number rather than a read
(engine-pitfall #71). This is also the claim most likely to be measured while vision is
rate-limited, so the mechanical answer has to be good enough to carry the note on its own.

The probe is a horizontal profile across the region, row by row: threshold dark, group
consecutive columns, and keep runs of eight pixels or more. Then sample the three
segments — left flank, the part, right flank — and compare mean luminance and colour.

Use `scripts/gap-profile.py` rather than writing this again:

```bash
~/image-studio/.venv-imgcheck/bin/python ~/.hermes/profiles/matejko/skills/image-studio/scripts/gap-profile.py \
  "$PNG" --box 660,480,1020,680
```

`--box` is `x0,y0,x1,y1` in pixels, and it must be **wider than the part** so both
flanks fall inside it — a box clamped to the part measures the part and nothing else.
The script flags any row carrying two dark runs, and says so plainly when no row does.
A claim like "the gap reads on both sides" is the class of sentence that got hand-rolled
into three separate scratch profilers in one session; the question recurs on every
"does not fit" picture, so it belongs in `scripts/`.

- **Both flanks must be dark and the part brighter than both.** One dark side is a
  shadow, not a gap. A block seated in a socket read flanks at luminance 42 and 37
  against the block's 78.
- **Name the runs in the note**, not just the verdict: `at row 570, dark runs at
  x 686-819 and x 917-1003 either side of the brighter block` is a claim a later
  reader can re-run; "the gap reads on both sides" is not.
- **A gap that closes has lost the picture its point** even when every prop the prompt
  named is present, and the repair is to widen the opening or the part's own `bbox`,
  not to add adjectives to the description.
- **A part described as standing "in" a socket can render passing through it**, with
  its lower half hidden below the bench top and no gap legible at all. The profile is
  what distinguishes that from a seated part, so measure before the card says "seated".

## A contact or seating claim on a 30 px prop is not settled by any reader

"Is the plug in the port, or lying against the machine?" is the one claim where a
read does not just wobble — it splits, and the split does not close with magnification.
On one render the same 8x disk crop of the joint answered twice, opposite ways: *"the
front end inserts directly into a dark port"* on the first pass, *"its outline is
visible all the way round as a closed end cap, so it is resting on the table"* on the
second, and a full-frame read agreed with the second. Both readings are internally
consistent. That is what a ~30 px prop in a 1216 px frame does: the model completes
whatever story the question implies, and "is it inserted" and "is it resting" each
have one.

So a contact claim is measured, and the measurement is **what material lies beyond the
part**:

- Sweep across the contact, row by row, and classify each pixel by its nearest
  reference colour — the cable's hue, the part's pale fill, near-black, the target's
  body tone, the surface the target stands on. The sequence is the finding:
  `blue -> cream -> near-black -> wood` and `blue -> cream -> near-black -> device grey`
  are different pictures, printed rather than described.
- **Beyond the part is the target's own body tone: it is seated.** The dark band is the
  recessed socket, and the note can say the part goes into the machine.
- **Beyond the part is the surface the machine stands on: it is not seated.** The dark
  band is the part's own cast shadow, the end cap faces the bench, and writing "seated
  in the port" on a card describes a picture that is not there.
- A 15-20 px dark band between a pale part and the target cannot settle anything on its
  own — it is exactly what a shadow and a recessed socket both look like. It is the
  far-side material that names the case.
- **State the cable's continuity separately, because it is countable.** A hue sweep
  gives the run's pixel count and bbox (`1206 px, x 120-496, y 375-581, one continuous
  tube`), which answers "does the cable reach the machine's vicinity" without touching
  the seating question. The two are different claims, and collapsing them is what lets
  a note assert the harder one on the evidence of the easier one.

**A deciding claim that the pixels argue about is a composition defect, not a wording
problem.** If the picture exists to show that a part reaches its target, a joint too
small for two readers to agree on cannot be judged by Wojtek either, and the repair is
not another adjective in the prompt: it is distance. Give the subject of the picture
roughly three times its current pixels — crop in, drop the far half of the room, and
let the connector enter the frame's edge in one straight diagonal to the part, because
**a cable that comes in from off-frame cannot stop short of anything**. Re-rendering
the same wide composition with "pushed fully home" in the prompt spends 21 minutes on a
claim the frame's scale cannot carry.

And when the round ships anyway, the card carries the measurement and the disagreement
rather than the more confident of the two reads: the far-side material, the dark band's
width, the cable's counted run, and one sentence saying which readings split. A frozen
card with both readings is honest; one with the reading that suited the conclusion is
the defect he judges from.

**Shipping the split reading is the branch that has been tested, and it is the cheaper
one.** A round-2 card that carried exactly this — the far-side material left unmeasured
because it would not settle, the dark band's width, the cable's counted run, and one
sentence naming which reads split — came back approved with no reason, so an honest
card costs him a look rather than a rejection; holding the render back and spending
another 21 minutes is not the safer choice when the picture clears the reason he gave.
The usual limit applies: a silent approval endorses the picture and says nothing about
whether a joint that size should be the subject again, so the composition fix above
owns the next round on that slot.

## Judge a prop against the series, not against an absolute standard

A small detail on one prop is not a defect on its own. The question is whether it is
**how this series draws that prop** — and the way to answer is to measure the same
detail on an image Wojtek has **already approved** from the same series, with the same
script.

Measured the same way on the same post: the candidate render carried one box label
with dash-lines, and the approved header of that very post carried **three** of them.
The candidate was the cleaner of the two, and the detail was a texture the series uses,
not a defect in the candidate. Judging the candidate alone would have put a false
defect on a frozen card and cost a round of his attention.

So: **before a small detail goes on the card as a defect, measure it on an approved
sibling image.** Same script, same parameters, same question. If the approved image
carries it too, it is series texture — say so on the card with both numbers, and let
him judge. If the approved image does not carry it, the detail is specific to the
candidate and the note stands.

The same comparison settles a "colourful artifacts" rejection clause. A channel-spread
test cannot measure it, because wood, rope and cardboard are all brown and brown has a
large channel spread — a spread test flags a third of a clean frame as saturated. What
the rejection named is colour *off the scene's own hue axis*, so measure hue, and
measure it comparatively:

```bash
~/image-studio/.venv-imgcheck/bin/python ~/.hermes/profiles/matejko/skills/image-studio/scripts/check-off-scene-colour.py \
  rejected.png candidate.png approved.png
```

The script reports, per image, the vivid pixels whose hue falls outside the scene's
axis, a hue histogram, the **largest contiguous off-scene region** and the busiest
32x32 cell. The last two are what separate the two cases: a pasted banner is one big
contiguous block that fills cells entirely, while scattered scene props are many small
ones. The numbers are only meaningful as a row against the rejected original and the
approved sibling, which is why the script takes several images and prints them
together.

## A note that is under-specified is not the same as a note that is wrong

When a claim on a frozen card turns out to be less well-founded than the check
supported, the card cannot be edited — but it does not need to be either. If the
measurement settled the *direction* (the detail is present, and the approved sibling
carries it too) while the *exact wording* overstated it, then the note is a report for
Wojtek, not a defect in the picture: say what was measured, name the comparison, and
let him judge. Withdrawing and re-posting is for a note that is **wrong** — the
picture does not hold what the note says. A note that is hedged and carries its own
evidence does not need the churn of a second card.

**Do not leave a claim on the card that your own later measurement contradicts,
though.** If the pixels say the opposite of the sentence in `detailsMarkdown`, the
sentence is the defect, and the withdraw-and-re-post route in the skill applies. The
discipline is to run the measuring before the card goes up, not after — the card's text
is frozen at the POST, so a claim that is going to be re-measured belongs in a comment
until the measurement is done.

## Comparing two instances of the same motif

When the picture is supposed to show **one thing and a copy of itself** — two seals
carrying the same engraving, two keys with the same teeth — the claim to settle is
whether the two really match. A note that says "the same pattern" is only as good as
the comparison behind it, and the comparison has a way of going wrong:

- **A side-by-side montage is not a comparison.** Pasting the two crops into one
  image and asking "do they match?" shrinks each and invites the reader to describe
  the difference between the panels rather than the pattern in each. A montage read
  reported one disc as a single spiral and the other as a double, while separate
  full-scale crops of the very same two regions both reported a double spiral. When
  the montage and the separate crops disagree, the montage is the unreliable one.
- **Compare like with like, at the same scale, one property at a time.** Crop each
  instance separately at the same magnification, read each on its own, and only then
  compare the answers.
- **Zoom the discriminating feature, not the whole face.** For a spiral, the eye at
  the centre decides single versus double, and the whole-face read is the one that
  wavers. Two 640x640 crops of the centres answered the same way — two hooks curling
  toward each other across a gap of bare gold — and settled the claim that the two
  engravings match. The outer turns of a spiral read as "concentric rings" at low
  magnification, so a full-face read of one can call the same engraving single.
- **Say what the comparison rests on.** "Both eyes are a pair of facing hooks, zoomed
  to 640 px each" is a claim Wojtek can trust; "both carry the same spiral" is a
  conclusion he cannot check.

## A downscaled full-frame read cannot be trusted for lettering

Fitting the whole frame inside the vision model's input costs the resolution that
in-image text lives in. A 900 px downscale of a 1216x832 render read a clipboard
header as **QUEST LIST** where a 10x disk crop of the same clipboard reads
**GUEST LIST** — G and Q differ by one short stroke, which the downscale smears
away. So a full-frame pass is the right tool for the whole-scene question (is this
one room, or a collage?) and the wrong tool for a spelling claim. Before a check
note says a word is spelled right, read it again on an upscaled crop written to
disk, and when the two reads disagree the crop wins and the note is rewritten —
never the other way round, because a spelling claim on a frozen card is the defect
Wojtek judges from. The same applies to a count: a full-frame read of a tiny ticket
reported "no marks below the word" that a tight crop and a blob sweep both found.

## When two reads disagree on the characters, the disagreement is the finding

A card must never quote lettering it cannot confirm, and on a small label it usually cannot: two reads of the same prop — a full-frame pass and a 3-5x crop written to disk — routinely return different strings for the same pixels (`WOTCK` on one pass and `WOLTEX` on the next, `Volt` on one and `MARMITEK` on the next). Neither is a transcription, and a quoted string is a spelling claim that a later crop can contradict on a card that is already frozen.

That disagreement **is** the measurement: invented pseudo-text reads as *different plausible words on different passes*, where a spelled word reads the same way twice. So the note states the finding without picking a side —

> a flat logo sits in the top-left corner with invented lettering under it; two reads give different strings for the same pixels, so it is pseudo-text rather than a word

**A disagreement where one string is a substring of the other is a crop cut, not a second reading.** A crop whose `--box` starts inside a word returns that word minus its leading characters — the full frame reads `ALLOW-LISTSEK` and a crop beginning 180 px in reads `LOW-LISTSEK` — and that is the box edge, not the model wavering. Two reads of pseudo-text give *different plausible words* (`WOTCK` / `WOLTEX`); a read that returns a **prefix or suffix of the other string** is the same lettering cut short, so move the box past the start of the line and re-read instead of writing the disagreement up as pseudo-text evidence. **And quote one string on the card:** `items[].description` and `detailsMarkdown` are separate fields written at different moments, so the same lettering appearing as `ALLOW-LISTSEK` on the card face and `LOW-LISTSEK` in the long note reads as a contradiction in an artifact he judges from and cannot be corrected. If the line runs to the frame edge and no wider box exists, the claim is "invented lettering on the page" with no quotation.

Two cases where a single reading does stand: **a word read at the size the picture ships** (a legible brand wordmark, a large sign), and **a string the prompt specified exactly**, because there the picture is meant to carry that text and the model has a word to be faithful to. Pseudo-text is by definition text nobody specified.

## A stylized letterform is not a misspelling

In-image lettering is drawn by a model, not typeset, and a drawn glyph can carry the shape of a letter the word was not meant to contain. A long-s — a tall stem with a crossbar, the `ſ` of an old-style serif — reads as an `f` at high magnification; the word around it still reads as the word. So a single glyph zoomed to the pixel is the worst possible instrument for a spelling claim, and a read that reports a wrong letter does not get to overrule the word.

The claim to settle is therefore the word, at the size the picture ships:

- **Read the word, not the glyph.** A crop of the whole line of text at 3-4x settles the spelling; a crop of one character only tells you what that character looks like.
- **Read at the published size, then at magnification.** A word that is unambiguous at 1x and ambiguous at 16x is legible text with a fussy letterform, not a typo. The published size is the size Wojtek reads it at, so that is the size the claim is made at.
- **Say so in the note when the zoom disagrees.** `"the second line reads per-session; zoomed 16x the first s is drawn as a long-s, so it can be misread as f, but at published size it reads per-session"` is a claim he can check and a defect he can judge. `"the second line reads per-fession"` is a misspelling claim resting on a magnification the picture never shows.
- **The same rule governs a single ambiguous digit.** A number drawn in a hand-lettered style can carry a stroke that reads as another digit at high zoom; read the whole numeral in the run of numerals, and settle the digit by how the sequence reads, not by its isolated shape.

## Sweeping a colour to prove an accent sits on one prop

Some of Wojtek's standing rules are about *where a colour appears*, not about a
shape: one gold accent only, never gold on every prop. A read settles that
poorly — it says "the key is gold" and stops, and it cannot say whether the
safe, the stool and the robot also carry gold.

The measurement is a colour sweep over the whole frame, with the same script:

```bash
~/image-studio/.venv-imgcheck/bin/python ~/.hermes/profiles/matejko/skills/image-studio/scripts/crop-probe.py \
  "$PNG" --find 245,158,11 --tol 90 --min-px 40
```

- **A blob is a colour region, not an object.** One gold-accent frame came back with
  three blobs: 2325 px on the key's shaft, 366 px on the key's bow and 366 px on the
  lantern's flame. The key is *one* object in *two* blobs, because the ring's hole
  splits the bow from the shaft. The number of blobs is never the number of props.
- **A sweep finds light sources and lit edges as well as props.** The flame matched
  the accent colour because the model drew it that way, and at a looser tolerance the
  lantern's guard bar picked up a 65 px warm rim. Read a crop of each blob before you
  count it as a prop, and say in the note which blob is the accent and which is the
  light.
- **Report the outcome, not the rule.** "The only gold object in the frame (blob
  sweep: 2325 px on the key shaft, 366 px on the key bow; the only other amber is the
  lantern's flame, 366 px)" is a claim that carries its own evidence. "One gold accent"
  without the sweep is a taste rule resting on a read.
- **Do not sweep for a `color_palette` hex to prove a shape came from the prompt.** A
  cel-shaded render repaints flat colour with its own shading, so an exact-hex `--find`
  on a palette entry returns **0 blobs** on a picture that plainly carries that hue:
  four palette entries searched at `--tol 12` all reported 0 against a corner holding
  blue, green, orange and red. That zero is a false negative about the render, not
  evidence that the shape is a prop, and a note built on it says the opposite of the
  picture. Sample the region's dominant colours instead — a `Counter` over the crop
  for the top handful of hexes — and compare hue and saturation to the palette entries
  approximately (same hue family, strong saturation). Then say what was measured: the
  blocks carry the prompt's own blue, green, orange and red, or they carry hues the
  prompt never asked for. Never report a match verdict that rests on a failed search.
- **The sampled colour is also what you sweep with.** The `Counter` pass is not only
  for the hue comparison: when the note needs a pixel count or a bounding box for a
  shape the prompt calls a palette colour, its second step is
  `crop-probe.py --find <the sampled r,g,b> --tol 30-50`. A flat graphic element comes
  back as one blob filling most of its own bounding box — a flat green bar measured
  10,504 px inside a 328x33 box, 97% fill — and that ratio plus the bbox is both the
  number for the card and the region to crop. The same sweep on the prompt's hex
  returns 0 and settles nothing.

## A flat block and a painted prop look the same in a read, and a guessed box measures the wrong pixels

Three reads of one blue rectangle disagreed: a whole-frame pass called it a pasted browser window, two 4x disk crops called it a textured poster board standing in the room. The statistic meant to settle it did not, because the boxes it was computed over were picked by eye — a box that overruns the block includes the wall, floor and figure around it, and the variance of *those* pixels is exactly what makes a flat panel read as "textured, so painted". On one frame the suspect panels measured a channel std of 40-80 in hand-picked boxes, which is the same range the genuinely painted furniture gave.

**The measurement is only meaningful inside the blob's own bounding box, and that box comes from a sweep**, never from your estimate of where the block sits:

```bash
~/image-studio/.venv-imgcheck/bin/python ~/.hermes/profiles/matejko/skills/image-studio/scripts/check-blank-margin.py "$PNG"   # frame-level fills first
~/image-studio/.venv-imgcheck/bin/python ~/.hermes/profiles/matejko/skills/image-studio/scripts/crop-probe.py \
  "$PNG" --find 53,125,211 --tol 45 --min-px 3000   # the block's own bbox
```

Then read three things off that bbox and nothing else:

- **Fill ratio.** A blob whose pixels fill most of its own bounding box is one flat graphic — 100,277 px inside a 363x284 box is 97% fill. A prop with grain, shading or an ink rim fills less and varies more inside the same box.
- **Edge contact and perspective.** A block flush to two frame edges and drawn straight-on, with no convergence against the room's own lines, is pasted on the frame. Concluding that from the read is what the two crop reads disagreed about; concluding it from the bbox is not a read.
- **The prompt.** A prompt-named prop may be flat and straight-on and still be the picture's own content, so name the prop the prompt asked for and treat the extra block as the deviation. On one header the prompt asked for one small browser window: the window at the lower left was the prompt's (title bar, three window dots, a padlock glyph, no lettering) and the second flat board at the lower right was the object no prompt element accounted for.

When the read and the numbers still disagree after that, put the numbers on the card with the read's own word for it — "a 4x crop reads it as a textured board; 97% fill of a 363x284 box flush to two edges and straight-on is the pasted-block geometry" — and let Wojtek judge. A frozen card that carries the measurement and the disagreement is honest; one that carries only the more confident of the two reads is not.

## An empty pale margin reports as a palette strip, and the fill share is the number

`check-palette-strip.py` answers about **rows**, so a draft image drawn on a plain studio field comes back with `PALETTE STRIP on the top edge: 91% flat columns and 3 hue groups in one row` when the frame simply has a blank pale border. The tell is in the block colours it prints: a band whose blocks are all near-white (`#F4FAFA`, `#F5F9FA`, `#F8FAFA`) is blank margin, not chips — a rendered `color_palette` strip carries the prompt array's saturated hues. Read the colours before the headline, as everywhere else in this file.

The measurement is `scripts/check-blank-margin.py`, which prints the dominant flat fill's share of the whole frame and the flat strip along each edge. One back-filled draft image measured **49.5% of the frame as a single flat pale fill, 116 rows over 80% pale, and the right-hand 107 px strip 99.8% blank** — an empty-margin defect `check-grey-bars.py` cannot see at all, because the fill is pale rather than grey, and `check-flat-bands.py` reports only as one of its many scenery bands.

Quote the share and the strip width on the card ("49.5% of the frame is one flat pale fill; the right 107 px strip is 99.8% blank"), never "lots of empty space". **`empty-margins` returns no rows at all from `verdict-class-rate.py`** — the table prints `no rows`, which is the class vocabulary missing the phrasing rather than evidence he accepts empty margins. Do not widen the script's keywords mid-card and do not invent a rate: say the class has no rows, and lean on the standing rule his approved cards have held — full-bleed to all four edges, no grey bars, no empty margins — then let him judge.

## A pasted graphic on a side edge is invisible to the band scripts

`check-palette-strip.py` and `check-flat-bands.py` both scan **rows**, so a flat
colour band running up the left or right edge of the frame passes both of them. That
is not a rare shape: one header render came back with a full-width banner along the
bottom **and** a flat panel up the left edge and two more up the right edge, all in
the prompt's own `color_palette` colours, and the two edge scripts reported only the
bottom one.

Locate the side panels by sweeping the block colours:

```bash
~/image-studio/.venv-imgcheck/bin/python ~/.hermes/profiles/matejko/skills/image-studio/scripts/crop-probe.py \
  "$PNG" --find 47,157,46 --tol 40 --min-px 3000
```

- **A flat pasted graphic is the exception to "do not sweep for a palette hex".** A
  cel-shaded prop repaints flat colour with its own shading, so an exact-hex search
  returns 0 blobs on a picture that plainly carries that hue. A UI banner or panel is
  drawn flat and hard-edged in the palette colour itself, so the sweep hits it. Sweep
  first and let the blob count tell you which case you are in before writing the note.
- **Read the blob's shape, not only its size.** `--find` bboxes are `x0,y0,x1,y1`, so
  narrow in x and tall in y is a vertical band. Three sweeps on that header returned
  `bbox=(0,0,63,349)` (a 64 px green panel down the left edge) and
  `bbox=(1136,263,1215,349)` with `bbox=(1136,351,1215,561)` (orange and blue panels
  down the right edge), beside the bottom banner's own blocks — the numbers name the
  edges, a read does not.
- **A side panel is the same pasted-graphic class as a bottom banner:** the same hard
  defect, reported on a round-1 card with the class rate quoted, never downgraded to a
  quirk because it is thin.
- **Read one upscaled crop of the panel before describing it.** A whole-frame read of
  that header called the left strip "a green block"; the crop showed it carried
  invented white lettering, which is the `unreadable-text` half of the same defect.
- **Say which edges you measured.** "Banner across the bottom 64 rows plus flat panels
  up both side edges, measured at x 0-63 and x 1136-1215" is a claim a later reader can
  re-run; "there is some UI chrome" is not.

## A flat colour cluster in a corner is a third shape the band scripts miss

`check-palette-strip.py` prints a headline, and `no palette strip on either edge` is a
statement about **rows**, not about the frame. One back-filled header came back with a
solid green rectangle 84x66 px bleeding off the top-left corner and a cluster of five
flat fills in the top-right — white disc, orange square, gold circle, light-blue band,
dark-blue wedge — and the edge script announced no strip at either edge.

Settle a corner with two probes, in this order:

1. `frame-map.py "$PNG" --box x0,y0,x1,y1 --cell 8` prints the region as a colour map,
one letter per cell (`Y` yellow, `O` orange, `B` blue, `R` red, `.` near-white, `-`
mid tone). It is the cheap way to see **whether** a corner holds a block of flat
colour and roughly where, before spending a crop on it: a run of one letter across
many cells with a straight edge is the cluster, scattered single letters are the
drawing.
2. `crop-probe.py "$PNG" --box <the corner> --scale 2 --out ...` and again at
`--scale 3`, each read on its own written file. **Two reads of the same corner at
different scales agreeing on the structure is the evidence** — that the shapes are
flat, unoutlined and axis-aligned — and it is stronger than one read at any scale,
because the failure mode here (a read inventing a tidy interpretation of a busy
region) does not reproduce identically at two magnifications.

Three rules keep the note honest:

- **The decisive tell is the missing ink outline.** In a series whose whole frame
carries bold black outlines — every series in this library does — a fill with no
outline, no shading and no perspective cue is a pasted graphic, however small it is in
the corner. Name the missing outline in the note; "it looks like a colour palette" is
a conclusion the reader cannot check.
- **The read's colour names are not evidence in either direction.** A crop of that
corner listed "white circle, orange square, golden-yellow circle, sky-blue band,
dark-blue wedge", and exact-hex sweeps for the prompt's own `color_palette` entries
found 0-7 px — so the shapes were not palette chips, and the read's names were still
approximations. Report the **structure** from the read and the **colours** from a
sampled `Counter` over the crop, and never let a hex sweep or a read's colour word
stand as the finding on its own.
- **A solid saturated rectangle that bleeds off a frame edge and whose colour appears
nowhere else in the scene is a generation artifact, not a prop.** Sweep it with
`crop-probe.py --find <r,g,b> --tol 40 --min-px 3000` and quote the bbox and the pixel
count — `bbox=(0,0,83,66)`, 5548 px, against a colour that appears nowhere else in the
frame. Those numbers are the whole claim, and they need no adjective.

**One post's images routinely share a defect family, so a clean PNG clears only
itself.** Three images from one post's batch carried a bottom UI band of flat cards
with misspelt labels, a full-width three-colour strip on the bottom edge, and the
corner cluster — one template behind all three, one probe each. Check every file on
the card.

## Two colour bands split at the same widths are the palette array rendered

One band along one edge is a candidate: it could be a painted floor, a shelf lip or a
coloured wall. **Bands along both the top and the bottom edge, split at exactly the same
x positions, are not scenery** — no room repeats a 387 / 88 / 211 / 134 / 392 px split
on two edges — and the second band's colours are usually the same array in a different
order, because the model lays the `color_palette` entries out twice.

- **Quote the widths once and say they repeat.** `five blocks at x 0-386, 388-475,
  477-687, 689-822, 824-1215 on the top edge, and the same five widths at the bottom in
  other colours` is the sentence that settles pasted-versus-scenery without a read; a
  bare "there is a colour strip" leaves the reader to take your word.
- **Read the script's `[TOP EDGE]` and `[BOTTOM EDGE]` blocks, never its headline.**
  `check-palette-strip.py` names one edge in the headline while printing both, so a
  note written from the headline puts one band on the card where the picture carries
  two, and the second is the one he sees.
- **A band can carry lettering, so crop each band before the note leaves it out.** A
  strip's caption block is where pseudo-text and misspelt words actually sit — a
  progress-bar-style top band read `Commit taking tfull imppprgatey`, and a bottom band
  read `Wojtok` — and neither is visible from the block widths alone.
- **The array is a trigger, not proof.** Two renders from one back-filled prompt family
  carried the same six-entry `color_palette`; one came back with bands on both edges and
  the other with none at either, and the clean one was approved. An array in the prompt
  therefore neither proves a defect nor clears one, and a note never says the palette
  array produced a shape unless that shape was measured on that file. Keep the three
  claims apart: the array is present (a fact about the prompt), a band is present (two
  row statistics and a crop), and the band came from the array (the widths and hues
  matching the entries).

## A proper noun the series already spells is the one text claim worth making

The same proper noun recurs across a series — the artist's signature, a product name
stamped on a prop — so its correct spelling is known before any model read of the
render. That makes a misspelt instance a plain defect with a known-right answer, not an
`unreadable-text` case, and it is worth stating as such because the distinction decides
two items on one card:

- **Painted into the art and spelled right is a quirk.** Name it with the spelling and
  move on; it is an invented inscription on a prop where a marking belongs.
- **Misspelt on a pasted band is a second defect on top of the pasted one.** Say which
  word, which spelling the picture carries, and which one is right — `the bottom band
  reads "Wojtok"; the series spells it "Wojtek"` — because "a typo on the banner" gives
  the next round nothing to fix.
- **Read the word at published size** as the stylized-letterform section says; the
  claim is the word, not a glyph.

## A banner in the middle of a painted scene passes every edge script

The band probes and the margin probe all look at the frame's edges, so an overlay that sits over the drawing in the lower third of a painted scene reports clean three times in a row. Measured on one header: `check-grey-bars.py` said "content fills the entire frame", `check-blank-margin.py` said "NO BLANK MARGIN" (dominant fill 5.3%), and `check-palette-strip.py` said "no palette strip on either edge" — while a flat UI banner (a blue rounded container, an amber text card and a pale pill button, carrying invented pseudo-text) lay over the rug and the figures' legs.

Settle it in three calls:

1. **Whole-frame read**, asking outright whether a flat UI panel, banner, button or swatch strip is pasted over the drawing, and whether the frame is full-bleed. A read that is never asked about overlays describes them as part of the room.
2. **Crop the region to disk** (`crop-probe.py --box … --out …`) and ask the same question of the crop, naming what is painted around it. Two reads of different regions agreeing is the evidence.
3. **Sweep the overlay's own fill colour** for its extent: `crop-probe.py --find <r,g,b> --tol 40 --min-px 3000` prints each blob's bbox and pixel count. `bbox=(194,578,857,770)` at 38,324 px plus `bbox=(525,733,910,806)` at 16,343 px for the container, and `bbox=(378,615,782,732)` at 40,664 px for the card, is the claim; "a banner across the bottom" is not.

**Do not take the extent from `check-flat-bands.py`.** On a painted scene it reports one multi-hue band spanning hundreds of rows — the drawing's own flat cel fills count as much as the overlay — so its row span says nothing about where the banner starts and stops. It is the trigger to go and look, not the measurement.

**The flat-and-saturated row count is the number that separates a strip from scenery, and `row-band.py` prints it per image.** It reports the rows that are both flat and saturated, the longest consecutive run with its row span, and then the wide blocks inside that run. A rendered `color_palette` strip is a contiguous run of 28-31 rows carrying four or five wide blocks in different hues across the full width; the painted header of the same post reported **0** such rows, so the run length is the finding and the presence of a band is not. Quote the run length, the row span and the block colours (`28 rows, y 804-831, five blocks orange/gold/green/purple/blue`) — and run the same call on an approved frame of the series, because a `0` there is what turns the candidate's number into a defect rather than a wooden floor.

**A large pale diegetic surface trips it from the other side, and that is the common false alarm on a handled draft.** A whiteboard, planner or board filling half the frame reports `PALETTE-STYLE BAND FOUND` plus dozens of multi-hue bands, because near-white flat fill and the board's own coloured column tabs are exactly what the heuristic looks for. Read the band's crop first: a painted board with tabs, note cards and a frame is scenery, not chips. Confirm with `check-palette-strip.py` (a real strip sits on an edge and repeats its widths), then write "no palette strip" and move on — the board is the section's own prop.

**A row of painted furniture trips the strip's own headline, and the headline is a row statistic, not a finding.** `check-palette-strip.py` answered `PALETTE STRIP on the top edge: 54% flat columns and 7 hue groups in one row` on a frame whose top rows are a perforated server rack, a pendant lamp and a white cabinet standing against a wall — three props with flat paint between them, and not one chip. Those counts are what a row of hard-surfaced objects *is*: flat columns because paint is flat, several hue groups because a room holds several colours. What separates chips from that row is geometry the numbers do not carry — chips sit **contiguous**, sharing their vertical edges with the next chip at one height, with no object outline and no scene light between them — so the headline is the trigger to tile that edge, never a sentence for the card. Tile it at 2-3x, read the tile, and write either the chip widths or the props that are actually there; a card that quotes the headline has told him the frame carries a palette strip on the strength of a lamp.

**Sweep by a sampled colour, not the prompt's hex.** A flat overlay is drawn hard-edged, but the model picks its own shade: an exact-hex search on the prompt's `color_palette` misses a banner painted `#2479D7` where the prompt said `#3B82F6`. `--tol 40` catches it, and a blob that fills most of its own bbox is the confirmation that it is a flat graphic rather than a shaded prop.

## Counting the cast is a crop claim, and an overlay in the frame corrupts it

A picture whose prompt names one figure can come back with two, and that is a real defect class (`wrong-count`). Count the characters off a crop that holds **every** one of them, at figure scale (4x), and say in the question what to leave out: a pasted UI panel sitting over the figures' legs invites the read to count a shape in the panel as a person, and a whole-frame read can split one figure into two just as easily.

Ask "how many painted characters are in this crop, ignoring the flat overlay" and have the answer name each one — shirt colour, hair, and what each hand is doing — because two men with different shirts and different hands on the props is a count a later reader can check. A bare number is not. On that header the middle man gripped the robot's raised claw and carried a rolled map at his hip while a second man held the open map in both hands; the prompt had placed one man pointing at the shelf.

**A limb count that comes out right says nothing about the hands themselves, so ask the hand question separately on a whole-figure crop.** A render can carry exactly two arms and two hands and still fail the owner's eye, because the engine's worst hand case is a grip on a thin vertical handle: the handle becomes a column and the fingers become five segments stacked down it, and the far hand opened near a prop fans out into too many elongated fingers. Both read as "more than one hand" at a glance — the class that gets rejected — and neither shows up in a count. So after the limbs check, crop the man at about 1.5x and ask how noticeable any hand oddity is; "obvious once you look" on a blog header is a hold-back, not a note. **But settle the threshold against an approved frame before the hold, not after it:** run the identical crop and question on an image of the same series the owner already approved, because this engine's cel-shaded fist reads as "stacked finger segments, clearly wrong" to a vision model even in pictures he accepted. When the approved frame rates the same, the hands are house style and the hold costs a render for nothing (post 035 spent one that way); the real fixes are compositional — a bigger prop so the grip is drawable, a closed fist with the thumb across the top, and the idle hand in a pocket. **The prompt remedy is composition, not more finger words:** enlarge the held prop so the grip is drawable at scale (a big brass rim rather than a thin stick), make the gripping hand a simple closed fist with the thumb lying across the top and the rest of the fingers curled out of sight behind the handle, and give the idle hand a trouser pocket so no fingers are drawn at all. Naming fingers positively is what produces fingers; removing them from the picture is what removes the artefact.

**The prompt is what grows the spare limb, so fix the wording and not only the check.** A prompt that gives the figure two hand jobs on the same side — "one hand holding the magnifier up to the slip, his other hand steadying the board's lower edge" — comes back with a third hand, because the model satisfies both descriptions instead of deriving them from one pair of shoulders. Write the count into the prompt: name the total ("exactly two arms and two hands"), give each arm its own shoulder in the element description, give the idle hand a resting position rather than a task, and add the negatives by shape ("no third arm, no extra hand, no open palm pressed on the wall, no hand emerging from his shoulder, no hand without an arm"). On the render after that, the limb count still runs on the body crop — the clause raises the odds, it does not replace the count.

**And when the hand is the thing gripping a small prop, re-wording the grip does not fix it — the fix is to take the hand out of the picture.** A hand pinching a peg, a coin or any thumb-sized object is where the model's limb drawing fails hardest, and an explicit clause does not rescue it: a second attempt carrying "exactly two arms and two hands, five fingers each, each drawn once, no separated fingers" and a closed-fist grip instead of a pinch came back with **three hands on two arms** (one resting on his own forearm, one empty fist, one on the prop), a **second identical peg floating in mid-air** beside the first, the peg flanged like a cartridge, and an invented pipe crossing the very gap the picture existed to show. The clause buys very little on a small object and not much on a large one either: a prompt that gave the man only one task — his open hand resting on a large twine-tied bundle in a scale pan — came back with a spare arm reaching that pan **and** an arm-less four-finger hand gripping the far side of the same bundle, so the effort so far has cost full renders rather than one.

So the third attempt changes the composition, not the sentence: **no figure at all, no hands anywhere**, the prop standing on its own flat base on the bench beside its target, the mismatch carried by the prop's size against the opening's (`a slot three times longer than the peg is wide and half as tall as it is thick`) with the gap stated as its own element. An object-only frame is a real composition for a beat that reads "this does not fit", and it deletes the failure surface instead of out-arguing it. Say on the card — and to the post's author when he wrote the composition — that the figure left the frame and why, because the alt text and the brief's own composition both assumed a person was in it.

**Count heads, torsos and arms as three separate claims.** They can disagree, and the disagreement is the defect: a full-frame read of one draft image reported "two men side by side", and a 4x crop of the figure region answered "two heads on one shared torso, two arms". Two figures is a `wrong-count` of the cast; one body carrying two heads is a malformed character, and they send the next prompt in different directions. Ask the crop for all three counts, write the numbers into the note ("two heads, one torso, two arms"), and name the reading that the tighter crop produced — a read that says "two people" is answering a different question from one that says "one person with two heads".

**Count repeated units over the prop's whole extent, and name the crop the number came from.** A long prop that carries a run of identical units — a rail of hanging cable tails, a row of sockets, a shelf of jars — is only countable on a crop that holds all of it. On one re-render of the DHCP route wall the same picture produced three different answers: the full-frame read found the six tails but got the split wrong ("four cut, two live green", where the true split was three and three), and a crop aimed by guesswork at x 300-900 found only three units (two cut, one live) because the rail ran wider than the box. The full-width 2x crop of the whole rail returned six tails, three cut to bare copper and three unbroken green, which is what the brief said. So: find the prop's full extent first, crop all of it at one scale, count left to right, and put the unit in the note ("six tails left to right on a 2x crop of the whole rail, three cut, three green"). A split that disagrees with the brief is worth this second crop before it goes on a card — the low-res full-frame read is the one that hallucinated the ratio, not the brief.

## A grid of cards is a prop the model draws as a UI layer

A prompt that asks for "a large grid of cards, most with green check marks, three with red X" hands the model a prop built to be inventoried, and the render comes back as a **layer** rather than a scene: dense rows of flat rounded tiles, uniform fills, no ink outline, no cast shadow, sitting in front of the figure. It looks tidy and it is the pasted-overlay class.

Two questions settle it, and neither is "does the grid look plausible":

- **Does the grid obey the room's perspective?** A grid lying on a desk, a wall board or a rack of slots converges, foreshortens, or sits at an angle to the room's own lines. Rows perfectly horizontal and columns perfectly vertical in screen space, against a scene with any perspective at all, are drawn on the frame rather than in the room.
- **Does it cover part of a body?** Crop the figure and read it: a prop that occludes a forearm, a shoulder or a hand — the limb vanishing behind a tile and reappearing on its far side — was composited over the picture, whatever the prompt called it. `frame-map.py` at a coarse cell shows the block sitting on the figure before a crop is spent.

Then quantify it for the card. `check-off-scene-colour.py` prints the share of the frame in vivid off-scene colour and the **largest contiguous off-scene region**, and a pasted layer is one big contiguous shape rather than scattered prop detail: 30.264% of the frame off its own hue axis, with the largest contiguous shape at 26.462%, is the number the note carries — and it says "a region", not "scattered detail".

**A draft's existing image usually has no comparator.** The script's normal use pairs the candidate with a rejected original and an approved sibling, and on a review-card image neither exists. Say so, and let the absolute numbers stand next to the class rate from `verdict-class-rate.py` — "30.264% off its own hue axis, largest contiguous shape 26.462%, and `pasted-overlay` is 9 rejected / 0 approved in the library" is a claim that needs no baseline. Do not skip the measurement because the comparison set is missing.

## Locate the prop before you crop it, or a clean read of the wrong region passes as clearance

``crop-probe --box`` needs coordinates, and guessing them from a full-frame read is how a check comes back falsely clean. On a busy painted room the guess that missed the monitor landed on the server rack underneath it, and the read answered **"there is no text on the screen in this image"** — a confident negative about a screen it was never shown. A negative from the wrong crop is indistinguishable from clearance, so it goes on a card as "no lettering" when the lettering is 200 px away.

The cheap locator is the colour map, aimed at a quadrant rather than the whole frame:

```bash
~/.hermes/profiles/matejko/skills/image-studio/scripts/frame-map.py "$PNG" --box 0,240,760,760 --cell 40
```

- **Read the run of letters, not the picture.** A monitor or UI screen shows as a block of `.` (near-white) or `B` cells at a consistent row and column band — on one header a `.` block occupied columns 7-14 and rows 280-400, which is where the screen actually was. `--cell 40` over a half-frame is fine enough to aim a crop; `--cell 60` over the whole frame is not.
- **Then crop that band and read the written file**, and only then write the claim.
- **A read that returns bare fragments is a clipped box, not a broken label.** A crop starting 40 px inside a whiteboard's label column came back `AY / ND / TAI / EL / S / N`; widening the box to `x=0` returned `DERIAY / ODEIND / OIY / ENNTAI / CKKEL / ONYS / PRIN`. Fragments mean the box edge cut the words, so move the box past the start of the line and re-read before calling the marks pseudo-text. **The reverse case confirms instead of contradicting:** fragments that are the identifiable tails of the words a full-frame read gave (`IAN`/`AULT` under `OBSIDIAN`/`VAULT`) are agreement — the crop clipped the same label, it did not invent one, so the two reads together settle the pasted-panel claim.
- **Do not narrow a vision read's output with `| tail -n`.** A `vread.py` answer piped through `tail -20` came back as a fragment of the question, which reads like a failed call and costs a second one. Run the reader bare, or keep the tail long enough to hold the whole answer.

**A full-frame read's coordinates for a FIGURE are the least reliable part of it, and a crop that misses the figure proves nothing.** One read placed a man and a small robot in front of a gate; two crops over exactly those coordinates showed gate, wall and fence and no figure, and a third at the far edge returned a "partly visible second person" that a 4x crop settled as the vertical slats of a fence under a pasted panel's shadow. The man was in the picture the whole time — he turned up in a crop of the **top strip**, because a standing figure's head and shoulders sit above a mid-frame overlay. So when a crop holds no figure the read promised, do not conclude the figure is missing and do not go looking for a broken picture: tile the frame (a top strip plus a mid strip at 2x is usually enough), let the tile that contains it define its position, then crop that tile at 3-4x for the question you actually have.

**And a "partially visible extra figure" at a frame edge is unproven until a 3-4x crop shows a head or a torso.** Vertical slats, a striped surface, or a dark mass beside an overlay's rounded corner and its shadow all read as hair at low magnification, and putting that on a card is a `wrong-count` claim about a picture that holds one person. Name the crop that settled it, and say what the shape actually was — a card that drops the false figure without saying why invites the next run to find it again.

## A multi-fill card has no single fill to sweep, and an invented one has no pixels at all

The counting recipes above start from a fill colour: sample one pixel of a panel, then `--find` it. That works on a card that is one flat fill and fails on the shape this library keeps getting, a card assembled from several — a mustard header band, a bright blue body, and a red rounded backing offset behind them. No single `--find` returns it, and there is no fill to sample until you already know the card is there.

So an overlay that sits on an **edge**, clipped by the frame, is found by tiling rather than sweeping. Cut the edge band to a file at 2-3x, read the tile, and take the card's shape and its fills from the tile — then each fill is separately quoteable with `--find <sampled r,g,b> --tol 40`. On a left-edge card the tile read a mustard header over a blue body with a red backing and a dark rounded corner above it, and the pseudo-text on it read `Stale / config / key ne= / ing longer`; the sweep on the blue returns the body's bbox and the sweep on the yellow the header's, and those two boxes together are the claim, where "a UI card on the left" is not.

**Existence is the one thing the tile settles outright, and it is also the thing a read invents.** A figure's position in a read is unreliable and has to be hunted; a pasted card's is not, because a pasted card fills its region and a crop of that region either holds flat blocks or holds painted scene. One read placed a white rounded callout carrying a name and a green check over the foreground book of a library scene; three crops of that book and the desk beside it, one of them wider than the read's own box, held an open book, a desk top and a shoe, and no white card anywhere. Nothing about it went on the card. Hunt a card only when a crop of the place the read puts it in holds a flat block; when the crop holds the drawing, the callout was the read's own assembly — often a prop from the picture printed beside it on the same card, so check the card's other images before looking a second time.

**Neither one fill nor several fills settle the count.** Do not read "one card" off a single fill, and do not read "several cards" off several fills: a header band, a body and an offset backing are three fills of **one** card, while two panels of the same hue a few hundred pixels apart are two. The tiles decide the count; the fills decide the wording.

## Locating an overlay, counting limbs and reading a dial are crop-scale claims

Three claims look like whole-frame questions and are not. Each one was answered wrongly by a full-frame read and correctly by a crop of the thing itself, on the same PNGs.

**A blue count is a signature, not a location.** `check-defect-signature.py` on one header measured 52,382 blue pixels against 0 on an approved sibling from the same series — a real finding about the frame, and a useless pointer: the blue blobs sat in the top-left night window and the two monitor glows, while the pasted cluster was in the lower right. A series lit cool on purpose inflates that number by construction, so the count goes on the card as the comparison and the *region* comes from a sweep of the overlay's own fill colour. On that frame two red rounded buttons, each 88x85 px, came back at `bbox=(668,616,756,701)` and `bbox=(778,617,866,701)`, and a near-white blob of 1053 px at `x804-841 y629-670` sat inside the right-hand button — the pseudo-text surface. Those four numbers name the cluster; "a UI panel is pasted over the picture" does not.

**A limb count comes from a body crop, at figure scale.** A full-frame read of one figure reported **six** arms; a 2x crop of the same figure reported **four** — two at the shoulders, one on each of the props, and two grafted at the waist under the shirt hem. Full-frame reads add limbs, because a hand near a prop body and a hand at the far side of a paper stack both get counted. So crop the figure head to feet at 2x, ask for the count with each arm's attachment point and what it holds, and write that number into the note. **The full-frame read errs in both directions, so the crop is not a tie-breaker — it is the count.** It has added arms that were not there, and it has passed a figure carrying a spare one: a header whose man raised a padlock in one hand and had two more hanging at his sides went onto a card because the full-frame pass counted the raised hand and said nothing about the pair, and the rejection opened with the count. Run the limb count on every render of a visible figure, before the card, not only when something looks wrong — an extra arm costs a whole round while the crop costs one call. Extra arms are also a defect worth naming rather than smoothing over: an anatomically impossible pair is the same family as a figure whose arms are missing, which he has rejected as "looks broken".

**A still-counted spare hand is usually the gripping thumb, and it is settled at 8x on the grip.** When the figure crop keeps reporting one hand too many, the shape it counts is normally the thumb of the fist wrapped round a handle: on a Toriyama-series figure gripping a magnifier, a 2x figure crop said three hands and the 8x crop of the grip said one fist plus a rounded thumb protruding beside the shaft — while the approved header and delegate of the same post come back "clearly wrong hands" from the same reader, so the extra hand is the reading, not the render. Crop the grip and the pocket at 8x and 4x, count the **discrete skin-coloured shapes**, and ask of each whether a forearm reaches it; two shapes with two forearms is two hands, and the note names the thumb's shape honestly ("a rounded blob beside the handle rather than lying across the fist") instead of holding a clean render back over the reader's count.

**A figure-scale crop that reports an impossible count is settled one hand at a time, and the tight crop wins.** The body crop is right about the number of arms and unreliable about the number of hands: on one flux render a 2.5x crop of the figure returned "three hands at his waist" and a 6x crop of each hand's own box found two — one hand at the end of each arm, the third shape being a trouser pocket and the folded shirt hem reading as digits. So when the count comes back impossible, crop each hand separately at 6x, count the **discrete skin-coloured shapes**, and ask of each whether a forearm reaches it: two shapes with two forearms and nothing else is two hands, whatever the wider crop said. Write which crop settled it into the note, because "the 6x crops show one hand per arm" is checkable and "there are two hands" repeats the earlier claim.

**House style covers how a fist is drawn, never how many digits it carries.** A fist that reads as one fused rounded shape is this series drawing hands and ships — the approved-sibling comparison above is what keeps a hold off it. A fist that carries a thumb and three fingers, with the little finger simply absent and the hand fully inside the frame, is a **counted** missing digit and a hold-back however tidy it looks, because the count is the claim and it is true. The prompt remedy is to describe the fist itself — four knuckles in a row across the outside, the thumb folded along the front, the little finger drawn as clearly as the others — since "the man has exactly two hands" never makes a model draw a fifth digit.

**When the same hand clause fails twice on one slot, the sentence is not the problem — the contact is.** Drop the hand-to-prop contact from the composition (both arms hanging empty, well clear of the bench and the prop, nothing touching it) or crop the figure so the hands sit below the frame's bottom edge; another round of finger words on the same grip spends a render and comes back with the same spare arm.

**A pointer's endpoint is settled at 3x on the pointer, not on the dial.** A gauge read at full frame put the needle "on the border between the yellow and red zones"; a 3x crop of the upper arc put the tip plainly inside the red band. The tip's position relative to a band edge is a few pixels of geometry, and a downscaled read cannot see it — while the picture's whole beat can rest on it (a gauge pegged in red is the section's argument, a gauge at the border is not). Crop the pointer's far end at 3x and say which band it ends in.

**The off-scene colour axis is a property of the scene, so it can only be compared with a frame lit the same way.** `check-off-scene-colour.py` scored three frames of a cool-blue-lit post at 45-51% off-axis against 3.3% on an approved sibling — and the sibling was lit warm, so the axis was its own lighting and the number said nothing about artifacts. Before the comparison goes on a card, check that the sibling shares the candidate's lighting; when it does not, quote the class rate from `verdict-class-rate.py` instead of a percentage that the scene's own glow produces.

## A thin flat line is neither a banner nor a painted edge

This file covers broad bands and side panels. A **thin** hard-edged line across the
frame is a third shape, and it reads both ways: a rule of rows that is near-uniform
white, a near-black line under it, then another near-uniform white line — eleven rows
in all — was read by a full-frame pass as "the picture is split into two panels with a
white divider" and by a crop of those same rows as "a painted shelf lip". Both
descriptions are plausible and neither is a measurement.

The measurement is per-row flatness, and the shipped probe prints it:

```bash
~/image-studio/.venv-imgcheck/bin/python ~/.hermes/profiles/matejko/skills/image-studio/scripts/check-flat-lines.py "$PNG"
```

- **Flatness is a number per row.** Rows that read near-uniform white at luminance
  std 1.0-5.5, and the near-black rows between them at std 4.3-9.8, are drawn rules:
  painted texture does not hold a std in single digits across 1216 px. Quote the std
  range with the row span.
- **Width coverage is the second number.** A painted edge is interrupted by whatever
  stands in front of it; a graphic rule runs the full width. Write the coverage out
  (`1213 of 1216 px`) instead of saying "across the frame".
- **The column scan is what separates one rule from a page frame.** A comic-page
  gutter comes with a vertical border, a single drawn line does not, and `no flat
  columns` is the reason not to report a two-panel split on a frame with no vertical
  border anywhere.
- **A line that leaves the section's beat intact is a named deviation, not a hard
  defect.** On a review card it ships with the numbers in the long note and one clause
  in the item description; a re-render is for a defect class the library rejects.

## No approved sibling? The frame's own neighbouring region is the baseline

`check-defect-signature.py` and `check-off-scene-colour.py` both want an approved
frame of the same series, and a draft's back-filled image usually has none. The
substitute is inside the same picture: crop a region you know is painted, crop the
suspect region, both at the same scale, and read each on its own written file.

That settled a 644x287 px dark rectangle in the lower right of one header. The
suspect crop read as straight edges, a uniform navy fill with no cast shadow, three
flat circular icons and invented pseudo-text; the control crop of the same bottom
band, same scale, read as a server rack, a desk with three monitors, cables and
painted shadows. One scene, one region in a different idiom — the pasted card — and
the comparison needed nothing from the library.

Two rules keep it honest:

- **Crop the control region at the same scale as the suspect and read each file
  separately.** A montage of the two invites a read of the difference between the
  panels rather than the idiom inside each.
- **Name both regions in the note** — "bottom left: rack, desk, three monitors,
  cables; bottom right: a flat navy card with three icon circles and invented
  lettering, its edges straight and its fill uniform" — and put the suspect's bbox and
  pixel count from a `--find` sweep beside the comparison, so it is auditable and not
  two adjectives.

## An annotation layer is a pasted graphic with lines, and it is measured the same way

A tag or a label plate carrying leader lines and an arrowhead is a shape a painted room never contains: an arrow that points at a prop, drawn flat with no texture and no cast shadow, is an annotation **on** the picture rather than an object in it. At low magnification it reads as diegetic — a name tag taped to a bench edge is plausible — so settle it on the geometry:

- **Sweep the tag's fill colour and quote its box.** A near-white flat rectangle filling most of its own bbox, sitting on a wooden bench with no shadow under it, is a graphic; the same sweep on the frame's painted near-white surfaces returns several textured blobs rather than one clean rectangle.
- **Follow the lines, because they are the discriminator.** A leader line, or a callout that changes colour partway (an orange upper segment joining a blue lower one) and ends in an arrowhead, has no diegetic counterpart. The shapes it points at are props the picture already has, which is exactly what an annotation would point at.
- **The words are a second claim, settled the usual way.** Lettering on such a tag that two crops read consistently is readable lettering the prompt never asked for, and that is the `pasted-overlay` class even when every letter is spelled right; lettering that changes between reads is pseudo-text. Quote neither string until a crop has settled which case it is.
- **Report it with its numbers and let him judge — this class is small in frame and he may approve it.** A header carrying a name tag, a label plate with a two-colour callout arrow and a flat bar inside a dark frame was approved on a round-1 card where the whole finding was written up, while another image on that same card was rejected for flat green and blue blocks. So the class rate is a **prior, not a prediction**, and a cleanly drawn annotation in a corner does not decide a picture the way a full-width band does. Write the measurement, name the geometry, and do not upgrade your own flag into a certainty on the card.

**What separates a prior from a rejection is dominance, and the question is "how much of this frame is the defect", never "how big is my flag".** A single flat card in a corner, one caption strip along the bottom and an annotation tag with leader lines have all come back approved on cards that named them plainly. The frames rejected for the same class carried it across the picture, or put it where the section's own beat lives: five flat panels with invented words over the back wall of an office, lettering that misspells the man's own name, panels wide enough to read as a layer rather than a prop. Measure it — `check-off-scene-colour.py`'s largest contiguous off-scene region, or a fill sweep's count of separate panels — and let that number decide the sentence: small and isolated ships to him named, dominant does not.

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

**Verify every deviation clause the brief hands you, not only the defects it clears.**
A round-2/3 brief's "deviations named on the card" block is an earlier run's read, and
the card re-states it as fact. Copying it blind ships someone else's wrong sentence: on
one card the brief said the flat envelope was "closed and intact" and a 3x crop of that
envelope showed a torn top edge with a dark gap but nothing protruding, so the beat that
failed was the spilled slips, not the seam. Crop the prop, read it at 3x-5x, and write
the sentence the crop supports.

**An absence is a claim about a region, so it is verified by scanning that region —
counting what is present never settles it.** A brief described a plate whose socket row
held three slugs with the fourth socket empty and a fifth opening lower on the face,
also empty. Counting the row (four sockets, all four seated) confirmed the brief's true
half and said nothing whatever about the lower opening, which was the clause the card
was about to repeat. A 3x crop of the whole plate face showed it solid below the row: no
empty socket anywhere, and the loose slug standing outside the plate rather than above a
gap. So ask separately *where the absence is supposed to be and what is drawn there*,
and crop that region — a count of the present instances and a scan for the missing one
are two different checks, and only the second can falsify an absence.

**When the brief is wrong about a structural fact, the card carries the measured version
and says it is correcting the brief.** The correction usually rewrites the deviation
itself rather than just its wording: here the beat moved from "three seated round one
gap" to "four fitted plus one waiting outside the plate", which is a different question
for the owner about whether the picture still carries the section — so state both what
the brief claimed and what the crops show, and let him judge the concept. Then record it
in the queue (`backlog.py note <n> "<what the brief claims, what the crops show>"`),
because the brief is what the next run reads and an uncorrected clause comes back as
fact on the following round.

**A corrected card is a new card, and it says so on its face.** Put the withdrawn
card's id and what the correction is at the top of the new card's `detailsMarkdown`,
so the reader of the new card alone can tell that there was an earlier one and why it
went away — the thread is not the only place he looks. Build it from
`templates/verdict-card-spec-corrected.json`, which carries the `idempotency_key`
field the default spec shape cannot express (`verdicts:<issueId>:round-<k>-corrected`).

The one-card-at-a-time rule counts **pending** cards, not cards already retracted.

**One re-post is the limit.** If the second card's item text is right and only the
withdrawn card's id is missing from its `detailsMarkdown`, do not withdraw again: a
third card and two cancelled ones read worse than one plain comment. Name the
withdrawn id and the correction in a thread comment, verify the live card is still
`pending` after that comment (your own agent comment does not supersede it), and leave
the round on the one open card.

## A large off-scene blob inside the figure is the figure

`check-off-scene-colour.py` reports the largest contiguous region whose hue falls off the scene's own axis, and on a warm-paletted series the biggest such region is routinely **the character**: navy trousers, dark hair and a grey shoe sit off-axis by construction while the room is amber and brown. A blob of 6001 px spanning a man's head and shoulder, with 4.2% of the frame off-axis overall, was the man himself and not a panel.

So before a side panel goes into a note, compare the blob's bbox with the figure's own span and read a crop of exactly that region:

- **Wholly inside the figure's span is clothing, hair or a shoe.** A pasted panel does not sit entirely within the silhouette of a person.
- **Flat, unoutlined and touching a frame edge or a bare region is a panel.** Clothing carries folds, an ink rim and cel shading, and a 2x crop of that region shows all three.
- **Say which it was.** "Largest off-scene blob 6001 px; a crop of that edge shows the man's own head and shoulder, no side panel" is a claim a later reader can re-run. Leaving the number unexplained on the card invites the next run to hunt a panel the picture does not have.

## A read that says every unit is marked is a class claim, not a count

A board, a shelf or a wall of repeated small units invites a crop read to report that **all** of them carry marks: one 2x crop of a board returned "77 slips, every one marked with dashes, 0 blank". That describes the prop, not a count of defects — at that magnification ruled lines, pin dots, paper texture and shadow edges all collapse into "text".

Spot-check one unit before the claim becomes a class:

```bash
~/.hermes/profiles/matejko/skills/image-studio/scripts/ascii-render.py "$PNG" --box 300,170,380,215 --mode ink
```

`--mode ink` prints only the drawn strokes at 1:1, so a face carrying handwriting shows horizontal bars and a blank face shows its edges alone. Then write what the pixels support — "the slip faces carry fine dash marks that read as texture at full size; no letters" — rather than "every slip has pseudo-text".

**Weigh it against the version he has already judged.** When the image of that same slot he ruled on carried the same marks and his reason did not name them, and the marks leave the section's beat intact, the render ships with the observation named in the item description instead of spending a 21-minute render on a detail his eye did not flag. Put the alternative composition in one line beside it ("the next version drops paper for small wooden blocks on a rail, which cannot hold written lines") so a rejection costs him nothing to answer. **That is the residual path, not a licence:** a class with no approvals is still a re-render when the mark is what the picture is about, and the class rate from `verdict-class-rate.py` is what decides which case this is.

**The discriminator inside that class is the face, not the pixel count.** A mark on a surface the picture itself presents as a label — a plate, a sticker, a sign face, a ticket, a nameband — is pseudo-text and belongs in the hold/ship decision above. A mark on a surface that is not a label is not the class at all: scratch hatching on painted steel, wood grain, tool scuffs and cable wear are how this series draws used metal, and putting them in a note as "stroke marks" invents a defect. Decide which one you are looking at before measuring anything, because the two look identical in a 4x crop and only the surface tells them apart.

**A small label on background storage is the third case, and it ships with the pixel size named.** A blank plate carrying two or three dash strokes, 20x8 px, on a filing box or a crate at the back of the room cannot be read as text at the size the picture is published, and holding it back trades a whole round for something his eye cannot reach without a loupe. Name it in the item description with the size and the count ("a couple of the filing boxes on the back shelves carry two faint dash strokes where a label would be, about 20x8 px") and let him judge. The line between this and the hold is legibility at published size, not the share of the frame — a 1-2% jar sticker at the front of a shelf reads as a label at 1x and held back a render; two strokes on a back-row box do not.

**Two slots carrying the same defect in one round get the same verdict, and the queue depth is part of the calculation.** Read `imagegen status`'s `eta_minutes` and `queue_ahead` before choosing to spend another attempt: on a busy shared worker a hold costs the queue depth times ~21 minutes, not one render, and that number is what the decision is actually buying. Applying the legibility test above to both files in the same pass is what keeps a round from shipping one mark and holding its twin, which is a card whose two item descriptions contradict each other about the same class.

## An alt text is a claim about the picture, whoever wrote it

A post's alt text can be written by the post's author from the composition document
rather than from the file, so it describes the composition and not the render. On post
033 the author wrote a correct caption for the two slots being re-rendered and a wrong
one for the approved image: it said the figure points **up at the phone**, that the
arrow turns **away** from it, and that the marker is a **pin**. Crops of the file showed
he points at the **monitor's green tick** with the other arm at his side, the arrowhead
points **toward** the phone with the dashed line continuing past it, and the marker is a
round **speech bubble** with its tail pointing down.

So read every caption against the PNG before it ships, and settle each detail the way
any other claim is settled: find the object by pixel signature (`crop-probe.py --find
<r,g,b>`, which returned the DNS bubble as a single 11,835 px blob at x 46-174, y
375-536), write a 3-4x crop of exactly it, and read that. A caption's claim about
direction is the one that fails most often, because a direction is cheap to assume from
the prompt and expensive to see. The correction is the author's to make - a review card
may not edit the post - so it goes back through the same hand-off issue that produced
the composition, with the measurements named, and that comment reopens the author's
issue, which is the intended route.

## A leading question manufactures the defect it asks about

On post 031's round-2 header, three reads of one render at increasing zoom all answered
"a floating left hand with no arm and extra finger clusters" and the third added "should
not ship". Every one of them was answering a question that named the defect: *is any hand
detached, is the arm continuous*. Asked the neutral version on the same file - "starting
at his left shoulder, describe what you see moving down along his left side" - the model
described a sleeve, a bare upper arm, an elbow bend, a forearm, a wrist and the hand
curled under the block, which is what the picture shows. The defect was in the question.

So a limb-continuity claim is settled in two steps:

1. **Crop the whole figure first.** The crop that produced "detached" cut the shoulder
   out of frame (`250,250,950,720` on a 1216x832 render whose figure starts around y 60),
   so the arm literally was not in the file. A crop that amputates the limb will always
   report a floating hand.
2. **Ask for a description, not a verdict.** Never put the suspected defect in the
   question ("is this broken", "does the arm connect", "is any hand floating"). Ask what
   is drawn along that side, then judge the answer yourself.

A confirming read is worth nothing when the question already contained the finding; two
agreeing reads that both carried the same leading clause are one read. This cuts the
other way too - a real defect survives the neutral question, so ask it first and hold
back only what a description, not a suggestion, produced.

**Check the prompt before you count a reported arm as spare, because the prompt may have put that arm across his chest.** A limb the prompt itself places in front of the body — a hand held up at chest height, a forearm folded across the shirt — is drawn *over* the torso, so a crop that holds the torso but not the shoulder reads it as an arm emerging from the centre of the chest with no joint, and a whole-figure read on the same file counts it as a third arm. Both readings are of a picture that has two. So before a limb count goes into a note, read the prompt's own arm placement and ask which reported limb is the one it asked for: the element description that says where each hand is held is the reference for how many arms the picture should have, and a count above that number is a claim to settle on a crop holding **both** shoulders. On one render a whole-figure read reported three arms and a torso crop reported one arm "growing from the middle of his chest"; the prompt put his left hand at chest height, and that forearm was both findings.

**Locate a hand on a mid-scale crop before magnifying it, or a guessed 6x box lands on the
face.** A grip held above the head sits higher in the frame than instinct says: a box at
`930,330-1130,500` of a 1216x832 render came back as the beard and the glasses, and its
reader answered "no fingers visible" about a fist that was there, one crop higher up.
Crop the quadrant at 2-4x first, read where the grip sits, then take the 8x box of the
fist alone. Expect two scales to disagree by design - the 4x crop of the grip sees three
fingers plus a thumb, the 8x box sees two bars and calls the stack a jumble - so take
the count from a crop where the **whole hand fills the frame** (4-5x, with the arm and
the room cropped out of it) and name the scale at which the drawing starts to read as
stacked segments rather than one fist. **A crop wide enough to keep the arm and the
room in frame under-counts the digits**, because the reader falls back on the cartoon
prior ("three fingers plus a thumb is how this style draws a hand") instead of tracing
the contour: one raised fist read three-plus-thumb on a 3.2x crop that held the arm and
the pegboard, and four fingers plus a thumb on a 5x crop of the hand alone, which is
the crop that saw each curled finger's own outline. So when two crops disagree on the
digit count, do not file the lower one as a missing digit: re-read at hand scale first,
because a hold-back taken from the loose crop spends a render on a hand that carries
five.

**A read asked "is there a signature here, spell it" answers with a name.** Asked about
the right edge of a flux frame, the reader returned a confident vertical "Enki Bilal";
`ascii-render.py --mode ink` on the same strip showed halftone dots with no glyph
structure and tesseract found nothing. Never file a mark from the question alone.
