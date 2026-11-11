# The series' look: 1990s anime, one palette, film grain

Wojtek's standing instruction for the blog series, given as a reminder because the renders drift away from it: the picture must read as a 1990s anime still — Toriyama's Dragon Ball proportions, or the register of Akira or Perfect Blue — with visible photographic film grain and **one** palette that holds across the whole set. Read this before writing any prompt in this series, and fold it into `style_description` rather than into the element list.

## Vision self-check is live, even when check notes say otherwise

A backlog card's check notes may claim "Vision self-check unavailable (text-only aux backend)" — that claim can be stale. Always try `vision_analyze` on every PNG yourself: it may be live and find defects (text in renders, extra hands, artifacts, grey boxes) that mechanical checks miss. A card whose check notes say vision is unavailable can still have readable text in every PNG. Do not put a broken image on the card because the check notes said vision was down.

**One 400 from the aux model group saying it supports text input only is a routing failure, not a
dead vision path: retry the same call once before concluding vision is down.** The retry usually
lands on another backend and answers normally, so a single such error is not evidence that the
self-check must be skipped or replaced by mechanical checks.

## Where the register goes

All three keys carry it, in words, or the model averages them back to modern digital art:

- `art_style`: `1990s cel-anime illustration in the style of Akira Toriyama, rounded exaggerated Dragon Ball proportions, flat cel paint with hand-painted gradients, fine all-over film grain, one restrained palette`.
- `medium`: `hand-painted 1990s anime cel, opaque gouache background, inked outlines with the slight print softness of an old animation still, fine even film grain`.
- `aesthetics`: the same register plus the mood and the palette families, e.g. `1990s anime cel animation ... with the muted cinematic restraint of a 1990s anime film still, fine photographic film grain across the whole frame, single warm palette of ochre, cream, weathered grey and deep indigo shadow`.

Never `clean blog illustration` or `vector-like clean coloring`: that vocabulary is what produced the modern flat look he keeps rejecting.

## One palette, stated in words

- **Drop the `color_palette` hex array.** It renders as a swatch strip and, worse, it makes every image a slightly different palette. Name three or four colour families in the prose instead (`warm ochre wood, cream, weathered grey steel, deep indigo shadow`; `ochre rock, pale cream sky, weathered grey stone, deep indigo shadow`) and repeat that phrase in `aesthetics` and `lighting`.
- **Accent props come from those families.** A green accent has read to him as `green stuff is not fitting generally the full concept`, on a green tick on a wall and on green UI cards; keep accents on the stated families and describe them as such (`a brass lantern`, `weathered steel`, `ochre canvas`).
- **A backlog prompt file can ask for the banned colour by name, and the re-render inherits it.** Old element lists carry lines like `three green checkmark badges arranged in a row on the wall` and `a small green checkmark drawn on its side`; the re-render drew them exactly as asked, three bright green hex badges with stars and ticks on a pegboard plus a tick on the cube, and the slot failed the palette clause with the prompt's own text to blame (4.6% green in three blobs against the 0.1-0.5% an approved frame reads). Before submitting a re-render of a backlog slot, read the old file's element list for green marks, ticks, badges and icons and **delete the elements** — a prose ban leaves the element standing and hands the model the shape to draw.
- **When a slot's beat is itself the banned colour**, a picture whose story can only be told in the hue he called "stuff" needs the ban split rather than obeyed blindly. Every green graphic mark goes (ticks, badges, tags, cards, column tabs) and all green scenery goes; a green material the scene genuinely needs stays as one prop named as a material, or the state is carried by a non-green material instead — a lit red-glass lamp against a plain cream one unlit says "it has to fail first" with no green pigment at all. Then say on the next card which clause was read how, so one word from him re-renders that slot alone. `references/1990s-anime-style.md` carries the longer version.
- **One palette across the set, not one per image.** When two images of one post disagree in temperature, that is the failure he names as inconsistent colour even if each frame is fine on its own.
- **Holding back an image that passes the bar.** When a round holds back most of a post's images and re-renders them in a new register, an image that passes all four clauses on its own can still be held back because it would be the odd one out in temperature on the card. That is a set call, not a defect call, and it must be said so on the card (and in the queue note) so the owner can overrule it; do not silently re-render it.

## Grain is a clause, not a filter

