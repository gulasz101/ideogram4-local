# Writing a figure and the object it holds

Almost every image in this series is one chibi figure acting on one prop, so the render's success usually turns on how the hand and the prop are described. These are the shapes that work and the ones that come back broken. They belong with `references/engine-pitfalls.md`, not instead of it: that file carries the numbered failure modes, this one the prompt recipe for the figure-with-a-prop frame.

## State the limb count in the `high_level_description`

Write it out, in the same sentence as the headcount:

> exactly one person in the whole picture, no other faces, no crowd, and that person has exactly two arms and two hands, each arm and each hand drawn once, clean and whole, with five fingers per hand and no extra fingers, no fused knuckles and no doubled hands

Without it the model drops an arm, merges both hands into one enlarged mass, or grows a third limb behind the object. All three are the "looks broken" class, rejected on sight, so this clause is cheaper than any re-render.

**A limb count is not a body layout: say where each arm is rooted.** A count alone can still fail: both arms and both hands can come back rooted on the same side, the lower one growing out of his flank. The repair is geometry, written before the pose: one head, one continuous torso, two separate shoulders, one on each side of his chest, each sleeve ending in one arm, the raised arm across the chest and the hanging arm on the opposite side with the whole chest between them, plus a negative in the same sentence — no limb from the ribs, the flank or the hip, no second arm below the raised one. A pose that puts both hands on the same side of the body needs that sentence most, because the model satisfies the count by stacking the arms.

## A hand that meets fabric or a flat surface is a contact pose too

The failure is the **meeting point**, not the prop. Two poses cost three renders each at both engines: hands pushed into trouser pockets (wrist and fingers fused into fabric); hands resting flat on a bench (arms as stumps below the elbow on ideogram, six splayed fingers on flux).

What works, in order of reliability: hands **out of the frame** entirely (arms run down behind a bench top or cropped at the sleeve — say "his hands are hidden below it and out of the picture, no hand or finger is drawn anywhere"); then one closed fist resting on a solid edge, "one simple rounded fist, no separate fingers". **Do not treat "both hands hanging open and empty at his sides" as safe** — both engines drew extra fused digits on both hands. A mitt with no fingers drawn at all is the house style and passes; what fails is a hand that has to hold, grip, enter or lie on something, or that is open enough to show its fingers. **Never hold a render because a read says "no countable fingers"** — at frame scale that is what the house style looks like. The hold questions are a **missing** hand, a **spare** hand, a duplicated forearm, or digits drawn as a spur or two thumbs, settled on a crop that holds both the hand and the surface or prop it meets. A thumb visible where the fingers fold is all the digit evidence a rounded fist owes you.

Given a second failure on one slot, change the pose, not the adjectives; given a third, let the slot wait for the next batch.

## An action that is a contact is drawn as proximity

A frame whose beat is a hand *doing something to an object* comes back with the hand parked beside it: a palm hovering over a dome, a key held at the keyhole rather than turned in it. "Pressing" and "inserting" name an intent, and a hand near the object satisfies an intent, so the contact must be written as a state of two things, not as a verb.

Both clauses belong in the same element as the hand:

- **the contact in the hand's own terms** — "his open palm pressed flat down on the dome, the heel of his hand touching the red surface, his fingers splayed over its curve, no space between hand and button";
- **the receiving object's state change** — "the dome pushed down under his palm", "the lever end resting against the stop", "the key's blade inside the keyhole". With no deformation, insertion or displacement described, a hovering hand passes every read.

Measure it on a crop of the contact point at 3x and ask only: does any part of the hand meet the object's surface, and is the object in its pressed or entered state. A full-frame read answers the intent it was handed. **The crop must hold both ends at once**; if it does not contain the object, widen it rather than tightening, and never let that miss stand as clearance.

**A beat built on a contact that fails runs the same rule backwards.** When the story is that the prop does *not* reach, write the gap as a property of the picture ("pointed at the mesh and nowhere near the padlock", "a hand's width short of the socket") so the absence is drawn deliberately.

## A state named by an adjective is drawn as the object's default

"The door stands open" came back shut flush in its frame. The engine has a default for that object and an adjective does not override it, so the state must be written as geometry a drawing can show: which way it swung, on what, which face the camera sees, and where the opening is and how wide.

> swung inward on its three hinges, its inner face turned toward the camera, the thickness of its edge down the left side, a band of darkness a hand wide between that edge and the frame

The same holds for any state the beat depends on: a lid `standing open behind the box` needs its hinge side and the space it leaves; a drawer `pulled out` needs how far and what shows inside. **A soft or flat object asked in a folded state comes back flat**, because one sheet is paper's own default. Write the fold as geometry — a crease line down the middle, the doubled thickness at the folded edge, a stack offset so every crease shows — or accept the flat version as a caveat and let the beat ride on the count and the places instead of the folds. Settle it on a crop wide enough to hold both the object and the space the state should leave, because shut and open read alike in a full frame. When the object is a companion's own story beat, a wrong state is a beat failure held back, not palette drift named on the card.

