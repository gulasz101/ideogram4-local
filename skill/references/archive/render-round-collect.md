# Collecting a render round

The wake that turns finished renders into a review card: who owns it, what the card may carry, what happens to a render nobody ships. `references/archive/review-loop.md` §4 holds the submit side and `references/archive/backlog-review.md` the queue rules; both are at the file cap, so the collect-side rules live here.

## One collector, and it is usually an issue that already exists

**When one slot's replacement is hours out and the rest of the round has passed, the render issue itself becomes the collector.** The passing slots go on a card from `ready <n> 1` plus `batch-open-ready 1` as usual, and the render issue stays `in_progress` under a monitor with nothing else on it: it already holds the thread, the assignment and the wake, so a second collector issue buys nothing. Create a separate collector issue only when the render issue has to go `done` for its own reasons (its card was answered and its round is over).

**Take the passing card through `batch-open-ready`, never `next`.** `next` hands the ready round the live slot, so the render issue's own card becomes the live one and the issue is no longer free to collect the absent slot; `batch-open-ready` opens the card as a batch entry and leaves the collector's monitor role whole. **When the create deduplicates to the render issue itself** (`deduplicated: true`, same title and parent), the card lives there and the issue description is NOT rewritten — it still holds the original brief, including any "do not render round 1" line. Put the current item table and the close branch in `detailsMarkdown` and one thread comment, record the render issue as the card with `opened <n> <id>`, and do not read the description as this round's brief.

Two lines make that role legible to every later reader, and both belong in the brief that becomes the passing card's description:

- `<render issue>` owns the absent slot and opens its card from the ready queue when the replacement lands;
- `card-done <n>` belongs to the card that answers the last slot, so the passing card's run must not release the post.

The wake that collects the last render writes the second brief, queues it as `ready <n> 2`, opens that card and closes the render issue in the same run.

**Arm a far-out replacement as hops, and put the real ETA in `notes`.** A monitor more than about two hours ahead is silently dropped, so a replacement four hours out gets a two-hour hop that reads the job, finds it still queued, re-arms and posts nothing. Size the next hop from the `eta_minutes` read in that same call, never from the time you stored.

## A mixed round collects in two phases, and a pending job's ETA is stale

**One worker, submit order: a slot's ideogram runs first and its flux twin waits behind it.** A round submitted as three slots × (ideogram + flux) is not six parallel renders. The first ideogram lands about 21 minutes in, and each flux companion starts only when the job ahead of it ends, then takes about 3 minutes. So the collect is two-phase — the ideograms at roughly 25 minutes, the flux twins after — and a monitor sized from the last-submitted job's ETA waits far longer than the round needs.

- **`eta_minutes` on a `pending` job is an estimate from submit time**, taken against the queue as it stood then. Three pending flux jobs reported 24, 27 and 30 minutes and all finished inside about ten, because the ideograms ahead of them were nearly done. Size the monitor from the **running** job's own ETA plus the turnover of the jobs before it, and re-poll instead of trusting a pending row.
- **`queue_ahead` is the honest signal for a pending job**, and it renumbers as jobs finish, so re-read it on every poll rather than reasoning from the count you saw at submit.
- **The timestamps in a job row are the Mac's local clock, not UTC.** `created_at` and `finished_at` come back on a CET (UTC+1) clock, so an ETA or a monitor time derived from them lands an hour out — and a monitor armed that far past the render sits idle while the PNG waits on the Max. Compute every `nextCheckAt` from your own UTC clock plus the `eta_minutes` you just read, and never from a timestamp string in the row.
- **Job state comes from `imagegen status <id>`.** `~/image-studio/jobs.db` is an empty stub on the Air — the worker keeps the real queue on the Max — so a query against that file answers `no such table` for a job that is running perfectly well.
- **Collect in the same wake as the re-poll.** Fetch and check every `done` job before ending, because a wake that only re-arms the monitor pays a whole wake for finished work — and a slot that fails its check in that pass can be resubmitted immediately, queueing behind the job still running instead of costing a round.

## A worker failure is not a prompt failure

**`sd-cli exited with code 1` on an ideogram is the worker dying mid-render, not a verdict on the prompt.** Resubmit the identical prompt file under the next attempt suffix — the attempt letters run `-r1b`, `-r1c`, `-r1d` (see `prompts/`) — instead of rewriting a prompt that never produced a pixel. A rewrite on a worker failure throws away a composition that has not been tested and changes the variable the next failure gets blamed on; the same job often passes unchanged on the retry, because the queue, not the prompt, was the fault.