"Photo graining is not here" is answered by the film-grain wording above in `medium` and `art_style`, not by asking for a texture overlay. Grain sits on top of a 1990s-cel drawing; it does not turn a modern digital drawing into one. A check read that says the frame reads as *a modern digital illustration imitating a 1990s cel* is telling you the inking is modern even though the grain is present — the register belongs in `medium` and `art_style`, and the fix is the drawing language, not more texture.

**Grain is measurable, so disagreeing reads get settled with a number instead of an argument.** `scripts/measure-grain.py <png> [<png> ...]` prints, per file, the mean |laplacian| over the flattest fifth of 32x32 tiles; film grain raises that figure and smooth digital fills do not, while edges and props barely move it because only the flattest tiles are averaged. Use it when one reader says "no film grain" and the brief says grain is present, and put the pair on the card (`6.1 against the ideogram's 7.5, grain present but the lightest of the set`) rather than either side's impression. It is a comparison, not a pass/fail: a cleanly inked cel render sits lower than a photo-backed one, and the same number on two files under the same mask is the only thing that decides anything.

## A drawn-line clause is a regression, not a repair

A flux prompt built around bold inked contours and halftone dots with the grain clause dropped — the "drawn line" shape one round settled on — comes back rejected for the thing it dropped: "not all flux images are having enough photo grain and also lines are still not enough in the style of animes". Both clauses earn their place at once, so write the opening paragraph with the film-still or photographed-print register **and** the ink-line words in it, then the scene.

- When his note says "more grain", restate the opening register verbatim with the grain inside it. A separate texture sentence, or the same prompt with "more film grain" appended, does not change the drawing language, and the drawing language is what he is reading.
- The lines and the grain are one register, so a re-render answers both or neither: an ink-only repair comes back as a cleaner modern cartoon, a grain-only repair as a modern cartoon with noise on it.
- Put the android in the frame on the same pass. "There are like two main characters" is answered by a picture with Wojtek and one small helper doing a job, not by the cast paragraph in the brief.

## The defect-fix prompt is where the thin style block creeps back

A replacement prompt written from a show-bar reason — a swatch strip along an edge, a pasted UI panel, a checkerboard border, garbled lettering — is where the banned vocabulary returns, and it is easy to miss because it is not the defect you are fixing. The defect dominates the words you type, the style block gets one thin line (`digital anime illustration`, `vector-like clean coloring`, `clean blog illustration`), and the render comes back modern: a vision read calls it "modern digital anime-style concept art" and notes it "lacks ... heavy film grain". So rebuild the whole register block (`art_style`, `medium`, `aesthetics`) on **every** replacement, even when the reason never mentions style — the repair is a new picture, not a patch on the old style block.

**The gate before the card is a grain comparison against the sibling.** Run `scripts/measure-grain.py` over every render of the card; a replacement whose flat figure is far below its sibling's (one card read 3.61 against the other render's 7.98) is under-registered even when nothing in the defect reason mentioned style. Rebuild it with the film-grain register before it goes on the card, and write the two numbers in the check note so the call is visible.

**When the side-by-side was run for an edge band or a checkerboard, the engine that repeats the band is the wrong route.** Ideogram4 can keep baking the strip, the transparency grid and a duplicated prop into the frame across attempts despite edge wording, while the flux companion of the same composition comes back clean. That is a slot one engine can carry: card the flux render, stop the ideogram route, and note the split in the check note rather than spending a third ideogram attempt on a bias that is the engine's, not the wording's.

## What this does not license

This file is about the look only. The prompt still needs one action, one figure, one prop, every corner described, and no text-bearing surface anywhere — see `references/engine-pitfalls.md` and `references/prompt-hygiene.md`. A grain clause has been observed to leave composition and props intact on re-renders, so adding the register to an otherwise working prompt does not require re-checking every prop from scratch; the hands, the contacts and the held props still get their crops.

## A backlog re-render inherits the old prompt's banned elements, so audit the element list

A legacy prompt is not neutral ground just because the defect you were sent to fix is lettering. The July element lists ask by name for the families this file bans, and the engine draws exactly what they ask: a beach slot's prompt carried "three green checkmark badges arranged in a row on the wall" plus "a small green checkmark drawn on its side" on the cube, and the render came back at 4.61 % green in three blobs of 12299, 9840 and 5146 px against the 0.1-0.5 % an approved frame reads. A green tick on a wall is the object he named as not fitting the concept, and it arrived with a fix for a different clause.

