# Churn on a backlog card: a stale brief, a withdrawn card, and a user comment as a blanket reject

Read this when a card you posted is gone, when a user comments on an open card, or when a brief and the post embed disagree.

Two failures cost a round on a backlog post and neither is an image defect. Both come from the gap between the card's brief and what other runs did to the vault in the same day. Read this before you build a card, and again when a card you posted is gone.

## 1. The brief can be stale against the post embed

A brief names the record and job that were current when the runner built it. A parallel campaign (a re-render batch, an engine switch, a vault audit) can replace that picture the same morning.

- **Before you write the card, read the post's embed and the record's `superseded_by`.** If the record carries a `superseded_by` and the file beside the embed is `<slot>.superseded-<old job>.png`, the picture in the post is a newer render with its own record.
- **Put the file the post actually embeds on the card**, with the newer record and job id, and name the supersession in the item description and the details table. Do not review a picture that is no longer in the post, and do not put the old file on the card as if it were current.
- Keep the item id the brief gave. The brief is authoritative for item ids, not for which job the slot currently holds.

## 2. A withdrawn card is not an approval, and a rebuilt card is not owed

A parallel run can withdraw a card you posted (fails its bar, wrong attachments, superseded by its own campaign). The owner then writes something like "there is no card i can approve all images here, or consider all images approved and just continue".

- **His sentence is the approval.** The review card is the mechanism that carries his verdict, not the source of his authority over his own blog. A cancelled or withdrawn interaction is not an approval either way: it proves no verdict was given.
- **Do not rebuild the card and do not re-render to a bar before he has something to look at.** Rebuilding re-poses pictures the campaign already condemned and asks him for a click he just said he does not want.
- **Write the approval into each existing image's record** (the brief's record, `superseded_by: null`), per `library-records.md`:
  - `verdict: "approved"`;
  - one verdict row whose reason carries his instruction as a short quote, names the defect that caused the withdrawal, and says plainly that no card was approved;
  - delete the `Back-filled from jobs.db; not reviewed yet.` line, change nothing else.
- **Leave an already-approved record alone.** A re-confirmed slot does not need a second row; say in the closing comment that it still stands.
- **Keep the staged replacements on disk and say so.** The prompts stay where they are and the queue note records that they were never submitted. The post ships with what he approved unless he asks for the clean versions; promising them without a verdict would replace an approved picture on your own read.

## 3. A user comment as a blanket reject (not an approval)

The legend on every round-1 card asks Wojtek not to comment while the card is open, but he sometimes does — and a comment on an `in_review` card is a wake, not a verdict submission. When the comment is a blanket rejection ("all images broken because of X, regenerate"), treat it as reject-all for the named reason rather than waiting for the card:

- **Withdraw the pending card** with `POST .../interactions/<id>/withdraw` and a reason naming the comment and the defect. Withdrawal is allowed for the card's creator; it settles the card as `cancelled` and leaves no pending interaction, which is what lets the issue move to `in_progress` with a render monitor. Do not submit or simulate verdicts on the card — the comment is the direction, the withdrawal just clears the mechanism.
- **Mark every affected record rejected** with the reason (`verdict: "rejected"`, one verdict row, delete the back-fill marker), per `library-records.md`. The reason is his words distilled to one clause, not a paraphrase of the whole comment.
- **Re-render per the reject column**: start from the record's `## Prompt`, revise from the reason plus the series style (lint risk 0, `engine-pitfalls.md`), submit with `--name <item id>-r<k+1>`, save the prompt as `~/image-studio/backlog/prompts/<item id>-r<k+1>.json`. A second attempt inside the round keeps the item id and rides the attempt suffix on the render name only (`-r2b`, prompt `<item>-r2b.json`).
- **Schedule the monitor** at the last job's ETA plus 5 minutes, set the issue `in_progress`, then `backlog.py card-done <n> --rendering` and Advance. Advance usually answers `wait` while renders run.
- **Record the verdict in an issue comment** with the job ids, prompt paths and check notes, so the thread carries what the withdrawn card no longer does.

A comment that is a question, a clarification, or a single-image nitpick is not a blanket reject — answer it on the issue and leave the card pending.

## 4. Closing order (one run, one pass)

1. `paperclip-write.py comment --issue <id> --body-file <path>`: what you recorded, the honest trade, and no lecture. If the card vanished under him, one short sentence owning the churn.
2. `paperclip-write.py patch --issue <id> --json-file <file>` with `{"status": "done"}`. A cancelled card leaves no pending interaction, so `done` passes the disposition guard; `in_review` would have no review path.
3. `backlog.py note <n> "<what happened and who decided>"` so the next run does not resurrect the card.
4. `backlog.py card-done <n>`: on a post already in `rendering` state with the slot moved on, it takes the `closed_without_slot` branch and marks the post done.
5. `backlog.py next` then create the next card and `backlog.py opened <n> <GUL-id>`. A `next` call claims the slot itself (`issue: null`), so a slot with no issue recorded is yours to fill, not a stuck slot.

## 4b. A repair round's card opens with the queue untouched

After a repair round (drafts held back, rebuild submitted, `card-done <n> --rendering`) the post reads `rendering` in `queue.json` with **no** `slot` and **no** `batch` entry, and the live slot belongs to a different post. No `backlog.py` command expresses "card open, no slot held": `next` claims another post's card, `card-done` moves this post out of `rendering`, and hand-editing `queue.json` is off the table.

- Build the verdict card on the post's **own** issue — uploads, `build-verdict-card.py`, `post-interaction.py` — and leave the queue alone. Confirm first by reading `q["slot"]` and `q["batch"]`: if neither names the post, the card is not tracked and must not be forced into the slot.
- Set the issue `in_review` with the pending `request_item_verdicts` as the wait path, and do **not** pass `reviewInteractionId` for a verdicts card (it answers 422 `invalid_review_interaction`).
- Record the card id, the interaction id and the job ids with `backlog.py note <n>`, and say in the comment that the post sits in `rendering` with its card on that issue — otherwise the next wake re-derives all of it or assumes the card was never opened.

## 5. Verify before you report

- `grep '^verdict:'` on each record, and the verdicts row, since the table row is what a later audit reads.
- `GET /issues/<id>` echoes the new status; the PATCH response alone is the write, not the proof he can see it.
- `backlog.py status`: the post reads `done`, the slot names the next post and its issue.
