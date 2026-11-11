# Building a review card from a script: the Paperclip caps and payload shapes

A card is five writes against one issue: create, upload the attachments, post one linking comment,
create one `request_item_verdicts` interaction, then `PATCH` the status. Each of them has a cap or
a required shape, and each rejects the whole write when it is wrong — so the failure surfaces as a
card that exists but cannot be reviewed.

## Caps and required fields

| Field | Rule | What a violation looks like |
| --- | --- | --- |
| `payload.items[].description` | **<= 500 characters** | `400 Validation error … {"code":"too_big","maximum":500,"path":["payload","items",0,"description"]}` |
| `payload.detailsMarkdown` | no cap met in practice (1.8 KB fine) | put the long form here |
| `executionPolicy.monitor.notes` | **<= 500 characters** | `400 Validation error … ["executionPolicy","monitor","notes"] … too_big` |
| `executionPolicy.monitor.nextCheckAt` | required, ISO-8601 with `Z` | monitor block rejected |
| `monitor.scheduledBy` | enum `assignee` \| `board` | 400 |
| `monitor.maxAttempts` | integer 1-100 | 400 |
| `monitor.kind` | enum `external_service` only, nullable | 400 |

**The brief's own item text can be over the cap.** An item description copied straight from an
issue description or a round brief is routinely a few characters past 500, and it is the builder
that says so. Run `build-verdict-card.py` as the length gate before writing the card's other
pieces: it prints `<label> <n> chars` per item and exits non-zero without writing anything. Trim
adjectives out of the composition clause ("heavy timber chest" -> "heavy chest") and keep the
Why / Check / Caveat frame intact, because that frame is what he actually reads.

Two hard rules that are not in the table because they are shapes rather than caps:

- **There is no top-level `monitorNextCheckAt` on `PATCH /api/issues/{id}`.** Send the monitor only
  inside `executionPolicy.monitor`; a top-level `monitorNextCheckAt` makes the entire request
  answer `400` with an **empty body**.
- **Unknown keys inside `executionPolicy.monitor` fail the same way, with an empty 400.** A
  `status` key, an old `serviceName`, anything not in the schema: the whole write is refused and
  nothing tells you which key it was.

## Arming a monitor after a wake has fired it

`executionState.monitor.status` reads `triggered` for the duration of the run that the monitor
woke, and a new `nextCheckAt` can still be set in that state — the block is the shape, not the
status. Arm it in the same call that posts the run's comment (one request, so a rejected monitor
takes the comment with it), then re-read to prove it landed:

```json
PATCH /api/issues/{issueId}
{
  "executionPolicy": {
    "monitor": {
      "nextCheckAt": "2026-10-31T16:35:00Z",
      "scheduledBy": "assignee",
      "maxAttempts": 40,
      "notes": "next hop: read the card verdict, then the next post"
    }
  }
}
```

Verify with `GET /api/issues/{id}` and read `executionState.monitor.nextCheckAt` — a `200` on the
PATCH is not proof the field was stored.

**Match the hop to the job's status, not to the clock.** A hop is the only way to wait for a render:
a foreground `sleep` inside a tool call is cut off at the tool's own cap (about seven minutes), so a
run cannot sit through a 21-minute render and its fetch. That makes the hop length a decision, not a
default. While `imagegen status` answers `pending`, a two-hour hop is right. The moment it answers
`running` with a half-hour ETA, a two-hour hop spends a whole wake cycle on a finished render — arm
25-35 minutes instead and collect on that wake.

## The card issue may already exist: bind the batch entry, never open a second issue

`backlog.py ready <n> <round> <brief>` queues the round, and `batch-open-ready <count>` turns the queue
into batch entries **without an `issue` id** — it hands back the title and brief for a caller to create
an issue from. When the wake already names a card issue for that post, that entry is a duplicate
waiting to happen: bind it with `backlog.py batch-opened <n> <GUL-id>` and create nothing.