So before submitting any re-render of an old slot, read every `desc` in the element list for: a `color_palette` array, a green tick, badge or checkmark, a sign, label or notice surface, a UI panel, a dial, a screen that is described in the background *and* again as its own element, and a figure box wider than one person. Delete the offending element and describe the region positively; do not restate it as a negative clause.

The same header prompt also proved the duplicate-box rule twice over: the background named a large flat panel screen on the wall and a separate element named one again, so the engine drew two monitors, and the boy's box spanned x300-850 of 1000 (half the frame), so it drew two boys and a third arm on one of them. One prompt, three defects, none of them lettering.

The register still comes from the post's own set: this file's exception holds, so a legacy slot being repaired inside an approved legacy set keeps the cel look and only the defect is rewritten.

## The cast: one main character, plus the androids

Every story on the blog is Wojtek and small androids helping him run his fleet of old
"junkyard PCs". State the count in `high_level_description` and give the figure a tight bbox:
**one** human, plus one or two small android helpers (a plain body taken from the scene's own
colour families — weathered grey or cream, never the hue the palette bans; two thin antennae, a
simple friendly face, one short helper job such as holding the work lamp or the cable end). A
second figure who reads as another main character is the defect he names as "there are like
two main characters", and a model asked for two people will often draw the same man twice.

**A handoff brief is a previous run's text, not his direction.** When a brief's item table says
`green android` or carries the round Android mascot wording, it is contradicting this section
while the same brief quotes him saying green does not fit: render the grey or cream body, and
say in the comment which line of the brief you corrected and why. Measure it before the card
with `scripts/check-green-share.py` against an approved sibling from the same week — an
approved frame reads 0.1–0.5% green with no blob, a green mascot body reads 6–27% with blobs
on the androids, and that number is the evidence a later run can re-check.

## A full-length figure fails on pose, not on anatomy

## The camera line serves the post title, never the template

The standing register ends with a camera sentence, and copying it by reflex can kill the post's own idea. A
post titled "the homelab from above" was rendered twice at `camera at chest height, no tilt` because that
line was pasted from the older prompts: both frames were floor-level views down the hall, and neither
carried a post about an overhead view. The fix cost a third render and was one sentence: `seen from high
above, straight down`, plus `no roof, no ceiling beams, no rafters in the frame` (an overhead view of a
workshop otherwise fills with the roof), and moving the dragon from the rafters onto the floor of the aisle
so it stays visible from that angle. Read the post title before fixing the camera, and change the props
the camera can no longer see.

Expect the engine to give a steep three-quarter angle instead of a true plan view even when asked. Name it
on the card; do not spend a fourth render on it.

## Two renders of one character were rejected on "body of main character is broken" in a single round, and neither was fixable by describing the body better. Both poses folded or stretched the torso: a man leaning across a steel pipe that ran the frame width came back with the torso stretched along the pipe and rejoined to a second pair of legs, and a man crouched against a machine came back with the chest running straight into the lap and the lower body twisted away. The rule that fixes it: **the figure stands or sits straight and the prop is beside him, not under him and not across him**, and nothing horizontal (pipe, rail, bench top, shelf edge, lintel) crosses between his shoulders and his knees. State the figure as *one man, one head, one torso, two legs* with a tight bbox, put the camera square on at chest or chin height with zero tilt, and check the crop before the card: at 2x from chin to mid-thigh there must be two continuous outlines from armpit to belt meeting the belt once. Hands in pockets also clears the hand clause in the same stroke. If a round still breaks the body, take the man out of the frame rather than re-describing him.

