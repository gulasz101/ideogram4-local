# Shipping approved frames

What happens between "the card is answered" and "the issue is done". The work is mechanical; the two judgement calls are which frame ships when a pair is approved, and what the alt text says now that the picture changed.

## Which frame ships when both halves of a pair are approved

A post step carries one image. When the ideogram and the flux frame of the same slot are both approved:

- the **ideogram** becomes the post's frame and its embed line;
- the **flux** frame still ships to the vault beside it as `<slot>-flux.png`, with its own record at `verdict: "approved"`, and the post's embed is left alone. The library already works this way — a `ls tech_blog/assets/*/*-flux.png` shows a hundred of them. Keep it, because a register change later swaps the frames without a render.
- nothing is deleted: the pair is the library's record of what he saw and approved.

**Say the tie-break on the card before the verdicts, not after.** One line — "if you approve both, the ideogram ships; put a line in the reason if you want the soft one" — turns an approve-approve with no reason into a decided case. Without it, both approved leaves you guessing, and guessing at which frame he wanted is exactly the judgement that is his.

Pass the alternative to the ship script with `"embed": false`. Without the flag the script refuses on a missing embed (`appears 0 times`), which reads like a broken post rather than an intentional alternative.

## Ship with the script, never by hand

`ship-approved-batch.py <spec.json> --dry-run`, read the plan, then run it without the flag. Per item it:

1. moves the file being replaced to `<name>.superseded-<old job>.png`;
2. writes the approved PNG **decoded from staging** — not `cp`, so the vault copy is an optimized re-encode;
3. rewrites that one embed's alt in place and refuses when the embed appears zero or twice;
4. repoints the old record's `asset:` at the kept superseded file and sets `superseded_by:` (its `verdict:` stays as it was — a rejected draft that was never shown does not become approved because a later render replaced it);
5. writes the new record as `<record_date>-<staging stem>--<job>.md`;
6. compares decoded pixels of every vault file against its staged original and exits non-zero on any difference.

A hand `cp` plus a hand-written record skips step 1 and step 6, and both are the steps that make a later audit possible.

## What the spec must carry per item

- `embed` — `false` for the approved alternative.
- `prompt_type` — `json` for an ideogram prompt, `text` for flux. Left to the default, an ideogram record claims a text prompt and the Prompt block is then the only honest part of it.
- `round` at the top level — the verdict table's round column. A round-2 card that writes round 1 into the records makes the library say the image was judged before it existed.
- `quote` — the paragraph or lead-in line the image sits under, copied from the post.
- `why` — the beat, one or two sentences tying the picture to the section.
- `alt` — see below.
- `post_status` — the post's real status; the script defaults to `draft`.

## Alt text is a claim about the picture that ships

Write it from a read of the render you are shipping: the room, the pose, the objects and where they sit. Never carry a noun over from the old alt — the old alt was written for the picture that failed, and it typically names a label, a checkmark or a prop the new frame does not contain. An alt that describes the rejected draft is a prose defect nobody re-opens.

When the render deviates from its own prompt (a rack that came out as a cabinet, pods that came out as canisters), the alt follows the render, not the prompt.

## Gotchas in the ship script's defaults

Five things the script does not warn about, all found by running `verify-slot.py` afterwards. Each surfaces as a FAIL that does not name its cause:

- `staging` must be the date folder and `stage` the basename. If `staging` is the staging root and `stage` carries `YYYY-MM-DD/...`, the record filename becomes `<record_date>-YYYY-MM-DD/...` and the record lands in a subdirectory. Set `staging` to `.../staging/<date>` and `stage` to the basename.
- The generated record writes `From [[post]]` then the quote, but `verify-slot.py` expects `From [[post]], section "<heading>":`. Patch the new record's Why line to add the section label, and keep the quote as a passage from that section rather than the heading itself, before running verify-slot.
- `ship-approved-batch.py` re-encodes the PNG with `optimize=True`, so the vault bytes differ from staging even though the pixels are identical (`maxdiff 0`). `verify-slot.py` compares bytes and will report FAIL. Overwrite the vault asset with the staging bytes (`cp`) after the ship run; the pixel check and the record still hold.
- **The record filename's date is the job's `created_at` date, not the spec's `record_date`.** The script names the record `<record_date>-<stem>--<job>.md`, but `verify-slot.py` compares that prefix against `created_at`, so a batch submitted the day before it is shipped fails "filename starts with the job's created_at date" and, because the stem is then mis-sliced, "heading is the stem" too. After the ship run, rename those records to `<created_at YYYY-MM-DD>-<stem>--<job>.md`; the heading already matches the stem, so nothing inside the file changes.
- **The quote must be a `>` blockquote, and the script writes it as a bare paragraph.** `verify-slot.py` collects the Why passages from lines starting `> `, so it reports "Why quotes at least one passage" as FAIL against a record that does carry the quote. Prefix the paragraph after the `From [[post]]` line with `> ` along with adding the section label.
- A header sits above the post's first `## ` heading, so its provenance line is `section "":` with the empty string — that is correct, and `verify-slot.py` passes it when the nearest heading above the quote is also "".

## Verify, then close

- every `assets/...` embed in the post resolves to a file on disk (loop the greps, do not spot-check the two you changed);
- the pixel check printed `maxdiff 0` for every shipped item;
- each old record reads `superseded_by: "<approved job>"` and its `asset:` points at the kept file;
- after the fact, the new records' `post_status` is the post's status and not `null`.

## The queue entry closes on the batch branch

Read `queue.json` (`slot`, `batch`) or run `backlog.py status` before closing. A re-render round is a `batch` entry, not the live `slot`; `backlog.py card-done <n>` frees whichever one holds post `n` and prints `{"ok": true, "state": "done", "batch": <count>}` — a `batch` count in the answer is the proof it took the batch branch and did not touch another run's slot.

`card-done` exits with "the slot is not held by post n" when the post sits at `state: "card"` but is in neither `slot` nor `batch` — the shape left behind when a post was released with `--rendering` and its later round's card was opened outside the batch machinery. Do not force the state through another command that touches the slot; take the queue lock, set that post's `state` to `"done"`, append the closeout note with the three job ids, and leave `slot` alone, because another run owns it.
