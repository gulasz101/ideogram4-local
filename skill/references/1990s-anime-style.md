# The 1990s anime film-still style (his standing brief)

On 2026-10-28 Wojtek rejected a whole set of backlog images with one reason that is now the standing style brief for the blog. Quote it exactly when you write a prompt; the phrases are his, and each one maps to a prompt change.

> texts are mostly not readable, green stuff is not fitting generally the full concept, photo graining is not here, reminder! it must be in style of 1990s anime, so akira toriyama, style (dragon ball or akira anime) or "perfect blue" anime
> so the color pallette must be consistent across image!
> create also companion flux images for comparing them
> also there are like two main characters, and all the stories on the blog are about main character Wojtek and some small androids helping him managing his fleet of old "junkyard PCs"

## Before you write a word of the new prompt

A style reason arrives on many cards at once — it is one direction for the whole blog, not a per-post critique — so the block you need has usually already been written somewhere, and the version sitting in the record is the one under rejection.

1. **Grep the library's verdict rows for the reason's own words** to see which other slots have already been through it: `grep -rh '^| [0-9]' 3-resources/image-library/ | grep -i 'grain\|1990'`. The rows name the job that answered the reason and the verdict that followed, which tells you whether the block you are about to copy already failed once, and whether a refinement (stronger grain, both grain and ink lines) has since been forced out of him.
2. **Take the block from the newest prompt file, not from memory of the series:** `ls -lat ~/image-studio/backlog/prompts | head -12` puts the latest written prompts on top, and a sibling run working the same reason has usually already written and submitted one. Copy its `style_description` verbatim, then change only the scene.
3. **Compare it with the `## Prompt` of the images he approved most recently.** If the two disagree, this reason wins and the difference is exactly what he is correcting — do not re-derive the block from the record's older prompt, because that is the version in front of him when he wrote it down.

## Clause to prompt change

| his clause | the prompt change |
| --- | --- |
| 1990s anime / photo graining | the style block below, verbatim. `medium` says hand-painted 1990s anime cel with fine even film grain; `art_style` says inked outlines with the print softness of an old animation still and fine all-over film grain. |
| green stuff not fitting, palette consistent across image | no green anywhere, and **no `color_palette` hex array** — the array is what renders as a swatch strip. Name the palette in prose instead, once, and add "one palette only, no other colour accent". |
| texts not readable | remove the text-bearing prop, never reword the label. No screens, no UI panels, no cards, no banners, no price badges, no signage. Close the `high_level_description` with "No lettering anywhere in the picture, no signage, no labels, no cards, no panels, no posters, no badges, no charts, no interface elements." |
| two main characters / Wojtek and small androids / junkyard PCs | one human per frame (Wojtek, chibi, Dragon Ball proportions) plus one knee-high boxy grey android with round glowing eyes and a short antenna. The world is the basement workshop with stacked old beige PC towers, and the android does a job in the frame (holds a lantern, holds a panel, tilts a bucket) instead of standing as decoration. |
| companion flux images | for every Ideogram render, also submit a FLUX companion of the same composition and palette, named `<item id>-flux`, so he can compare engines on one card. The FLUX text mirror is 200-260 words. |

## The style block (copy as written)

JSON `style_description`:

```json
"style_description": {
  "aesthetics": "1990s anime cel animation, Akira Toriyama Dragon Ball character style with the muted cinematic restraint of a 1990s anime film still, fine photographic film grain across the whole frame, one consistent palette of warm ochre wood, cream, weathered grey steel and deep indigo shadow",
  "lighting": "warm workshop lamp light from above, soft falloff into indigo shadow at the edges of the room, gentle rim light on his hair and shoulders",
  "medium": "hand-painted 1990s anime cel, opaque gouache background, inked outlines with the slight print softness of an old animation still, fine even film grain",
  "art_style": "1990s cel-anime illustration in the style of Akira Toriyama, rounded exaggerated Dragon Ball proportions, flat cel paint with hand-painted gradients, fine all-over film grain, one restrained palette"
}
```

FLUX opening paragraph:

> A wide 16:9 illustration for a technology blog header, drawn as a 1990s anime cel-animation film still in the style of Akira Toriyama's Dragon Ball, with fine photographic film grain across the whole frame and one restrained, consistent palette of warm ochre wood, cream, weathered grey steel and deep indigo shadow — one palette only, no other colour accent.

Variation is allowed in the palette nouns only (a basement scene may lead with weathered steel blue-grey), never in the grain, the cel medium or the "one palette only" clause.

## A "drawn line" clause never replaces the grain

A hand-inked \"drawn line\" clause written *in place of* the grain (the shape used after post 041) is a regression he catches on the next card: on post 042 he wrote \"not all flux images are having enough `photo grain` and also lines are still not enough in the style of animes i mentioned to you multiple times... regenerate the flux images, more grain!\".

