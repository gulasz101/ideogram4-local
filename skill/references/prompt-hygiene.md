# Ideogram 4 prompt hygiene

Session: 2026-07-02 safety-filter investigation.

## Finding

The Ideogram 4 local GGUF grey box ("Image blocked by safety filter") is primarily a prompt-vocabulary and JSON-structure filter baked into the model weights, not a pixel-level classifier.

## Fix hierarchy

1. **Prompt hygiene first.** Rewrite the prompt to use sparse canonical JSON and describe situation/location/mood rather than naming items. Keep only `high_level_description`, `style_description`, `background`, and 1-3 `elements`. Drop `canvas` and `layout` fields; dense structured prompts can drift off-distribution.
2. **Encoder swap second.** Set `IDEOGRAM4_LLM_MODEL=aggressive` (HauhauCS) or `generation.llm_model: "aggressive"`. In our 2026-07-06 A/B tests, only the aggressive encoder rendered a clean image, and only with a sparse prompt.
3. **Sampler workarounds third.** If a clean prompt + aggressive encoder still greys out, enable `two_pass` (neutral-prompt first pass + img2img second pass) or the cheaper `single_pass` CFG schedule.

## Canonical JSON shape (schema-compliant)

```json
{
  "high_level_description": "one-line situation / persona",
  "style_description": {
    "aesthetics": "...",
    "lighting": "...",
    "medium": "...",
    "art_style": "...",
    "color_palette": ["#..."]
  },
  "compositional_deconstruction": {
    "background": "...",
    "elements": [
    ]
  }
}
```

The exact schema is documented in `references/ideogram4-oss-schema.md`. The key rules from the official `ideogram-oss/ideogram4` code:

- Only three top-level keys in order: `high_level_description`, `style_description`, `compositional_deconstruction`.
- `style_description` must contain exactly one of `photo` (for photos) or `art_style` (for illustrations/renders/design), plus optional `aesthetics`, `lighting`, `medium`, `color_palette`.
- `compositional_deconstruction` must contain exactly `background` and `elements`.
- `canvas` and `layout` are **not** in the schema and should be removed.


## A flux comparison must carry the ideogram's linework, not just its composition

`references/archive/hold-back-or-ship.md` carries the same clause and the case behind it. It costs about fifty words, which puts a 300-word flux prompt at 320–360; the encoder holds it, but the negative tail is the first thing at risk, so trim scene description rather than the tail and read the first render for a pasted panel before trusting it. **Approved flux prompts have run to 374 words, and about 400 is where the tail starts coming back cut** — a rewrite that overshoots is not a reason to wait or to delete the clause: there is no cancel, so send the trimmed version as a second job behind it, check both against the same bar, and keep whichever passes. **Check the twin's length with `wc -w` before the submit, and write it as its own compact prose — never by pasting the element descriptions in sequence.** A twin assembled from the JSON's `desc` strings inherits every clause twice (the room once in the background and again as an element) and comes out at 600-plus words, where the negative tail is the first thing the encoder drops; the version that fits is hand-written at 400–430, keeping the ink clause, the palette line, the room in one sentence, the beat, the figure, and the tail. Trim the scene description to make the number, not the clause. The long one is the one that loses its tail, so the trimmed prompt is usually the frame that ships, and the two jobs cost one fetch each rather than a lost round.


## An audit's suggested replacement can carry the defect it is meant to fix

A pixel audit's `replacement` column names the scene a fixed prompt should ask for, and it is written by a reader looking at the picture, not at the prompt rules — so it can hand back the same defect family in a new costume. One post's column asked for two monitors showing a stopwatch and a lightning bolt (screens holding pictures of other things: the flat-UI family), a box holding up a blank red warning triangle (a literal mark), and a dial with its needle in the red zone (a face that invites invented numerals — the rejected render had a name stamped across it).

## Reframing examples

| Risky | Safer |
|---|---|
| a woman in a bikini | a cheerful young woman having fun at the beach on a sunny day |
| blood on the floor | a red hydraulic fluid spill on the datacenter floor |

## The linter reads your prohibitions, so a negative clause cannot name the banned thing

`lint` scans for the term, not for the intent wrapped around it. A prohibition that names a flagged noun is still the term appearing in the prompt, and it counts: `no other human figure` trips the `human_shape` flag, while the same prohibition phrased around the count — `one person only in the picture, no second person, no crowd` — does not. The picture can be entirely safe and the prompt still be rejected over a word used to forbid something, and a shape the model never drew has already cost you a lint cycle.

**The flag fires on plain description too, not only on bans.** `with his whole body facing it` trips `human_shape` in an element `desc` that forbids nothing at all, while `facing the wall` scores 0. The linter cannot tell a description from a prohibition, so the same rule covers prose about the figure: describe his stance by what he faces and what he does — `he stands in front of the wall, one hand raised toward it` — and keep the mass words (`whole body`, `full body`, `limbs`, `anatomy`) out of the prompt entirely. **`full body` fires as readily as `whole body`, and a sentence written to prove the figure is ALONE still scores**: `he is the only figure in the picture and the only full body anywhere in the frame` trips `human_shape`, while `he is the only figure in the picture; the rest of the floor is bare flags with nobody on it` says the same thing for nothing. So the rule covers prose about isolation and not only prose about anatomy. The rewrite is the cheap fix, because the flagged word is the term appearing whatever the sentence meant by it. **But do not read that as "no body words at all": the flag is per word, not per family, and the geometry words a coherent figure needs score 0.** A prompt that states head-to-body ratio, a narrowing waist, level hip points, square shoulders, a pelvis on the seat, level knees and vertical shins lints at risk 0, so the body can be specified in its own vocabulary. The word that does fire is `thigh`: `both thighs run forward at knee height` scores +2 per occurrence (4 for the plural and the singular in one prompt), and `both legs run forward below the pelvis at knee height` scores 0 with the same geometry. Same for the arm: `his left hand lies on his left thigh` becomes `on his left leg just above the knee`. So when a pose has to be pinned down, lint the draft once, read the flagged term off the output, and swap that one word for its plain synonym rather than deleting the sentence the render depends on.

