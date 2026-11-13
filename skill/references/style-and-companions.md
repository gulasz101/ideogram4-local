# The series look, the accent-colour rule, and companion renders

The style block is where most rejections land, so it is the first thing to check before a prompt is submitted. This file carries the register he asks for by name, the three reason-clauses that recur, the companion-render deliverable, and the props that carry information without inviting lettering.

## The register: 1990s anime, not clean digital

The accepted look is a **1990s anime cel still** — in the Akira Toriyama / Dragon Ball line, with Akira and Perfect Blue named as the other references he accepts. Say it in three keys, not one:

- `aesthetics`: 1990s anime cel animation, the named director/line, the muted cinematic restraint of a 90s anime film still, fine photographic film grain across the whole frame.
- `medium`: hand-painted 1990s anime cel, opaque gouache background, inked outlines with the slight print softness of an old animation still, fine even film grain.
- `art_style`: rounded exaggerated Dragon Ball proportions, flat cel paint with hand-painted gradients, fine all-over film grain, one restrained palette.

`templates/style-block-1990s-anime.json` is that block, ready to copy.

**"Clean blog illustration" and "vector-like clean coloring" are the wrong register and read as the flat digital look he rejects for having no grain.** They come from the older templates in this skill, so a prompt started from one carries them by default — delete both phrases and put the grain sentence in instead. His reason for that rejection is literal: *photo graining is not here*.

**A character described by a bright jumpsuit, spiky hair and glasses can anchor the render in a Western cartoon register even when the style block asks for 1990s anime.** The style keys do not override a silhouette the model reads as a named cartoon, so check the figure's outline and colour against the register on a full-frame read, not only the style keys; if the silhouette wins, change the costume or the hair before re-rendering.

## The cast: one main character, androids are helpers

He states the series' cast in his own words: *"all the stories on the blog are about main character Wojtek and some small androids helping him managing his fleet of old 'junkyard PCs'"*, and a picture that reads as *"like two main characters"* is a defect. So each frame carries **one human figure — Wojtek — stated as "one man only in the picture"**, and a second human or a second character-shaped figure (a robot with a face and antennae, a prominent android) is what triggers that clause. An android as a small helper holding a lamp or a lid is canon and allowed; a second figure with its own agency is not. Old junkyard machines as objects (a squat server case, spent shoebox-sized devices with cracked dark glass) are props, not cast — drawing them without faces, arms or antennae keeps them out of the cast.

**Every figure stands on the ground, and the ground is part of the prompt.** His *"the characters are not standing on the floor, so you have to arrange scene better"* is about staging rather than pose: a figure cropped at the shins, drawn at a scale that floats over the scene, or set on a floor the prompt never named reads as pasted in. So name the floor plane in the `background` element (boards across the bottom third running back towards the wall), say in the figure's own `desc` that both boots are flat on it with bare floor in front of them and that his boots, legs, beard and hair are all inside the frame, and put the helper android on the same floor rather than at knee height over nothing. A wide shot with a stated floor line costs one clause and is what makes the frame read as a room.

## One palette, stated in words, with no array

Describe the palette inside `aesthetics` as the scene's own materials — ochre wood, cream, weathered grey steel, deep indigo shadow — and **do not add a `color_palette` array**: the array renders as a swatch strip along an edge or across the middle of the frame (engine-pitfalls #34). "The palette must be consistent across the image" is answered by one sentence naming one palette, not by a list of hexes.

## An accent colour he calls "stuff" is a prop list

A reason that names a colour as *stuff that does not fit the concept* means every object in that colour is off-series, not that the hex needs adjusting. Take the props out: the green tick on the wall, the green badges, the green tags, the green coins, the green cards — and then name no green prop anywhere in the prompt, because a colour you mention is a colour the model places. Sweep the prompt file for the colour word and for props that carry it before submitting; the same rule holds for whatever hue the next reason names.

A palette that keeps one accent is allowed when the accent is a material the scene needs (brass, rust), not a graphic shape.

**Answer the colour clause with a share against a sibling he already approved, not with an absence claim.** Run `check-off-scene-colour.py` on the new render and on an approved image of the same series, and put both numbers in the note ("4.974% off-scene vivid against 27.179% in the approved header"); "there is no green anywhere" is an impression, while the pair of shares shows the whole frame sits closer to one palette than the picture he already passed. Where the colour survives as scenery rather than as a prop — indicator dots on a rack — say what carries it and its size on a crop instead of claiming absence.

