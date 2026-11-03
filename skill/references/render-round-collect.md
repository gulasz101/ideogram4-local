# Collecting a render round

The wake that turns finished renders into a review card: who owns it, what the card may carry, what happens to a render nobody ships. `references/review-loop.md` §4 holds the submit side and `references/backlog-review.md` the queue rules; both are at the file cap, so the collect-side rules live here.

## One collector, and it is usually an issue that already exists

**When one slot's replacement is hours out and the rest of the round has passed, the render issue itself becomes the collector.** The passing slots go on a card from `ready <n> 1` plus `batch-open-ready 1` as usual, and the render issue stays `in_progress` under a monitor with nothing else on it: it already holds the thread, the assignment and the wake, so a second collector issue buys nothing. Create a separate collector issue only when the render issue has to go `done` for its own reasons (its card was answered and its round is over).

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

## What the card actually carries

**A brief's item table is the slot list for that card, not a promise about how many rows the card carries.** The card's own run re-reads every PNG and may hold back an item the brief listed as passing — a four-item brief became a two-item card, the card run's pixel-exact crops overruling the collector's full-frame pass on two renders. Verify the card's items against its attachments and its holds against its own `detailsMarkdown`; do not re-post the card, do not call the brief wrong, and let the held-back replacements ride the next round. The row count is the card run's call.

**A held-back item's replacement can land after its slot was approved by the other engine, and then nothing collects it and nothing should.** Its slot is approved, so it is a spare attempt, not a lost render: `backlog.py note <n>` its job id and `eta_minutes` with the words "spare, stays uncollected unless he rejects the approved picture", because the next run that sees a finished job with no record and no card otherwise reads it as a render somebody dropped.

## Verify the previous card's closeout instead of trusting its comment

A collect wake that follows an answered card should re-check the durable artifacts, because the card's run can be correct in the thread and short in the vault:

- the staged PNG and the vault copy hash equal (`shasum -a 256` both);
- each embed the card claims is in the post with a new alt text, and the untouched slot still points at its old file;
- a record exists for every render of the slot, approved and held back, with the verdict and its row;
- every earlier record of the slot carries the approved job id in `superseded_by`.

**An earlier record that reads `verdict: "unreviewed"` beside a set `superseded_by` is correct, not a half-finished edit.** When no card ever showed the leaf image, the library's statement that nobody judged it is the truth; `references/library-records.md` says why the tidy-up is forbidden. Say in the closing comment that it is deliberate.