**When the state lives on a SMALL prop, the geometry clause buys one attempt, not a cure — move the proof to a large element.** A shackle that must read as sprung open stayed seated through three renders; even stated as a gap of wood, it stayed shut. After one miss, move the beat's proof to a large element the picture cannot get wrong: the door standing open with a band of light in the gap, the lid beside the box, the drawer pulled out far enough to show the file. Keep the small prop in frame doing its pose and let the big element carry the state. **When the state cannot move off the small prop, choose between two exits.** If the action reads and only the following state is missing, ship with that stated as a residual on the card. If the missing state makes the frame say something false, send the composition back to the post's author as a hand-off. Never write a third re-description of the same clause.

## Two hands cupping a small round prop is the worst hand pose — remove the prop instead

A disc, plate, coin or token cradled in two hands came back as finger soup from both engines, while the same man's hands were clean in neighbouring frames. The cause is the pose: two hands must meet at a small object's rim, so the model invents overlapping fingers.

Re-describing the fingers does not fix it. Take the prop out of the hands: stand it in a wooden cradle, lean it against the frame, lay it flat on the bench — and give the figure two closed fists on a surface, "drawn as one simple rounded shape, no fingers spread" for each hand. A hand that touches nothing has nothing to mangle. A hand resting flat on a rim is second best and needs a crop at 6x.

**The fist is not a cure when the prop has to meet a surface.** When a small prop must sit near a face, stop describing the hand: stand the prop on the surface ("one loose round slug standing upright on the bench in front of the empty socket, its flat base on the boards") and let the count and the arrangement carry the beat. Only the arm leaves the frame.

Settle every hand claim on a crop, never on the full-frame read. `crop-probe.py --box <x0,y0,x1,y1> --scale 6 --out <path>` on the hand alone is the evidence.

## Never ask for a pinch grip

A thumb-and-forefinger pinch around a small object is the one grip the model cannot draw: fused hand, two thumbs, extra knuckles. Ask for a **closed fist with the thumb laid over the folded fingers, and no separated fingers sticking out**, with the prop's end visible above the thumb.

**Run one mechanical check before `submit`:** grep the drafted prompt for the pinch in any spelling — `thumb and the forefinger`, `between thumb and forefinger`, `pinch`, `forefinger and thumb` — and rewrite the hand element if it fires.

## A hand contact per hand, not "both hands around it"

"Both hands closed around a big X" produces a hybrid: the model invents where each hand meets the object and threads it through itself. Write the contact hand by hand — "one hand closed on each side of its body", "his right hand on the shaft, his left steadying the base" — and the object keeps its own geometry.

## A tray held out with something standing on it grows a hand at its rim

A wide flat tray or shallow box held in both hands with a prop standing on it came back with a **third detached hand** on the tray's near edge: each rail took a hand, and the prop on the open surface invited one more.

Write the grip and the placement as two separate facts:

- one hand per rail, named per hand — "his right hand grips its right-hand wooden side rail and his left hand grips its left-hand wooden side rail, one hand per rail";
- the content prop away from the hands — "standing alone in the middle of the mesh, away from both rails";
- the closed set — "nothing else in the frame touches the tray, and the picture contains exactly two hands".

A third hand at a rim is settled on a 2x crop of the tray's edge. If a second attempt still grows one, take the tray out of the hands and rest it on the crate it is emptying into.

## Let the beat live in the object's condition, not in a symbol

When a broken template asks for a text surface or a symbol for the idea, the substitute that reads fastest is **one object drawn in a state of wear, repair or adjustment**. A jar crossed by plaster seams and iron staples says "rebuilt from its own pieces"; a key with its shaft freshly filed says "re-cut to fit, not replaced"; a post with a bright wear band says "the threshold moved"; an unlocked bay with a dry funnel says "the one that is not running".

Why this beats a symbol or a comparison pair: a symbol has to be decoded and invites a badge or icon, while a state is geometry the engine can only draw correctly or not. It keeps the frame to one object and one figure, the cheapest composition the bar allows, and gives the beat a crop-settleable proof.

Check it by asking the full-frame read what **state** that object is in, in its own words. If it answers "a jar on a bench" and not "a jar that was broken and mended", the state did not draw — rewrite the state as a physical fact rather than adding an adjective.

## A diagram in the prompt becomes a fact of the room

A drawn diagram is an overlay in a different idiom from the painted room, so it reads as a pasted graphic. Replace it with a physical fact of the same room:

- **"everything the public can reach goes through one tunnel" → one small window in a wall.** Exactly one small square pane lit from the room behind it, nothing else set into the brick.
- **"a sidecar that asks the big machine for numbers" → a small tap on the machine's flank.** A tall riveted pump with a plain brass tap bolted to its side at knee height, one thin thread of water into a small tin cup, a damp ring in the dust.
- **"the same page, restyled" → two identical jars, one plain and one glazed.** Same height, belly and mouth, one size repeated twice.
- **"a report with a column for each field" → a grid made by ONE object, never many dividers.** Ask for one iron rake head — a straight spine, six equal tines in one row at even spacing, three flat collars slipped across all six tines at three even positions — so the crossings belong to a single object and alignment cannot go irregular. Keep the collars as thin flat bands: drawn as rings they fuse into the tines.

Four clauses make these hold. Say the **count** in the picture's own terms (`exactly one small square window`, `one size repeated twice`), because a symmetric frame invites a counterpart. Keep the **light** where it cannot argue: a pane lit from a room the camera never enters glows from inside the glass. Keep every prop out of hands. **Build repetition into a single object**, so alignment is structural rather than described.

Cheapest slots in a batch: an object in a state with nobody in the frame cannot lose a hand, an arm or a head.

## Name the prop's parts and then the absences

A mechanism described as a whole comes back as something recognisably neither object. A padlock written as "a big brass padlock" came back as a bent grey bar threaded through a brass loop. Spell the parts, then say what is not there in the picture's own terms:

> a solid brass body the size of a fist with a small round keyhole on its front face, and one thick U-shaped steel shackle standing up out of the two holes at the top of the body with both of its ends pushed into them; the shackle is the only piece of metal above the body, nothing is threaded through it, and there is no rod, no bar and no handle anywhere in the picture

Phrase the absence as a property of the picture ("nothing is threaded through it", "no rod anywhere") rather than as a bare prohibition on a word: the linter also reads the ban, and a concrete noun inside a negative clause is still a noun the model can draw.

**A mechanism that acts on a cable where the cable meets its device is drawn as the device's own fitting.** Stand the mechanism on open length of cable a hand's width clear of the port, say what it rests on, and add the absences for the position as well as the part. The same trap sits wherever an object has a default neighbour: a valve at a pipe joint, a gauge on a panel, a plate on a door. Read the result on a crop of that joint.

## Say which end of the prop meets the target

A mismatch described only by size leaves the model free to choose which end of the prop goes where. A prompt that said an oversized old key was pushed at a socket came back from both engines with the man gripping the shaft and offering the round bow to the hole: the size relation was drawn and the orientation was not.

Write the contact as a spatial fact in the prop's own `desc`: name the end that enters, name the target opening as the thing it approaches, and place each hand.

> the notched blade enters the small round socket on the front face and is far broader than it; his hands are closed around the round bow behind the blade, one hand at the bow and one on the shaft

Then settle it on one crop of the contact point and name the units in the note.

**A beat that says "this will not fit" needs both profiles written as geometry.** Name the profile of each object inside its own element: the opening "cut with four straight sides and sharp square corners, an empty socket with nothing in it", the prop "a straight round shaft of even thickness from the bow to the tip, the bit cut square at the end". One profile unstated turns the frame into a key and a door.

- **Give each part of a relationship its own element and its own `bbox`** even when both sit on the same surface an inch apart.
- **Check the two ends on two crops, one per object**, and ask whether the cut of the hole and the section of the shaft read as different shapes in the same frame.
- **The same clause covers every wrong-shape story**: a coarse-threaded collar against a fine-threaded one, a wide blade against a narrow slot, a square tenon against a round mortise. Write the difference in the terms a draughtsman would count.

**Choose the direction whose physics actually fail.** Square into round reads at a glance; round into square does not. Say the sentence out loud with the profiles swapped before submitting.

**A corrected geometry prompt fixes one engine at a time.** Ask "would this go in" of each file separately at the collect; a twin that misses the fit twice makes the slot single-engine on the card.

## Write the body top down before the pose, or the head grows out of the chest

A figure whose element gives only a pose has no stated neck and no stated shoulders, so the model invents the junction and puts the head straight into the torso. That is the "head growing directly from torso" rejection: the scene passes and the body does not, and an anatomy failure outranks every other defect.

So when the figure's body is visible below the chin, write the parts in order, in one element:

> one round head with …; below his beard a short bare neck, fully visible, joining the top of his t-shirt collar; below the neck two wide level shoulders; from each shoulder one whole arm reaching down with the elbow slightly bent, ending in a hand pushed into his pocket

Two clauses do most of the work: **the neck is named and called visible between the beard and the collar**, and **the shoulders are level and sit below the neck**. Add the posture as a state when the previous render came back hunched.

Do not answer this defect with a negative clause naming the broken shape: the render is caused by a missing part, and naming the wrong shape puts a head shape on a torso. Tighten the element's `bbox` to a tall narrow block for an upright figure as well.

**A figure with no torso at all — head and legs with nothing between — is the same family.** Fix it by writing the full chain in the element's desc — head, neck, shoulders, chest, torso, hips, then legs — and widening the `bbox` to a tall block. State the count too ("one single character, full body visible from head to waist, no missing torso"), because a count clause alone is not enough and a parts list alone is not enough.

