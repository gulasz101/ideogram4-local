# Prompt wording that trips the mechanical checks

Small traps found while linting prompt files for the series prompts. Each one costs a lint round-trip, not a render; fix the wording, keep the picture.

## `check-bboxes.py` reads "thin" as a NARROW claim

A full-frame background element whose desc says "a thin crescent moon" or "a thin line of light" is flagged as `desc says NARROW but the box is 1000x1000`, because the checker keys on the word, not on what it describes. Say the thing's size without the word: "a small crescent moon", "a narrow beam" still trips it, so name the object instead ("a bare bulb on a short black cord"). Re-run the checker after the reword; the box was never wrong.

The same matcher fires on `narrow` describing a tall prop: a door boxed 500x620 answered `desc says NARROW but the box is 500x620 - not a narrow strip`, because the check wants a narrow *strip*, not a tall shape. Say "a tall steel door" and keep the box; if the prop really is a strip, the box is what needs to change.

## Prompt file names collide across posts, so look before you write

Every post has a `header` slot and many have an `architecture` or `server-error` slot, so `<item id>-r<k>.json` names a file that already exists for a different post's round: `~/image-studio/backlog/prompts/architecture-r2.json` was another post's junkyard render when post 148 needed one. Never overwrite it — the old file is that round's prompt history. List the exact names first (`ls ~/image-studio/backlog/prompts | grep -x '<item id>-r<k>.json'`) and disambiguate with the post's own subject (`architecture-optionb-r2.json`), then name the file you wrote in the card's row and in the closing comment so the next round finds the right one.

## `lint` risk 0 comes from element count before wording

Six elements including the background is the comfortable ceiling. A seventh costs +2 exactly like a banned term, so merge props that share a beat (the laptop and its dust ring and the mug into the bench element) rather than rewording a flagged word.

## The palette phrase is repeated, never a hex array

Drop `color_palette` entirely and state the families in prose in `aesthetics`, `lighting` and the FLUX opening (`rust brown, olive grey, teal-cyan, cream and dark ink`). A hex array renders as a swatch strip at the frame edge, which is a rejection.

## `lint` flags a word by class, and the class is often not the scene's subject

The linter scans every field for vocabulary classes and adds +2 per hit, so a harmless noun costs the same as a seventh element. Verified hits and their plain synonyms:

- `sheet` is flagged `[garment]` even when it is paper: `paper sheets` -> `paper pages`. (Same word the SKILL.md lint example catches in `brushed metal sheet`.)
- `dead` and `kill` are flagged `[violence]`: `the job is dead` -> `the job has stopped`; `dead jobs` -> `stale jobs`; `kill signal` -> `stop signal`. A post about zombies, crash recovery or signal handling is exactly where these words come naturally, so sweep the whole file for them before the first lint.
- `wrapped in` is flagged `[garment]`: `a shaft wrapped in flame` -> `a shaft trailing flame`.

Swap the word, re-lint to confirm the synonym is clean (do not assume an untested synonym passes), and keep the picture. The element count is unchanged.

## A surface left undescribed gets a logo or a label

A laptop lid, phone back, monitor bezel, or device casing that the prompt does not describe as plain and unmarked comes back carrying a brand logo or a pseudo-word the prompt never asked for. The header flux render in post 149 carried an invented Apple logo on a `dark grey laptop` whose lid was never described. Name the surface in the desc (`plain dark grey lid, nothing printed on it, no logo`) and the model has nothing to invent. This is the same failure class as invented text, only quieter, because a logo reads as decoration until you look for it.

## Text surfaces multiply: every label asked for is another chance at gibberish

The model has no spellcheck and no consistency check across a frame, so each surface you ask it to letter is an independent draw at a wrong string. A prompt with four drawer labels *and* a labelled barrel stack *and* a four-column table inside a magnifying lens rendered most of them correctly and still produced two garbled tokens — a misspelt file name on one barrel and an invented word on a background box — which is the same hard defect as round one and spends a render.

- **Budget the lettering: the shortest set of short lower-case words that carries the section's beat.** Four short labels on one prop the character is acting on is a comfortable set. A table, a chart, a readout or a lens showing data is a text surface too, and the section's meaning survives without it — draw the rows as glowing bands of light instead of columns with headers.
- **Scenery carries no lettering.** Boxes, crates, shelves, walls and packaging get `plain, unlabelled, nothing printed on it` in their own desc, because a model asked to fill a storeroom will letter the cardboard if the prompt leaves it open, and that lettering is never the one you would have chosen.
- **Label once per class, not once per object.** A stack of five database cylinders carrying `state.db` on every one is five chances at `shate.ds`; one cylinder with the label, the rest plain, says the same thing.
- **After a gibberish rejection, cut surfaces before rewording.** The fix is fewer places for the model to write, not a stronger "no gibberish" clause — the clause is already there and the model still misses one draw in six. Rewrite the slot with the text budget above and keep the picture's beat.

## A monitoring screen is a chart surface even when the prompt says "no text"

A dashboard or metrics panel is shaped like a readout, so Ideogram lettered it
anyway: a prompt asking for six small flat graphs, each with `no text`, came back
with axes, invented words and one misspelt series name. The `no text` clause does
not clear it, because the prop is the trigger and the clause only names a shape
the model can draw.

- **Redraw the beat as physical hardware.** "Metrics look calm, one series is
  missing" survives as a tall wall panel of round glass status lamps in round
  metal bezels, every lamp steady, with one socket dark and empty where the
  missing series should sit. A character points at the dark socket. The absence
  reads at a glance and the panel has no face to write on.
- **Keep the word "dashboard" out of the prompt.** Say "a tall metal panel of
  small round indicator lamps"; the noun "dashboard" invites the graph grid
  back, and a graph grid brings its labels.
- **A dark socket is a described absence, not a blank surface.** Give it its own
  element with a bbox, or the model fills the empty hole with a lamp or an
  invented dial. The same holds for any "missing" thing the section is about: box
  the absence and say what is not there.

## An object named twice is drawn twice

Naming the same prop in the `background` prose and again in its own element gives the engine two descriptions to satisfy, and it satisfies both: a header whose background said *a large flat panel screen on the back wall* and whose fifth element said *a large flat panel screen mounted on the back wall* came back with **two monitors**, splitting the scene between them. The doubling is silent — `check-bboxes.py` passes it, because each desc matches its own box.

- Name each object in exactly one place. The background describes the room and its surfaces (`a plain board wall with a peg rack`); the element says `one computer monitor, the only screen in the picture`.
- When a re-render of an old prompt comes back with a doubled prop, grep the file for every mention of that noun before you reword anything — the second mention is the cause, and rewording one of the two leaves it in place.
- The same count applies to the element list itself: one object, one element, one box.

## Read the checker's output before the submit, never in the same command

`check-bboxes.py` keys on words in a desc against the box's geometry, so it produces false alarms on correct boxes: a full-figure element whose desc ends *his shoes rest flat on the floorboards well inside the bottom edge* answered `desc says BOTTOM but the box starts at y=330 - it is in the top half`, while the box (y330-810 of 1000) was right. The check is still worth reading — it catches a swapped `[x1,y1,x2,y2]` box, which the engine follows over the prose and which costs the render.

Run the checker as its own call, read every line of its output, then submit in a separate call. Composing the two (`check-bboxes.py … && imagegen submit …`) queues the render before the warning is visible, so a real box problem is discovered only after the job is on the queue and can no longer be withdrawn cheaply.
