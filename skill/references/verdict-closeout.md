# Closing a verdict round: ship the file, record it, free the slot

The steps after an `approve` comes back on a card. Do them in this order; each one leaves something a later run can verify.

## 1. Ship under the branch the picture needs: a new filename, or the draft's own path preserved

Two branches, and the brief names which one this close is on.

**A slot whose picture is not yet in the draft** gets a NEW filename: copy the staged PNG to `tech_blog/assets/<close date>/<item id>.png` and leave the original file alone. The day folder is the day the close runs, never the post's own date: a brief that names the draft's `assets/<post date>/` path is carrying the location of the picture being replaced, and its embed line repeats it. Follow the close-day rule, `ls` the folder first because every post closed that day writes into it, and say the departure in the closing comment so the brief and the vault are not left disagreeing in silence.

**A backlog re-review of an existing draft image is the other branch and overwrites in place.** When the brief names the draft's own current path (the header the draft already embeds) and the round exists to replace that picture, the path must not move: the embed stays and only its alt text changes. Copy the old bytes beside it as `<slug>.superseded-<old job id>.png` first, then write the new bytes over the original, and hash the copy against staging. A close that invents a new filename here leaves the draft pointing at the rejected picture.

An asset can be embedded by more than one post, and that decides the branch on its own. The header of one draft is also the header of a sibling draft that has its own review card. Overwriting `header.png` while closing one card silently changes a post nobody reviewed this round, and the sibling card still holds a verdict on the old picture. A new filename per round makes the swap visible in the embed and reversible, so a shared file is never overwritten in place: grep the drafts for the path with the ripgrep-backed `search_files` tool — a shell `grep -rn` over the vault's `tech_blog/` runs past a 180 s tool cap and answers nothing — and when a second post embeds it, ship under a new name and repoint only the post under review.

**Nothing gets moved when the target is a new file.** The old picture stays at its own path, its record's `asset:` still resolves, and the only edit that record needs is `superseded_by`. The `.superseded-<old job>.png` preservation step belongs to the other branch — a brief that names the draft's own existing path, which is a real in-place re-review — and running it on a new-path close leaves a record pointing at a filename nobody will open.

## 2. Repoint only the post under review

`grep -n '^!\[' <post>.md` lists every embed. Change the path for the slot you closed and nothing else. Then check each path resolves to a non-zero file — an embed pointing at a name you forgot to copy renders as a broken image on the blog.

## 3. Write a NEW record for the shipped render

