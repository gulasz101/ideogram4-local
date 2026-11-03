# The backlog runner's daily watchdog

The runner issue never holds a card. It wakes on a daily 07:00 UTC monitor, and that wake is the only thing that keeps a stalled backlog moving. This file is the order of that tick and the stall taxonomy it exists to catch.

## The tick, in order

1. `date -u` and `~/image-studio/backlog/backlog.py status`. `/next` says `wait` whenever the slot is held — that is the normal answer, not an error. Redirect `status` to a file instead of piping it through `head`/`tail`: the table is long enough to break the pipe, `BrokenPipeError` aborts the print mid-file, and the exit code you read back belongs to the pipe, so a working read looks like a failed command.
2. Rebuild the `queue` document with `scripts/put-queue-doc.py --issue-id <runner> --run-id <this run>`. The runner wake holds the checkout, so the PUT lands; a card run cannot do it. **Read the stored revision first and skip the PUT when it already matches live state** — its snapshot line carries the counts and the slot, so a document whose counts equal `backlog.py status` and whose live-slot line names the same card was rebuilt minutes ago (another runner run, a closeout). Writing again is revision churn on a table he scrolls: say in the comment which revision you found current instead of minting a new one.
3. Run `scripts/scan-cards.py --runner-id <runner>` and read only the non-`ok` rows. It reads the runs and interactions of every card, so on a board with 120+ cards it runs for several minutes: wrap it as `timeout 560 python3 <scan> --runner-id <runner>` and give the `terminal` call a timeout above that, or the call dies at the default and a working scan reads as a broken script. Its last two lines are the ones to keep — the flag count, and whether every claimed round names its card issue.
4. Investigate the live slot only when it is over the 24-hour line.
5. Comment once: counts, doc revision, slot age and holder state, what you touched and what you deliberately left alone.
6. Re-arm the monitor for +24h with the **minimal** body — a fired monitor's attempt budget is spent, so a body carrying `maxAttempts`/`timeoutAt` answers `Monitor bounds are already exhausted` and arms nothing. Schema: `references/paperclip-api.md`. **Read `monitorNextCheckAt` before you write it.** A wake can arrive as `issue_assigned` or as a repair wake hours off the daily hour, and such a runner already carries a monitor aimed at the next 07:00 UTC: re-arming it is a needless write that can only lose the field. Leave it, and say in the comment that the watchdog was still armed.
7. End without a release. The runner must stay `in_progress`, assigned to you, no user assignee, or the watchdog can never fire again.

## An empty slot is a close that never advanced

`backlog.py status` showing `"slot": null` with posts still in `todo` is not a resting state: the last card ran `card-done` and never picked the next post, and nothing else will. The watchdog is the only actor that advances the queue between cards, so this wake opens the card itself — **unless the next post's renders are still in flight**, in which case the tick must not touch the slot at all (see below):

1. `backlog.py next` — it returns `create` and **claims the slot as a side effect**, so the queue reads `issue: null` for that post from this instant.
2. Create the issue from `.brief`: parent the runner, project, assignee you, `status: todo`, description read out of the file, and compare the created description's length against the file's byte count.
3. `backlog.py opened <n> <ID>`.

Never end a run between steps 1 and 3. A half-finished Advance leaves a slot held with no issue recorded, which next morning's tick reads as a dead claim and repairs by releasing — handing the post back out and risking a second card. If the create cannot land, `backlog.py release` first.

Say the hole out loud in the comment: a slot that sat empty overnight is information about the closes, not a routine number, and the tick that fills it is doing the work this wake exists for.

### Unless the next post's renders are in flight

`next` claims the slot, so on a post whose round-1 renders are still landing it opens a card on the **broken originals** the round exists to replace, and the card's run has nothing honest to put in front of the human. Before any Advance on an empty slot:

- read that post's newest `notes` entry — it names the render jobs, the round cap and who owns the collect;
- read `imagegen status <job>` for each one; never trust the ETA written in the note, ideogram ETAs freeze;
- find the collect owner (normally the repair campaign, not the runner) and read its `monitorNextCheckAt`.

If any render is still out: leave the slot free — no `next`, no release, no placeholder card — and arm a **short hop**, 30–60 minutes past the collect owner's monitor, instead of the daily beat. That wake lands after the collect, finds the card already open and healthy, and re-arms the daily beat. Name the jobs that were out and when the collect owner wakes, so the next tick does not read the free slot as a miss.