**A figure's `bbox` must not start or end on the frame edge unless you want him cut there.** An element boxed `y 10-520` starts on the top edge, so the model reads "crop this figure at the top" and does exactly that. A figure who should be cut only by a side edge gets a box that starts well inside the frame (y 40 or lower) with the sentence saying so. And **hands in pockets hides where both arms end**: when the arms matter, put the hands on a surface.

**A box that starts well inside the frame still loses the head when the top of the picture is furniture.** Two clauses prevent it: *his whole head is inside the frame and well below the ceiling beams, with clear painted brick space above his hair, and nothing crossing his face or his neck*; and start his box below the beam or joist that occupies the top of the frame.

**A head that keeps getting cropped by the top edge comes back hidden behind his own shoulders, so the repair has to forbid the lean.** Write the posture as a state and give him nothing to lean on: *his back is straight and he is not leaning over the bench, he stands a hand's width back from it, his head up and his face turned toward the <object>* — in the figure's own `desc`, not only in `high_level_description`.

**Bare forearms at cel scale come back saturated, so keep the cuffs down.** Say the sleeves are *buttoned at the wrist* and that no bare skin shows on the arms. `references/prompt-hygiene.md` carries the palette side.

**A body part the element's `bbox` cannot hold is a body part the model draws without a boundary.** Name no garment or part that sits outside the box — either extend the box over the whole visible body, or drop the trousers, hips and legs from the prose and say in one sentence where the frame cuts him.

**A pair of boots is a count, and a pair is two only when the sentence says so.** Write the count as a fact about the picture: "exactly two legs, one left and one right, grown from his hips; exactly two brown boots planted side by side, the only footwear anywhere on the flagstones; a single soft shadow under the pair and no other shadow on the floor". Check with a frame-wide count of shoes with their x-positions, then a 10x strip of each frame edge.

**Counting boots is not counting legs, and a third leg can end in mid-air.** Ask the count of the trousers on a crop of the belt-to-floor column: how many trouser legs leave the belt, and does each one end in a boot.

**When the count fails twice, remove the part — but the cut buys one attempt, not a cure.** Stop writing legs altogether: the bench's near edge crosses in front of him at the waist, and the element's `bbox` stops above that edge. Say it in both places. The cut ships only after a whole-figure crop read answers both questions — is each arm drawn from the shoulder, and where does each hand end. On the next miss the figure comes out of the frame entirely.

## The whole silhouette is its own read, and the pose decides it

A rejection can name the body rather than the hands, and a frame whose hands, props and palette are clean is still rejected whole on it. The body gets its own question, asked on a wide crop of the figure alone, before the hand crops.

Two poses break the silhouette:

- **the torso laid across a prop that runs the frame's width.** "Leaning his upper body over the horizontal pipe" draws the torso elongated along the pipe and effectively duplicated.
- **the figure folded low against a machine.** Cross-legged or crouched with the chest over the knees gives no waist.

Neither is fixed by re-describing the joints. Change what the picture contains: **an upright figure with the prop beside him, not under him.** State the posture as a static fact ("standing upright, his weight on both feet, his back straight, the tank beside him") rather than as an action ("leaning in to look"). When the beat genuinely needs him low, cut him at the chest.

Ask the read for the four things that failed: head size against the torso, shoulder width against hip width, the length of the torso, and how the torso meets the hips. Add one yes/no: **is any part of the body drawn twice?**

## Count the renders before writing the next prompt: a figure that keeps breaking is the concept, not the sentence

One slot can lose three renders to the same figure and each fails differently, which feels like progress while the defect is unchanged.

**Count the renders before writing the next prompt, not after.** At two failed attempts on one figure, stop re-describing the body and change what the picture contains: take the figure out, reduce him to a hand and forearm entering the frame, or stand him behind something that legitimately hides the body. When the figure is the only thing the owner objected to, removing it clears the objection exactly. `references/archive/re-render-defect-persistence.md` §7 carries the hand version of the same move.

**The three-render arithmetic in `references/archive/hold-back-or-ship.md` is a card's attention budget, not a cap on a slot nobody has seen.** Count by defect, not by render: two misses of the same clause is the signal to change what the picture contains, and a slot whose successive attempts each fix one thing and drop another is progressing even at its fifth render.

**The same count applies to a dressing prop, not only to a figure.** A prop that cannot render cleanly twice is cheaper to remove than to describe a third time.

**The composition belongs to the post's author, so a removal is a hand-off, not a unilateral call** — a child issue of the card assigned to the author, asking for the composition with no human figure, then `blockedByIssueIds` on the card. List the failed attempts and what each drew.

