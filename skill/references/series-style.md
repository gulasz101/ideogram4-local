# The house look for a post image

Open this before writing any prompt for a Wojtek post image. It is the series' look as he has stated it, not one post's preference: the same complaints arrive on several cards in the same week, in almost the same words.

## The style block

- **1990s cel anime, and name the references.** `aesthetics` reads: "1990s cel anime, Akira Toriyama Dragon Ball character design, Perfect Blue film stock, bold black ink outlines, flat cel-shaded colour, heavy 35mm film grain". He asked for exactly that range (Dragon Ball / Akira / Perfect Blue). "Cel-shaded digital illustration" alone renders as modern vector art and comes back as "not the style".
- **The drawn line comes first; the grain is a finish laid on top of it.** An instruction to be uniform is an instruction to be smooth: "an even layer of fine film grain over the whole picture, the walls, the floor and the empty air alike" renders as a clean digital image wearing noise, and a round that answered a grain complaint with more grain came back *too flat and too polished*. Open the style block with the ink — tapered inked contours with a slight hand wobble, shadows built from visible hatching rather than airbrush, flat cel colour laid slightly off-register so paper shows at each colour edge — and let the grain ride on that. `references/prompt-hygiene.md` carries the flux case in full.
- **Name the grain twice.** A rejection said "photo graining is not here" about a frame whose style block mentioned grain once. Put it in `aesthetics` and again in `lighting` ("grain visible in the shadows"), so the grain is a property of the light and not only an adjective.
- **Flat colour, bold ink outlines, chibi proportions.** That combination is what reads as an old animation still rather than a painting.

## The palette: one named list, in words, no `color_palette`

- Pick four or five named colours once per post and write the same sentence into every prompt of that post: "rust brown, olive grey, teal-cyan, cream, dark ink". Consistency across a post's images is something he asks for by name ("the color pallette must be consistent across image").
- **Never put a `color_palette` hex array in the prompt.** The array renders as a swatch strip along an edge. `scripts/check-palette-strip.py` exists because it kept happening.
- **Keep green out of it.** A green badge, green flag or green glow reads as an "OK/verified" sticker rather than part of the scene, and he rejects it as "green stuff is not fitting generally the full concept". One teal-cyan accent on one surface per frame is enough. **The ban covers the android's own body and its cast shadow**, not only graphics: measure the finished file with `scripts/check-green-share.py` against an approved sibling of the same week before it goes on a card — an approved frame reads 0.1–0.5% green with no blob, a green mascot body reads 6–27% with the blobs sitting exactly on the androids. Treat a reading in the high single digits as a prompt to look, not an automatic hold.

## The cast: one Wojtek, plus small android helpers

- The blog's cast is **Wojtek** — long straight brown hair below the shoulders, full dark-brown beard and moustache, clear rectangular glasses, oversized t-shirt — and **small androids that help him manage a fleet of old "junkyard PCs"**. He states this as the standing cast whenever a frame reads as having two protagonists.
- **State the count in the prompt.** "One main character ... plus one small android helper". Two human-scale figures in a frame is read as "there are like two main characters", even when the second is a prop.
- The androids: **knee-high, boxy, weathered grey steel** — a small rounded rectangular body with two thin antennae, a plain face plate with two round dark eyes, and **a job** (holding the work lamp, holding a cable end). The round green Android mascot body is retired: the current series reads grey, and a green mascot is the "green stuff" he rejects. An android standing still is furniture; he is managing a fleet, so let the little one help.
- Setting: a basement workshop or junkyard server room — racks of stacked old beige PC towers, tangled black cable, scuffed concrete, oil stains, a bare hanging bulb. Old hardware is the series' furniture, so the towers do not need an explanation.

## A national flag must be the real flag

- A flag in the picture is a claim about a country, so write the bands out: Spain is "a red band, a wider yellow band, a red band"; Germany is "black, red, gold". Add "no crest, no marks, no lettering".
- An abstract colour patch where the beat names a country IS the defect: a blue-and-white banner beside a Spanish exit came back as "spanish flag should be SPANISH not just blue and white".
- If the beat does not need the country named, **drop the flag** rather than approximate it — a second wrong flag costs the whole render.