Read `imagegen status <id>` and its `error` field before choosing the repair: a job that finished and failed a bar clause gets a rewritten prompt, while a `failed` job whose error is a process exit or an artifact-retrieval 502 gets the same prompt again. **The `-r1b`/`-r1c`/`-r1d` ladder is for worker failures only.** A bar failure gets one corrected re-render per round and then the slot waits (or the card ships without it); a second corrected attempt on the same clause is not a cleaner test of it, it only spends queue time behind every sibling run's renders.

## What the card actually carries

**A brief's item table is the slot list for that card, not a promise about how many rows the card carries.** The card's own run re-reads every PNG and may hold back an item the brief listed as passing — a four-item brief became a two-item card, the card run's pixel-exact crops overruling the collector's full-frame pass on two renders. Verify the card's items against its attachments and its holds against its own `detailsMarkdown`; do not re-post the card, do not call the brief wrong, and let the held-back replacements ride the next round. The row count is the card run's call.

**A held-back item's replacement can land after its slot was approved by the other engine, and then nothing collects it and nothing should.** Its slot is approved, so it is a spare attempt, not a lost render: `backlog.py note <n>` its job id and `eta_minutes` with the words "spare, stays uncollected unless he rejects the approved picture", because the next run that sees a finished job with no record and no card otherwise reads it as a render somebody dropped.

**The brief's sha256 must be in the file before the card is created, because the harness claims the new card before you can patch it.** Once the POST returns, the harness sets `checkoutRunId` within seconds, and a PATCH to the description after that answers 409 Conflict. So compute the sha256 of every staging PNG (`shasum -a 256`) and write it into the brief's check notes before calling `backlog.py ready` and the POST. A brief that carries only paths and byte sizes forces the next run to re-hash the file, which works but loses the audit trail's hash proof. Do not plan to "add it later".

**What the brief's hash is for: the card run re-measures every staging file against it before uploading.** `upload-attachments.py` prints `sha_match`, but that compares the upload to the file on disk, so it clears an overwritten or re-rendered staging path just as happily as the render the brief checked, and the card then shows a picture nobody read. Run `stat -f%z` and `shasum -a 256` over the brief's list first and stop the build on any size or hash difference: either a later attempt replaced that path (find it and its own check note) or the number in the brief is the stale half, and each is a comment rather than a card.

## A round whose only remaining slot has no passing render opens no card

A post can reach its card with nothing showable on it: the one unsettled slot is a draft image that fails the show bar — invented lettering on a screen, a pasted panel, a cast that is not this blog's — so the replacement render *is* the round, and the card waits for pixels.

- Keep the card issue `in_progress` under a real monitor, and open no verdict card: a zero-item card is not a card, and asking for a verdict on the broken draft image is the habit the show bar retired.
- Hold the queue slot on that post and say so in a `backlog.py note`. The queue's next post waits behind it, and that is correct: releasing the slot only hands the post back to a runner that would meet the same broken slot.
- **Contrast with a post whose only image is a settled one** (a header already approved on the campaign card): nothing is pending there, so that run posts a closing comment, `card-done <n>` and Advances. Same zero items, opposite disposition — the difference is whether a render is owed.

**In an engine failure band, hop an hour or more, not ten minutes.** A submit is traffic on the account whether or not it renders, and the refill that ends an artifact-retrieval band needs quiet: the proxy's own measurements put recovery after roughly two hours with no requests at all. One submit per hop, 45–90 minutes apart, learns as much as five hops at ten-minute spacing and leaves the allowance a chance to come back. Say in the comment that the gap is deliberate, so the next run does not read it as idleness and shorten it.

## Verify the previous card's closeout instead of trusting its comment

A collect wake that follows an answered card should re-check the durable artifacts, because the card's run can be correct in the thread and short in the vault:

- the staged PNG and the vault copy hash equal (`shasum -a 256` both);
- each embed the card claims is in the post with a new alt text, and the untouched slot still points at its old file;
- a record exists for every render of the slot, approved and held back, with the verdict and its row;
- every earlier record of the slot carries the approved job id in `superseded_by`.

**An earlier record that reads `verdict: "unreviewed"` beside a set `superseded_by` is correct, not a half-finished edit.** When no card ever showed the leaf image, the library's statement that nobody judged it is the truth; `references/library-records.md` says why the tidy-up is forbidden. Say in the closing comment that it is deliberate.