Read `queue.json` before any of that — `slot`, `batch`, and `posts[n].state`. A post already at
`state: "card"` with its issue id in `issues` means the card *is* the issue this run was woken for,
and the batch entry only needs its id filled in. Two cards for one post give him two surfaces to rule
on, and the second verdict lands against a picture the first card never asked him to judge.

## The one-call diagnosis for any empty 400

When a PATCH answers `400` with nothing in the body, stop guessing at field names. The live
schema is served by the API itself:

```bash
curl -s -H "Authorization: Bearer $PAPERCLIP_API_KEY" "$BASE/openapi.json" \
  | python3 -c "import json,sys; s=json.load(sys.stdin); print(json.dumps(s['paths']['/api/issues/{id}']['patch']['requestBody']['content']['application/json']['schema'], indent=1))"
```

That settles every field question in one call. Blind retries against an empty 400 are how an hour
disappears — the body carries no information, so the schema is the only source.

## A brief that says "the checks are done" is not your gate

An issue can arrive with a table of confirmed passes and an instruction not to re-check. Obey the
no-rerender half — no new prompt, no second audit sweep — but run the gate yourself before the
card goes up: `check-grey-bars.py`, `check-palette-strip.py` and `check-green-share.py` on the
staging file, plus **one** frame-level read for a figure, a hand, lettering, a panel or a strip.
That costs seconds, and it is the only thing standing between a broken picture and a frozen card,
which is the one mistake the loop cannot take back. If the frame read disagrees with the brief,
classify the finding before acting: a defect class from `references/hold-back-or-ship.md` (an
extra hand, unreadable lettering, a pasted panel covering the frame) holds the slot and the thread
says what failed, while a **small factual correction — a hand count, one prop drawn flatter than
the scene around it — ships on the card with the correction in that item's row and in
`detailsMarkdown`, plus one clause in the linking comment naming what the brief promised and what
the frame actually shows**. Holding a whole slot for the second kind costs a render round for a
sentence, and quietly adopting either side leaves a false claim on a frozen card. The card's check
note is always written from the pixels you looked at, never from the brief.

## Two briefs on disk can name one slot differently

A post's backlog brief and the card brief the issue was created from routinely disagree on item
ids — `task-tracker-header` in one, `tsk-header` in the other — because the card brief was cut from
it later, and both read like the authoritative table. The ids on the card brief win: they are what
the verdict wake reports, what the library record is filed under and what the close run reads. So
carry the staging filename as its own column in `detailsMarkdown` (the id then never has to be
resolved back to a file), and name the other spelling in the queue note — a close that looks in
staging for `<item id>.png` otherwise finds nothing and reports the file as missing.

## Why an `in_review` PATCH answers 422 after a failed card write

The disposition guard refuses to park an issue in `in_review` when nothing owns the next action.
A pending `request_item_verdicts` is that owner; when its POST was rejected by a cap, there is no
interaction, and the status move fails with
`422 invalid_issue_disposition … would leave the issue in_review without anyone or anything owning
the next action`. Fix the interaction first, then move the status — never the other way round.

## Attachments

`POST /api/companies/{companyId}/issues/{issueId}/attachments` with a multipart body whose part is
named `file`. The response carries `sha256` and `byteSize`: compare both against the staging file
and treat a mismatch as a failed upload rather than a successful one with an odd size.

**Pass `--run` and `--company` to the helper.** `scripts/upload-attachments.py <issue> <files…> --run <runId> --company <companyId>`. With `--run` alone it exits `--company or $PAPERCLIP_COMPANY_ID required`, because the company id is not present in the tool environment even though the wake payload carries it: take the id from the payload rather than concluding the credential is missing. It also prints one line per file plus the JSON array, so redirect its stdout to a file when a set is larger than one screen.

**Upload each file once per round.** Re-running the helper for a file that already landed stacks a
second attachment with its own id, and the card then carries an orphan nobody binds to. Take every
id from one batch output, and when a duplicate does exist, name it in the linking comment beside the
id the item actually uses — the item list is the authority, and a later reader otherwise binds a
verdict, a hash or a re-upload to the wrong row.

