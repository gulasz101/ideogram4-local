# Advance: what `backlog.py next` hands you and how to act on each shape

The full Advance procedure lives in `references/backlog-review.md` (*Advance*). This file carries the rules that have to land somewhere the two workhorse references cannot take new text: `SKILL.md` and `references/backlog-review.md` are both past the 100,000-character cap, so `skill_manage` refuses a patch to either and rolls the whole batch back. Read this beside them.

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

## After the create

`backlog.py opened <n> <ID>`, then re-read the slot: it must name the issue, the post must read `card`, and `q["ready"]` must no longer hold that round (popping it is `next`'s job, and a copy left behind becomes a second card for one round).

If you also refreshed the runner's `queue` document, the release that follows must leave the watchdog alive: `release`, then a plain PATCH of `status: in_progress` and `assigneeAgentId`, then read back all four fields — `status`, `assigneeAgentId` set with `assigneeUserId` null, non-null `monitorNextCheckAt`, and `checkoutRunId` null. A re-arm PATCH re-acquires the checkout, so arm the monitor only when the release actually cleared it.

## An empty slot is not an invitation to card

The watchdog sees `slot: null` and the instinct is to call `next` at once. Decide first: card a post only when it is cardable *right now* — every image either sits in the vault as the draft embeds it, or is a fetched, checked render whose handoff brief is written. `next` claims the slot as a side effect of the read, so a claim made before that check has to be handed back with `release` in the same wake, which reads as churn.

**Renders in flight → the slot stays free.** The post's last queue note says `SUBMITTED <time>` with job ids and an ETA, and `imagegen status` still answers `running` or `pending`. Carding it puts the pictures the round exists to replace in front of Wojtek, which is the one thing a review card must never do. This is a different case from the render-plan brief above: there, nothing was rendered and the card is created with a correction comment; here, renders exist and are landing, so no card at all.

Also leave the slot free when the brief is a submit-time placeholder — a plan with no item ids, no staging paths and no check notes — and when a sibling issue's monitor owns the collect.

What the watchdog still does in that wake: rebuild the `queue` document from live state, run the card scan, confirm the runner is `in_progress`, assigned to you, no user assignee. Then arm the monitor for a **short hop past the collect** (roughly 40 minutes after the sibling's monitor time), not the next daily tick — a 24-hour re-arm leaves the queue idle for a day when the blocker clears within the hour. Say in the comment which post was left free, what its job states were, and which issue owns the collect; an empty slot with no explanation reads as a broken runner.

Never advance past an uncarded post to find one that is cardable. The queue's order is the review's order.