If the renders are done and no collect owner is alive, the slot has no way to fill itself: that is a stall even though every issue looks healthy. Collect the renders or fix the owner's monitor, and say which one you did.

**A finished render on a post that holds no slot belongs to the same owner.** A post can read `rendering` in `queue.json` while its newest job already reads `done` and its `issues` list names only a closed card: the round was submitted by a card that then closed after shipping its approved images, and the collect that opens the next card has not run yet. Read the campaign issue's `monitorNextCheckAt` before doing anything — when that wake is minutes away, report the post, the job id, the job's `status` and the owner's next check, and fetch nothing. The campaign's collect opens the card with hash-matched attachments and records it with `opened <n> <ID>`, so fetching it yourself here opens a second card for a post that already has a round in the vault, or leaves a checked render with nowhere to go. Only when no owner is alive is this a stall you repair.

## The slot is over 24 hours: three shapes, one repair

Look at the **holder issue**, never the age alone.

| holder | what it means | action |
| --- | --- | --- |
| `in_review` with a **pending** verdict card | waiting on the human. Nothing is broken | Report the age and the card id. Open no second card; new posts stay blocked until he answers, and that is the rule working, not a fault |
| `in_progress` with a **monitor armed** and renders in flight | the shared render queue is deep, so the renders are hours away | Report the job ids and the next check time. Do **not** re-render and do **not** release the slot — a duplicate render costs the whole wait again |
| recorded but `not in_review` and no pending card and no monitor | the run died mid-card | Fix it from the runner: fetch/patch its images or re-render, then advance the queue |
| slot held with **no issue recorded** | a run died between claiming the slot and creating the card | `backlog.py release` (guarded), then Advance |

Say in the comment which shape you found. "Checked the holder: pending card, waiting on you" is the honest answer, and it is different from "nothing to do".

**The middle row is the one a card run has to be told about, so the card run announces itself.** A card that holds the live slot while its renders sit behind a deep queue looks, from the runner, exactly like a dead run: recorded, not `in_review`, no verdict card. Before ending such a run, post one comment on the runner naming the slot, the job ids, the ETA and the monitor time, and say plainly that the slot is held on purpose and must not be released or re-rendered. Otherwise the next watchdog tick repairs a post that is working.

## The `ready` queue is a staging list, not a claim order

`ready` means "somebody wrote a round brief", not "this round is cardable". Two things can make an entry un-claimable, and neither `backlog.py next` nor `batch-open-ready` can see either one:

- **Another issue owns the collection.** A round's brief can say the card is opened by a collector issue that waits for the renders itself ("the collection is owned by GUL-x, which opens this card once both PNGs are fetched and checked"). Claiming it then takes the job from the run that owns it and opens a card ahead of its images.
- **Its renders are still `pending`.** `backlog.py ready` is called by the run that wrote the brief, which happens when the round is *planned*, not when the PNGs exist. A render can be hours out — the shared queue is deep — and a card opened now has empty image rows on it. A planning brief announces itself in its own first lines ("round 1 submitted, six renders in flight, the card brief comes after the collect", "this ready entry is a PLACEHOLDER, no sibling run may claim it before the collect"), and that sentence settles the question before any job id is read: a plan brief's table carries job ids and ETAs, a showing brief's table carries staging paths, byte sizes and hashes.

So before any `batch-open-ready`, read the head of the brief and check every job id in it:

```bash
head -12 ~/image-studio/backlog/handoffs/<nnn>-round-<k>.md          # owner clause, if any
imagegen status <job> | jq -r '.status, .queue_ahead, .eta_minutes'  # one line per job in the brief
```

Leave the entry in `ready` when either check fails, and name it in the watchdog comment with its owner and the render ETAs. "One round is ready and I did not claim it, because its brief hands the collection to X and both its renders are still pending" is the honest report; claiming it to look busy is the failure.

## Advance can consume a plan brief and put it on the live slot

Leaving a plan brief in `ready` is right, but it does not guarantee it stays out of play: when a card closes, Advance pops the queue and can claim that very round, so the new card issue's description is the **plan** — "six renders in flight, the card brief comes after the collect" — and its own run wakes to a brief that tells it to show images that do not exist yet. From the runner the advance looks healthy; the defect is one level down, on the card.

