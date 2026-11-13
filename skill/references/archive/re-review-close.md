# Re-review close

The close of a card whose **re-render was approved**. The record format lives in `references/library-records.md`; this file is the order of the close and the two traps that the format rules do not cover.

## The close in order

1. Read the card's answer per item (`result.items[].verdict`). An approval with no reason is still a verdict.
2. Copy the approved staging PNG over the post's own asset, preserving the old bytes first. The live path is `tech_blog/assets/<day>/<item id>.png`, the path the draft already embeds. Hash the old file, copy it to `<stem>.superseded-<old job id>.png` beside it, hash-check the preserved copy, copy the staging file over the live path, then hash-check live equals staging. The free-path refusal does not apply here: the target is this post's own asset, so preserve-then-overwrite is the required branch. Never pick a new name and never leave the draft on the old bytes.
3. Edit only that embed's alt text. The path stays the same, so there is no `tech_blog/tech_blog/...` risk. Read the post back from disk and assert the whole `![alt](path)` line, not the path count alone.
4. Write the new studio record. Its Verdicts table copies the earlier round's row and prefixes that reason with the earlier render's stem, then adds the approval row (`Approved on review.` when he gave no reason). Rounds ascend.
5. Repoint the earlier record in the same pass. Set `superseded_by` to the approved job. Set `asset:` to the preserved copy. **Set the body `![[...]]` line to the preserved copy too.** That line is a second claim about the record's own render: leave it on the live path and the record that documents the old picture renders the new one. Keep `asset_location: "vault"` and `asset_present: true`, because the preserved copy is in the vault, and keep its verdict (rejected or unreviewed), because that verdict belongs to the old render.
6. Run `verify-slot.py` with the earlier record in `--earlier` and quote the count. An approved close should reach 0 failed; the earlier record's `superseded_by` is what the duplicate guard counts.

## What the record step also owes

- **The record's month and day prefix come from the job's `created_at`, never from the round brief's path.** A re-review brief is written against the slot's earlier record, so it names the *old* month folder and the old render's date (`image-library/<old month>/<old date>-<item id>-<8 hex>--<job>.md`). The render behind the approved attempt is new, so its record lands in the month of its own `created_at` with that date as the prefix, and the old folder keeps only the records already there. A record written to the brief's path fails `filename starts with the job's created_at date`.
- **A round's held-back attempts usually have no record until this close, so write them here.** One record per attempt, in the same pass: `asset: null`, `asset_location: "max-only"`, `asset_present: false`, `superseded_by` the approved job, one `rejected` row whose reason starts `held back at the self-check, never shown to Wojtek` and names the defect, and no `![[...]]` line. The approved record's table carries one stem-prefixed row per attempt, with the attempt's own issue column and the same round number as the approval.
- **Name the replacement by stem, never by job id, inside an attempt's record.** The duplicate guard counts the approved id across every file in the folder, so a job id written into the attempt's `## Why` or row makes the approved record's own verification fail `job id appears in exactly this record plus its earlier records`. `superseded_by` is the only place a job id other than the record's own may appear.
- **A held-back record still carries provenance.** It quotes the section it was rendered for, by line position, like any other record: the missing asset does not make `## Why` optional, and on these records the prose is the only account of why the render was dropped.

## The earlier round's card can have no per-item reason

Step 1 reads `result.items[].reason`. When that card was superseded by a comment before anyone submitted verdicts it settles as `expired` and carries no items at all, so the reason survives only in that issue's comments (`GET /api/issues/<id>/comments?order=asc`, the message from the board user). Do not force a verbatim match against a row the earlier run wrote as a summary: a paraphrase that names the card it came from is honest history, and rewriting a pass of back-filled records at the close to satisfy one string is a bigger edit than the defect. Say in the closing comment which card expired and that its forwarded rows carry that run's summary rather than his words, so a reader knows where the verbatim reason lives.

## The round is not closed until `card-done` and Advance

The close ends with the queue, not with the records: post the closing comment, set the card issue `done`, run `backlog.py card-done <n>`, then Advance (`backlog.py next`, and on `create` open the next card and record it). **`scripts/open-card-issue.py` cannot create that next card.** It requires at least one `--item`, sends `status: in_progress`, and sends no `parentId`, so a card made with it is not a child of the runner and the queue's tree loses it. Create the issue with an explicit body — `title`, `description` = the brief verbatim, `parentId` = the runner issue, `projectId`, `assigneeAgentId`, `status: todo` — then run `backlog.py opened <n> <identifier>`; that card's own run uploads the PNGs from the brief's staging paths.

## The verdict is his; a defect found after it is a caveat

A render he approved ships when the late read is a prop or palette drift. Do not withdraw it, do not rewrite its `## Why` toward the prompt's intent, and do not invent a rejection. Put the picture's actual read in the `## Why` prose and name it in the closing comment as a caveat, with an offer to re-render that prop. The record's asset and verdict stay approved. **If the late read is a breakage that would have kept the image off the card** (garbled lettering, an extra hand, a grey box, an empty margin), a caveat is not enough: hold the image, say what the crop shows, and ask him for the call. A caveat covers a frame that still works, not a broken one.

Confirm a small-prop claim on two vision routes before writing it as fact. `vision_analyze` can 429 on the shared proxy, and a single read can call flat cel shading a pasted sticker. Read the crop again through `scripts/vread.py` on the agent provider (`--box x0,y0,x1,y1`, pixel coordinates, upscaled). Two independent routes agreeing is the bar for a record sentence; one route alone is a question in the closing comment, not a claim in the library.

## The preserve step cannot be recovered afterwards, and `imagegen fetch` will not do it

Preserve the old bytes **before** the copy, not after: `cp` the live asset to `<stem>.superseded-<old job id>.png` beside it, hash both, and only then copy the staging file over the live path. Once the overwrite has landed there is no route back. `imagegen fetch <old job>` answers with the **current** file under that basename rather than the job's own output (it reported success and wrote a byte-identical copy of the new render), the render worker keeps only recent `output/studio/<day>/` folders, and the vault is not a git repo, so the July bytes are simply gone. When that has already happened, do not invent a preserved path: set the earlier record's `asset: null`, `asset_location: "lost"`, `asset_present: false`, replace its body embed line with a plain note saying when and why the picture was replaced and that no copy exists, and say it in the closing comment as a miss of yours. `superseded_by` and the verdict stay, because they are true of the render that was lost.

## Two checks `verify-slot.py` runs that a careful close still trips

Run it from the vault root (`cd ~/vault`), because the record's `posts:` path is resolved against the working directory and a wrong cwd reports `FAIL post exists` on a healthy post. Then read the two content checks it is actually there for:

- **Alt text must describe the picture, not label the slot.** `header`, `posting to socials`, `persistent profile verified` all fail as placeholder words, and after an approved re-render they describe a picture that is no longer in the file anyway. Rewrite the embed's alt text in the same pass as the copy — the path stays, the description changes — and assert the whole `![...](path)` line.
- **The `section` label is checked against the nearest heading above the *quote*, not above the image.** An image that closes a section (the embed sits at the end of `## CLI usage`, the next heading introduces the prose) needs a quote from its own section, or the label must name the heading the quote actually sits under. An image above the first heading with no prose above it takes that first heading as its label.

A close is done when each slot prints `40 checks, 0 failed`.

## A header with no prose above the first heading

If the image sits above the first `##` heading and no prose exists before that heading, label `## Why` with the first heading and quote a passage under it. The empty label is honest only when a passage exists above the first heading. Quoting a paragraph under a heading while labelling the section `""` fails the nearest-heading check even though both halves are real.