## A count or a check gets a physical object, not a surface

A beat that needs a count, a tick list or a verdict comes back as pseudo-text whenever the prompt gives it a surface that would be written on: a clipboard, a checklist board, a label panel, a face panel. Give the beat an object that carries the same information as a **shape**: a carved wooden tally stick with four notches cut along one edge, a stack of counted objects, a carved tick on a post, a plain coloured token with one tick cut into it. Two gains: nothing in the picture can be misspelt, and the prop reads at thumbnail size.

Ask of every prop that could hold lettering: *what would the model write on this?* If the answer is anything, replace the prop.

## A beat about something invisible becomes a physical object with one visible state

Most of the backlog is about things that cannot be drawn — a token's scope, a permission, a rotation, a flow. The temptation is to draw the computer: cards, keycards, panels, screens. That is the family that carries the pasted overlay and the invented words, so translate the beat into a physical object with a state the eye can check:

| the beat | the prop | the state that carries it |
| --- | --- | --- |
| a credential exists but lacks one right | a key held at a lock plate | the blade is visibly too broad (or too short) for the slot |
| the right is checked at use, not at listing | a bar across the door plus the lock | the bar is still seated in both brackets while he holds the key |
| the same code appears in two places | two identical notched tags | the notch pattern is the same on both faces |
| only one of two credentials did the work | a door standing open, its key still in the lock | one key in the lock, a second different key in his hands |
| access was granted but the goal is still shut | one lock open, a second barrier intact | one turned, one not |
| two permission layers, the obvious one fixed | two doors side by side, key turned in one, an iron bar still seated in two brackets across the other | one standing open, one barred — and the key is raised toward the barred one, because the bar is what the key cannot answer |
| a stale copy nearly went back over the good one | one worn rusty gear lying flat on the bench, one polished greased gear bolted in the open case | the worn one is outside the machine and his open hand is held back a hand's width above it, palm down and empty |
| two jobs finished with nobody touching them | two rebuilt towers side by side, one amber lamp lit on each plain front panel | both hands open and empty, held away from the bench |

Four rules hold the table together:

- **A mismatch must be drawn on the side that stays visible.** A part too big for its hole covers the hole, so the render shows a fit that is wrong with nothing on screen to prove it; invert it (a slot too wide, a key too broad, a bar still across) so the gap survives the drawing.
- **Different beats of one post get different props, not the same prop three times.** Three frames of keys and doors is a set, but three frames of the same door is one picture printed three times, and the card asks him to judge the same thing three times.
- **The key, the bar, the tag and the rag have no flat blank face**, which is what keeps the lettering gate clear without a ban: nothing in the frame has a surface a model would write on. A lock plate is a lock plate; a card is a writing task.
- **A state the beat depends on is a default unless it is drawn as geometry.** A frame whose section is "the door stands open for the key that fits" comes back with the door shut flush in its frame, the key in the lock on the near face, because a door beside a key defaults to closed. Write the state as a spatial fact — swung inward on its three hinges, its inner face toward the camera, the thickness of its edge down one side, a band of darkness a hand wide between that edge and the frame — and check it on a 2x crop of the hinge side: an open door shows its edge and the dark beyond, a shut one shows only rivets and a shadow seam. The same applies to any prop state the section rests on (a lid up, a bar swung clear, a drawer out): name the parts and where they sit, never the adjective alone.

## An object under judgement does not go in his hands

When the beat asks him to weigh one part against another, put the prop **down** and keep the hands off it. A hand closed around a gear's rim comes back with the fingers blurring straight into the teeth on both engines, and a two-hand hold across a wide prop comes back with smudged extra digits — the model cannot draw a grip and a toothed edge at the same point. So the worn part lies flat on the bench and he holds one open hand a hand's width above it, palm down, stopping himself; a finished machine gets both hands flat and relaxed on the bench edge. When the hands are not the subject, say so on the prompt face: *five fingers on each hand, nothing gripped in them, no hand touching any gear*.

**A contrast beat names both finishes as materials, or both sides come back the same.** "One good gear, one worn" gives two rusty gears and a rusty one fitted in the machine, and the comparison the picture exists for is gone. State each side by its finish — *polished steel, freshly greased, teeth sharp and even* against *pitted with rust, teeth rounded and dulled* — because an unnamed finish defaults to the aged one.