- Every flux prompt carries **both** clauses at once: the film-still + **strong fine photographic film grain over the whole frame** opening, and the bold black inked outlines with flat cel paint and halftone shading. Dropping grain to get cleaner lines is what produced the rejection.
- The android belongs in the frame on every slot, doing a job, so \"two main characters\" is answered with picture, not with prose.
- A style rejection on flux is repaired by restating the opening paragraph verbatim with the grain words in it, then adding the ink-line words — never by trimming the ask to the lines alone.

## When a slot's beat is itself the colour he bans

A picture whose story is red-then-green (post 050's smoke-test slot, `itsaplan-redgreen`) cannot obey "no green anywhere" and still say its sentence. Split the ban by what the green *is*: every green **graphic mark** goes (ticks, badges, tags, coins, cards, column tabs) and all green **scenery** goes (grass, foliage), because those are the shapes he calls "stuff that does not fit the concept"; a green **material the scene needs** may stay as one prop, and the prompt names it as material ("red-glass indicator lamp", "reagent in the tube") rather than as an accent. On post 050 the resolution went further: the pass state became a plain cream lamp with a brass base against the red lit one, so the frame carried the fail-then-pass sentence with no green pigment at all. Whatever the split, say it on the next card in one line — which clause was read how, and that one word from him re-renders that slot alone. A silent interpretation of a clause he wrote is the defect; a named one is a choice he can correct.

## Prompt-side traps that this style does not fix

- **A visual read that calls a frame clean is not a pass on this brief; the two measurements are.** A back-filled Sep header read clean at full frame (one chibi, no lettering, no pasted panel) and still failed both clauses: `check-green-share.py` found 1.83% green in one 17.8k-px blob sitting exactly on the monitor's tick, and `check-grain.py` against an approved frame read hf_residual 3.62 against 4.79. A tick on a monitor is a green **graphic mark**, which is the first thing the ban removes, and the monitor showing it is the banned screen surface — so both defects are the same prop, and the fix is to drop the surface rather than recolor it. On a slot whose subject is a state (healthy, alerting, failing), carry the state on a physical lamp dome the scene needs (the sanctioned "red-glass indicator lamp") and never on a glyph inside a screen.

- **"Green stuff is not fitting" is measurable, so measure it before you fear it.** `scripts/check-green-share.py IMAGE.png --baseline APPROVED.png` prints the share of the frame whose hue sits in the 70-170 deg band at usable saturation, the largest green blob with its bbox, and the busiest 32x32 cell. A vision read calls an olive-grey android "green"; the number separates a 0.3% paint drift from a real green prop. Run it whenever the frame holds anything grey-green, and quote the percentage on the card rather than the read's adjective.

- **"Photo graining is not here" is measurable too, and it is the clause he repeats.** `scripts/check-grain.py IMAGE.png --baseline REJECTED.png` prints the frame's high-frequency residual — the per-pixel grain floor — for the candidate and for the picture he rejected, and says which carries more. A read answers this clause with an adjective in either direction ("clean digital art with a heavy noise filter" on a frame that does carry grain), so quote the two numbers on the card instead. Read it comparatively: content edges raise the number as much as grain does, so the baseline is what makes it mean anything. The same script's `flat_std` is content busyness, not grain — do not quote it as grain.

- **A beat expressed as an absence inverts; a beat expressed as an obstacle holds.** "A brass keyhole plate whose surface is smooth and unbroken, with no slot for the key" rendered as a real keyhole with an open slot and the key hovering a few centimetres above it, so a picture about being denied read as a picture about about-to-unlock. The model draws the noun it is given, and a hole is the whole meaning of a keyhole plate: name the body instead ("a small blank brass disc, polished, with nothing cut into it") and carry the refusal with something physical in the frame — an iron bar or a bolt holding the door shut, a hasp with no lock — so the picture says denied without needing an absence to survive.
- `check-bboxes.py` flags the word `thin` in a `desc` as a narrow-strip claim; "a thin ring of dust" on a 550 px box is a BBOX PROBLEM. Write "a faint ring of dust".
- The linter's risk score counts elements, so fold the companion props into the figure or the object they touch: five or six elements is the working ceiling and the background counts as one.
- A FLUX companion is an *attempt*, not a round. It gets its own item id only when it goes on a card as a separate item (`<slot>-r2-flux`), and the item id it is approved under is the name of the vault asset and the record stem.
- **Expect the companion to miss the brief's specifics and do not hold it back for that.** The companion exists so he can compare two engines on one composition, and on a three-slot round it routinely drifts inside its own scene — a door that renders shut while the man points a key at it, a row of five jars drawn as three, two androids where the brief says one, the magnifier held out at arm's length instead of over the prop. Those are reasons to name the miss in the item's description and to say plainly that it is a comparison and not a shipping candidate; they are not reasons to re-render the flux text until it matches, because matching the Ideogram frame is not what the comparison is for. Hold a companion back only when it stops looking like the same picture at all — a different room, or a frame carrying lettering, which is the one class that never ships.