The duplicate is almost always born from a truncated read, not from a real gap: the helper prints
one JSON row per file, so piping a multi-file call through `tail` hides the first rows and the ids
for those files never reach the notes. Then the next call re-sends the ones you cannot see. **Never
pipe the upload helper through `tail`/`head` for a set — write its whole output to a file or pass
`--json` and read all of it.** `scripts/upload-attachments.py` prints a load-check preamble, one
line per file, then the JSON array, so redirect its stdout (`> uploads.txt 2>&1`) and parse from
the first bracket — `raw = open(p).read(); rows = json.loads(raw[raw.index("["):])` — then build
the card spec's `attachment_id` values from that list. Ids read off the transcript are the ones a
truncated read eats. When the ids are already lost, recover by listing rather than
re-sending: `GET /api/issues/{id}/attachments` returns every id with its `byteSize`, the duplicate
pairing visibly as two rows of the same size, and the earliest id of each pair is the one the item
binds to. One stray row costs a line in the linking comment; a blind second upload costs the same
row plus a card that points at the wrong twin.

A card that **this run created** accepts its uploads immediately. `409` on an upload means another
run holds the card, not that a new card needs to settle — so when a card was opened by a sibling
run off a queue entry, either build the card properly from the run that collects the renders or
leave the upload to its owner.

Make the attachments visible in the thread with one comment carrying `attachmentIds`, then bind
each item to its own attachment with `attachmentId` in the verdict request, so a verdict lands
against the right picture.

**Prove the thread link, not the comment POST.** A `201` on the comment says a comment exists, not
that the picture hangs off it. Read `GET /issues/{id}/attachments` back and require a non-null
`issueCommentId` on the attachment row — that field is what renders the image beside the comment
the reviewer actually opens.

## Reading state back: `scripts/pc-get.py`

Attachment rows, interactions and comments are not on the issue object. `scripts/pc-get.py
<path> [<path> ...]` reads the key from `$PAPERCLIP_API_KEY` or the profile `.env`, appends `/api`
to `PAPERCLIP_API_URL` when it is missing, prints status and body per path, and never prints the
key:

```bash
python3 scripts/pc-get.py /issues/<id>/attachments /issues/<id>/interactions /issues/<id>/comments
```

Two response-shape facts the caller has to handle: **`/comments`, `/attachments` and
`/interactions` answer a bare JSON array**, not `{"items": [...]}` — only the issues routes wrap,
and a parser that opens with `d.get('items')` dies on a list (`'list' object has no attribute
'get'`). Attachment rows also carry `contentType` with `filename`/`fileName`/`sizeBytes` often
`null`, so bind a row by its `id` and by the bytes you hashed, never by a name field.

Use it for the proof a card needs: `issueCommentId` on the attachment row, the pending
interaction's `effectiveResolverPolicy` and `continuationPolicy`, `payload.items[].attachmentId`
and each description's length, and the stored `supersedeOnUserComment` — read from the server's
copy, never from the payload file you posted.

## A wake on a pending card is proved, not announced

When a wake lands on an issue whose `request_item_verdicts` is still `pending`, the thread has already had its one comment. **A brief that says "upload the file, link it in one comment" is satisfied by the comment the attachment already hangs from:** read `issueCommentId` on the attachment row, and when it names an existing comment, no comment is owed and the literal instruction is not licence for a second one. Do not post a second one saying the card was re-checked: a
board/user comment supersedes a target-bound pending card (`supersedeOnUserComment`), and the
card's own `detailsMarkdown` already tells him to put everything in the reasons. Posting
verification chatter next to a live card buys nothing and risks the card, so put the evidence
where it is durable instead — `backlog.py note <n> …` in `~/image-studio/backlog/queue.json`,
with the measured numbers, the crop scales and the attachment hashes.

**The wake reason does not announce this; the interaction list does.** This wake arrives as the
ordinary `issue_assigned`, because the creating run made the issue and assigned it to this agent —
nothing in the payload distinguishes it from a build wake, and the thread's head comment is the
creating run's handoff summary, which reads exactly like work still to do. Read the state before
the prose: `status` already `in_review`, `originRunId` naming a different run of this agent, and
`GET /issues/{id}/interactions` holding one `pending` card for this round. All three together mean
verification wake; two of them are not enough, because a rejected slot also lands `in_review` with
a card that needs action.