## No prop that invites lettering

- Screens, terminals, plaques, label cards, banners, lower-thirds, price badges and wall signs all come back with pseudo-text, and the pseudo-text is a defect class he rejects without exception (see `scripts/verdict-class-rate.py`).
- **The fix is removal, not a negative clause.** A negative that names the shape ("no UI panels", "no signs") is a concrete instruction and the model draws it — the negative-clause recipe in `references/prompt-hygiene.md` and engine-pitfalls #62/#63 cover the phrasing.
- When the beat is "read the result", replace the screen with a physical instrument: a hand-held gauge, a dial, a meter with a plain face described as "no numbers and no letters". A terminal wall plus a desk is what produced two pasted UI panels of gibberish over one picture.
- Close `high_level_description` with "No readable lettering anywhere." It is the one sentence that survived several approved renders, and it belongs in every prompt of the series.

## Hands and posture

- "Hands ... body looks strange" is answered by **giving the hands a job and describing them**: both open hands closed on one rim, "five fingers drawn cleanly on each hand", shoulders turned into the pull, feet planted. An empty raised hand is where the model improvises, and a second object in the other hand doubles the chance.
- **A rejected "body" is a pose fault, and it is fixed by staging rather than by describing the body better.** Hands in pockets, or behind the back, take the hand clause out at the same time. A full-length figure in a strained pose is the failure mode: leaning across a long horizontal prop, or folded down against a machine, comes back with the torso stretched along the prop or the chest running into the lap. `references/series-look.md` carries the rule, the numbers and the 2x crop check.

## The figure stands on the ground

- A verdict clause like "the characters are not standing on the floor, so you have to arrange scene better" names a composition fault, not a shading one: a figure whose feet are cropped by the bottom edge, hidden behind a prop, or drawn above the floor line reads as pasted onto the picture however good the rest of the frame is.
- Name the ground plane as scenery in `background` — the floorboards run across the bottom third of the frame back to the wall — and in the figure's own `desc` put bare floor in front of his boots and say both boots are flat on it. "Feet planted" on its own is a posture; the floor in front of him is what shows contact.
- Put every other standing thing on the same plane and say so: the android stands on the same boards at his heel. Two figures grounded differently is the same defect twice.
- The floor is also the described prop that fills the bottom band, so it pays twice: a named ground plane is what stops an edge strip or a pasted block from landing there (see the bare-region rule in `references/prompt-hygiene.md`).
- Settle it on the whole frame rather than a crop: is there floor visible under and in front of every standing figure? A frame whose bottom edge is all prop, wall or a colour band has no ground for the figure to stand on.

## Companion FLUX renders

- He asks for "companion flux images" to compare engines and to develop the FLUX side. Answer with **the same composition on both engines**, both on one card, and say on the card face which one ships: the ideogram render is the item that can put a picture in the draft, the FLUX twin is a comparison.
- Write the FLUX prompt from the same scene description in natural language, under about 300 words, and keep the palette sentence and the "no readable lettering" clause identical.
- Record rules for a second engine of one slot (an approved comparison copy keeps `verdict: approved`, its vault asset and no post embed) are in `references/library-records.md`.
- **Build the FLUX text from the ideogram prompt's own words** — its `high_level_description` and each element `desc` — never from the PNG, and close with one sentence naming the beat ("The beat is simple: …"), because a text prompt has no `lint` and no bbox check, so the prose is the whole specification.
- **A pair is two card items, because an item carries one attachment.** `<slot>-r<k>` and `<slot>-r<k>-flux` sit in adjacent rows with the same `Why`, and each description names its engine plus — the part that makes the pair readable — the one thing that differs between the two renders. Two pictures side by side with no difference named leaves him to do the comparison alone.
- **Check both on their own evidence; a clean render on one engine does not vouch for its twin.** The two engines fail differently on the same scene: on one slot the ideogram drew the figure with its prop floating beside an empty hand while the FLUX twin held it correctly, and on the next slot the ideogram was clean while the FLUX twin put a plank walkway across the gap the whole picture was about. Read and crop both.
- **A companion that contradicts the beat is a hold-back like any other render, and its cheapness is the argument for re-rendering it** — about three minutes against one of his clicks.