**A waist cut is not that answer, and a still life is.** Framing the man behind a bench so no legs show removes the leg count and hands back a different broken limb: he came out with no hands and one arm running as a smooth sausage through the bench leg, which fails the same rule the legs did. An arm whose far end is cropped away, or a limb that visually merges with furniture, is as much a defect as a third leg, and it does not clear a card. The version that ships is the one with no figure at all — props alone still carry the beat, and one still life between two figure frames does not break the series (post 077's third slot, approved with no reason after two count fixes made two new defects).

## A band across the frame cuts the figure in half

A flat colour strip pasted along an edge is not only a swatch artefact: it slices the drawing, and a figure standing near that edge reads back to him as "the main character is misssing half of the body" even when every prop is right. The fix has two halves — drop the `color_palette` array that renders the strip, and describe the feet as inside the frame: `his shoes resting on the floor well inside the bottom of the picture, with floor visible around them and his hair inside the top of the frame`. Write it that way from the start: `whole body` inside the picture is the phrase that trips the linter's `[human_shape]` flag (risk 0 comes back with the shoes-and-floor sentence instead), and asking for a full body without naming the floor still leaves the crop to the model.

## A decorative bar on a prop reads as a pasted sticker

Never ask for a decorative bar, stripe, band or plate face on a prop. `an octagonal red plate with one white horizontal bar across it` came back with a uniformly flat, untextured white strip that a zoomed read called a pasted UI sticker, and the slot had to be held back and re-rendered — the model paints scenery and props with texture, but a mark described as a bar is drawn flat, so it sits on the frame like an overlay.

The fix lives in the prop's `desc`, not in an adjective: name the object by its parts and its material (`one long straight shaft and one broad triangular head, both solid painted red, trailing a short streak of orange flame`), then state absence in the same sentence — `every face plain and unmarked with no bar, no stripe and no plate`. Put the same wording in the flux companion's natural-language prompt. A painted glyph the scene earns (a red X across a broken server) still reads as paint and ships; a white or light bar on a coloured face does not.

**A flat, textureless patch on a prop's face is a prompt defect, not a bad roll.** When a crop reports even, untextured colour where the prop should carry a mark, rewrite that prop's description; re-running the same prompt spends a queue slot on the same flat strip.

**A brand mark the section asks for is not that sticker, even when the model draws it with a die-cut white edge.** When the prompt names a real product or service whose logo IS the section's subject, the render comes back with the model's own flat vector rendering of it: a uniform white cut edge, no ink outline, covering the wood or wall grain behind it, so a reader calls it a pasted sticker. It is a scene object of the right size in the right place carrying the post's subject, so name the edge on the card as a caveat (`the orange cloud carries a clean white die-cut edge and no ink outline, so it sits flatter than the wood around it`) and ship it. The sticker class that costs a round is a mark that covers a region the prompt never described, or a symbol that states the outcome; a named brand the section earns does neither. The same reading applies to a brand word painted on a plank in front of that mark — correct English on a scene surface is what his readable-text branch asks for.

**A symbol that states the outcome is a sticker, not a prop; replace it with an action.** A green tick floating over a switch, a red X and a green tick on a diagram board, a checkmark badge beside the thing being fixed: each renders as a flat vector mark pasted into the scene and costs the slot even when every other clause is clean. Three things make it worse — the tick in the banned hue, the tick on a blank panel face (a surface that invites lettering), and the tick carrying the meaning the action should carry. Do not reword the symbol. Take it out and give the figure one physical action that says the same thing: a single clenched fist pulling one heavy lever down carries "the flag is now set" with no mark in the frame at all. A mark the object itself earns still ships — a red X scorched across a broken server reads as damage — but a mark that states the result is the model drawing your caption.

## Proving the clauses are cleared

His reasons are acceptance criteria, so each one is answered with a number or a named observation, never with "the new render looks right".

- **"Green stuff is not fitting generally the full concept"** is a colour measurement: count green-dominant pixels (`g > r + 18`, `g > b + 18`, `g > 60`) and quote the share of the frame, e.g. `0 px, 0.00%` against `58 px, 0.01%`. `scripts/count-hue.py` answers the same question with an explicit hue/sat/val window when the palette is known, and its two-file shape lets the note compare the new render with the rejected one on one mask.
- **"Texts are mostly not readable"** is cleared in one of two ways, depending on Wojtek's verdict: (a) if his reason says "text not readable" without "must be readable," clear it by having no text-bearing prop left, so the note says where the read looked — cases, walls, floor, the android, the clock face — and what it found there (`ticks and vents, not numerals and words`). **Removing the "no text" clause alone is not enough**: the model adds text to props that invite it, so the prompt must also remove the inviting prop — change "each tile shows a different service with its public URL below it" to "each tile shows a different service icon with no text below it", change "a chat window on the left" to "a blue panel on the left", change "a small service icon" to "a small abstract colored shape". The model labels what it can name; an unnamed shape gets no label. (b) If his reason says "texts must be readable by human," the fix is the opposite: include clean readable English labels with valid content (real service names, real log lines, actual logos) and describe them explicitly in the prompt ("a signpost bearing a clean readable English label 'Mattermost'"). The content must come from the actual deployed services — read the homelab-2nd repo for real service names, real log output, and real logos; do not invent plausible-looking service names or log lines. **"Use actual logos, do not come up with just random artifacts"** is the bar he names on the card: an abstract colored shape with a label is not enough, the recognizable service logo/icon must be present and drawn from the real thing. The standing series rule "no baked-in readable text" is a default that an explicit verdict overrides. **An unanswered offer is not a decision:** when the reason is ambiguous — "text not readable" could mean remove it or make it readable — ask him once on the issue which branch he wants, and when no reply arrives ship the default and say plainly in the card and the closing comment that the other branch stays open as his call. Do not hold the post waiting for an answer, and do not treat the silence as approval of the readable-text branch. **When his reason asks for words that make sense together, not just characters, the label must be a real short phrase on a physical card, never a single letter or a prefix.** A prompt that asked for "a large letter K" and an "sk- prefix" on two scrolls came back as a frame of invented glyph strings; the same slot with two paper cards reading `THE KEY WORKS` and `THE TOKEN FAILS` gave him the readable English he meant. Letter-shaped marks (a lone K, a T, a red X) are glyph invitations, so replace them with words, and let the cards carry the sentences while every other surface stays plain.
- **A figure cut by an edge** is cleared by a read that puts the shoes on the floor inside the frame, not by the count of figures.
- **A swatch band** is cleared by `check-palette-strip.py` reporting no strip on **either** edge, on every render of the round — the old defect has come back on the top edge alone and on the bottom edge alone.
- **An invented logo or brand mark is invented text.** A model that adds an Apple logo to a laptop lid, a badge to a tower, or a label to a board is inventing a prop the prompt never asked for, the same defect class as invented lettering. The fix is to name the surface as plain and unmarked in the prompt and to verify it on a crop; do not treat a readable logo as acceptable just because the prompt did not forbid it.
- **A comparison pair** clears both items with the same measurements, and the companion's own deviations (an extra limb, a flatter register) are named in its own item description rather than folded into the shared note.

## A national flag must be the real flag

When a picture marks a country, draw that country's flag and describe its bands in order in
the element's own `desc` — Spain is red, wider yellow, red, "no crest, no marks and no
lettering on it". A generic blue-over-white banner standing in for a country reads to him as
the wrong flag, and he names it on every image it appears in.

## Hands never grip a rim

A wheel, valve, spoke ring, handlebar or round hatch with both palms closed on it comes back
with fused, extra or melting digits, and he rejects the frame for it — "a fucked up situation
with hands and generally body looks strange" — even when the rest of the picture is right.
Give the hands a job with no rim in it: both forearms resting flat along a pipe or a desk,
both palms pressed flat against glass, one open palm on a surface, hands hanging loose and
empty. Keep "five fingers, spread apart, drawn cleanly" in the `desc`, but that line does not
rescue a grip; remove the grip. What he approved is a figure with both forearms down and both
hands empty.

Two slots of one post can fail this the same way inside one round: once a frame has been held
back for a grip, change the shape in the sibling prompts too rather than describing the same
wheel more carefully.

**Removing the grip lowers the risk; it does not clear it, so the hand still gets its crop.**
The no-grip versions of two slots came back one with six fingers on a flat palm pressed to
glass, the other with one hand drawn as a rounded block at the hip and the other forearm
running off the frame edge. Decide what that crop means with `references/hold-back-or-ship.md`
rather than here: a hand fused or over-counted on the beat prop is a hold-back, while a hand
that is merely indistinct or clipped by the frame ships with the sentence named in its item
description. When the residual is nothing but hand detail and every other clause of his
reason is cleared, ship it named and give the next composition the hands **out of the
picture** — in his pockets, behind his back, below the frame edge — instead of spending a
third render on the same anatomy.

**A digit count is read at 3x on a wide box, never at 6x on a per-hand crop.** On one round's six renders the 2x figure reads and the 6x per-hand crops called a six-digit hand on three of them, and two of those read as clean five-digit hands at 3x with an arm's worth of context around them; only the one that really was six survived three reads. A per-hand crop loses the wrist and the neighbouring shapes a reader needs to tell a finger from a fold, so the over-count is the common failure and a hold-back spent on it delays the post for a defect that is not in the picture. The 3x read is also how the removal is judged afterwards: taking the key out of his hand and stating four fingers and one thumb on each beat a hand-on-prop contact that both engines had drawn as a fused cluster.

**An empty open palm is the shape that gets the sixth digit, and rewording the palm does not fix it.** A figure asked to hold `the palm open, flat and empty` toward something came back with six digits twice on the same slot — once with a key hovering over the palm and once with the palm bare — while the clause said `four fingers and one thumb` both times. So an empty splayed palm is a pose defect, not a residual: change the pose on the second attempt instead of describing the palm more carefully, and take the hands out of the picture the way the grip rule already says. Both arms down with `both of his hands tucked behind him, out of sight` keeps the beat whenever the props carry it — the door open, the key standing in the lock, the notes going in.

**Naming the hands hidden is not the same as a frame with no hands, so the pose is a claim to verify like any other.** That exact wording came back with both hands drawn clasped together behind his back — the model kept the gesture and put it out of the way rather than out of the picture — which lands the digit question in a place where it cannot be measured: a clasped pair behind the torso is about 50x70 native pixels, under the 250-300 px native crop the hand rule needs, and no ink print at that size resolves individual fingers. When the hands land there, do not record a defect and do not record a clean hand: a count read off a shape that small is the reader completing the question it was asked. Say in the item description that the clause is unverified at that size, and change the occlusion on the next attempt — a pocket drawn as flat fabric with a seam, or the hands below the frame edge — because an occlusion the body does not create is the only kind that reliably removes the shape.

**The pocket occlusion is the version that clears the clause, so write it first when the beat does not need his hands.** `both hands pushed deep into the front pockets of his trousers, the pockets drawn as flat fabric with one seam each and no fingers drawn anywhere in the frame` came back clean on a slot that had already failed three poses — an open palm, a key held above that palm, and a clasped pair behind the back — and two reads on the same 3x figure crop of that render agreed there were no finger shapes anywhere in the frame. Keep the residual honest when it appears: a thumb-base contour or crease line at the pocket opening is a hand drawn above the pocket, so name it as indistinct and ship, rather than spending a fifth render on it. And when the figure still needs to *do* something, put the action in his gaze and in a prop the scene holds (the door open, the key in the lock, the notes going in), not in a gesture — a gesture is what the hand clause came from in the first place.

**A prop set on an upturned palm is drawn floating above it.** Asking for `a heavy brass key lying across that open palm` produced, on both engines, a key with daylight under it and a palm fused into a cluster; the same key standing upright in the lock plate of the open door reads sharper and gives the hand nothing to grip. Put the prop where the scene holds it — in the lock, on the bench, hung on a nail — rather than on a hand.

## The legacy style block still carries the modern tell

The back-filled records' `## Prompt` blocks for the older posts end `aesthetics` with `clean
technology blog illustration` and describe the `medium` as `digital anime illustration,
vector-like clean coloring`. Those phrases are the vocabulary this file bans: a re-render that
keeps them reads back from a vision check as "a modern digital pastiche of a 1990s anime cel"
and looks modern to him however much grain is added. When a prompt is rebuilt, replace the
whole style block with the wording above instead of editing the old one in place.

**The exception is a single-slot re-render on a post whose other pictures are already approved in the legacy register.** A post can reach review with most of its images approved in the old cel look and one slot sent back for a non-style defect (lettering, a wrong prop, a missing contact). Re-describing that one slot in the standing register puts one frame in a different temperature beside approved siblings, which is the inconsistency he names as a colour failure even when each frame is fine on its own. Keep the post's own approved register for that slot, fix only the defect, and switch the whole set together only when he sends the post back for its look; the standing register governs the next post built from scratch, not a single repair inside an approved set.

## An existing backlog image is judged as it is, not retrofitted

A backlog review judges the draft's existing pictures, and many of them were built on that old
style block or on an older idiom altogether (flat cel figures over a rendered set). Judge that
frame on its section's beat and on the real show-bar defects — unreadable lettering, grey bars,
swatch strips, extra limbs, a pasted-on element that breaks an otherwise consistent scene — and
write the older register into the item's check note as an observation. **Do not hold back or
re-render an existing image only because it reads modern or because its record carries the banned
vocabulary**: he reviews such frames as they are and has approved legacy ideograms with no reason
at all. A whole-frame older idiom is a style note; a pasted-on element inside a consistent frame
is still the montage defect. Reserve a re-render for the real defects or for his reason.

## The flux companion he wants is a photographed 1991 print, not a clean cel with grain

His round-1 note ("1990s anime, Toriyama, film grain, one palette") was not the end of the register, and a render that answers it word for word still comes back rejected if the picture reads as a modern digital cartoon. On one round-2 card he approved the two ideograms and rejected all three flux companions with one note: early 1990s Japanese anime **production art**, hand-inked black outlines with uneven line weight, flat cel-painted colour with a single hard-edged shadow tone, no gradients, no airbrush, no glossy highlights, no rim lighting, no 3D look, simple rounded character design with small eye highlights, background hand-painted in gouache and softer than the character, muted slightly faded palette, and the whole thing is **a photograph of the printed illustration lying on a wooden desk**: slightly yellowed paper with visible texture, one edge of the sheet inside the frame, warm uneven desk-lamp light, mild vignette, slightly soft focus, shot on 35mm Kodak Gold 200 with visible grain and a slight colour cast.

So the medium clause does the work, not the grain overlay: describe the print, the paper and the desk in the positive inventory, and let the illustration sit inside the frame as the photographed sheet. The rejection names the register and never the scene, which is why the same compositions passed as ideograms on the same card — do not re-render an approved ideogram to match a flux note, and put the note into the companion prompt only.

## A companion render on the other engine is a comparison, not a candidate

When he asks for "companion flux images for comparison", submit the same brief twice: the
ideogram JSON prompt and a natural-language prompt for `flux2-klein` under about 300 words.
Name them as a pair (`<item id>` and `<item id>-flux`), put both on the same card, and name the
companion's deviations in its own item description — how many figures it drew, whether its text
is clean, whether its style register holds. The ideogram render is the one that can ship; an
approved companion never replaces the asset the draft points at. What the second engine did
differently is the deliverable, so a flawed companion is reported, not silently re-rendered.

**A companion rejected for register on a slot whose ideogram he approved is recorded, not re-rendered.** The slot is decided, the ideogram ships, and a fresh flux render spends a queue shared by every card on a question he has already answered. Give the rejected companion its own record with `asset: null`, his reason verbatim in a single `rejected` row, and `superseded_by` pointing at the job that took the slot, then carry the note forward into the companion prompt of the next slot that is still open. The exception is the slot that is still open on the same card: there the companion note IS the round's fix, and the companion is rebuilt to it rather than recorded.

## A named residual does not cost the round, and one engine can carry a slot

- **Naming a deviation in the item description is how it ships, not a confession.** A card went up with two caveats written into their own items — a third tap with its own basin where the prompt asked for two, and the severed rung pieces hanging at the rail instead of sagging mid-rung — and he approved both with no reason on either. The test is whether the beat still reads: when it does, name the deviation in the item's own words and spend nothing on a re-render. "Naming a defect on a card is not a fix" covers a clause of the show bar (a fused hand, a body cut in half); it never covers a composition deviation the section's beat survives.
- **A slot does not need both engines.** After one engine's header was pulled for a figure fused into the bench, the slot went to the card with only its ideogram and was approved with no comment. When one engine fails the bar, hold that frame and card the clean one; do not queue a replacement twin before the verdict unless the two-engine comparison is the round's actual question — and when the owner's standing instruction for a held-back slot is to compare engines, that comparison *is* the question, so both attempts are named on the one card rather than split across cards. When the verdict does not ask for the twin, the spare stays in staging as an `asset: null` record instead of becoming a second card.
- **An approved companion lands in the vault beside the ideogram, and the embed stays on the ideogram.** The item id names the file (`<slot>-flux.png` in `tech_blog/assets/<date>/`), the draft keeps `assets/<date>/<slot>.png` on the ideogram, and the companion gets its own record with the asset row the copy actually produced. Do not repoint the draft at the companion, and do not leave it unrecorded in staging once he has approved it.