**A removal that keeps the frame is not a composition change, so it needs no hand-off.** When the figure is the only thing that leaves — same camera, same room, same bench, same props in the same places — delete the figure element, re-aim the remaining `bbox`es at the props the beat rests on, and say in `high_level_description` that nobody is in the picture, with no hands, no arms, no legs and no figure of any kind.

**A slot that owes two independent fixes takes the still life in one move.** Count the families, not the renders.

## Keep the small prop plain, or it becomes another object

Every extra feature on a small metal prop invites a different reading. A brass cylinder described with a flange came back looking like a spent cartridge; written as "smooth and plain with flat ends, no flange, no ring, no cap and no bullet shape" it read as a plain peg. Where the prop's *shape* is the story, make the mismatch a stated proportion and set the prompt boxes so the proportion survives a crop.

## A prop shaped like a body part has to be checked as a prop, not as a hand

A pair of empty work gloves lying on a bench came back drawn correctly and was still the riskiest element: at full frame the read called them *glove-like hands*. The beat was "the task was posted and nobody's hands were in it", so a frame whose gloves could be read as hands says the opposite of the section.

Settle it on a 3x crop of the prop alone, and ask what the object is, not whether it is a hand: visible cuffs, a hollow collapsed body, stitched seams, no fingernails, and no wrist or forearm running out of the shape into the frame edge.

The same check covers every body-shaped prop: a mitten, a boot standing on its own, a mask on a hook, a mannequin's hand, a jacket on a nail. Give the prop one object-identifying feature in its own `desc`, and never place a body-shaped prop where a real hand would be.

## An object that carries a label in real life renders with pseudo-text on it

The bar allows no lettering unless it is readable text (SKILL.md text rule), and the engines fill every **label surface** they recognise with letter-shaped marks. `references/prompt-hygiene.md` carries the mechanism and the ban rules; what this file adds is the composition rule.

A fire extinguisher on a wall bracket came back with a white label of blurred text lines, and it was the only defect in an otherwise clean frame. The prompt said "no labels" and it made no difference: an extinguisher, a gas bottle, a first-aid box, a shipping crate stencil and a warning plate all have a label as part of their identity.

- **Take the label-bearing object out of the composition.** Replace it with something that has no face to write on — a closed plain toolbox standing on the tiles, a bare shelf plank, a coiled hose.
- If the object has to stay, give it a positive plainness clause plus one room-level sentence ("every object in the room is plain: no labels, no plates, no writing on any of it"), and buy at most one attempt with it.
- Check it on a crop of the object at 3x.

A tiny printed mark plausibly part of the object can be named as a caveat on the card; a label carrying lines of text is not.

## A bezel cluster is settled by the crop, never by the frame read

A screen whose beat needs only one flat shape still comes back with two or three window-control dots on the monitor's **bezel**, and a full-frame read reports that cluster on frames whose bezel is blank — so the claim goes to a 2x crop of that corner before it is written on a card or used to hold a render back. The screen composition itself is in `references/archive/prompt-repair-audit.md` under *Translating a beat that lives on a screen*; do not write a second copy of that rule here.

## Choose a dressing prop that cannot carry text or a wrong size

The corner props are the ones nobody checks. A cellar frame whose oval track, crank and crate count were all correct was held for the spanner lying on the flags: several floor flags long, longer than the bench is wide, with faint stamped pseudo-lettering down its handle.

- **A tool is the worst corner filler.** Prefer something with no flat face and no size to miss — a short length of chain coiled flat, a folded cloth, a plain closed tin.
- **Anchor the size to another object in the sentence**, not to an adjective: *a short length of chain no longer than the bench is wide*.
- **Ban the marks at picture level, not object level.** Add the whole-frame sentence *no stamped, engraved or embossed mark on any metal surface in the picture*.
- **Crop the dressing props at 3x–4x before the card**, not only the beat's object.
- **When a repair fixes the beat and introduces a defect in a prop the repair added, the next render is subtractive** — drop the prop or swap it, keep the geometry that now works, and state the overage.

## Check it on a crop, at two scales

A hand or a small mechanism is exactly the kind of detail a full-frame read smooths over. Two independent reads that agree on the defect is enough to hold the render back; write the crop to disk with `scripts/crop-probe.py` and read the file, because the `region` parameter resolves to different content between calls. A read that says the pose is "natural" has settled nothing — count the arms, count the fingers, and check whether the object's parts still connect.

**Aim the crop before you trust it, because the element's `bbox` does not tell you where the hand ended up.** Locate first, then zoom: one wide pass over the whole figure at 3x–4x (or `frame-map.py` on the quadrant) to find where the arms actually end, and only then `--box` that spot at 6x.

**Find the figure by asking for its pixel bbox, not by hunting its colours.** One call of the shape *give the approximate pixel bounding box of the standing man in this 1216x832 image as x1,y1,x2,y2* answers a real box, and the crop then wants a head-to-floor column roughly 340 px wide around it, upscaled 4x–5x. A crop whose header region does not contain skin is a miss and must be re-aimed.