The repair is not to release the slot and not to edit the card's work: the renders are minutes away and the collector run is usually already armed. Post one comment on the card and let its own run finish:

- the job ids with their state at that minute, and the last `eta_minutes`;
- **no verdict card until every PNG it shows is fetched and checked** — an item row pointing at nothing is the one card that must never reach him;
- which issue owns the collect and its monitor time;
- that the description has to be replaced with the real brief, byte for byte, once it exists (`PATCH /issues/{id}` with `description` read out of the file), because a card whose description is a plan is a card whose next run cannot tell what it is reviewing.

Then say on the runner what you found and what you deliberately left alone, so the next tick does not read the plan-shaped card as a stall and rebuild a round that is already running.

## A batch entry that names no card is a claimed round whose create never landed

`batch-open` / `batch-open-ready` write the claim first and the card issue is created by a run afterwards. When that create fails or the run dies between the two, `q["batch"]` carries `{"n": …, "round": …, "brief": …, "issue": null, "since": …}` while the post sits in `card`: the round is claimed, nothing is in front of the human, and no monitor can ever wake it because there is no issue to wake. The scan's closing line ("batch entries: every claimed round names its card issue") is the check that catches it.

Tell the two variants apart before creating anything, because one of them already has a card:

- **the post's `issues` list already names a card for that round.** The create landed and only the recording was skipped. Confirm the card really holds that round, then `backlog.py batch-opened <n> <ID>` to fill the entry, and `card-done <n>` only if the card has already closed.
- **no issue for that post and round exists in the company list.** The card was never created. Create it from the round's brief.

Repair, and each step is a guard rather than a formality:

1. Read the brief end to end. A round that has been waiting hours may have been written while a render was still out.
2. Check every staging PNG the brief's table names against the bytes it recorded — `stat -f%z` for size, `shasum -a 256` for the hash. A repaired card is the round's first impression; a missing or mismatched file would put an empty or wrong row in front of the human.
3. Create the issue from the brief with the description read out of the file, then compare the created description against it (`len(created) == brief bytes`). The brief is the card, so a truncated tail changes what gets reviewed.
4. `backlog.py batch-opened <n> <ID>`. The entry keeps its original `since`, so the age stays honest.

Never hand-edit `queue.json`, never release the slot for this, and never re-render: the renders exist, the work is the missing card.

## A cancelled card is retired, and never automatically replaced

A card issue can land `cancelled` — its run withdrew it, the board superseded it, or another campaign retired it — and its verdict card settles as `cancelled` too, so the images were **never judged**. The post is then stuck: `rendering` or `card` with a card the heartbeat can never wake.

Before opening a replacement card, find out whether another live issue already owns the work. A repair campaign, a Florian concept issue, or a successor card in flight means the regeneration belongs there, and a fresh card from the runner collides with it and duplicates the render. Check the company issue list for a successor with the same post number, and read the cancelled card's own last comment — a run that retired it usually said who replaces it.

Only when nothing owns it does the runner rebuild: `backlog.py ready`/`batch-open-ready` for a fetched round, or a new round-1 card when the images themselves are broken at prompt level.

## Stall shapes the scan already knows, and the false positives it must not report

Real stalls: an answered verdict card with **no live run and no monitor** (the approvals exist nowhere but Paperclip); a `blocked` card with an empty `blockedBy` (its monitor is dead); a handoff brief whose staging paths are still `<token>` placeholders (the round was never queued).

Not stalls, and reporting them buries the real ones:

- a card on a scheduled monitor — the monitor *is* its live mechanism;
- a card whose verdict card is `pending` — that is the designed resting state, waiting on the human;
- a `todo` card with a live run — that run is what opens it, and a batch of fresh cards looks like this;
- an answered card with a live run — that run is applying the verdicts;
- a card whose renders are queued behind a deep shared queue — the wait is the renderer's, not the card's;
- a `cancelled` card — retired, its work moved elsewhere (see above);
- a **pending** verdict card on an `in_progress` issue — status convention drift, not a stall: the card is answerable where it stands. Leave it to its own run when a monitor is armed, and say in the comment that its wake is what will move it.

When a flag fires on something that is working, fix `scripts/scan-cards.py` in the same run and say so in the comment. A scanner that cries wolf gets skipped, and the stale-approval case it exists for then runs for days.