**The flagged noun need not belong to the body family.** A ban clause written for overlays still trips whatever flag an ordinary word in it happens to match: `no paper sheet` scores on the garment flag for *sheet*, while the same ban as `no paper page`, or dropped, costs nothing. **A verb phrase fires it too:** `the key wrapped in a folded cloth` scores on the garment flag for *wrapped in*, while `the key held inside a folded cloth` scores 0 — so when a legitimate prop is enclosed in fabric, describe what holds it rather than the wrapping action, and re-lint rather than assuming the flag came from a noun. Any ban list is prose and passes through the same scanner, so after a non-zero score read the flagged term and not only the score — the word to replace is usually a plain noun sitting in the harmless half of the clause.

**A plain scene word can trip the violence flag on a machine.** `the machine is dead and quiet, no light on it anywhere` scored +2 on `violence` for *dead*, inside an element `desc` that describes nothing violent at all, and `the machine sits quiet and dark, no light on it anywhere` scores 0. The state is what the picture needs and the word is what the scanner reads, so describe the state — dark, unlit, silent, still — and keep the diagnosis out of the prompt. **The flag does not care whether the word is a diagnosis or a measurement:** `both cut pipe ends are dead flat at the break` costs the same +2 for *dead* on a joint that is not alive in any sense, while `sawn flush` scores 0 — a word that reads as emphasis to a person still reads as the term to the scanner, so lint the draft and swap the one word rather than dropping the measurement the render depends on. Read the flagged term off the lint output every time: the score says a word is wrong, only the term says which one. **And a blade in a still life is that flag on an object:** a plain cook's knife lying beside a cut onion — no violence in the picture at all — scored on `violence` for *knife*, and the fix is to replace the prop rather than soften the word, because the object was never carrying the beat. A shallow bowl of the peel curls beside the cut onion says the same thing at risk 0. Lint the prompt before deciding which props the scene needs; a prop that trips a flag and earns nothing in the frame is deleted, not reworded.

## The negative clause for things the prompt did not ask for

**The most dangerous gap is the one behind a figure.** A paste in an empty corner is read as an overlay; the same paste where it touches the character's back or shoulder is read as something growing out of his body, which fails the character rather than the background and gets a harsher verdict. So describe the space behind and beside the figure in its own words — `the bare concrete floor behind him, nothing standing on it` — move any prop that was sitting there clear of him and say so in the prose, and drop the `color_palette` array, because the shape's saturated hue usually came from that array rather than from the scene. A repair that redraws the region but keeps the palette gets the shape back in a new outline.

**Name the shapes you do not want.** Put one clause in `high_level_description` listing the specific overlay shapes that have bitten you, so the model has a target for the negative:

```
no poster, no banner, no placard, no overlay card, no advertisement,
no charts, no graphs, no logos, no badges, no emblems
and no readable lettering anywhere in the image
```

Naming the shape is what works; "no text" alone does not stop a chart-shaped grid of tiles, and the shape is what a reader sees. Keep the clause in `high_level_description` rather than in an element `desc`, because a negative inside one element reads as describing that element.

**But a negative clause does not fix lettering the model invented on its own.** The clause stops a shape the prompt put a gap for; it does not undo an invention the composition invited. A prop standing alone on empty ground is a product in an advert, and the model gives an advert a name — the word appears in the render even though the prompt asked for no lettering anywhere, and adding "no readable lettering" to a prompt that already said it changes nothing. The fix is to change the **composition**: give the prop neighbours and a setting so it reads as part of a scene rather than as an item on a backdrop. Say the negative too, but treat it as the belt to the composition's braces — the braces are what carried the fix. `references/engine-pitfalls.md` #42 carries the case.

**And do not ask for a prop the model cannot spell or chart.** A `desc` that requests numerals, a data visualisation or a labelled panel gets faked: garbled digits, aligned tiles with no axes, an empty band under the grid. Replace the prop with a physical object instead of rewording the request for the same one — a glass porthole showing gears, a plain wooden panel with three carved discs, a row of closed ledgers. `references/engine-pitfalls.md` #36 and #37 carry the mechanism.

**Grep the rejected prompt for the words that order writing outright.** `labelled`, `marked`, `sign`, `plaque`, `log`, `readable` and `with text` are instructions to print words, and a negative clause does not undo one. A prompt asking for `small labelled collection trays` produced invented lettering on three shelf labels in the same render whose ban list already said no readable lettering anywhere, and the fix that worked was deleting the word and every surface it described. **A ban argues with the prop; deleting the word removes it.** Run the list over the prompt before the submit, and when a rejection names invented text, treat a hit as the cause rather than a wording to soften. **And a container is a surface with a label face whatever adjective precedes it**: `plain unlabelled jars and tins` still comes back with one jar wearing a sticker of dash-lines, because the noun is the instruction and the adjective is not something the model can act on. Replace the container with a shape that has no label face — closed wooden boxes, a coiled cable, a stack of ledgers — rather than adding a ban. `references/engine-pitfalls.md` #77 carries the case, and the check that catches it is a 4x crop of the shelf: three dashes on a small sticker read as `no lettering` in a full-frame pass.

**A repeated container is a whole row of label faces, so plainness has to be stated across the set rather than the prop.** When the containers are the subject — a hoard of drums, a belt of canisters, a shelf of identical tins — the replace-the-container fix above is not available, and the row is what invites the mark: a render of a belt of yellow drums came back with five of them wearing small embossed loops filled with illegible squiggles, invisible in a full-frame pass and unmistakable in a 2x crop of the row. Write the plainness as a positive inventory in the same sentence that counts them — `every drum is completely plain and bare: no labels, no stamps, no embossed marks, no scuffs shaped like letters, nothing printed on any drum anywhere` — and settle it on a crop of the row rather than of one member, because the marks land on some of them only and read as dents or shading at frame scale.

