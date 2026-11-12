# Queue repairs: when the backlog runner's state is wrong

Use this when `backlog.py status` disagrees with the board, or when `next` refuses to hand out a post that plainly still needs a card. Every repair below is a `backlog.py` call, never a hand edit of `queue.json`.

## What `next` hands out, and what it silently skips

- **`todo` posts** become the slot (one at a time).
- **`ready` rounds** pop first, ahead of new posts.
- **`card` posts** are skipped while they are in the slot or in `batch`.
- **`rendering` posts are skipped forever.** Nothing in `next` ever returns a `rendering` post to the queue, so a post wrongly in that state quietly leaves the campaign: the runner can never reach `finished` while it sits there.

That last line is the reason most repairs exist. A post lands in `rendering` whenever a card closes with re-renders queued (the `--rendering` branch), and it only becomes `done` when some later run calls `card-done <n>` again.

## The repair table

| symptom | repair | what to check first |
| --- | --- | --- |
| Post `rendering`, its last card closed and its pictures were shipped | `card-done <n>` | The helper's third branch (`closed_without_slot`) closes it and touches neither the slot nor any other post. **Only** when the verdicts were applied — read the closing comment of the last card and confirm the assets, records and `verify-slot.py`. Never use it on a post whose pictures were never judged: it marks an unreviewed post `done`. |
| Post `rendering` with **no card issue, no `ready` round, no handoff brief** | `ready <n> 1 <briefs/<n>-<post>.md>` | Nothing can wake that post: the campaign or a sibling track closed its images on some other issue and the backlog card never existed. `ready` is the only path back into the card queue. Then `note <n>` what the brief cannot say — see "the brief may be stale" below. |
| Post `done` while a card issue is still open | `reopen-card <n> <GUL-id> <round>` | The batch entry or `ready` round is the source it rebuilds from; if both are gone it refuses, and the queue needs a rebuild report rather than a guess. |
| Slot names a post with `issue: null` | `opened <n> <ID>` if the issue exists on the board, else `release` | Look for the issue the failed run created. `release` hands a round-1 post back to `todo` and a later round back to `ready`; re-queueing by hand would open a second card. |
| `batch` carries an entry whose card is already `done` | `card-done <n>` | The batch branch drops the entry. Confirm the post's own state afterwards; a `done` post stays done. |

## The brief may be stale, and the card's run cannot tell

A brief is frozen at the moment it was written. When another track (a header campaign, a repair campaign) has since replaced one of the post's images and shipped it to the same path, the brief still names the old record and job. A card built from it will put an already-approved picture in front of the owner again, which is exactly the review we do not want to spend.

After any repair that queues a card, call `backlog.py note <n>` with the one thing the brief gets wrong: which slot is already approved and shipped, the job id that shipped, the superseded file name, and which slots are left to judge. The note outlives the repair and rides the queue document.

## Read the queue once per decision

Card runs close posts in parallel, so two reads seconds apart legitimately disagree — a post can flip `card` → `done` between them, and a slot claimed by one `next` looks like the holder to the next. Take the state you act on from a single fresh read, act, then re-read once to confirm. Do not report counts assembled from two reads as if they were one snapshot.

**`posts` in `queue.json` is a list, not a dictionary.** The top level carries `slot`, `batch`, `ready` and `posts`, and `posts` is an array of objects with `n`, `post`, `state`, `issues` and `notes` — so a lookup is `[p for p in q["posts"] if p["n"] == n][0]`, and `q["posts"].get(...)` dies with `'list' object has no attribute 'get'` mid-closeout. Only `slot`, `batch` and `ready` are keyed structures.

## Repair discipline

- One helper call per intent, in the order the description prescribes; a repair that touches the slot or another post's card is a different decision, not a cleanup.
- Say it in a `note` when the next run needs the context, and on the runner comment what you did and why — a repair with no note is invisible to the run that inherits it.
- Never release the runner and never hand-edit `queue.json`; the watchdog rebuilds the `queue` document from live state after the repair.