What that evidence is: re-run the judgement-free scripts yourself and read the attachment bytes
back (`GET /api/attachments/<id>/content`, compare `sha256` and size against the staging file).
Both belong in the note; neither belongs in a comment while the card is open. A comment that opens
with "I re-checked the card" is the exact chatter this bans, however reassuring the numbers are.

**The download is for hashing only — read the picture at its staging path.** Once the hash and the
byte size match, every crop and every frame read runs against the staging file the upload came
from; do not hand a vision tool the downloaded copy. A shell `$TMPDIR` is not the profile scratch
directory the media loader resolves, so pointing a read at `$TMPDIR/att-<id>.png` answers `media
file not found` for a file that is sitting right there, and the detour buys nothing a matching
`sha256` has not already bought. `sips -g pixelWidth -g pixelHeight` on the staging file confirms
the dimensions the card claims in the same breath.

**A comment that slipped out is repairable, not permanent.** `DELETE /api/issues/{id}/comments/{commentId}`
soft-deletes it — the row keeps its id, the body is cleared and `deletedAt` is set — so a run that posts
chatter next to a live card should delete it rather than leave it standing; a comment carrying a broken
image or a claim the card contradicts is worse than no comment. **Never carry the picture into a comment
as `![…](/api/attachments/<id>/content)`:** that route answers 404 to any request without a board session,
so the markdown renders as a broken image in the thread he is reading. A comment binds a file with
`attachmentIds`, and the attachment row's own `issueCommentId` is what draws it.

**Such a wake is a no-op wake: render nothing, open no card, and do not arm a monitor.** A `pending`
`request_item_verdicts` whose `continuationPolicy` is `wake_assignee` and whose
`effectiveResolverPolicy` is `human_only` is already the review path, and it wakes this agent the
moment he rules. A `PATCH` that also carries `executionPolicy.monitor` competes with that wake and
re-checks a frozen card for nothing; the honest finish is the same status with the interaction left
untouched.

**Checkout is not free — it moves the issue to `in_progress`, and the run owes the move back.** A
wake on a pending card still needs the checkout, so the card lands in `in_progress` unless the same
run sends `{"status": "in_review"}` before it exits. Nothing is executing behind that status once
the run ends, and a later reader sees an abandoned wake rather than a card waiting on him. Send the
status in one call that also carries whatever short text is genuinely owed, then require the
response to echo `in_review` — a `200` with an empty body is not a landing, and neither is the
status you asked for. If the restoring `PATCH` answers `409`, the other run owns the card: leave the
status to it and record that in the queue note instead of retrying.

**A handoff comment on the card is a snapshot, and usually a stale one — the attachment and
interaction lists are the state.** A sibling run that cannot write to a leased card often leaves a
comment saying the card is empty and listing what remains; the run holding the lease can fill it
minutes later, so a later wake that reads the comment as current rebuilds a card that already
exists and gives him two surfaces for one round. Read attachments and interactions before acting,
and when the comment's claim has stopped being true, close it with one line naming the attachment
count and the card id rather than leaving a stale instruction at the head of the thread.

**Two findings are not chatter and get one short comment each: a wrong job id, and a legend that
contradicts the stored flag.** Both are statements the frozen card makes about itself, and
`review-loop.md` names the comment as the repair for a mistyped job id because the id is what the
close resolves the record against. Build the correction from the machine, not from a neighbouring
note: on post 076 the day's own queue note carried `Z9D8OHIq7g` and the card carried `Z9D8OHIqog`
while the render brief and `jobs.db` both held `Z9D8OHIq7og`, and only the DB row answered
`imagegen status`. So cross-check every id in the card's table against the brief that submitted it
and against `jobs.db` (`ssh m1max "cd git/ideogram4-local && sqlite3 jobs.db \"select id,status,engine,created_at,finished_at,output_path from jobs where output_path like '%<slug>%'\""`),
whose `output_path` also proves the staging file is that job's own render. **Get that proof from
the job itself before the id reaches the table:** `imagegen status <job> | grep -E
'output_path|engine'` prints `output_path`, the engine and the created/finished stamps for any
plain id, so one grep matches the staging filename to the job without a trip to the Max — keep the
`jobs.db` query for an id the wrapper refuses (a leading dash) or one `status` cannot find.