**A crop that cuts a limb off reports the limb as missing.** Count limbs, heads and contacts only from a box that holds the whole figure's width — a single band across the figure at 1x–1.5x, scaled to about a thousand pixels wide. **A crop holding one hip, waistband or pocket invents a hand that is not there**, so a third-hand or third-arm claim needs the whole-figure crop before it costs a render. Then take each hand separately, tight, when the question is digits.

**A soft refusal is not a rate limit and not a finding.** Re-ask as a plain description: `describe what this crop shows, part by part: the key, the opening behind it, and how they sit`. A refusal copied into a check note reads as evidence about the picture when it is only evidence about the question.

The description also settles the case two closed reads answered oppositely. Treat a leading question's answer as one reader's guess, and settle a fit, a contact or a count on the description of the parts.

**But when the two reads disagree about whether anything is drawn in a region at all, neither read is the tool.** `scripts/check-pale-band.py <png> --columns <x0>,<x1>` prints the dark-pixel share per sampled column. Run that script rather than writing the same profile inline in a heredoc. `references/archive/hold-back-or-ship.md` carries the case where one crop read invented a panel border.

## An open palm with spread fingers is the second hand shape that fails on both engines

Beside the grip, the raised open palm is the other pose that never survives. At blog-header scale a spread hand is a fan of five thin shapes, and both engines draw it as a convoluted mass with no countable digits.

The lesson generalises: an open hand of any kind is unreliable. An open hand is a fan of thin shapes whether it is spread wide or hanging loose.

**The one reliable answer is no hand drawn at all — but hide the arms behind a described SURFACE, never behind the body.** Arms that run down behind a bench top, a desk edge or the far side of a crate leave the frame's own object exactly where the forearm would end, so there is nothing to draw. The same sentence written as *both arms run down behind his back* puts the end of the arm inside the silhouette, so the model closes it as a **rounded stump with no forearm, no wrist and no hand**. Settle it on a 4x–5x crop of the shoulder. When no surface can hide the arms, take the figure out of the frame. Second best is a closed fist resting on a surface, stated as "one simple rounded fist, no separate fingers", counted on a crop at 5x-6x.

**A fist held up in the air is not the safe option — it comes back as a duplicated arm.** A chest-height fist with nothing under it failed both engines: each drew the **whole forearm twice**. The words `exactly two arms and two hands` were already in the `high_level_description` and did not outvote the pose. A limb with its end free in the air has no surface to be anchored to, so the model carries the shape on down and closes it a second time.

**Give the fists a surface to rest on and describe that surface as its own element with its own `bbox`** — a plain work stool on the floor, "four straight legs, a square worn seat, the man's two fists resting flat on the seat". A raised fist has passed nowhere.

**A surface anchors the arm; it does not guarantee the hand, and the two engines fail the same surface pose differently.** Write the contact as flat and closed rather than as a weight on an edge ("both hands resting flat on top of the seat, the fingers of each hand folded under, no fingers curled over the edge"), and settle it per engine. When one engine still fuses where the other passed, that is a **single-engine slot** — ship the passing render, name the held job id and its defect on the card's face, and do not spend a third render restoring symmetry.

Consequence for the check: on a figure whose arms are meant to be down, the crop question is **count the arms, not the fingers**.

## A hand curled round a handle fails on both engines — give the prop a rest instead

A grip is the smallest curled shape in the frame: five digits closed round a cylinder a few dozen pixels wide. Flux fuses them into one mass; ideogram keeps a thumb on top and three merged knuckles underneath, which reads plausible at full frame. Cropping at 4x settles it either way.

Do not reword the grip and do not try the other engine. Rewrite the composition so nobody holds the prop. A magnifier stands upright in a plain wooden rest; a lamp sits on its own base; a lever hangs from its pivot. The figure then gets hands that draw nothing to go wrong — one simple rounded fist each on a desk edge, or the arms taken down behind the figure so no hand is drawn at all. Never fall back to "open and empty at his sides".

## State the floor, or the figure floats

A correct painted floor does not put the man on it. The man and the boiler both hovering two brick courses above it, no contact and no shadow, reads as two cut-outs pasted on a background, which fails the bar's "one continuous scene" clause even though every limb, prop and corner is correct.

Fix the wording in both places: in `background`, name the floor as running unbroken to the foot of the wall and say every object in the room stands on it; in the figure's `desc` and in each floor-standing prop's `desc`, say the shoes are planted flat and the legs rest on the stone, each with a soft dark painted shadow underneath. A shadow is what proves contact.

**Check the grounding on a tight crop, not a wide strip.** Locate the figure in **pixels** first, then cut a small region around the contact point at 4x-5x. A verdict of "floating" is only trustworthy from a crop that shows the sole and the floor line in the same small frame.