**An inherited prompt is an old prompt, so run the audits on it before you reuse it.** A record back-filled from an earlier job, a round-1 prompt a brief quotes, or a re-render named in a handoff was written before these rules existed: it will carry a `color_palette` array and props described as `labelled`, and both triggers come back exactly as they did the first time. Copying such a prompt forward and editing the one thing the rejection named reproduces the other defects it was already carrying. So before a re-render from an inherited prompt: delete `color_palette` and rebuild the look from `aesthetics`, `lighting` and `medium`; strip every word from the grep list above and the surface it described; then fill every edge and corner with a described prop. The one part to keep is the composition the owner praised — the action, the position of the figure and the prop he acts on.

**A prompt recovered from the renderer's job database is the strongest case of the rule above, and "it lints clean" is not a clean bill.** When a job failed and its row still holds the prompt, that prompt was written months before these rules and can carry all of them at once: a `color_palette` array, literal marks (*green checkmarks arranged around the rack*, *badges with a small lock symbol*), logos and a monitor screen, and `arms crossed`. `ideogram4_local.py lint` reads **schema shape and safety vocabulary** — risk score, flagged terms, density — so it answers 0 on exactly such a prompt and says nothing about the acceptance bar. Run the three audits (palette, literal marks, text surfaces) over a recovered prompt like any other inherited one, and keep the recovered composition, the character and the engine while replacing the mark-family props with the state they stood for: four bays each carrying one small round green lamp replaces a column of tick badges, and a grin with two simple fists replaces arms crossed.

**An author's paste-ready prompt is an inherited prompt too.** When the post's writer hands you a JSON block to submit, it was written to a description of the picture, not to these rules, so it arrives carrying the same triggers: run the three audits before it reaches the renderer — `check-bboxes.py` for axis order (a writer who thinks in `[x1, y1, x2, y2]` transposes the cabinet door and the crate into full-width bands across the frame), the `color_palette` deletion, and a rewrite of any ban clause that names a shape. Then say in the issue comment which edits you made and why: he will read the render against the prompt he wrote, and a silently changed prompt turns a defect of his block into a defect of yours.

**A post's images written in one sitting share their prompt traits, so they share the defect family and differ only in where it lands.** A draft whose images were generated in one batch from one template carries the same array, the same `fills the entire frame edge to edge with no empty space` phrasing and the same absence of props in the corners — and the model answers all of them the same way: a pasted graphic in a corner on one image, a band along the bottom edge on the next, a labelled card strip on a third. So the audit runs over every prompt of the post, not only the one whose rejection you are answering: when a review card shows one image with the artifact, open every sibling prompt before writing the notes, because the same two causes will be in all of them and the card's per-item reasons are where he will point. On the re-render side the same fact cuts the other way — a sibling's **style block and character description** are what makes a new image belong to the set, never its element list, because that list is the thing carrying the defect.

**But the array is a trigger, not a certainty, so measure the strip instead of inferring it.** Renders carrying the same six-entry `color_palette` can come back with no strip at all, so the presence of the array never decides a verdict on its own: run `check-palette-strip.py` and read the block for *each* edge, because its headline names only the edge that fired first and the same blocks can be lying along the other one at 99% of the width. A note that calls the array itself the defect puts a false defect on a frozen card, and a sibling render carrying the same array may be the clean one he approves.

**When the picture does want text, the prompt gives the exact characters.** The standing rule from this owner: text is asked for as human-readable language and spelled out, never as a `label`, `title`, `caption` or `text` field the model fills itself — a request for lettering without the lettering in the prompt is a request for invented words. If the section needs no writing at all, ask for none and remove the surfaces that invite it.

**A speech balloon, sign or callout is the one prop whose whole job is a sentence, so it gets exact words or it does not go in the scene.** A blank balloon reads as an unfinished placeholder however well it is drawn, and a balloon tinted with a `color_palette` accent reads as a graphic pasted onto the wall — plain white with a clean ink outline is what reads as drawn. Letter it by putting the exact phrase inside that element's own `desc` and stating in `high_level_description` that this phrase is the only writing in the picture; when the section needs no words, drop the balloon and carry the beat on a prop that does not need lettering. `no random letters, no pseudo-text` cannot rescue a blank one, because it leaves the hole where the sentence should be. **And check the lettering on a crop**: a balloon's words are small relative to the frame, so a full-frame read reports `no lettering` and a single wrong character is invisible at that scale — read the balloon at 2x or more, character by character, before the render goes on a card.

**`check-bboxes.py` reads spatial words, so a correct box can be flagged by the sentence beside it.** Its rules fire on `the left`, `top edge`, `at the bottom`, `in the lower`, `full width` and similar, and a full-width shelf plank or a prop described as "hanging head down" will trip them while the box is exactly right. The fix is the wording, never the box: describe the position without the trigger phrase ("at the end of the plank that the picture cuts off" instead of "at the far left end", "hangs from its own nail with bare wall above it" instead of "head down at the bottom"). Rewriting the sentence keeps the layout the author gave you; moving the box to satisfy a keyword deletes it.

## Editing a prompt: the prose and the element list must name the same props

A re-render edits one field at a time, usually the `elements` list. The `high_level_description` and the `background` are prose about the *old* composition, and the model reads all three fields as one instruction: a prop deleted from the elements but still named in the prose comes back — wherever the model decides to put it — and a prop moved out of its own element into the background prose can be drawn twice, once as furniture and once as loose goods. **So read the prompt top to bottom after every edit and make the three fields describe one scene** — same props, same count, same places. Check `high_level_description`, `background` and every `desc` against each other before the submit, not after.

**And there is no cancel.** `imagegen submit` prints a job id and nothing undoes it, so an inconsistency you notice after the submit costs the render or a re-render on a picture he has to judge. The read-back before the submit is the only cheap moment.

