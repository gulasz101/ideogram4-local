# Advance: what `backlog.py next` hands you and how to act on each shape

The full Advance procedure lives in `references/backlog-review.md` (*Advance*). This file carries the rules that have to land somewhere the two workhorse references cannot take new text: `SKILL.md` and `references/backlog-review.md` are both past the 100,000-character cap, so `skill_manage` refuses a patch to either and rolls the whole batch back. Read this beside them.

## A card run must not touch the runner, whatever the other reference says

**The runner's own description outranks `references/backlog-review.md` here.** That reference tells a card run to claim the runner, PUT its `queue` document and then release it with a repair. On GUL-64 the description forbids all three from a card issue: "Never release this issue, from any run", and "Card runs don't touch the runner." The description wins, because the release it forbids is the failure that orphans the runner: a release on an `in_progress` issue clears the assignee and sets it to `todo`, Paperclip hands the orphan to another agent, the next checkout is refused, and the daily watchdog stops firing because it only fires on an `in_progress` issue assigned to the agent.

**On a card run: do not check out the runner, do not PUT its `queue` document, do not release it.** Advance and `card-done` are the queue writes a card owns; the document is a derived view and the runner's own wake rebuilds it. If the queue changed in a way worth noting, post a short comment on the runner instead.

**If you have already released it** (this happened on 2026-11-04 from post 093's card): repair in the same run and verify by reading the issue back — `PATCH /api/issues/<runnerId>` with `{"status": "in_progress", "assigneeAgentId": "<your id>"}`. A monitor whose time has not yet come usually survives the release, so a plain PATCH is enough; check `monitorNextCheckAt` on the read-back and re-arm only if it came back null. Say plainly in a comment on the runner that the release was yours and that the state is restored, because the runner's history is the only place the next watchdog can learn the assignee was ever cleared.

## The create route, and what a `201` proves

`POST /api/companies/<CID>/issues` with `title`, `description`, `projectId`, `assigneeAgentId`, `status: "todo"` and an `idempotencyKey`. `POST /api/issues` answers `{"error":"API route not found"}`, which reads like a broken board rather than a wrong path.

A `201` is not proof of a faithful card. Read the issue back and compare `description` with the brief by equality, not by eye: a truncated tail silently changes what the next run reviews. Take `identifier` out of the create response for `backlog.py opened <n> <ID>` — the queue records the identifier, never the uuid.

## A brief that is a render plan, not a round of checked renders

`next` returns `create` for a `ready` round, and that round's brief may have been written by a run that queued the work without ever submitting it. Its tells: it names the slots, the beats and the prompt files to write, and carries no staging path, no job id and no check note. Nothing has been rendered.

Create the card anyway — the queue needs the slot recorded and the description is frozen at the POST — and put the correction in the creation comment, because the brief cannot be edited afterwards:

- the brief is a plan, not a checked round;
- the card's own run starts at the render step: write the prompt pairs it names, lint them, run `check-bboxes.py`, submit, arm the monitor;
- at the collect wake it fetches and checks the PNGs, holds back what fails, and only then writes the round's brief with real staging paths, byte sizes, sha256 values and check notes and queues the showing card.

Without that comment the next run reads a brief whose prompt files do not exist, and it fails one of two ways: a verdict card with no attachment behind it, or a stall waiting on renders nobody submitted. Mirror it into the queue with `backlog.py note <n>` so the runner's table carries the state, and say in the closing comment of the card you advanced from that the next round starts with a render.

## `next` is a write, so never call it to read the queue

`backlog.py next` claims the slot: it takes the next post, sets it to `card` and installs the slot. A call made only to see what is coming next therefore leaves the slot held with `issue: null`, which reads as a card that was never created and is repaired by the watchdog only after its 24-hour window. Read live state from `queue.json` instead — `slot`, `batch`, `ready`, and the post's own `state` and `issues` — and call `next` exactly once per card, from the run that is genuinely advancing.

When a run has claimed a slot it does not intend to fill, hand it back at once with `backlog.py release`, then confirm `slot: null` and that the post returned to `todo` with no issue. Say in the closing comment that the claim was made and released: the queue note written minutes earlier can name a live slot that no longer exists.

**A second `next` in the same run is the way this bites, and releasing is the wrong repair.** The first call printed `create` and claimed the slot; a script that calls `next` again to decide what to do gets `wait` with `issue: null` — a body that carries only a reason, no title and no brief, so the card cannot be built from it. Do not release: the post is already yours. Take `slot.n` and `slot.brief` out of `queue.json`, build the card from that brief file, POST it, and record it with `backlog.py opened <n> <ID>`. Capture the `create` JSON once and pass it into the creator instead of re-deriving it.

## After the create

`backlog.py opened <n> <ID>`, then re-read the slot: it must name the issue, the post must read `card`, and `q["ready"]` must no longer hold that round (popping it is `next`'s job, and a copy left behind becomes a second card for one round).

If you also refreshed the runner's `queue` document, the release that follows must leave the watchdog alive: `release`, then a plain PATCH of `status: in_progress` and `assigneeAgentId`, then read back all four fields — `status`, `assigneeAgentId` set with `assigneeUserId` null, non-null `monitorNextCheckAt`, and `checkoutRunId` null. A re-arm PATCH re-acquires the checkout, so arm the monitor only when the release actually cleared it.

## An empty slot is not an invitation to card

The watchdog sees `slot: null` and the instinct is to call `next` at once. Decide first: card a post only when it is cardable *right now* — every image either sits in the vault as the draft embeds it, or is a fetched, checked render whose handoff brief is written. `next` claims the slot as a side effect of the read, so a claim made before that check has to be handed back with `release` in the same wake, which reads as churn.

**Renders in flight → the slot stays free.** The post's last queue note says `SUBMITTED <time>` with job ids and an ETA, and `imagegen status` still answers `running` or `pending`. Carding it puts the pictures the round exists to replace in front of Wojtek, which is the one thing a review card must never do. This is a different case from the render-plan brief above: there, nothing was rendered and the card is created with a correction comment; here, renders exist and are landing, so no card at all.

Also leave the slot free when the brief is a submit-time placeholder — a plan with no item ids, no staging paths and no check notes — and when a sibling issue's monitor owns the collect.

What the watchdog still does in that wake: rebuild the `queue` document from live state, run the card scan, confirm the runner is `in_progress`, assigned to you, no user assignee. Then arm the monitor for a **short hop past the collect** (roughly 40 minutes after the sibling's monitor time), not the next daily tick — a 24-hour re-arm leaves the queue idle for a day when the blocker clears within the hour. Say in the comment which post was left free, what its job states were, and which issue owns the collect; an empty slot with no explanation reads as a broken runner.

Never advance past an uncarded post to find one that is cardable. The queue's order is the review's order.

## `card-done`: pick the flag from the renders, and read the branch before you report it

`backlog.py card-done <n>` has one flag and three branches, and the flag follows the renders, not the card's type:

- **`--rendering` if and only if this card queued re-renders** (an item was rejected and resubmitted, or a missing image's render was submitted). The post goes to `rendering` and stays out of `next` until its collect wake.
- **plain, no flag, when every item on the card is settled** — approved or kept as-is — and nothing is in flight. The post goes to `done`.
- **Read `queue.json` first to know the branch you will get.** `n` in `batch` is a batch card: `card-done` drops that `batch` entry and frees no slot, because the slot was already null or held by another post. `n` is the live `slot` when it is not in `batch`; a post already in `rendering` takes `closed_without_slot`.

The two ways it bites: a plain `card-done` on a card whose renders are still out marks the post `done` and drops its tracking while the pictures land; `--rendering` on a card with nothing in flight parks the post in `rendering` with no monitor to collect it. Then word the closing comment to match the branch — "batch entry released" for a batch card, "slot freed" only when the post actually held the slot. "Slot released" on a batch card is a claim the queue does not support, and the next watchdog reads that comment.

## `next` opens the FIRST ready round, not the one you want

`backlog.py next` pops `q["ready"][0]`. When several rounds are queued (different posts, or the same post twice), a call made to open *your* post's round opens whichever round happens to be first — usually someone else's, and it claims the slot doing it. The printout says `create` with a title and brief, which looks like success until you notice the `n` is wrong.

Before calling `next`, read `queue.json` and check that your post's round is at the front of `ready`. If it is not, do not call `next`: repair by releasing any slot you already claimed (only when `issue` is null), reordering `ready` so your round is first under the file lock, then calling `next` exactly once. Never reorder to jump ahead of a round that was queued earlier by another run unless your run genuinely owns the post — the reorder is a repair, not a scheduling tool.

## A post released as `rendering` that later gets a card of its own

`card-done <n> --rendering` frees the slot and parks the post at `rendering`, which is right while its re-renders are in flight. When a later round for that same post is checked and its card opened, no `backlog.py` command puts the post back at `card`: `opened` wants the live slot, `reopen-card` is only for a batch entry released by mistake, and `ready` means queued behind the slot. Left at `rendering` with a card open, the next watchdog reads a collect that never came and may card the post a second time.

Write the state under the queue lock, the same way every other state write happens:

```python
import fcntl, json, os
with open(".lock", "w") as lk:
    fcntl.flock(lk, fcntl.LOCK_EX)
    q = json.load(open("queue.json"))
    p = next(x for x in q["posts"] if x["n"] == n)
    p["state"] = "card"
    p.setdefault("issues", [])
    if issue_id not in p["issues"]:
        p["issues"].append(issue_id)      # the identifier, never the uuid
    p["notes"].append("<time>: round-<k> card opened on <issue>, state=card")
    tmp = "queue.json.tmp"
    json.dump(q, open(tmp, "w"), indent=1)
    os.replace(tmp, "queue.json")
```

Append the note in the same locked block rather than with a second `backlog.py note` call: two separate writes let a concurrent run's edit land between them, and the note then describes a state the file no longer holds. Do not touch `slot` — another post's card may hold it, and this post's own `state` is what keeps it out of `next`.
