# When both vision routes fail: the third model group

**Order of attempts before you write "reads at close: none".**

1. `vision_analyze` (aux proxy) on the full image.
2. `scripts/vread.py IMAGE "one short line" deepseek-v4.1-flash-1017-ds` (the documented fallback group) — vision-capable and fast.
3. Only if both fail or return empty, fall back to mechanical verification (file present, dimensions, non-blank via PIL mean luma, grey-bar / blank-margin / palette scripts, tesseract for lettering) and write "reads at close: none" in the check note, naming which routes failed.

Do not skip step 2 because step 1 returned a text-only or proxy error; that is the failure that makes the fallback worth having.

`vision_analyze` (aux proxy) and `scripts/vread.py` with `qwen3.8-flash` (the agent's provider) are the two documented routes. They fail together often enough to plan for, and on 2026-11-05 they failed for different reasons at once:

- aux proxy: `502` with `cookie 池里 1 个账号都不可用 … google.com/sorry` — the Gemini web cookie pool is dead, and this also kills nano banana renders on the same morning.
- aux proxy: `400 This API supports text input only` — the current model group (e.g. `beam-free-go`) is text-only, so `vision_analyze` cannot carry an image at all. This is not a proxy outage; the fallback to `vread.py` with `deepseek-v4.1-flash-1017-ds` is the whole answer. **A lone 400 can still be transient routing rather than a permanent capability gap** — retry once with the *same* image (do not resize first; the failure is the route, not the payload size); if the second call also returns text-only, then the route is text-only and the fallback is the whole answer. Do not loop past that. When the retry succeeds, record it in the check note as "aux proxy (retried once)" so a later run does not re-read the image believing vision was never available on this card.
- aux proxy: `400 gemini-4-argon is unavailable without a Google account cookie: anonymous requests … are silently downgraded` is the same dead cookie pool as the 502, reported by a different model group. That is configuration state, not a routing blip, so the retry-once rule above does not apply: go straight to `vread.py`, and say in the check note that the aux route was unavailable and which model read the pixels.
- `qwen3.8-flash` and every `*-go` group: `429 Go usage limit exceeded`.
- aux proxy: `429 ip_slot_full` — `direct IP slot full: concurrent limit reached (configure proxies to scale)`. That is contention on the shared reader IP, not a dead route and not a spent quota: other agents' calls hold every slot for a few seconds at a time. Pause about 20 s and retry the same question once. **A 429 never justifies `reads: none`** — when a full-frame read has already answered and only a crop read is left, settle that point from the read you have plus the mechanical scripts rather than spending more calls on it; a crop is a tie-breaker for a contested claim, not a required step after every successful read.
- `qwen3.8-27b-mlx`: answered twice, then `524` Cloudflare origin timeout on every call for twenty minutes, including 56 KB JPEGs; that repeat is the mark of a route-level failure rather than a payload problem. **A single 524 proves nothing about the route.** A `524` can be the origin timing out on one long multi-part question while a short fixed-slot question on the same route answers on the very next call (the 120 s proxy window is spent on the long ask, not on the pixels). So retry once with the six-slot frame question before switching readers or writing "reads: none"; only a second 524 on the short question means the route itself is out.
- `qwen3.6-plus-go` `400 Model is unavailable`; `qwen3.5-397b-ollama` `410 retired`; `qwen3.8-9b-heretic-uncensored` `400 does not support image inputs`.

**The group that answered: `deepseek-v4.1-flash-1017-ds`** — vision-capable, fast, and it is in the provider's own fallback list. Read a frame with

```bash
python3 scripts/vread.py IMAGE.png "One line: how many hands, and where is each?" deepseek-v4.1-flash-1017-ds
```

**`vread.py` is not on `PATH`.** It is `scripts/vread.py` inside the skill directory, so `which vread` answers nothing and reading the fallback as a missing install costs the round its vision read. Run it as `python3 scripts/vread.py …` from `~/.hermes/profiles/matejko/skills/image-studio`.

Two traits that cost calls:

- **It spends its budget on reasoning, so a multi-part question can return `empty read: finish_reason=length` with the answer stranded in `reasoning_content`.** Default to one short line at a time ("How many hands are visible on the man? One line."). A numbered list of short questions also lands, so use this fixed six-slot frame question when a whole PNG needs checking — it answered on four files in a row, while a free-form "describe everything and flag any defects" over the same file came back empty:

```bash
python3 scripts/vread.py IMG.png "Answer in 6 short lines: 1) figures 2) hands/fingers 3) any text or labels? 4) dominant colours 5) ink lines and grain? 6) defects?"
```

The free-form version fails for the reason the bare-number demand does: "flag any defect" is a reasoning task the model never finishes emitting, whereas slots with a fixed shape are answered in order. An empty read still means go back to single-line, and do not treat an empty multi-line read as a failed route.
- **A bare-number demand is the worst case, and a descriptive one-liner is the fix.** "How many monsters? Answer with a number only." returns `empty read` on both the full frame and a crop, because the model reasons through the count and never emits an answer; "How many monsters are marching, and does one man face-palm at the end?" answers in a sentence that carries the number. Two reads that disagree (eight, then nine) are a range to quote in the check note, not a precise count to assert.
- **A two-option question with a defect in one option gets the defect answer, so never ask "pasted or drawn?"** Asked whether a green terminal screen was "a drawn monitor in the room, or a bare cut-out pasted on top", the reader answered "a bare cut-out with no frame"; a neutral "describe the back wall and how each thing is rendered" read then put the same class of shape (a wall logo) inside a framed picture on the wall, and the pixel probe settled it: the screen's left edge drifts x604->x626 down 104 rows and its top edge climbs y270->y237, which is a quad in one-point perspective, not an axis-aligned paste. Ask for a description, not a verdict, and settle a paste claim by measuring the edges of the blob.
- **A whole-frame read invents readable words that a crop of the same region refuses.** On one render the full frame reported vertical `c-shop` and `security` on a chained document; a 2x crop of exactly that document returned "no readable characters, illustrative squiggles". The crop is the tie-breaker in both directions, so quote the crop and say the whole-frame claim was a misread rather than writing invented text into a check note.
- **It completes the story it is asked about, so a crop that cuts the subject gives a confident wrong count.** A crop of x 640-1000 on a figure standing in the middle third (x 459-917) reported "the left sleeve ends below the elbow, no hands"; the same man on a wider crop read "two arms, two hands, one in a pocket, one behind the back". Establish the subject's bbox first ("which third of the picture width is the man in, and what vertical band does his body occupy"), then crop wide enough to hold all of him, and settle a limb on the written crop.
- **A house pose is not a defect.** "Zero visible hands" is the correct read of the series' standing pose, both hands pushed into trouser pockets, which the approved headers carry. Say it as a caveat on the card ("hands in his pockets, the pose of your approved header"), never as a bar failure.
- **A read's volunteered verdict on a prop is a judgement, not a measurement.** Asked about a dark round object on a desk, the reader called it "an unexplained stray prop that draws unwanted attention" — yet the prop was in the prompt, sat on the desk, and was cropped only because the frame is full-bleed by design. The pasted-artifact defect class is a texture and perspective break, which a whole-frame pass cannot distinguish from a described object at the border. Name it in `detailsMarkdown` ("a round prop at the far-left edge, cut by the frame") and ship; holding a slot on one model's adjective spends a 21-minute render on nothing.

Mechanical checks keep running while all of this is down: `check-grey-bars.py`, `check-palette-strip.py`, `check-blank-margin.py`, `check-defect-signature.py`, `check-green-share.py`, and `tesseract FILE - --psm 11` for lettering (clean words mean readable English; `Corevibia` / `Rortariggerigntiotcnet` mean invented text). Name the reader in the check note.

**Locate invented lettering before you crop it, or the crop lies by omission.** `tesseract IMG out tsv` writes one row per word with `left`, `top`, `width` and `height`; read those coordinates, crop each label at 2-4x, and quote the words the crop shows. `tesseract FILE - --psm 11` gives the words but not where they are, so a hand-aimed crop that misses the label answers "no text there" — which reads exactly like a clean frame. A note that names the exact garbled words and where they sit is the one he can act on; a note that says only "there is some text" gives him nothing to reject against.

**A full-frame word list is a lead, not evidence, and the error runs both ways.** The omission case above is one direction; the other is a full-frame pass that lists words the frame does not carry — it named two brand names on a row of small figurines that a crop of that spot showed to be a plain face with no lettering at all. So the hold-back note quotes only words a written crop shows, and when a crop of the box the tsv points at shows nothing, the word was the reader's and that slot is not held on it. Locate, crop, read, then quote.

**A zoomed crop over about 1200 px wide returns `empty read: finish_reason=length` on a question the same label answered inside the full frame.** The zoom multiplies the encoder's tokens, not the legibility, so a 5x crop of a small label goes empty even on a one-line question. Crop from the tsv box, then downscale the crop to roughly 800-900 px wide before the read: a label twenty pixels tall is legible at that width, and the file stays small enough to answer.

**The lettering-sweep questions that land.** On a full frame, "What words are written in this picture, and are they spelled right?" returns the whole list with a per-word verdict, where "read every piece of lettering verbatim" overflows into an empty read. On a crop, "Read the lettering in this crop exactly as it is written." and "What word is printed on this label?" both answer; a crop may hold several labels when the question asks for one line each ("Read every sign's lettering in this crop exactly as written. One line per sign." returned all three correctly).

When a batch mixes routes (some images via aux proxy, others via vread), name the reader per image, not once for the batch — the two readers have different reliability profiles, and a card that says only "vision available" hides which read came from which.

**A nano banana PNG is small and the grey-bar script calls it a grey box.** A 1376x768 render from the campaign lands at 0.20-0.28 MB because the engine returns a JPEG, so `check-grey-bars.py` fires `FULL GREY-BOX (safety filter): file 0.22 MB < 0.4 MB threshold`. That is the size threshold, not a grey frame — confirm with a read or `check-blank-margin.py` (fill share, blank strips) before writing a defect note.

**A second reader model settles a prop claim that one whole-frame read asserts.** `deepseek-v4.1-flash-1017-ds` mislabels small props: the knee-high android standing on the floor came back as "a nonsensical floating pipe" on one pass and "a metal handle" on the next. `gemma4-31b-ollama` is the cross-check — same `vread.py`, one plain descriptive sentence, no defect framing:

```bash
python3 scripts/vread.py IMG.png "What is the metal object on the floor in the lower left? One line." gemma4-31b-ollama
```

Two models naming the same object independently is the evidence to quote; one model's label is a lead. Use it on the prop the prompt asked for, before holding a slot back for a "floating pipe" or passing one whose android is supposed to be holding a lamp. When the two disagree, a written crop decides — not a third read.

**Read reliability is a separate concern.** `references/vision-read-reliability.md` covers how to interpret a read, when a full-frame pass invents props and defects, why a parallel batch of reads is unsafe, and how to resize a large file for a smaller upload (`sips -Z 800` on macOS or PIL `Image.open(src).convert("RGB").resize((912, 624), Image.LANCZOS).save(dst)`). Read it alongside this file whenever you are self-checking images.

**When the brief already carries these reads.** A fresh card build whose brief names a fallback reader per image with crop-level detail does not need a second `vread.py` pass of the same image: the brief's per-image read stands in for the frame-level read required by `references/archive/review-card-api.md`. Re-run the mechanical gates yourself regardless, name the reader per image in the item description, and name any caveat that does not reproduce instead of copying it forward.
