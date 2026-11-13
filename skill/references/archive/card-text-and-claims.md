# Card text, and whose claims reach it

The words on a verdict card — the item description, the `detailsMarkdown` table, the check note, and the alt text written at approval — are the only thing he judges from and the only record the next run can read. This file is about getting those words right and about not inheriting a predecessor's wrong ones.

## The item description is a length problem before it is a writing problem

`build-verdict-card.py` refuses a description over 500 characters, and every refusal costs a full tool round-trip. Do not draft prose and then measure it: write five candidates in one small script and print `len()` beside each, then keep the first that fits under about 470.

```python
cands = ["...", "...", "..."]
for c in cands:
    print(len(c), c[:60])
```

Estimating by eye runs about 15% long: a draft that feels like 450 characters routinely measures 620. When trimming, cut restated premise and adverbs first; the two things that must survive are the clause that answers his reason and the caveat he will judge.

## A previous run's check note is a claim about its prompt, not a measurement of the pixels

The note in a handoff brief was written by the run that fetched the render, often from the prompt it had just submitted. Its weakest sentences are the ones that describe **contact**, **state** and **count**, because those are exactly what the prompt asked for and what a whole-frame reader will agree with out of expectation:

- *contact* — "one hand on the door handle" is frequently the prompt's intent and not the picture; a raised fist near the frame reads as a grip at frame size. Crop the figure and answer it.
- *count* — question marks, racks, jars, tiles. The prompt's number is not the render's number.
- *state* — open or shut, ajar or flush, full or empty. Settle it on a crop of the prop with its own edges in the frame.

Re-derive all three before any of them reaches the description, the `detailsMarkdown` table, or the alt text written at approval. A card that repeats the brief's sentence is a statement about a picture nobody made, frozen where the next run will trust it.

**Crop wide enough to hold the feature you are asking about, because it usually sits at the subject's own edge.** A door's open gap lives exactly at its latch edge: a box that ends at the door panel cuts the gap and the brick behind it, and the reader then reports the door shut flush with nothing behind it — the wrong answer, drawn by the crop. Include the frame, the jamb and a margin of the room beyond, then judge.

## When your crops contradict the brief, repair the brief in the same run

The run that writes the record and the alt text reads the brief, not this thread. So before ending a card-opening run whose crops disagree with the brief's check note, `patch` the brief: append a short section naming each sentence that does not match the pixels, the value that replaces it, the crop that settled it, and the measured figures (size, bytes, sha256, and each check script's own output). Read the brief first — it is an unseen file to this run, and `patch` on an unread file is refused.

A correction that lives only in a comment is lost to the close; a correction in the brief is read by the run that has to write the alt text.

## A colour count that runs high because the composition needs the colour is stated, not held back

A standing palette rule bans a colour by default, so a frame that carries a lot of it looks like a defect the moment the check line prints a percentage. A count answers "how much", never "was this wanted": on a scene whose good path is a green door, `check-green-share` reported 12.71% of the frame and every one of those pixels was that door and the room behind it. Name the prop the pixels belong to, say the prompt asked for the colour because the prop carries the beat, and offer the neutral alternative in one clause — "tell me if you want it neutral instead" — so the choice stays his. Holding such a render back spends a round on a colour he never objected to; shipping it past a standing ban without naming the count leaves him to find it himself.

## An empty list from the API prints nothing, and reads like a failed call

On a fresh card issue, `GET /interactions`, `GET /attachments` and `GET /comments` all answer `[]`. A script that prints one line per row then prints nothing at all, which looks like a dead request and invites a re-check. Print the count explicitly (`print("comments", len(coms))`) and assert the expectation — a card issue that should hold no card yet is a state worth seeing in the output, not an absence to interpret.