**The same tight crop governs a PROP whose beat is its distance from the floor.** Ask it of the contact edge itself at 5x-6x: is there a lit strip of floor between the object's bottom plank and its shadow, and does the shadow touch the object. **A marginal answer is a caveat, not a hold:** when the gap reads at 5x and the shadow is separate, the frame ships with `the air gap under it is narrow, about a quarter of a plank` written on the item.

## A repeated cast multiplies the body risk, and an airborne verb is what lifts it

A frame whose point is several identical copies of one helper carries the count sentence for the *set* and still comes back with each copy broken in its own way: two of three hovering above the floor, one with a single leg, one with an arm fused into the back of its head. The count says how many there are and nothing about the body of any one of them.

Write the body into **every** copy's own element, not once for the set:

- "exactly two legs, both drawn whole from hip to floor, both feet planted flat on the floorboards", plus "exactly two arms: the right arm raised holding X, the left arm hanging down at its side", plus "nothing hangs behind its head" when a raised arm shares the space above the shoulders.
- Replace every pose verb that has no surface under it. "Caught mid-step", "slightly tilted forward", "leaning in to look" all resolve to a jump or a hover. A static state does the same job: "standing one step behind it, both feet flat on the floorboards".
- Keep the ground clause in `background` as for a single figure.

The check is a count of copies and legs on one crop wide enough to hold two adjacent figures. **Check each engine's file on its own**.

## One small figure comes back as two — check the frame edges for a twin

A short full-body character drawn in a symmetrical room was duplicated: one complete figure in front of the rack and a second, identical one cut by the left edge. The prompt said "one figure, exactly two arms and two hands" and the count was satisfied twice over, so the count clause did not stop it — the duplicate is the model balancing a symmetric composition.

- Write the singleton twice, in the `high_level_description` **and** in the character element: "exactly one person in the whole picture, nobody else anywhere in the room or at any edge, and no reflection or mirrored copy of him". The room-edge wording is what matters.
- **A partial figure at the edge is still a second person.** Crop the suspect edge and count bodies, not faces.
- The same failure arrives from a symmetric backdrop. Break the symmetry with a deliberately uneven prop set.
- **The doubled clause buys one attempt, not immunity: on the second duplication the figure comes out of the frame.** Ask the people count on the full frame before cropping edges whenever the composition is symmetrical.
- **A duplicated figure does not always stand beside him** — the engine sometimes welds the spare body to him or floats it next to him. The fix is structural: **narrow the figure's box** and ban the objects by name in the `high_level_description`.

**The spare limb also arrives as a SLEEVE in the arm-and-hip overlap, where a wide read calls it a fold.** Settle this class with the 2x figure to locate, then a 6x of the arm against the torso, then one 4x of the whole torso. In the prompt, say each arm is drawn once from its shoulder and that nothing hangs behind him or between his arm and his body.

## A contact clause on the helper is read as a limb on the man

A render grew a third limb: a grey segmented mechanical arm out of the protagonist's own shoulder. The prompt had the grey android helper "lean its elbow on the far side of the belt" — a contact clause belonging to a secondary character, which the engine attached to the nearest human instead. Settle it on two crops and fix it by removing the contact, not by adding another "exactly two arms": the android now stands a step back with both stubby arms at its sides.

## A companion animal's traits migrate onto the person

When the frame holds a small animal mascot beside the figure, the model blends the two bodies: the person comes back with the animal's tail curling out of his waist, and the animal comes back with a third ear or the wrong number of legs. Proximity is the cause and no rewording fixes it. Two misses means the animal leaves the picture: drop its element, re-aim the remaining boxes, and put the negative in `high_level_description` — `no animals in the picture, no fox, no tail on the person, no animal ears on his head`. A single miss is settled on two crops: 4x of the figure's waist and 4x of the animal's head.

## When it fails, re-render rather than argue

The fix for a mangled hand or a hybrid mechanism is a prompt rewrite, never a note on the card. Say in the held-back attempt's record that it was held back at the self-check and never shown to him, and keep the attempt suffix on the render name.

## A sixth-digit claim needs the tightest crop before it costs a render

A loose crop adds the arm's own contour as a segment, so a mid-zoom read over-counts where a wide read under-counts. Take the digit count from the tightest crop in which the whole hand fills the frame, and treat any extra-digit or extra-limb claim as unsettled until that crop exists.

**Two hand crops that overlap count one hand twice.** Treat the counts as a union, not a sum.

## A figure behind furniture and his shoes in the bottom of the frame cannot both be drawn

One sentence pair is geometrically self-contradictory: `stands behind the bench` plus `shoes flat on the concrete inside the bottom of the frame`. If he stands behind the bench, its apron hides his legs.