**When `lint` answers `density risk: yes` with a non-zero score, the fix is fewer elements, not a reword.** Fold the props that share a region into the `background` or into the room element, and keep the elements whose *position* decides the picture: the figure, the prop he acts on, and the thing that fills a region that would otherwise be bare. Folding four dressing props into the background commonly takes a seven-element prompt from risk 2 to risk 0 without losing a single described object, and it leaves the element list as the short list of things whose placement matters.

**Some `check-bboxes.py` flags are ordinary adjectives, not geometry — reword the `desc`, never narrow the box.** The audit exists to catch a transposed box and a slab where the `desc` names a region, and it does not know that a long object is legitimately long: `thin dark outlines` reads as NARROW, and `from the left edge … to the machine on the right` reads as LEFT and RIGHT on a conveyor whose box spans the frame by design. Clear it by taking the misleading word out (`crisp outlines`; `its near end at the frame edge and its far end running into the machine`) and keep the box — a track or a connector whose box stops short of its target is the defect the wide box was drawn to avoid. Only a box that contradicts a *position* the picture really has gets its coordinates changed. **The NARROW flag only fires on a box over about 400 px on both sides**, which is why the same adjective passes on one element and returns on the next: take the word out first and re-run the audit before you suspect the numbers.

**A fraction is a region word too, so `left two thirds` on a box that genuinely is 640 px wide is flagged as a full-width band.** The scanner reads the direction and measures the box; it cannot tell a fraction of the room from a region of the frame, and the message (`desc says LEFT but the box is 640px wide`) reads like a coordinate error when it is a wording one. Write the extent instead — `spanning most of the width of the room` — and keep the box, because a bench narrowed to a third no longer stands under the objects laid along it.

**The same flag fires on direction words that qualify the members of a set inside one element, not only on the element itself.** One wide element holding three heaps of card described `a tight bundle of cards on the left, a loose drift in the middle, and a stack standing in a tin on the right` answered LEFT *and* RIGHT against an 840 px box, and a trough spanning the frame answered RIGHT for `the near right end of the trough bare and dry`. Ordinal language costs nothing and reads the same to a person — `a tight bundle of cards tied with plain twine, a loose wide drift beside it, and a small stack standing in an open tin at the other end` — and `one end of the trough bare and dry` clears the same claim. The compass word is never the thing the picture needs; the ordering of the set is.

**The other common contradiction is a region word written from the scene in your head rather than from the box you typed.** A `desc` opening `in the lower right of the picture` over a box at `y 110-420, x 830-1000` is in the upper right, and `cropped by the bottom edge` over a box that ends at `y=620` describes a crop that is not there; the audit answers `desc says BOTTOM but the box starts at y=110`, which reads like a coordinate error and is a wording one. Read the region word off the box's own numbers before the submit — `y` first, so a small `y` is the top of the frame — and when the word is what is wrong, change the word. Move the coordinates only when the picture genuinely needs the prop at the other end.

**A prop described by its own extent is read as a region of the frame, so a flag's `bottom edge` trips the same rule.** A `desc` that fixed a hanging flag with `its top edge at his shoulder height and its bottom edge at his hip` over a box spanning `y 300-520` was flagged `desc says BOTTOM but the box starts at y=300` — the audit cannot tell a measurement of the prop from a claim about where in the picture the prop sits, and both words in that sentence are frame words to the scanner. Write the extent in the prop's own vocabulary (`its upper edge … its lower edge level with the top of the workbench below it`), or express the anchors as heights the scene already has, and keep the box. The tell is a flag on an element that is plainly in the right place: a hanging prop, a plank, a banner — anything whose described span starts at one edge and ends at another.

**A prop he holds belongs in the figure's own element, because a prop in its own element gets a second figure invented to stand beside him and hold it.** A prompt that describes the man's raised hand holding a phone, and then lists that phone as its own `element` with its own `bbox`, hands the model a prop whose described holder sits in a different element; the model resolves that by drawing another person. The render comes back with two identical copies of the character side by side, one holding each device — which reads as a mistake, and is one, but the cause is the element list and not the prose. **The fix is the fold: delete the prop's element and put its description into the sentence about the hand that holds it.** Then re-count: one figure plus the prop he acts on is two elements besides the background, and anything beyond that should be a thing standing on the ground rather than a thing in his hands. State `one person only` inside the element that describes him as well as in `high_level_description`, because the count is read where the body is drawn. More prohibitions do not clear it — the extra body comes from the structure, not from a missing ban. **This is also the one duplicate-figure case that earns a silent re-render rather than a card note**: the defect is a structural artifact with a mechanical fix you can state in one line, whereas an extra figure the model added for its own reasons is a note for the card. **The same structure resolves the other way just as often: the prop floats.** A `desc` that said the prop was "held between his thumb and forefinger", in an element with a box of its own, came back as a twig hanging in mid-air beside an empty hand — no second figure, just a prop with nothing holding it, which is the same lost beat in a quieter costume and not something a card can explain away. Write the grip into the figure's own sentence and make the two one shape — "his hand CLOSED AROUND the middle of it, arm and prop one connected shape" — and give the prop a described place to be (directly above the open bin it is about to go into) so a drift has a position to land on. **A third cause is the box itself: a lone figure's `bbox` spanning nearly half the frame width is room for two people, and the engine puts two in, whatever the count sentence says.** Narrow his box to one column the width of one person and say what occupies the rest of the floor; `references/archive/hold-back-or-ship.md` carries the case. **And narrowing his column moves him into other boxes, which the audit will not tell you about.** `check-bboxes.py` compares a `desc` with its own box; it never compares elements with each other, so a figure re-boxed into a 220 px left column can end up sitting on top of a prop's box and the audit still answers *no bbox contradicts its own desc*. After any box moves, walk the rest of the grid by hand — read the figure's `y`/`x` span against every other element on the same rows — and move the prop rather than widening the figure, because the narrow column is the thing keeping the duplicate out. **A narrow box does not stop a twin that stands where a person could stand.** With the man written at one end of a workbench, the engine mirrored him at the other end — two identical men, each with his own shadow, and the singleton clause said twice. The repair is the one that fills a bare region: put a described non-figure object in the counterpart position (a low stool against the brick, a stack of crates, a sack leaning on the wall) and say that position is the only thing there, because a position shaped for a person is filled with one however the count is worded.

