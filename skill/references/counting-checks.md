# Counting hands and repeated objects in a render

Companion to `references/verifying-image-details.md`. That file settles *where* a detail is
(a `vision_analyze` `region` box is a prompt, not a measurement; locate by pixel signature and
crop with PIL). This file settles *how many* — a different failure mode, and one that reaches
the card.

## A count in prose is a frozen claim

`items[].description` and `detailsMarkdown` are frozen at the interaction POST. Every number you
write there — three crates, five panels, seven padlocked doors, two fists — is a claim Wojtek will
check against the picture. A wrong number in the prose costs more than a wrong number in your head,
because the picture is right and the sentence is not.

Measure every count from a crop **before** the POST. Also count the render against any count stated
in the prompt or in the post's beat ("exactly one lock, six that gave it up"): the contrast can read
correctly while the count is off by two, and the contrast is what you were looking at.

## Full-frame reads are not counts

Both failures recur, on ideogram and flux alike:

- **Hands.** A full-frame read reports a spare hand on a two-fisted figure. Cropped to 2x or more
  and traced shoulder-to-hand, the figure has two. A "three hands" verdict from a full-frame read
  is not evidence of a defect. The usual spare is the far side's own fist seen past his torso, so
  cut each hand as its own crop, sleeve to hip: a box wide enough to hold both fists manufactures
  the third one, and two per-side crops are what settles it.
- **Legs.** A boot count is not a leg count. Both boots can stand on the floor with shadows under
  them while a spare trouser leg hangs between the real pair and ends in mid-air, bootless — so a
  crop aimed at the feet reports two boots on a three-legged figure, twice in a row, with the
  owner's own verdict as the thing that catches it. Count legs from the waist down and follow each
  one to a boot; a limb that ends in no boot is the tell.
- **Repeated objects.** Panels, crates, doors, locks and tiles come back off by one or two, in
  either direction, and a second full-frame read can land on a different number again. The same
  wall read as five panels, then four.
- **A seating or compression state.** "The bolt head stands proud on a collar", "the spring is an
  open coil", "the door is not latched back" are conclusions drawn from 3-D shading at frame
  scale, and they read as exactly the defect a repaired prompt was written to remove. Cut one
  crop on the assembly at 2-3x and ask the two closed questions separately (bare shaft between
  head and plate? daylight between any two coils?) before the full-frame verdict touches anything.
  The same frame that read "proud and loose" answered "flush on its washer, coils tight" on the
  crop. A verification wake is where this costs most: nothing is re-rendering, so a full-frame
  disagreement with a card already posted is a reason to crop, never to hold the slot.
- **An absence in a pair.** A read that says one of two twins lacks a feature its sibling has is
  usually describing the neighbour: a pipe carries a valve and, at its end, a flanged collar where
  it enters the wall, so "the right arch has no valve, only a coupling" was a card caveat written
  about the collar while the valve sat a hand's width along the same run with a smaller handle.
  Before you write or believe that a part is missing something, crop that part alone and name every
  fitting along the run, left to right. Absence is the most expensive prose to get wrong, because
  the card then sends him looking for a defect that is not in the file, and the file is what he
  judges.
- **A spare limb that is background furniture.** A suspected third arm or extra sleeve seen at 2–3x
  is often a vertical shape standing *behind* the figure — a door post, a beam, a pipe, a chair back
  — whose edge runs alongside his arm and reads as a second sleeve. Before holding, re-crop at 5–6x
  around the joint and ask what is behind him: a limb has a shoulder, an elbow and a wrist that join
  the body, and a post has none. Holding a clean render on a background edge costs a full
  re-render round for nothing.

Treat any number from a full-frame read as unmeasured, and any number two reads disagree on as
unmeasured still — a third read of the same frame is not a tie-breaker. The higher-zoom crop wins
**only while the crop still holds the whole subject.** Keep zooming into a single feature and the
crop starts clipping the end of the row it is counting, so the count falls as the scale rises:
notch cuts in a painted arc, chips along a worn edge and teeth on a hand-drawn gear are that shape,
and four crops of one arc read 5, 4, 2 and 7 with every answer stamped confident. When the counts
move with the scale instead of converging, the feature has no countable edge and no crop of it is a
measurement — so the record states no number. Write the part that does read (which notch the lever
rests in, how many teeth are cut cleanly, which end the marks start from), name the scales you cut
and what each answered, and never promote one of the disagreeing counts into a record just because
it came from the tightest crop.

**A fist counted on a box whose edge cuts the hand loses the digit nearest that edge, and the loss
reads as a defect in a good render.** Two deep crops whose frame ended just past the knuckles
returned "thumb, index, middle, ring — little finger missing" on a render whose whole-figure read
and a wider re-read both gave four fingers plus a thumb: the box was cutting the finger, not the
render. So a hand count can hold a render back only when the box carries clear margin past the
outer edge of the fist on the side the missing digit would sit, and the count that decides the
hold-back is the one taken on that wider box. Cut hands at 5-6x with margin rather than at 10x
against the knuckles: the extra scale adds no countable edge, only a slower read. A count that
changes when the box grows is a count of the box.

