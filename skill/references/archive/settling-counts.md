# Settling a count when the readers disagree

Companion to the crop-and-count rules in `references/archive/review-loop.md` section 6 and the
longer procedure in `references/verifying-image-details.md`. Read this one when two
reads of one render return opposite answers about a *countable* fact — hands, arms,
digits, figures, props — because that is the shape where a wrong call costs a render
slot in one direction and puts a defect on a frozen card in the other.

## The rule

**Two readers answering one count differently is a tie both of them lose.** Re-ask the
same neutral question on a tighter crop of exactly the patch the claim is about, and
let their agreement on that file decide.

- One render came back from a full-frame read as three arms, with a third hand that
  could not be traced to any shoulder. The second reader, on the same file, answered two
  hands, two arms, every arm traceable. Both reads were fluent and confident; neither was
  an answer.
- What settled it was a 6x crop of the single patch the claim named — the desk beside
  the second hand — asked as counts only: *how many separate hands are in this crop,
  what does each rest on, how many fingers*. Both readers then said one hand, and the
  third arm turned out to live only in the low-zoom frame.

## The steps

1. **Locate the patch the claim names, not the figure.** "A third hand beside the
   second" is a question about one small region; cropping the whole figure re-opens the
   ambiguity the claim came from. Confirm the whole figure or the whole row once on one
   wide crop first, so a crop that cut the limb off cannot send you hunting a patch that
   does not exist — then go in tight.
2. **Crop it to disk at 6x** with `scripts/crop-probe.py <png> --box x0,y0,x1,y1 --scale 6
   --out <scratch>/crop.png` and read the written file, never a `region` parameter.
3. **Ask both readers the identical short counts-only question** — the same words, the
   same file. Two different questions produce two answers that cannot be compared.
4. **Let agreement decide.** Agreement on the tight crop is the finding; disagreement
   there means the patch is still mislocated, not that the render is broken.

## Write the count so it can render at all

**A count written inside another object's `desc` does not reach the canvas.** Six parcels described in the workbench's own element came back as five from ideogram and three from flux on the same prompt shape: the bench's `desc` is read as the bench, and the parcels dilute into dressing on its top. The countable set needs its own element with a `bbox` over the whole row, so the model gets a region that has to be filled with exactly that many shapes.

These clauses are what make the number hold:

- **its own element, its own box**, spanning the row's length rather than sitting inside the container's;
- **an ordinal list** — "first a small flat pouch, second a slightly bigger pouch, third a small round bundle, fourth a middling bundle, fifth a large bundle and sixth a big sack at the far right end" — because a bare numeral gives the model nothing to build up, and each ordinal is a place to put one thing;
- **a gap of bare surface between each pair** ("a gap of bare wood between it and its neighbour"), so the shapes cannot merge and be counted as one;
- **the total said once, plainly** ("six parcels and no more"), with the container saying what is *not* on it ("nothing on it but the row of parcels") so the model does not add a seventh as dressing;
- **the differences stated per item** when the beat is that they differ: an ordinal list of identical shapes reads as one shape repeated.

Element count is the budget. A countable row promoted to its own element can push the prompt past six elements, and the linter charges +2 risk for that, so drop a dressing prop to make room rather than folding the row back into the container.

## A bare how-many is not a count

**Ask for the list before the total, on a crop that holds the whole set.** "How many parcels are on the bench" returned three and then five from two readers over the same region. The same crop asked as "count them left to right, one by one, then give the total" returned five twice, in list form: two readers agreeing on an enumeration is stronger evidence than two agreeing on a number, because the list can be checked against the picture and a number cannot.

- **Name the file and the scale in the note** — a count taken at frame size is not a count.
- **A band crop invents limbs.** A 2x crop of the lower third, cutting the figure at the waist, came back "an unnatural number of arms and hands clustered at the torso"; the whole-figure crop at 3x from the same file read one head, two arms, two hands, every one traceable. Cut the figure whole, or cut one patch tight — never a band across the middle.
- **A wrong count is a beat failure, not a caveat, when the beat is the number.** If the section's sentence is "six archives of six different sizes", five does not carry it and the slot re-renders; the number goes on the card as a caveat only when it is dressing.
- **But a live card carrying a short count is not withdrawn over the count alone, and `wrong-count`'s rate does not say it should be.** That class's rejection rows are almost all *figure* counts — a second character where the slot is one man — so 0 approved there is evidence about the cast, not about a row of parcels. When the slot's re-render came back worse than the render already on the card, the card stays pending with the shortfall disclosed in the item's description, and the record carries the measured number: a picture that carries the beat without the literal total can be approved, where the miss is named in the words beside it. Withdraw only for a replacement that passed every check the first one did.

## A detail that is missing is not a count that is wrong

A prompt names a small feature (two antennae on the android's head, a hook on a hasp, a knob on a door) and the render may simply not carry it. That is a different question from a miscount, and the answer decides whether the note says *deviation* or *defect*:

- **Crop the region with bare air above the feature.** A crop that starts at the object's crown cuts off exactly the thing being looked for, and every reader then answers "none". Three crops of one android's head said zero antennae while the full frame said two, and the top of the head was flush under a bench edge: the readers were answering about occlusion, not absence.
- **Ask "is anything thin sticking up from the head, and what is above it" rather than "how many antennae".** The second form presupposes both the feature and the count, and a reader that sees a smooth dome just says zero to the question it was handed.
- **Say "not visible" when the crown is flush to another surface.** "The head reads smooth; the bench edge sits at its crown, so the prompt's two antennae are not in view" is true and checkable. "No antennae" is a claim the file does not support, and "the antennae are missing" is a defect nobody measured.
- **An absent dressing detail on a file already approved is a named observation, not a re-render.** It goes in the note beside the picture's other measurements; only a missing feature that carries the beat (the only key, the one lit stove) makes a slot fail.

## What not to do

- **Never name the suspected defect in the question.** A reader asked "is the shape
  crossing his chest a third arm, or a sleeve fold?" answers that question and describes
  an arm, because a read completes the story it is handed. The leading form manufactures
  the defect it was checking for — the same mechanism as asking a reader whether a prop's
  state is open or shut.
- **Do not hold a slot on one reader's limb claim.** A body that is complete at 6x is
  complete: report the one ambiguous shoulder joint as a caveat in the item's description
  and let the two hands the prompt asked for carry the beat. Holding back a clean render
  costs ~21 minutes and a round; shipping a genuine third hand costs his trust in the
  self-check.
- **Do not quote a count taken at frame size.** The reader's confidence carries no
  information; the crop scale goes beside the number in the note.
- **A shape claim is a count claim, and the same crop rule settles it.** A whole-frame read
  of a card-ready header said the key's shaft was "cylindrical/round" and half-undid the
  beat; the same file at 2x said four flat sides with sharp corners, which is what the
  prompt drew. A prop that carries the section's point — a section, a state, a fit — is
  never settled at frame size: crop it tight, name the scale in the note, and only then
  write "no caveats". A defect reported at frame size is a candidate; the crop is the verdict.
- **A re-render that fixes the count can arrive carrying a defect the first one did not
  have, so it displaces nothing until the whole check runs again.** A slot re-rendered for
  five parcels instead of six came back with six and an unprompted glossy black spill
  pooling on the bench and dripping over its lip — the number was right and the frame was
  worse, and only the spot-the-artefact pass (`check-green-share`, `check-off-scene-colour`,
  a full-frame read) found it. Run the same suite on the replacement as on the original
  before it is called a swap, and when it fails, leave the live card pending and say in the
  thread what failed: a withdrawn card with a defective replacement behind it leaves the
  post with no review path at all.