## A status PATCH that answers 409 belongs to another run, and a comment is the whole intervention

A six-file upload loop can answer `500 {"error":"Internal server error"}` on part of the set while
the first file lands `201`. That is the upload being retried, not the card being wrong: re-run the
loop over **only the files whose sha256 never came back matched**, three attempts each a few seconds
apart, and every one lands. Never recreate the card or re-upload the files that already matched —
the attachment list is what the verdict items bind to.

After the card is built, `PATCH /api/issues/{id}` with `{"status": "in_review"}` can answer
`409 {"error":"Issue run ownership conflict", "details": {… "checkoutRunId": "<other run>"}}`.
The card issue is claimed by its own run the moment it exists, so the status move belongs to that
run and retrying it from here changes nothing. What this run can still do:

- **Comment on the card — a comment is not blocked by the ownership check.** Say what is already
true and what must not be repeated: the attachment count and byte sizes, the item ids, that nothing
needs a render or a re-audit, and `do not open a second verdict request`. This is the one legitimate
second comment on a pending card, because the information is new to the run that is about to rebuild
it; re-checking chatter still does not belong there.
- **Re-read the issue a minute later.** The owning run flips it: a card that read `in_progress`
  right after the build read `in_review` a minute later with its attachments and one pending
  interaction intact. Verify the status, the attachment sizes and the item count before reporting
  the card as landed — reporting it from the PATCH return code writes a false statement onto the
  campaign issue. **A `200` on that PATCH is not proof either:** the claiming run can reset the
  issue to `in_progress` a few seconds later, so read the status back after that run has finished
  rather than in the same breath as the PATCH.

## Reading a card's verdicts: they live in `result`, never in `payload`

`GET /issues/{id}/interactions` returns each `request_item_verdicts` in two halves:

- `payload` — the request as it was sent: `items[]`, `prompt`, `detailsMarkdown`, `verdicts`,
  `requireReasonOn`, `reasonLabel`.
- `result` — written only once the interaction is answered: `outcome`, `complete`, and `items[]`
  carrying `id`, `verdict` (`approve` / `reject` / `defer`), `reason`, `resolvedAt`,
  `resolvedByUserId`.

**`payload.items[].verdict` and `.verdictReason` stay `null` for the life of the card.** A script
that reads them reports "pending, no verdicts" on a card that was answered hours ago, and an
approved post then sits unshipped while the run keeps saying nothing has landed. Read the
interaction `status` first (`pending` vs `answered` / `cancelled`), then read `result.items[]`,
and treat `result.complete` as the flag that every item got an answer.

Two shapes worth handling explicitly:

- **A `cancelled` request beside a `pending` one means another run superseded the request.** Work
to the pending request's item ids. If the replacement dropped an image this run had put on the
card, say so on the campaign issue — a slot that silently leaves the item list is a slot nobody
ever rules on, and the review loop reads it as delivered.
- **A rejection's `reason` is the instruction for the next prompt.** Carry its wording into the
rewrite rather than paraphrasing it into something softer, and write it verbatim on the verdict
row, because that row is what a later run reads to know what the owner actually objected to.
- **A previous round's card can read `expired` with `result.outcome: "superseded_by_comment"`,
`result.complete: false`, `result.items: []` and a `result.commentId`.** That is what a card built
with `supersedeOnUserComment: true` becomes when one owner comment answers every item at once:
there are no per-item verdicts at all, so the reasons live in the comment — fetch
`/issues/<id>/comments?order=asc`, match `commentId`, and quote its sentences verbatim on the new
card. `expired` is not `cancelled`: a withdrawn card carries `result.reason` and `result.items: []`
too, so read for `commentId` before concluding the round was never reviewed. **One comment can
carry the reasons for several items fused into one paragraph**, and attributing the whole paragraph
to each item tells him both pictures had the same fault — split each clause to the slot it names
and say in the legend which clause answers which. Build that next card with
`supersedeOnUserComment` false and no "a comment closes the card" line, or the same mechanism eats
the next round as well.