## A beat that hinges on a pair

When the beat is a contrast — the original and its copy, the sealed box and the key still out —
count the instances the beat compares, not the objects that happen to be in the frame. A single
bright duplicate over a tray of filings can read as the exact opposite of a copy still at large:
cutting a copy and destroying the only key share the same visual shorthand, so a reader can see
"the key was ground down" where the frame means "the copy is still hanging there". Both halves
have to be visible (the same key pattern in the new lock, a blank in the vice) before duplication
reads as duplication. Fix the composition, not the prose — no caveat on the card turns one object
into two.

## A read's label is a hypothesis

"Pasted panel", "sticker", "badge" and "painted on" are the reader's conclusion, not what the
pixels are. Crop the suspect area at native size before that label holds a render back. A pale
wedge under a door, a highlight along a rim and a hard contact shadow all read as flat pasted
shapes at full-frame scale, and the cropped frame shows the same wedge grading into the floor and
shading the stone. The test: uniform colour with hard straight edges that ignore what they meet is
an artefact; falloff, reflection and a cast shadow are the painting. Settle which one it is on the
crop, because the two labels send the slot in opposite directions — one re-renders a good frame,
the other ships a pasted panel.

## Procedure

1. List the numbers already in play: the prompt, the beat, the card prose, the issue description.
2. Crop one region that holds the whole row or stack, tight enough that one object fills roughly a
   third of the frame. Never split a row across two crops — the count then has two halves and no one
   adds them.
3. `scripts/crop-for-count.py` does the crop and the upscale; use 2–3x and LANCZOS.
4. Ask for a left-to-right (or bottom-to-top) enumeration, and ask for the state of each object
   ("1 open, 2 shut with a padlock, 3 open"), not only a total — a bare total hides a swap.
5. For a figure, ask for each arm traced shoulder → sleeve → forearm → fist, one side at a time, and
   each leg traced hip → knee → boot on one crop that holds the waist down to the floor. Two bounds
   on that crop: it must reach the floor, or a limb ending above it is invisible, and it must hold
   both legs, or the count has one leg and no way to see the spare.
6. Write the measured count, or no count at all when the readings move with the crop scale rather
   than converging (see above) — and never a count a scale-dependent read happened to give. If it
   disagrees with prose already on the card while that card is still `pending`, the correction goes
   into the post's queue note (`backlog.py note <n> …`) and nowhere else — a comment beside a live
   card is the chatter `review-card-api.md` bans, and a board comment supersedes a target-bound
   card; the issue comment naming both numbers is for a card already answered. Do **not** withdraw
   and rebuild the card to fix a number — the
   pictures are unchanged, and a withdrawal pulls the card out from under him mid-read.

## Reading the answer

An answer that hedges ("or the second door, depending on how the count is framed") has not counted.
Ignore its summary and re-ask for the enumeration on a tighter crop.

A colour-threshold blob count does not replace the crop. On this register skin and warm brick share
hue, so a hand-rolled skin mask returns the wall as its largest blob and the fists dissolve into it;
the crop plus a left-to-right enumeration is the measurement, and a mask is a second guess wearing
the clothes of an instrument.

**But a mask does earn its place as a locator, for a row of identical objects with their own light.**
Nine lamps on a bench, a run of gauges, a rank of little doors: threshold the warm bright pixels
(roughly `R>200, G>140, B<120, R-B>60`) and walk the frame's columns collecting runs wider than two
pixels with a few pixels in them. Eight evenly spaced runs 35–40 px apart give the row's object count
and its spacing without any reader, which is what a crop needs before it can be framed: the row's x
range comes from the runs, and the crop is cut at 3–4x on that range instead of by eye.

What the mask cannot answer is each object's **state** — lit or cold, open or shut — and that is the
part reads disagree about. On one row of lamps three reads gave seven alight, then four, then all
eight, each of them enumerating left to right with confidence. When two reads disagree on a state
total, do not ask a third reader and do not average them: the disagreement is the finding. Then:

- **a beat whose meaning is a fraction holds the frame.** "A great many small fires, most already
  out" needs a majority one way, and a row that can be read three ways is not carrying it. The slot
  goes back for a re-render with the state stated in the objects rather than in a total ("seven of
  the eight are cold and sooty, one still burning at the far end"), because a count of states is
  what the engine gets wrong, not the row itself.
- **a beat where the count is incidental ships with the disagreement named**, in his terms and with
  the number you did measure (`four cold with smoke threads, two burning, at the two ends`).

Either way the item description carries the number the frame actually shows — never the number the
prompt asked for, and never a total no crop supported.