- **Write the figure clear of the furniture from the first pass.** Stand him beyond the end of the bench or table, on open floor, and keep three clauses: `clear floor all around his whole body`, `nothing crossing his waist, hips or legs`, `his trousers running unbroken from waistband to shoes`. Drop `behind the bench` entirely.
- **Judge it on a written 2x whole-figure crop, and let two readers decide.** Keep the question to one line.
- **The two engines do not share the defect rate here**, so judge each frame on its own crop.
- **Compare the figure's `bbox` against every waist-height object's box before you submit.** `check-bboxes.py` reports each element against its own `desc` and prints "no bbox contradicts its own desc", because the overlap between two elements is not a contradiction it tests. Read the pairs yourself.

## A post's slots are one sequence, so check the states against each other

A three-slot post whose sections tell one story reads best when the three frames share one room and one repeated object, and that object's **state** carries the arc. Verify the flip by comparing the two frames to each other, not each against its own prompt. Write the state each slot must show into its item description. Submit the set as one batch.

## A beat that means "there is no room" must not be drawn as a container with compartments

An empty slot is the strongest signal in the frame, and it says the opposite of a full one. A grid of slots with one crate outside it is its own story; no wording fixed it.

The fix is an object with **no compartments to leave empty**: a chest packed so full that its lid rides up on the contents and the clasp no longer meets its hasp, with the spare crate standing outside it.

The same shape applies to a **seated** state: state the head flush against the plate with no bare shaft visible between them, and the spring behind it crushed to a stack of coils touching with no daylight between any two turns.

## A count across many objects is drawn against one shared reference

When a section says *the same correction was made to N things*, do not ask for N objects each in the corrected state. Carry the count and the sameness on **one shared reference every object has to meet**:

- nine identical pale planks lying in one evenly spaced row on the joiner's bench, every near end cut to meet **one taut cord strung between two small iron pins**, none overhanging it and none falling short;
- the pieces the correction removed **kept in the frame as evidence** — the nine trimmed slivers, all cut to the same length, heaped in a tin tray at the near corner.

State the count in the picture's own terms and say that no object overhangs or falls short of the reference. Settle it on a crop that holds the reference and several ends at once.

**At N=2 the count is the whole beat, and "side by side" collapses into one object.** Write the pair as geometry a draughtsman would place, and say the count three times: a clear gap of a hand's width between them; each named by its own position; each with its own state; then "there are exactly two planks in the picture and no third plank, no board and no beam of any kind". Check the count on a wide crop of the span.

**A set of faults reads as a row of objects each mended in its own way.** Put three objects along one bench, each plainly mended, and let the repairing differ. The room and the camera stay the same across the three.

Both shapes are still lifes, which is why they are the cheap slots.

## A beat that is a choice is drawn by where the figure stands

A comparison invites two shapes that both fail. A **pointing hand** is an open hand, and an open hand of any kind comes back as a fan with too many fused digits. A **left/right split of the frame** reads as two pictures pasted together.

Draw the decision as a place rather than a gesture:

- give the refused option every mark of complication;
- give the chosen option nothing but output;
- stand the single figure at the chosen object with **his back square to the refused one**, both fists resting flat on the bench's near edge, one on either side of the finished pieces, head down at them. **Do not put his hands in his pockets for this beat** — the waist is the one region where every zoom level invents a limb.

The choice then reads from where he is standing and what he has already made, with nothing pointed at, no arrow and no split frame.

## A thing that holds nothing is an open frame you see through

When the section's point is that something keeps no state, do not draw an empty space where the store would be. An absence is the one thing this engine will not draw.

Put the state into the object's own construction: build it as an **open frame** — one square beam across the top, one across the bottom, four uprights joining them, and the painted wall visible straight through the middle of the machine — and say in its own element that it holds nothing. The see-through middle is positive form.

To make the contrast explicit, put one older object that does hold something at the frame's edge and say in one sentence that it is the only object in the picture that does.

**The same positive-form rule covers a thing that has been shut: draw the closure as an added object, never as fittings taken off.** Express the closure by what was **added**: four stout oak boards nailed flat across the door's outside, each running its full width, a pair of square iron nails at each end with the heads proud, fresh saw cuts on the board ends, and the front way shut for good. Keep the old fittings in the negative clause only.

## A brand name in the prompt becomes readable text on a surface

When a prompt names a real product or brand, the model can render that brand name as readable text on the casing or screen. Fix by removing the brand name and describing the object generically, then strengthening the negative to name the specific thing that appeared: "no brand names, no logos, no lettering of any kind on any surface, including laptop screens and casings."

## The negative cast statement has to name every shape you are forbidding

"One person only" in the high-level description is a positive count, and this engine reads a count as a target rather than a ceiling: in a scene with two stations it puts a figure at each station. State the cast negatively and exhaustively in `high_level_description`: "one person only in the whole picture, no second person, no crowd, no helper, no assistant." Then, in every element `desc` that names a station or object, state that it stands alone.

Settle a duplicate-figure claim by splitting the frame: write the left and right halves to disk at 2x and ask each half one scoped question — is there a human figure in this crop, and what is it doing.