## The card's render-collect hop is not the watchdog

A card whose renders are queued behind a deep shared queue wakes itself on a short monitor, and that hop is a different mechanism from this watchdog with a different discipline:

- **About two hours per hop, and every hop is a fresh run with none of the last one's context.** A long `nextCheckAt` is dropped silently, so a collect that is ten hours out needs five or six hops, not one. Put the whole next step in the monitor `notes` — the job ids, then fetch → self-check on crops → brief → `ready <n> <k> <brief>` → comment → `done` → Advance — so a hop that loses the thread can still finish the round.
- **`queue_ahead` is the pacing number; `eta_minutes` is only a snapshot.** Both move as other runs submit and clear: the same batch read 65, then 40, then 17 jobs ahead across one night at two to six jobs an hour. Read `queue_ahead` on every hop and let it decide whether the next hop is worth two hours or should wait.
- **A batch of six can land spread over ninety minutes.** Fetch and check each job as it reports `done` rather than waiting for the last one, and never re-submit a job whose `status` already reads `done` because the summary said it was still pending.
- **Do not post the card mid-round to look productive.** A card missing a slot is a card for a round that is not finished, so the round waits for the held-back attempt and goes up once, with every slot.
- **A wake another run armed is yours to correct when it fires before its own renders exist.** A sibling run's collect set for a time when three of its four jobs were still queued spends an attempt on an empty lane and re-arms from nothing; the same batch read 2–5 jobs from the front on the next hop, so the correct arm was over an hour later than the one that was written. The monitor PATCH is not gated by run ownership — the issue is assigned to this agent, so `PATCH /issues/<id>` with `{"executionPolicy":{"monitor":{...}}}` answers `200` from any of your runs — so read the last job's `eta_minutes` again and move the wake past it. Keep the job ids in the note (500-character cap) so the collecting run has the list without the old context, and say in the comment that you moved another run's wake and why: two runs correcting one wake costs a call, while two runs collecting the same batch builds the same card twice.

## Reading the board without tripping the runtime

- **Keep large API dumps out of `python3 -c` one-liners.** A command that references a big response file (a full `?limit=500` issue list) is refused before it runs, on the grounds that the referenced file cannot be scanned. Put the fetch, the filter and the print into one small script under the profile scratch dir and run that: it stays inspectable, and it survives the retry.
- **The company issue list does not filter by identifier.** Pull it once with a large limit, match client-side, and cache an identifier→id map to a scratch file so the reads and writes that follow are a single lookup each.

## A card another run opened: verify, do not edit

A collect can open the post's card between your reads, so an empty slot at the top of the tick is often a card by the time you comment. Check three things, cheapest first:

1. the issue is `in_review` with `monitorNextCheckAt` null — the card's own run finished;
2. `/interactions` carries exactly one **pending** `request_item_verdicts` with the expected item count;
3. `/attachments` count and each `byteSize` match the brief's table — byte sizes settle identity without hashing anything twice.

If the description is shorter than the brief file on disk afterwards (the collect rewrote a fuller brief a minute after the create), **do not edit the card**: it is another run's work, the verdict card already carries every item, and the gap costs nothing. Name it in one line in the comment and move on.

**A post can read `done` while a card for one of its slots is still live.** The post's queue state tracks its own rounds, and a repair campaign can lift a single slot onto a card of its own afterwards, closed outside the runner: post `done`, its header card `in_review` with two items. Both readings are correct. Report the row — post, card, item count, and what the post's note says happens when it answers — and touch neither: opening a card for that post duplicates the campaign's work, and closing the campaign's card settles a verdict that is not yours.

## Watchdog comment shape

The comment is the audit trail for a wake nobody watched happen. Four blocks, no narrative:

- counts (`backlog.py status` numbers, not your own recount) and the queue-document revision;
- the slot: post, round, card, age, holder state, and the verdict card id when it is a human wait;
- the scan line (`0 flagged out of N`) plus any card whose monitor fires later today;
- what changed since the last tick, and what you deliberately did not touch — a parked post with its owner named is information; a silent parked post reads as a miss.

Name the card that closed a post out of `queue.json`'s `issues` list for that post, not out of the card you happened to be reading. A post takes a card per round, so the closing card is often not the slot card the last tick saw, and a comment that credits the wrong one is a wrong fact in the audit trail nobody will re-derive.