**A fold must carry the prop's description with it.** Moving a prop into the `background` prose and leaving its old element in place is the double-draw above; deleting the element and not describing the prop in the background leaves a vacancy, which is exactly the gap the overlay clause exists for. Move the words, then delete the element.

## Tooling

### Prompt files in the shared backlog directory carry the post number

`~/image-studio/backlog/prompts/` and `~/image-studio/staging/<date>/` are shared by every post in the backlog, and item ids repeat across them — `header`, `header-r2`, `mobile-test-r2` all exist for several posts. So:

- Name the prompt file `<post number>-<item id>.json` (`032-header-r2.json`) while the render name stays the bare item id (`--name header-r2`), so the card's item row, the fetched PNG stem and the record stem still resolve to the same string.
- **The identical refusal in a run-scratch directory is your own earlier throwaway, and the fix is a new name rather than a read.** Helper scripts in the profile's scratch directory are reused verbatim from run to run, so a generic name (`runner-comment.py`, `create-card.py`) is already occupied by a previous run's script written for a different post. The error text is the same as the shared-directory one and the two need opposite responses: in `backlog/prompts/` the existing file is another post's work, so you read it before writing; in scratch it is yours and disposable, so reading it back to satisfy the guard costs a call and leaves two near-identical helpers. Suffix the name with what this run serves (`runner-comment-<post number>.py`) and write again.
- The same collision bites on the render side, because `staging/<date>/` can already hold a `<slug>-<8 hex>.png` from a different post. Always carry the exact path `imagegen fetch` prints; never glob for the slug.
- **Batching renders: the last job sets the wait.** A queued job's `eta_minutes` already counts the jobs ahead of it, so schedule the monitor from the LAST job's ETA plus five and re-read the clock then — a deeper queue puts a late submit hours out even when its own render is 21 minutes, and arming on the first job's ETA wakes you to nothing collected. **On a deep queue the ETA is a floor, not a promise**: other runs submit behind you and the queue grows, so a submit quoted at fourteen jobs ahead can finish well over an hour later than the number said. Expect the first wake to be a reschedule rather than a collect, treat that as the monitor working instead of a fault, and on that wake re-read both jobs before touching anything — when neither is `done` there is nothing to fetch, so PATCH the monitor again from the fresh ETA plus five, keep the issue `in_progress`, and end the run. **When the fresh number is many hours out, arm a shorter checkpoint instead of trusting it** — a couple of hours, then reassess — because an early wake costs one run, while a render that finishes with no monitor waits for ever, and a card held on a quote that long is a card that could have shipped. A wake that reschedules an already-scheduled monitor is one line of work; a wake that fetches a half-written PNG or submits a duplicate render is a wasted round. **The monitor's `notes` field is a hard 500-character limit, and a longer note 400s the whole PATCH — including the comment riding in the same request.** Keep the note to one or two imperative sentences (what to fetch, which crop to take, what to do with a failure) and put the reasoning in the comment body, which has room for it. When a PATCH answers `Validation error … path: ["executionPolicy","monitor","notes"]`, nothing was written: re-send with a shorter note and re-read `monitorNextCheckAt` afterwards, because a failed request leaves the old schedule silently in place.

### The linter and the rewriter

**Where a new prompt rule goes.** `references/archive/backlog-review.md`, `SKILL.md` and `references/engine-pitfalls.md` have all reached the 100,000-character file cap, so `skill_manage` refuses a patch to any of them and rolls the whole batch back — a one-bullet append to `SKILL.md` is already enough to answer `content is 100,488 characters (limit: 100,000)`. Do not spend a run trying to squeeze a rule into them. Until they are split, new prompt-shape and file-naming rules land here; anything about verdicts, hand-offs and rebuilt rounds goes to `references/archive/re-render-defect-persistence.md`; batch-scale work — auditing a whole backlog's prompts, repairing slots, engine pairs, sizing a render batch against the shared queue — goes to `references/archive/prompt-repair-audit.md`; and the series' standing look — the style block, the one named palette, the cast, real national flags, the props that invite lettering, how the hands are described, and the companion-FLUX request — lives in `references/series-style.md`, which every post prompt is built from. **Measuring what is still broken across the backlog** — walking the drafts rather than the asset folder, resolving embeds, telling a card's in-flight replacement from a defect, and handling a dead embed — is in `references/archive/backlog-measurement.md`.

The repo ships `ideogram4_prompt_tools.py` and `ideogram4_local.py lint`/`rewrite` commands:

```bash
python3 ideogram4_local.py lint prompts/my-scene.json
python3 ideogram4_local.py rewrite prompts/my-scene.json -o prompts/my-scene-safe.json
```

The linter returns a risk score and flags explicit garment/anatomy/situation/violence terms plus **density risk** (`canvas`/`layout` or many elements). The rewriter applies whole-phrase reframes, masks remaining flagged words, and now drops `canvas`/`layout` fields. It preserves canonical JSON structure when present.

## Sampler fallbacks

If prompt hygiene alone is not enough, add a `"generation"` block to the JSON:

```json
{
  "generation": {
    "safety_bypass": true,
    "safety_bypass_mode": "two_pass",
    "safety_bypass_steps": 4,
    "safety_bypass_cfg": 1.0,
    "steps": 20
  }
}
```

The wrapper strips this block before passing JSON to `sd-cli`. Modes:

- `two_pass` (default): neutral first pass → img2img second pass. ~2× generation time on M1 Max.
- `single_pass`: one pass with `--extra-sample-args guidance_schedule=1.0xN+7.0x(steps-N)`. Cheaper, weaker.

See `references/ideogram4-safety-filter.md` for backend details.

## The pre-submit lettering gate (Wojtek's standing instruction, 2026-10-27)

The gate is a read of the prompt file, run before `imagegen submit`, not a feeling about the picture:

1. List every element whose `desc` names lettering, print, a label, a badge, a sign, a caption, a wordmark, a chip, a panel readout or a number display.
3. If a prop survives with characters nobody wrote down, the prompt is refused — do not send it.

Cost: one file edit before the submit, against 21 minutes and one round of his attention after it. The library agrees — `unreadable-text` is 8 rejected / 0 approved and `pasted-overlay` 9 rejected / 0 approved (run `scripts/verdict-class-rate.py` bare for the live counts).

**The gate governs the prompts you write; it is not a forecast of his verdict on a picture that is already in a draft.** On one review card he approved two images carrying exactly the surfaces the gate forbids — a flat dark UI card pasted over the corner of the room, and a plain white caption across the bottom misspelling the section's own subject — both of them named on the card face as hard defects with the class rate quoted. He kept them because the scene still read. **That reading is retired: the owner has since said he does not want to review pictures that are already broken, so a draft image failing the gate is repaired and re-rendered instead of shown (the one exception is a slot that cannot be re-rendered at all, which goes up with its defect and class rate named on the card face), and the gate is now a filter on what reaches a card — `references/archive/prompt-repair-audit.md` carries the gate and the method.** What survives from that card is the other half: the gate is never proof he will reject a picture, and the size and dominance of a defect in the frame is what decides a rejection from an approval. The gate is a filter on what you submit, and the class rate is a prior that decides whether a defect is worth *naming* — the size and dominance of the defect in the frame is what decided his two rejections from his two approvals on that same card.

## The pose rule: a held object above the shoulder buys an extra arm

What fixes it is the composition, not the count:

- **Same prop is not enough: both hands go to the SAME HEIGHT, side by side.** A re-render that put the right palm on the door's top corner and the left palm "on the same band lower down" still came back with both arms leaving one shoulder, folded over each other, reading as three — the count sentence was in the prompt twice and lost to the pose. Two hands at two heights on one vertical band force one arm to cross in front of the other, and the model resolves the crossing by growing a second arm out of the chest. Send both hands to one horizontal line about a hand's width apart, turn his chest square to the prop so both shoulders are visible one on each side, say in the figure's own `desc` that the right arm begins at his right shoulder and the left at his left and neither crosses the other, and keep both hands away from the prop's top edge — a hand drawn at the top pulls one arm up and the overlap returns.
- **Then state the count anyway**, in the `high_level_description` and in the figure's own `desc`: "both of his arms are fully visible and clearly drawn as whole limbs from shoulder to hand ... exactly two arms and two hands, nothing in either hand, no third arm and no extra hand anywhere in the frame, and nothing raised above his shoulder." Also name the shoulders: "each arm begins at its own shoulder, one on each side of his chest, and neither arm crosses or passes in front of the other" — a count with no attachment point is a sentence the pose can still overrule.

**Count limbs on a crop before a figure goes on a card.** A whole-frame read reported one raised hand and missed the pair hanging at the sides; the defect was settled on a 3x `crop-probe.py` crop of the figure, where three arms are unmistakable. An extra arm costs a round and it is the cheapest thing on the frame to check. **And when the full-frame read and the crop read disagree about the number, the render is already failed** — one calling it three arms while the other calls it two arms leaving the same shoulder, distorted and overlapping, is not a close call to settle in the render's favour. A picture whose arm count cannot be settled in one look is the defect he names first, whatever the true number turns out to be, so hold it back rather than putting a disputed count on a frozen card.

**A pinch is the same failure squeezed into the hand, and the fix is a closed fist.** A `desc` that has the figure pinch a small prop between thumb and forefinger comes back with a fused multi-thumbed mass — two thumbs, extra knuckles, a shape that cannot be read as a hand — because the model has to invent where five digits wrap a cylinder whose far side it cannot see. State the grip rather than the fingertips: *a closed fist, the thumb laid over the folded fingers, no separated fingers sticking out*. Then give the prop **plain flat ends** so it has nothing to resolve into: a short brass cylinder came back as a cartridge until *no flange, no ring, no cap, no bullet shape* was added, and a flanged peg is a second object for the hand to mangle around. Check the hand on a 3x crop before the render reaches a card — a whole-frame read called one of these "a hand pinching the peg" and the crop showed a fist with two thumbs.

**An enumerated set gets its count stated, and the shape that can stand in for a member is banned by name.** A board asked for four device-shaped tags on five hooks came back with three tags and **two** bare hooks: the fourth hook's own mounting plate carried a round cutout, which the model treated as that hook's tag, and its prongs were left empty. The prompt listed the set ("a phone, a tablet, a pair of earbuds and a small speaker") but never the arithmetic, and the count was the whole joke of the frame. State it as a count in `high_level_description` — *exactly five hooks, exactly four tags, the first hook is the only bare one* — and ban the substitute explicitly (*no hook carries a round hole or a circular cutout*), because a backplate with a hole reads as a tag at a glance. `wrong-count` is 2 rejected / 0 approved in the library, so a set that arrives short is a re-render, not a card note.

## A handover between two figures cannot be drawn in transit

So the spanning `bbox` is necessary and not sufficient. Describe the **contact state at one end**, by the actor who should be doing the work — his thumb and forefinger on each temple of the new pair, pressing it onto the robot's face, the old broken pair lying on the floor beside them — and keep the box spanning from his fingers to the face. The transfer is then a fact about the picture rather than a hope about the motion.

