# Runner wake checks (backlog review)

The runner issue is the queue's clock: it holds no card itself, it opens one card per post
per round, and its daily monitor is the only thing that repairs work the card runs left
half-done. A card run must not check the runner out or rebuild its queue document; the
runner wake is where the queue is reconciled.

## The order of a runner wake

1. `date -u`, `backlog/backlog.py status`, `backlog/backlog.py next`.
2. Check every claim in the queue, not only the slot — see "The three claims" below.
3. Rebuild the queue document from live state:
   `scripts/put-queue-doc.py --issue-id <runner> --run-id <this run>`.
   Never patch its cells by hand; the builder's column layout and counts are what the
   document is trusted for.
4. `scripts/scan-cards.py --runner-id <runner>`. Fixed delay: give it a long timeout.
5. Re-arm the monitor with the minimal body
   `{"executionPolicy":{"mode":"normal","monitor":{...}}}`, then read the issue back.
6. One comment: what was repaired, queue counts, document revision, scan total, which
   cards are in flight and untouched. End without a release.

## The three claims

`queue.json` holds three kinds of claim, and only the first one is visible as a card:

- **`slot`** — the post the runner is currently carding. A slot that names a post and no
  issue has lost its card: run `backlog.py release` so the round can be claimed again.
  A slot whose issue exists but is not `in_review` and has no pending card is being
  worked, unless it has no monitor and no live run.
- **`batch`** — rounds claimed by `batch-open` / `batch-open-ready` so several cards can
  be in flight. Each entry must carry an issue id. `batch-open` claims the round first
  and the card issue is created afterwards, so a failed create leaves an entry with
  `"issue": null` and a finished, checked round behind it.
- **`ready`** — rounds with a brief written and no card yet. An entry here is waiting by
  design; do not claim one whose brief assigns the collection to another live issue.

### Repair: a batch entry with no card issue

No card exists, so `scan-cards.py`'s per-card loop cannot see it — that is why the scan
now also prints the batch entries that name no issue. Repair on the runner wake:

1. Read the entry's brief. The staging PNGs are usually already on disk; confirm each
   one's byte size and sha256 against the brief before creating the card.
2. Create the issue with `description` = the brief verbatim, `parentId` = the runner,
   the project id, your own agent id as assignee, `status: todo`, title
   `Backlog review <nnn>/153, round <k>: <post title>`.
3. Check the returned `description` length against the brief's byte size — that is the
   cheapest proof the card got the whole brief.
4. Record it with `backlog.py batch-opened <n> <GUL-id>`. Never record before the create
   lands: an entry pointing at a wrong or absent issue is worse than an unrecorded one.
5. The new `todo` card is picked up by its own run; do not work it from the runner wake.

## The document's home is the runner, and it is not inferred from a title

Only one issue in the campaign carries a `queue` document. Several share the backlog's
vocabulary — the runner, a campaign issue, a PM brief — so settle which one it is with
`GET /api/issues/<id>/documents` and look for a `queue` key before naming it anywhere.
A card run that posts its fallback row on a similarly named issue leaves a wrong link on
a card that may already be closed, and the only repair is a correction comment, because
comments cannot be edited.

A card run's fallback comment carries the three things the document is rebuilt from: the
post's own row and what changed, the `batch` line, and any slot that names a post with no
issue (reported, never repaired from a card run). Say in it that the document is one card
behind live state, so the next reader knows the staleness is deliberate.

## Keeping the monitor alive

- 2-hour hops persist across wakes. A ~7-hour `nextCheckAt` is silently dropped and the
  wake never comes — use short hops, or the daily body.
- A `blocked` issue fires no monitor. Park a card `in_progress` + monitor, not `blocked`.
- Bounded bodies (`timeoutAt`, `maxAttempts`, `recoveryPolicy`) are refused once the
  attempt budget is spent (`Monitor bounds are already exhausted`). Clear with
  `{"executionPolicy":{"monitor":null}}` first, then re-arm with the minimal body.
- Read `monitorNextCheckAt` back after the last write; the wake you are in usually fired
  the monitor, so the read before the re-arm shows `None`.

## Tooling notes

- `scan-cards.py` makes three API calls per card. At ~120 cards the default 180 s command
  timeout kills it mid-run; run it with `timeout 560` (or a raised tool timeout) and only
  then read the total.
- Don't dump the company issue list to a file and reference it from a command that also
  runs something: a file over the scan cap (1 MiB) makes the whole command refuse to run.
  Filter in the same pipeline, or list with a smaller limit.
- `?identifier=GUL-nnn` does not filter; list company issues and match client-side.