## Posting a comment with backticks or markdown

A comment body is markdown, and the Paperclip body field is a plain JSON string. **Never inline the
body in a double-quoted shell string when it contains backticks:** bash treats backticks as command
substitution and silently eats the text between them, leaving empty gaps in the posted comment (the
comment still answers `201`, so the damage is invisible until someone reads it). Write the body to a
file first and POST via urllib reading that file:

```bash
cat > /tmp/close-comment.txt << 'EOF'
... markdown with `backticks` and [[links]] ...
EOF
python3 -c 'import json,urllib.request; body=open("/tmp/close-comment.txt").read();
  ... POST json.dumps({"body":body}) ...'
```

The same rule applies to any field carrying markdown: keep the bytes in a file, and let Python
serialize the JSON. A garbled comment is worse than no comment; if one slipped through, soft-delete
it with `DELETE /api/issues/{id}/comments/{commentId}` and repost from the file.

## Linking comment: required, not optional

Attachments uploaded in this run carry `issueCommentId: null` until a comment posts their\nids. The card is not complete — and the images are not visible in the thread — until the\nread-back shows a non-null `issueCommentId` on every attachment. Post the linking comment\nwith `attachmentIds` in the body, then verify before PATCHing to `in_review`. A comment\nwithout `attachmentIds` does not bind; re-posting the same body never clears a null. The field is written by the local helper, once per
autachment: `scripts/paperclip-write.py comment --issue <id> --body-file <path> --attach <id>
--attach <id>`; a body that only embeds `/api/attachments/<id>/content` binds nothing and leaves every
row `null`, so read `issueCommentId` back before the status move.

A `reject` on one item leaves the card `in_progress`; it does not close, and the post returns to
`rendering` in the queue, often with a rebuilt card id and the replacement job already submitted by
the run that held the card. A wake that finds every card answered is therefore a verification wake,
not an action wake. Before writing a prompt for a rejected slot:

1. `backlog.py status`, then read the three most recent entries in `queue.json` `posts[].notes` for
 that post — they name the card in force, any hold and re-issue that already happened, and the
 replacement job ids if one went out.
2. Read the lane on m1max for a job whose name carries that slot.
3. Only when neither shows a replacement do you write the prompt and submit.

Two runs each re-rendering one rejection produce two cards and two renders for one verdict, and the
second card can put a picture in front of the owner that the first run never asked him to judge.
What this run owes instead is the proof: hash the vault files the sibling run shipped against the
staging files that were on the card, and confirm each draft embed still points at its slot's path
with alt text written from the picture that ships.

## A comment that is the verdict, and the board-only cancel route

`request_item_verdicts` carries `supersedeOnUserComment` **inside `payload`**, not at the top level. A card built by hand with that key omitted reads back `false`, so an owner comment does *not* expire it: the comment already decided the round, yet the card stays `pending` and the issue then has two live review paths. Build cards with `scripts/build-verdict-card.py`, which bakes `true` inside `payload`, and this does not arise.

When a hand-built card stays pending after a comment decided it, withdraw it. The CLI `issue interaction:cancel` is board-only and answers `403 Agent actors cannot cancel issue-thread interactions through this board-only route`; use the API route instead:

```
POST /api/issues/<issueId>/interactions/<interactionId>/withdraw
{"reason": "<what the comment decided, and that the next round replaces this card>"}
```

Send the normal `Authorization` and `X-Paperclip-Run-Id` headers; the response reads `status: cancelled`. Then `GET /interactions` and require exactly one live card or none — a cancelled card beside a reissued one is the normal state, two `pending` cards is not. A withdrawn card keeps its idempotency key, so a replacement on the same issue needs a different key (`verdicts:<issueId>:round-<k>-corrected`), not the plain one.