**Read a hand twice, at 2–3x on a 250–300 px native crop.** A small crop blown up past 3x turns film grain into "the fingers melt into the metal", and one read at that scale will send you re-rendering a hand that is only stylised. Crop from the native render at 250–300 px, scale to about 900 px wide, and keep the defect only when the second read names the same thing. "Merging into the teeth" that survives two reads at that scale is real; an "amorphous lump" that appears only in a 4x blow-up is the upscale.

## A "worn against clean" beat needs two different materials, not two steel parts

"An old copy against the good one" (a stale file, a reverted config, a rolled-back component) fails when both parts are steel: the model paints rust on **both**, so the frame shows two old things and the comparison is gone. Three attempts on one slot failed this way, including after the worn part was moved out of his hands onto the bench. The fix is a material contrast the render cannot blend: a **bright brass or polished copper** part fitted in the machine, and a **dark rusted iron** part on the bench. Name both materials in the element descriptions and in the flux text, and say the fitted one gleams. The same trick covers any "which one is current" beat — different metal, different age of wood, different cloth.

## "Does not make any sense" with "a lot of random stuff" is subtraction

That reason is the inventory defect with the style approved in the same breath (he says he likes the platformer/game-story look and then that the picture has no idea in it). So **keep the genre and cut the scenery**: drop the props that were never part of the beat (stray clouds, bushes, stepped blocks, wall decorations, background machines) and give every remaining prop a job in one action.

Open `high_level_description` with the sentence that states the action, in his terms: "The picture says one thing: <who> stands on <where> holding <what> out over <the gap>, reaching toward <the target>; <the obstacle> is why it cannot cross." A prompt whose first clause names the action cannot be read as a set of placed objects.

## A companion render in the other engine is a deliverable

When he asks for companion FLUX images to compare against, every slot of that round ships as a pair, not one image plus a draft:

- Submit the companion with `imagegen submit --prompt-file <slot>-r<k>-flux.txt --engine flux2-klein -W 1216 -H 832`, and the Ideogram render with `--prompt-json <slot>-r<k>.json`. Those are the only prompt flags: `--prompt-json` for the structured file, `--prompt-file` (or `--prompt` for inline text) for the natural-language one, so a submit loop that dies on `--prompt-txt` guessed the flag name — run `imagegen submit -h` once rather than inferring it.
- The FLUX prompt is natural language, under about 300 words, written from the JSON's own scene: the register line first, then the setting edge to edge, then the figure and his single action, then the props the beat needs, then the one sentence the picture has to say, then the no-lettering line. `templates/prompt-flux-companion.txt` is the skeleton.
- Both prompts keep the same scenario, props, palette and register, because the comparison is between engines, not between two different pictures.
- The next card carries **two items per slot** — `<slot>-r<k>` and `<slot>-r<k>-flux` — because one card item holds one attachment. Each gets its own check note, and an approved companion gets its own library record like any other approved render.
- **An approved companion is copied into the vault but never embedded.** Copy it to `tech_blog/assets/<render date>/<slot>-r<k>-flux.png` — the folder is the date the render came back, not the draft's own date — check the copy's `shasum -a 256` against the staging file, and write its record with that `asset`. The draft keeps pointing at the Ideogram, so no embed line moves for a companion: the only files a companion approval touches are its vault copy and its record.
- Submit the companions first: at about three minutes each they clear the queue before the 21-minute Ideogram jobs start, and only the last job's `eta_minutes` decides the monitor. The wrong order is invisible at submit and expensive: with three Ideograms queued ahead of them the companions read 252 to 258 minutes out instead of under twenty, so the pair lands hours late even though the engine that finishes in minutes was the one that mattered.
- **A companion whose beat is "the same object twice" will draw two different objects.** Flux2-klein reads a described pair as two props rather than as one shape repeated, so a tag with two notches came back as a square with a cross cutout beside a rectangular plate with four slots, and the picture lost the thing it existed for. Do not hold the pair as the only way to say "the same code in two places": settle the beat on the ideogram, and give the companion's flux prompt one carrying prop plus a second place the same shape is *seen* (a reflection, a second figure holding it flat against a surface) rather than two held copies. **Tightening the pair's description instead of reducing it to one sighting fails the same way:** a rewrite that gave the plate one fixed count and position of notches, then named the second copy as "the same plate again", still came back with four corner holes on one copy and a single edge cutout on the other. Two attempts at one pair, both lost — after the first failure change what the picture contains, do not describe the pair more precisely.
- **A companion whose beat is a direction will draw the action backwards.** Flux2-klein puts the figure on the wrong side of the prop it moves, so "the android pushes the cart into the drum ahead of it" comes back with the android standing between the cart and the drum, one hand on the handle, and the picture says the copy is being taken *away* from storage. Positional wording does not fix it: a rewrite that set the case, the man, the cart, the robot and the drum at named fractions of the width, and said in two sentences that the robot is behind the handle pushing to the right, produced the same arrangement at 0.13 / 0.31 / 0.54 / 0.63 / 0.89 against the first attempt's 0.15 / 0.32 / 0.51 / 0.60 / 0.86. So settle a directional beat on the Ideogram and expect the companion to fail it; two attempts with the figure on the wrong side is the engine's limit, not a wording problem, and the slot then ships the Ideogram alone with the comparison closed and said so on the card. Position fractions measured off the frame are the cheap way to prove it — a full-frame read disagreed with itself about which way the robot faced, while the five x-positions settled the arrangement in one call.

