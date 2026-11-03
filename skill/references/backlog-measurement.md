# Measuring the backlog: what a reviewer will actually see

The campaign question is never "how many PNGs fail a check". It is "in the posts still waiting for review, which pictures are broken right now". Those are different numbers and only the second one is worth reporting.

## Walk the drafts, not the asset folder

A sweep of `tech_blog/assets/` counts **files that exist**, so it cannot see an embed pointing at a file that was never written, and it counts files that no live post embeds any more. Measure from the drafts instead:

1. Read `backlog/queue.json` and take every post whose `state` is not `done`.
2. For each, open the draft at the queue's `post` key (it is a vault-relative path such as `tech_blog/<slug>.md`).
3. Parse every `![alt](path)` from it.
4. Resolve each path relative to **`tech_blog/`**, not the vault root — the drafts write `assets/<date>/<name>.png`.
5. Run the mechanical checks (`check-grey-bars.py`, `check-palette-strip.py`) once per distinct file.
6. Report: live posts, distinct embedded images, failing images, and **unresolved embeds as their own line**.

`check-flat-bands.py` stays out of the report: it fires on cel-shaded art, including approved frames, so it is a prompt to look, never a count.

## A flagged image on a post that holds a card is not yet a defect

Before telling anyone a card carries a broken picture, compare the card's own items with the draft's embeds. Read the pending `request_item_verdicts` interaction and list `payload.items[].id`; the slot ids usually read `<slot>-r2`.

- Every embed covered by an item → the flagged files are exactly what the card replaces. They clear on approval; calling them a defect wastes the owner's attention.
- An embed with **no** matching item → that slot will still ship broken after the card is approved. Name the file and the slot to whoever holds the card.

Report both cases explicitly rather than lumping them into one number.

**This comparison is a script — run `backlog/audit/card-embed-coverage.py` instead of hand-writing it, before a card goes up and again on a hop that has nothing to fetch.** It walks every post whose queue state is `card` (add `--rendering` for the lane), resolves the draft's embeds, runs both edge checks, and asks whether that post's card carries an item naming the slot; it writes a table to `backlog/audit/<date>-card-embed-coverage.md` and prints the uncovered rows. A hand-written version of this check has been re-derived at least three times, and the run that skipped it put a card up carrying one of its draft's three broken embeds. Three details decide whether the output is right:

- **The card's items are at `payload.items` of its latest `request_item_verdicts` interaction**, each with `id`, `label`, `description` and `attachmentId`. `issue.items` on the issue object is `null` and `issue.attachments` is `null` too — a first run that read the issue object reported every card as empty. Attachments come from `GET /issues/<id>/attachments`, which also carries `originalFilename`, `byteSize` and `sha256`.
- **A post in flight carries its issue on `queue.json`'s `slot`, not in the `batch` list.** Reading only `batch` reports the busiest post as having no card at all and flags every embed on it — which is exactly the post you were checking.
- **A card with zero items is a card still being built, not a finding.** Report its embed list as the thing its own run needs, separately from the uncovered rows; and match items to embeds by token overlap between the item id and the filename, so treat a hit as a pointer and a miss as what gets looked at. A generic token (`header`, `enrich`) matches too eagerly, so drop only truly meaningless tokens (`r2`, `png`, the date segments) from the comparison — dropping the slot-ish ones makes a covered header slot read as uncovered.

## Run the same comparison on your own card, before the post is called covered

The cross-check above reads as a rule for someone else's card and it matters most on your own. A post's broken embeds and your card's items are two different sets, and only the intersection clears: building a card for the one slot a round was opened for — the dead embed, the slot a verdict rejected — leaves every other broken embed of that draft untouched, and approving the card reads to the owner as "this post is done".

So before the card goes up, resolve that post's embeds the way the walk above does and write down, per embed, which item replaces it. When the list is short:

- **Write the round-2 brief for the uncovered slots**, keeping the paths the draft already embeds, so the post needs no edit when the renders land.
- **Say it on the card, in one paragraph, before the verdict.** This card carries k of the post's n images; these embeds still fail the bar; they are not on this card and approving it cannot fix them. He rules on one picture per item and should not have to reconstruct the post's coverage from the queue.
- **Do not submit the replacements while another post holds the render slot.** A card waiting on a verdict does not hold the queue; the round-2 renders join it when `backlog.py next` names that post again.

## Two script checks passing is not a clean picture, and one flag is not its own cause

`check-grey-bars` and `check-palette-strip` count flat geometry — an edge band, a row of hue groups. They cannot see the two families that dominate this campaign's defects: **a pasted graphic**, and **lettering the render invented**.

Two sibling embeds of one draft settled it. One passed grey-bars and fired only the weak single-hue palette variant, and a 1:1 crop of its top band showed a UI icon pasted over the scene under a made-up brand word (`cloamflareTunnel`). Its neighbour passed grey-bars outright and was not a painting at all — three vertical columns, a clock on a flat yellow field, a column of distorted pseudo-text, a blue panel headed with two invented names.

So add one read to every embed the measurement is about to call clean: `crop-probe.py <png> --box 0,0,W,220` at 1:1 with no upscale, the same for the bottom band, and one read per crop. Two crops a file is the cost; the alternative is a report that counts a collage as clean.

**Read a flag as a measurement, not as a cause.** A palette-strip hit means "flat blocks of several hues in one row or column", which a `color_palette` swatch bar produces and a multi-column collage produces too — the two share a signature and nothing else, and only one of them is a prompt-palette defect. Crop the flagged edge and name the object before the note says *swatch*; and when the crop shows a collage, the finding is `pasted-overlay` plus `unreadable-text` and the slot needs a new prompt, not a palette deletion.

## A dead embed is a draft fact, not a render defect

When a draft embeds a path that does not resolve, no prompt can fix it: there is no asset to re-render. Hand it to the post's author as a child issue with the exact paths and a two-outcome ask — *the picture is meant to be there, I render it*, or *the embed is stale, the line comes out*.

Say whether the file ever existed, because it changes the work:

- **Never submitted.** An asset directory that has never existed plus zero jobs created on the night the draft was written (check the ideogram job database on the M1 Max) means the render step never ran. The slot notes in the child issue are then the brief, and the images are first renders, not re-renders.
- **Job exists, worker died.** Recover the prompt verbatim from the job database rather than writing a new one — but audit it against the acceptance bar before resubmitting (see `references/prompt-hygiene.md`, "A recovered prompt is an old prompt").

## Quote the live number, not the vault number

The whole-vault count can rise while the campaign improves, because every new approved render adds a file. It is also blind to dead embeds. When reporting progress, quote live posts / distinct embedded images / failing images, name the script and its output path so the next run can re-run it, and keep the earlier sweep number only as history.

## Keep the measurement runnable

Put the measuring script under `backlog/audit/` beside its outputs, with the vault path, queue path and check-script paths at the top. Write one `.md` table for humans and one `.jsonl` for machine comparison. A number nobody can re-derive is an assertion, not a finding — and the second run of the same script is how a stale claim gets caught.
