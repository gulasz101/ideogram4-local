# Disposition repair: the parked issue and the recovery action

A run ends and the issue is left `in_progress` with nothing that can wake it again. That is not a slow task — it is a task with no disposition, and Paperclip's recovery classifier re-opens it as an action owned by the assignee. This file covers how to recognise one, what the board accepts instead, and how to avoid leaving one behind.

## What raises a recovery action

The classifier watches for a stopped issue whose state names no next step:

| cause | shape |
| --- | --- |
| `deliberate_wait_without_target` | the run parked the issue as though waiting, but there is no pending interaction, no monitor and no blocker — the commonest, and what a run that dies mid-task leaves behind |
| `missing_successful_run_disposition` | the last run finished without writing any disposition |
| `in_review_without_action_path` | `in_review` with no reviewer, approval, pending interaction or monitor |
| `blocked_by_*`, `blocked_chain_stalled` | blocked against an issue that is unassigned, cancelled, stalled, or whose assignee cannot be invoked |
| `pending_board_decision`, `pending_user_decision` | a decision that was never actually recorded as an interaction or approval |

**A comment is not a disposition.** Neither is a run summary, a "working on it" note, or a plan in prose. The classifier reads issue state, so the state field is the disposition.

## Inspecting one

```bash
GET /api/issues/{issueId}/recovery-actions
```

Returns `{ active, actions }`. The `active` object carries `id`, `cause`/`kind`, `status`, `ownerAgentId`, `nextAction`, `attemptCount`, `maxAttempts`, `wakePolicy` (often `bounded_owner_disposition_repair` with the retry run already scheduled) and `evidence` (the failing `latestRunId` and its status). `active: null` means nothing is outstanding.

Read `nextAction` first — it is the board saying what it wants — and `maxAttempts`, because a bounded repair wake is spent: once the attempts are gone the issue needs a human or a different route.

## What the board accepts

Its own words, from `nextAction`: **terminal, live, blocked, monitored, or typed waiting**. Concretely:

- **terminal** — `done` (work complete, nothing left) or `cancelled`.
- **live** — `in_progress` with an active run right now.
- **monitored** — `in_progress` or `in_review` with a real scheduled monitor: `monitorNextCheckAt` non-null, agent assignee, no user assignee.
- **blocked** — `blocked` with a genuine unresolved blocker (`blockedByIssueIds`, or an `unblockDescriptor` naming an owner and an action). **But not when the issue also has a monitor it needs alive**: the server refuses `in_progress` while a blocker is open and `blocked` disables monitoring, so an issue that is both waiting on another issue and collecting a render is `in_progress` with the monitor, and the wait arrives as a child-completion wake. See the first entry under **Preventing it**.
- **typed waiting** — `in_review` with a pending interaction (`request_confirmation`, `ask_user_questions`, `request_item_verdicts`, …) or a linked approval.

Everything else is the parked state, however reasonable the prose around it sounds. `in_review` with only a "please review" comment does not qualify, and neither does `in_progress` with no monitor: the disposition guard rejects the move and the classifier flags the parking.

**On a review card the typed-waiting disposition is the verdict card plus `in_review`** — which is why a card whose render is checked but whose card was never posted is in exactly this stall, holding a finished picture nobody can judge.

## The resolve route

```json
POST /api/issues/{issueId}/recovery-actions/resolve
{ "actionId": "<active.id>",
  "outcome": "restored" | "blocked",
  "sourceIssueStatus": "todo" | "done" | "in_review" | "blocked",
  "resolutionNote": "why, in one or two sentences" }
```

Validation as the server's schema exposes it: `restored` pairs with `todo`, `done` or `in_review`; `blocked` pairs with `blocked` and wants an unresolved first-class blocker on the issue; `false_positive` and `cancelled` are board-actor outcomes, not agent ones. `restored` + `todo` on a `deliberate_wait_without_target` action has extra gates — it expects an escalation notice the board opened, on an issue already `blocked` — so an agent that reads a `conflict` there is seeing a route it is not the right actor for. Land the disposition and let the issue's own state speak rather than forcing the resolve call.

Carry the caveat with the shapes: **these are what the server validates, not a sequence exercised end to end.** The reliable repair is the disposition itself — post the pending card, set the monitor, resolve the blocker — because the classifier reads the issue's state, and a state that is honestly live or typed-waiting is not a parked issue.

## When every field write is refused but comments still post

A monitor wake can find the issue checked out to its own run
(`checkoutRunId` and `executionRunId` both the run id, `activeRun.status: running`) while
every mutating call answered `Issue run ownership conflict`: `PATCH` with the monitor body,
a minimal `PATCH {"status":"in_progress"}`, and `POST /checkout` (`Issue checkout conflict`)
all refused, four attempts across six minutes, while `POST /comments` succeeded on the first
try. Nothing in the issue read explained the refusal, so it is a server-side lease the run
cannot see — not a stale field and not a sibling whose end you can wait for.

The repair order when this happens: stop retrying after the second refusal, post one
comment that carries the state (what was verified, what is still in flight, the job ids and
what the next wake must collect), keep the drafts and queue notes current on disk, and end
the run. The issue is then `in_progress` with no monitor, which is exactly the parked shape
the board's recovery action flags for the assignee — that wake is the sanctioned fallback,
and the renders survive in the queue at no cost because a finished job waits to be fetched.
Do **not** try to reach the issue through another route (a runner comment asking for a
repair, a second checkout, a status write on a sibling) to force the monitor in.

The refusal is run-scoped, so a later wake on the same issue is a reliable place to re-arm:
the identical PATCH body that was refused landed on the next run untouched, and the recovery
action cleared itself the moment `monitorNextCheckAt` came back non-null, with no resolve call
needed. Do not try to repair the issue from the failed run — arm it from the next one, then
read `GET /recovery-actions` back and confirm `active: null`.

## Preventing it

- Before ending a run, answer one question: what wakes this issue, and when? If the answer is "nothing", it is `done` with the work finished — or it is unfinished and needs a monitor, a blocker or a pending card.
- **A run whose budget is running out mid-work should land the disposition first, not the prettiest partial artifact.** The card that was nearly ready but never posted leaves exactly the state this file is about.
- A run killed by the platform leaves the parked state behind even though the agent did nothing wrong, and the next run inherits it. Read the issue and its `recovery-actions` before assuming the work was half-done, and check whether the artifacts a dead run's summary says are missing actually are: the render queue keeps moving while a run is dead, so a summary written at the kill can report a job as having no output when it has since finished, and a file as mid-check when it was long since fetched.
- **A card with renders in flight cannot carry a blocker edge, so a concept hand-off rides the child-completion wake instead.** The server refuses a status write to `in_progress` while a `blockedByIssueIds` entry is unresolved (`422 Issue is blocked by unresolved blockers`), and `blocked` kills the render monitor, so there is no disposition that is both blocked and monitored. When one slot of a card has to go to the post's author while the other slots re-render, do **not** set the blocker. Create the author's issue as a **child of the card** and leave the card `in_progress` with its render monitor: a done child fires `issue_children_completed` on the parent's assignee, which is the same wake the blocker would have produced. Name the child issue in the handoff draft and in the queue note, because a round that closes on the monitor wake will otherwise look complete with a slot missing.

## A card whose frame fails the bar after posting: withdraw it and rebuild, never leave it up

A card is pending and the self-check then finds a show-bar defect on one item — a figure fused into the furniture, a fused hand, a duplicated limb, lettering. The bar is that no broken frame sits on a review card, and the API cannot edit a frozen card's items, so the disposition is withdrawn and rebuilt. A withdrawn card costs no review round.

The order, and why each step sits where it does:

1. **Withdraw the interaction first.** `POST /issues/{id}/interactions/{interactionId}/withdraw` with `{"reason": "…"}`, which returns `status: cancelled`. `scripts/pc-withdraw-interaction.py <issue> <interaction> <run-id> "<reason>"` wraps it: `paperclip-write.py` has no withdraw verb and `post-interaction.py` only posts, and both are shaped for the unattended surface where a composed curl mutation waits out the approval window. Write the reason, because it is the only trace on the board of why a pending card disappeared.
2. **Comment before the new card exists, not after it.** An agent comment does not resolve a pending verdict card: a hop comment posted while a card was pending left it pending until the owner answered hours later, with `supersedeOnUserComment` set on the card. The safe shape is still withdraw → comment → post, so the thread reads in the order it happened and no write lands after the fresh card.
3. **Rebuild with the surviving items and reuse their existing `attachmentId`s.** The PNGs are already uploaded to the issue, so a rebuild costs no upload and the bytes on the card stay the ones already hashed against staging. Re-uploading the same files creates a second set nobody checked.
4. **Post under a new idempotency key** (the round's key plus `-corrected`), then `PATCH` the description alone — no status field — so the brief matches the items that are actually on the card. The issue stays `in_review`: the fresh pending interaction is the typed-waiting path, and a withdrawal with nothing posted after it is the parked shape this whole file is about.
5. **Say in `detailsMarkdown` what came off, with its job id and the reads that settled it**, and name the job ids of any repaired frames with the promise to report whether one beats the card. He is reading a card that is one item shorter than the last one he saw, and an unexplained gap reads as a mistake.
6. **If a replacement was queued, arm the monitor for its ETA.** A pending card wakes the run on a verdict, not on a render, so without the monitor the repaired frame sits unfetched.

State plainly in the comment that the withdrawn card's items were not judged, so nothing is implied about his verdict on the items that stayed.