**The companion is the same frame in another engine, so every rule about the figure and the prop applies to it unchanged — and the anatomy clause fails on the flux side on its own.** A wide riddle held out with a canister standing on it came back from flux with a third, detached hand at the tray's rim, while the Ideogram of the same slot drew two clean hands: a passing main render is not a reason to skip the companion's check. Read `references/figure-and-prop-prompts.md` before writing the companion's text — the grip-and-placement triple (one hand per rail, the content prop away from the hands, "nothing else in the frame touches it") is written out there — and crop the companion's hands at 2x exactly as you crop the Ideogram's. A companion that fails is held back and the slot ships its Ideogram (rule in `references/archive/bulk-library-triage.md`).

**Two items, one slot, so the card has to say which one wins.** Say on the card face, in `detailsMarkdown`, that the Ideogram render is what the post would ship and the companion is the comparison he asked for, that approving both means the Ideogram one ships and the companion stays a reference, and that a reason saying otherwise overrides it. Without that sentence a double approval leaves the rule to whoever applies the verdicts, and the post can end up carrying the fast draft.

**Read the companion before you decide to hold the Ideogram render back.** Two engines on one composition is also the cheapest read on whether a residual defect is the prompt or the engine: when the companion is cleaner on the clause he named — blank where the Ideogram one had marks, a tick on its own card where the other drew it on the wall — the pair ships with the residual named on each item and he picks, and no 21 minutes are spent on a silent re-render. Hold the Ideogram attempt only when it fails the clause outright, not because a defect class he always rejects is present in a few pixels.

**A residual that survives both engines is the prompt's, not the render's.** If the companion carries the same scratch marks, the same invented label or the same count, the composition is asking for it, so the next round changes the prop rather than the wording (see the prop-substitution table above).

**Expect the companion to lose the register more often than the Ideogram does, and do not hold it back for that.** On the same brief the flux2-klein render reads as a modern digital cartoon carrying a grain filter while the Ideogram one reads as a 1990s cel. That is the comparison's own finding about the engines — name it in the companion's item and let him judge it, rather than re-rendering the companion or spending the pair's read on a style fight the Ideogram side already won.

**A flux companion can frame the whole illustration as a photograph of a physical print** — a white border, a desk surface, a slightly lit sheet — even though the prompt described a scene. That framing is a photo+vector montage under the show bar, so check the frame edges and the background on a full-frame read of every companion; if the scene has become a photo of a drawing, the companion is held back and the slot ships its Ideogram.

## Pre-submit checklist for a re-render after a style rejection

1. Register named in all three keys, grain sentence present, no "clean"/"vector-like".
2. No `color_palette`; one palette stated in words.
3. No prop in the colour he called out, and no mention of that colour in any field.
4. Every surface that would invite lettering replaced by a shape-bearing object.
5. `high_level_description` opens with the one action.
6. `lint` risk 0, `check-bboxes.py` clean, FLUX companion written from the same scene.