The new job is a new record (`3-resources/image-library/<YYYY-MM>/<created_at date>-<fetched stem>--<job>.md`, where the stem is the fetched PNG's basename without `.png`), not an edit of the old one. Both the folder and the date prefix come from the job's own `created_at`, never from the day the verdict landed:

- frontmatter: `job_id` of the shipped render, `asset` set to the new vault path (vault-relative, `tech_blog/assets/...`), `asset_present: true`, `asset_location: "vault"`, `verdict: "approved"`, `source: "studio"` — a card approval is a studio record, and `"render"` is a value the index does not read — `posts:` the post that embeds it, and `post_status:` the post's real frontmatter status.
- `## Prompt` holds the prompt JSON from `backlog/prompts/<slot>-r<n>.json`.
- `## Verdicts` gets one row: the round number, the date, `approved`, the reason (or `Approved on review.`), and the issue link.

An approve with no reason is the common case. Do not invent one, and say "no reasons" in the closing comment rather than paraphrasing a silence into a lesson.

## 4. Settle the old record the right way

- **Replaced, not shared:** set `superseded_by: "<new job id>"` on the old record and append a row naming the job that replaces it. `superseded_by` holds a JOB ID, never a path.
- **A brief's "set `verdict: approved` and drop the back-fill line" is the back-fill recipe, and it does not fit a record that already carries a rejected row.** A slot judged in an earlier round has no back-fill marker, so `approve_record.py` refuses it ("no marker line; is it a back-filled record?"), and the verdict in its frontmatter is the verdict of the picture it documents. Leave that verdict, its row and its asset fields exactly as they are, set only `superseded_by: "<new job id>"`, and put the approval row on the NEW record's table — with the earlier round's row copied into that same table, stem-prefixed, so the slot's history reads in one place. Rewriting the old record to `approved` writes a decision onto a picture he rejected.
- **Shared between posts:** append a verdict row and leave `superseded_by` alone. The sibling post still embeds that file, so marking it superseded declares a live asset dead and loses the history of which card approved what.

## 5. Run the mechanical close check before the slot is freed

`scripts/verify-slot.py` is the gate, not a nicety: the filename against the job's `created_at`, the heading against the stem, the prompt block byte-for-byte, the `superseded_by` chain of every earlier record, the vault asset byte-identical to staging, the post embed and its alt text, the Verdicts table shape and the `## Why` provenance. Run it from the vault root with vault-relative paths, and quote its counts in the closing comment.

```bash
cd /Users/paperclip/vault
python3 ~/.hermes/profiles/matejko/skills/image-studio/scripts/verify-slot.py \
  --record 3-resources/image-library/2026-11/<stem>--<job>.md --job <job> \
  --earlier 3-resources/image-library/2026-07/<old stem>--<old job>.md \
  --earlier 3-resources/image-library/2026-11/<attempt stem>--<attempt job>.md \
  --post tech_blog/<post>.md \
  --prompt ~/image-studio/backlog/prompts/<slot>-r<n>.json \
  --asset-source ~/image-studio/staging/<round dir>/<fetched stem>.png --source studio
```

**`--earlier` takes one path per flag.** It is `action="append"`, so two paths after a single `--earlier` exit with `unrecognized arguments` before a single check runs, which reads like a malformed command rather than a missing flag. Repeat the flag for every earlier record of the slot, the held-back attempts included, and read a non-zero exit as the gate failing rather than as advice.

## 6. Free the slot once every image of the post is approved

`backlog.py card-done <n>` with no flag marks the post done. `--rendering` is the earlier state, used only when re-renders have just been submitted. `{"ok": true, "state": "done", "closed_without_slot": true}` is a normal answer — it means another card already held the live slot; nothing is wrong. `{"ok": true, "state": "done", "batch": <count>}` is the other normal branch (a re-render round sits in the batch, not in the live slot) and its presence is the proof the close freed the batch entry rather than another run's slot. Read the echoed `state` and the branch key instead of assuming which entry moved.

## 7. Close the issue with the evidence

Final comment: each shipped file with its job id and the round that approved it, which records are new, which are superseded, and which renders stay held back with their self-check reasons. Then `PATCH` the issue to `done`.

**That comment is the audit trail, so a value it states that later changes is repaired at the comment rather than corrected underneath it.** A close that moves an asset path after posting leaves two comments claiming different paths, and the first one reads as the current state to every later reader. Delete your own run's comment (`DELETE /api/issues/<id>/comments/<commentId>`, allowed for the run that posted it) and repost the corrected close instead of adding a "correction to the comment above" reply. A comment another run posted cannot be deleted by this one — correct that one with a single short comment naming the stale value. Read the thread back by body, not by count: a deleted comment stays in the list with an empty body, so `len(comments)` still counts it and the count proves nothing about what a reader sees.

## A card a comment closed has no item reasons, so the reason lives in the comment — and a paraphrase in the library is repaired, not copied forward

An owner who answers a card by commenting on the issue settles it as `superseded_by_comment`: the interaction reads `status: "expired"`, `result.items: []`, and `result.commentId` names the comment that decided the round. No `reason` exists anywhere in the result, so:

- read the comment and split it into the clauses that belong to each item, then write those clauses into the new records **verbatim** — the row is the library's durable quote of a decision he made, so his loose wording stays;
- and read the slot's earlier record before copying its round row forward. That row was written by whichever run first read the comment, and it is usually a paraphrase of his sentence: copying it promotes the paraphrase into the slot's history, and a later reader cannot tell it from his words. Compare it against the comment, replace the reason cell with the verbatim clause (stem prefix and both pads kept), and name which rows you repaired in the closing comment — nothing on that post's own issue will ever show the edit;
- the card's item description is not the authority either: it was written from the brief, before any verdict existed.

## Pitfalls

- **One card's round can be answered while the next render is still queued.** Apply the answered round, open a new card for the pending render, and do not hold approved images hostage to it. Splitting rounds is normal; a card that waits for a queue costs the owner a review cycle.
- **Only a card result resolves an item.** A self-check that passes is a filter for defects, never an approval; nothing ships until the card says `approve`.
- **Verify mechanically what you shipped** (embed path exists, `asset_present: true`, verdict row present) instead of trusting that the write landed.