The tell in the self-check is the **empty hand**: a figure whose `desc` said offering, passing or reaching, drawn with an open hand and nothing in it, is this defect. It is a re-render, not a card note, because the beat the picture exists for has gone.

## When a re-render still letters something, change the prop rather than the prompt

## The pre-prompt forbidden-memory gate (Wojtek's standing instruction, 2026-10-27)

So the order of work on a re-render is: `hindsight_recall` on the defect class the rejection named ("colourful artifacts", "swatch strip", "invented text", "pasted overlay") and read the remedies the bank already holds, then write the prompt, then lint, then the lettering gate, then submit. The recall is cheap and it is the difference between re-deriving a known fix and buying a render to discover it again: on this card it returned the palette-array trigger, the undescribed-corner mechanism (#75) and the corner-overlay-without-a-ban rule (#60) in one call.

1. **A `color_palette` array** — its entries come back as an edge strip, a mid-frame band, or a cluster of flat blocks in the one corner the prompt left undescribed. Delete the array and rebuild the look from `aesthetics`, `lighting` and `art_style`, naming two or three hues in prose ("warm amber lamp light, cream paper, medium brown wood").

## A shape analogy in the prompt is a concrete instruction, not a simile

Naming a thing to describe the *shape* of another thing makes the model draw the named thing. On post 031's `header` re-render the shell was written as "a thin brushed aluminium shell shaped like a flat computer screen frame, open on its back" — the intent was a thin rectangle, and the render came back as a two-part hinged housing with a lid carrying a filled dark panel: a laptop with a blank screen, the exact object the composition's own reject list forbade.

- not "shaped like a screen frame" -> "four bare metal strips joined into one open rectangle"
- not "like a control panel" -> "a flat steel face with two rows of rivets"
- not "like a dashboard" -> "a rail with five cable tails clipped along it"

**When two attempts of one slot fail on different invented artefacts, the scene is too busy — reduce it instead of rewording a third time.** A header slot came back first as a laptop (the shape analogy above), then as a flat black panel carrying invented characters pasted over the upper picture; the third attempt passed once the composition itself shrank: a tighter crop onto the bench, the pegboard cut to three spanners, and the jars, parts box, rag and oil can deleted. Two failures that name *different* objects are evidence about the scene's density and the number of surfaces it offers, not about the phrase that failed — so keep the concept, the room, the light and the figure, and take the prop count down until the action the picture needs is the only thing left in frame. A slot that fails twice on the *same* object is the opposite case: keep the scene and change that one prop (`references/archive/re-render-defect-persistence.md` carries the escalation ladder).

**A word borrowed from another medium drags that medium's marks into the picture.** The same post's header needed a thin rectangular object and the prompt called it a "frame" six times; the render came back with a flat black panel over the picture carrying clean white characters (`23 -0`), a glyph and a grey L-shaped **crop-mark** — the furniture of a film or photo frame, drawn literally. Avoid the vocabulary of printing, photography, film, screens and dashboards when you mean a shape: say `four thin aluminium bars joined at their corners into one open rectangle`, not `frame`; `a bare metal rim`, not `bezel`; `a shallow tray`, not `display housing`. The same rule bans `crop`, `letterbox`, `slate`, `watermark` and `caption` from a prompt unless the picture is genuinely about them.

Check this on the file before the submit by grepping the prompt for every noun that names a typable or UI object — `screen|display|monitor|panel|plate|label|badge|sign|dial|dashboard|browser|notification|card` — and for each hit ask whether it is a prop the picture needs or an analogy standing in for geometry. An analogy is a rewrite, not a reword.

**A product's name draws its logo, and the logo comes back wearing invented branding.** A homelab section's subject is usually a named service — a tunnel daemon, a photo server, an observability stack — so the prompt naturally writes the product in, and the model answers a product with a mark: a pasted icon over the scene carrying a made-up word under a cloud glyph (`cloamflareTunnel` was one), or a flat vendor-UI panel in the corner. Both pass `check-grey-bars` and `check-palette-strip`, so nothing upstream of a crop will catch them, and a card shipping one is a card he reads as broken. Translate the product to its physical form before the submit — the tunnel becomes a cable through a brick wall, the photo server a plain stack of drives with no face, the dashboard a rail of cable tails — and keep the product's *shape nouns* out as well (`cloud`, `tunnel`, `hub`, `portal`, `console`), because a cloud is drawn as a cloud and a cloud in the corner is a logo. Grep the prompt for the section's product names, not only for the UI nouns in the list above. **The name also leaks as text on surfaces:** a product name written in an element `desc` ("a white container labeled CloudNativePG", "a scroll reading NUQ schema init") comes back as readable lettering on that surface, even when `high_level_description` says "no text of any kind" — the model treats the name as content to draw, not as a label to suppress. Describe the surface's shape and silhouette only ("a white container with an elephant-shaped mark", "a blank cream-coloured scroll, completely empty") and never put a product name, service name, or schema name in any element description.

## A prop with several states is one element per state, and an absence is not a description

Three failures with one cause: an element that asks the model to draw more than one thing.

**A count spread over two elements is a count the model rounds up.** Post 038's allow-list attempt described a plate with four sockets where "the three right-hand sockets each hold a slug and the left-hand socket is empty", plus a separate element for one loose slug standing on the bench. It rendered four sockets, **all four filled**, and a fifth slug on the bench — a legal reading, because nothing in the prompt said how many slugs exist in the frame, so the loose one became an addition. When a spare copy of a prop shares the frame with the fitted ones, state the total in the `high_level_description` ("exactly four slugs in the whole picture: three seated in sockets and one standing on the bench") and keep the empty socket described by the surface the eye should find, per the absence rule below.

**A container described as empty, dry or bare is still a container the model fills.** "Bone dry" is a modifier, and the model answers a trough with the shape it has drawn a hundred times: full of water. Describe what is visible *in* it instead — the pale dry stone floor of the trough, the seams of its slabs, a ring of grey dust along the rim — because a described surface has no room in it, while an absence has all the room. Naming the missing thing is worse than saying nothing: a negative about water carries the noun `water`, and the noun is read as an instruction (#62). This is the rule for every absence — the empty recess, the bare shelf, the dry run, the plugged socket — describe the surface the eye should find, never the thing that should not be there.

**Two ends facing each other across empty space become one connected part.** A beat that says *this does not reach that* — a shaft that stops short of its socket, a pipe that ends before the flange, a plug that never goes in — cannot be drawn as an air gap however carefully the gap is said. Describe the stub and the matching socket inside one element, name what is visible through the space between them, restate the gap in `high_level_description`, and the engine still runs one continuous member from end to end: it reads two aligned ends as the instruction and the gap as the decoration. So the repair is not a third wording of the gap. Take the connecting member out of the linkage altogether and carry the break as a member **laid aside**, where its state is a fact the model can draw: two bare sprocket wheels with the drive chain coiled on the bench between them and both ends on the wood, a belt hanging on a hook beside two bare pulleys, a plug lying in its own coil beside an open socket. State that the laid-aside part touches neither end. A coil on a bench is drawn as a coil; a gap is drawn as a connection.

## A before/after pair needs the reversed state on every part, not a cue

## Motion marks are the house style; an arrowhead is a symbol

The ink arcs a cartoon puts around a ringing bell, a struck hammer or a spinning wheel are part of the look and pass the bar. What the same stroke does at its end does not: an arc finishing in a pointed head is a **drawn arrow**, a graphic mark lying over the painting rather than movement in it. One header's arcs carried an arrowhead that no frame-level read named and a 5x crop of the bell's mouth did. Keep `no arrow` in the negative clause beside the overlay nouns — it costs nothing, because the ban names a shape the picture never needs — and when one still arrives, name it on the card rather than holding the frame: the bell, the rack and the figure are what the section needs, and a single arrowhead is a caveat the reviewer can see for himself, unlike a pasted panel. It becomes a hold only when the arrow points at something the picture does not contain, which is an invented relationship rather than a mark.

## An industrial panel invites engraved labels above its sockets

## A swept-dust mark draws as a white patch

## A canister, tin or box with a flat face gets a small rectangular label

## A member that can reach the walls gets rested on them, and the count it stands for collapses

## A mechanism comes back complete, and in its resting state

**The wall band must be the brick immediately beside the object, at the same height — and that is how this rule failed me once.** The pair above was passed on the numbers quoted in the previous paragraph, and the pass was wrong: the "wall" band had been measured on a patch that sat in shadow to one side of the crates, so the crates beat a dark surface and looked lit. Re-measured against the brick immediately beside them, the same two frames read crates **103** against brick **185** in the header, and crates **60** against brick **147** in its companion: the light was on the wall in both, the pair did not argue, and the header frame was showing the absent state. So pick the comparison band as the nearest same-height brick the object does not cover, measure both frames of the pair the same way, and treat a margin under about 15 points as no contrast at all. A pass on a light-contrast pair is only as good as the patch it was measured against. Run `scripts/check-light-contrast.py` rather than measuring inline in a heredoc — it takes `--object x0,y0,x1,y1 --wall x0,y0,x1,y1` (0..1 fractions work too), several frames in one call, and `--pair` for the verdict, and it prints the sign per frame so a session's numbers stay comparable with the ones already in the notes. A pair whose frames all come back with the same sign is the failed pair, whichever engine drew it. And when a pair exists to argue a contrast, both frames of the pair are checked against each other — two frames in the same state is a failed pair even when each is a clean picture, and the frame that fails is the one whose whole purpose was the contrast.

## An object that must not join its twin gets joined — change the kind, not the wording

## Closure is geometry: raise the camera, do not re-word the loop

Two causes, both structural:

Two smaller findings from the same frame: identical objects named once come back in three sizes — say **one size repeated three times**; and `check-bboxes.py` rejects the words *left*/*right* inside the description of a wide box, so a ring spanning the frame has to be described by its ends ("the curve at each end"), not by sides.

Third, found on post 089's header: the checker's NARROW rule matches **thin**, **narrow** and **slim** anywhere in a full-frame element's description and calls it a narrow-strip claim on a 1000x1000 box. Plain scenery language trips it — "thin ground mist" did, twice, even after the phrase left the `high_level_description`. Write "low ground mist", "fine haze" or "pale drift of dust" in any element whose box is the whole frame, and re-run the checker after every wording change that touches element 0.

## The flux engine flattens structure — give it the pose, not the cross-section

## A repair that adds a decoration buys a new defect

Two rules follow, and they hold on every repair:

## Lesson

For this user, always try prompt hygiene first. Only fall back to `two_pass`/`single_pass` for persistent false positives on otherwise safe prompts. Do not rely on sampler tricks to bypass the actual safety guardrail on genuinely policy-violating prompts.

## A brass fitting is drawn as an instrument with a numbered plate

Post 089's `cpu-fire` slot asked for a small brass measuring collar clamped on a pipe, with "no gauge face, no dial, no needle, no numerals" already in the negative clause. The engine drew a round brass fitting with a knurled rim, radial tick marks, a central hub, and a **small rectangular plate on its side carrying a numeral** — read as `6` at 4x and as `60` at 1.6x. Two reads disagreed about what the object was (handwheel against gauge) and agreed about the plate and the digit, which is all the verdict needs.

Two rules:

## A lighting clause can paint a bar across the frame

The restyle slot of post 089 asked for "deep indigo shadow at the near edge of the bench", and both the prose and the lighting block said it. The engine painted exactly that: the scene ends at row 724 and the remaining **108 px (13 % of the 832 px height)** is a featureless dark band, first a grey strip then a near-black one. Every edge script but one passed it, and `check-blank-margin` only fired on it because it was uniform.

Two rules:
