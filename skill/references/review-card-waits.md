# Waiting on a review card (studio side)

You woke on a post's review issue that already has the verdict card pending. That run is a
verification pass: no render, no resubmit, no second card.

## Verify with reads, then post one short audit comment

1. `GET /api/issues/<id>/interactions` — the card must be `status: pending`, kind
   `request_item_verdicts`, `effectiveResolverPolicy: human_only` for Wojtek's verdict, and
   `continuationPolicy: wake_assignee`. That pending card is both the review path and the wake
   path; do not add a monitor to the card issue to "watch" it.
2. Attachment objects echo a `sha256`. Compare that field with `shasum -a 256` of each staging PNG.
   Equal hashes prove the card shows exactly the renders the card text describes, with no
   re-download. Do this before saying the card is intact.
3. `GET /api/issues/<id>` — `in_review`, `assigneeAgentId` set, `assigneeUserId` null, no monitor.
   Healthy wait; nothing to patch.

Then post exactly one short comment: the card is unchanged, the hash prefixes and check results you
verified, and that the verdicts are the next thing. That comment is the audit trail for a wake that
did no work, and it is the only thing this run owes. Post no second one, do not re-post or re-upload
the card, and do not PATCH the status. An `issue_assigned` wake on a card that was already pending is
(re)assignment bookkeeping, not new direction — verify, report, exit.

## Route shapes for these reads

- Read the card from the list route, `GET /api/issues/<id>/interactions`. There is no
  single-interaction GET — `/interactions/<interactionId>` answers `{"error":"API route not found"}`,
  which reads like a lost card. The list row is the authority: `status`, `outcome`,
  `effectiveResolverPolicy`, `continuationPolicy`, and `payload.items[]` with their `attachmentId`s.
- The issues collection takes a uuid in the path. `GET /api/companies/<cid>/issues/<IDENTIFIER>`
  answers `API route not found`; resolve it first with `?q=<title words>&limit=5` and take `id`.
- Match an attachment row to its render by `sha256`, not by name. The row's keys are `id`,
  `originalFilename`, `byteSize`, `sha256`, `issueCommentId`, `contentPath`; there is no `filename`,
  `name` or `size` key, so a reader that prints those reports four anonymous rows. Hash every PNG in
  the staging directory and name the file whose digest equals the row's. A non-null `issueCommentId`
  is the proof the file is bound to the card comment and will render; a null one is the only shape
  that means an empty row.

## Where the lane state lives

`~/image-studio/backlog/queue.json` is one dict: `total`, `built`, `posts`, `skipped`, `batch`,
`ready`, `slot`.

- `posts[]` — one entry per post: `n`, `post`, `title`, `brief`, `state` (brief / audit / ready /
  card / done), `issues[]`, `notes[]`. The notes are an append-only log; read the tail for what is
  in flight and what was held.
- `batch[]` — the claimed lane(s): `{n, round, brief, issue, since}`. A post is mid-flight when it
  appears here.
- `backlog/briefs/<nnn>-round-<r>-card.md` is the card text as posted; `backlog/prompts/` holds the
  prompts that produced each file.

A post in `state: card` with one issue means the ball is with Wojtek; the next move is his verdict,
not another render.

## Siblings still rendering

A repaired slot submitted after the card went up (a changed header object, a third pose) belongs to
the campaign issue that carries the monitor, not to the card issue — check that issue's
`monitorNextCheckAt` before calling the lane stranded. Never open a second card for the same post
while the first is unanswered.

Another run may hold the shared workspace; the wake payload names it. Read-only checks are always
safe; do not write `queue.json`, staging files or the card while that run is active.

## When the card comes back answered

The verdict wake (an `issue_commented` wake whose `interactionOutcomes` names the card, or the
item-verdicts wake) is the start of the close, not the end of the run. Check `status: answered` with
`result.complete: true` before touching the queue, then follow `review-loop.md` §8–9 for the order and
`references/closing-pass.md` for the decisions that order assumes: which name the vault copy takes,
which engine suffix means what, what the replaced file and its earlier record get patched to, what a
record says when no fresh read was possible, and which `card-done` branch a partly filled post takes.
