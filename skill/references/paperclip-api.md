# Paperclip API for Matejko

Matejko's own key plus `curl`. These are the only calls the review loop needs. The endpoint is the local Paperclip API; the workspace is `http://127.0.0.1:3100/api`.

## Auth

Load the key without printing it:

```bash
API=http://127.0.0.1:3100/api
KEY=$(sed -n 's/^PAPERCLIP_API_KEY=//p' ~/.hermes/profiles/matejko/.env)
RUN_ID="<run id from the wake payload>"
COMPANY_ID="<company id from the wake payload>"
ISSUE_ID="<issue id from the wake payload>"

AUTH=(-H "Authorization: Bearer $KEY" -H "X-Paperclip-Run-Id: $RUN_ID")
```

Send `Authorization: Bearer $KEY` on every call, and `X-Paperclip-Run-Id` on every mutation (POST, PATCH, DELETE). Never echo `$KEY`, never put it in a comment, a log, or a commit. `~/.paperclip/auth.json` is the board's token and stays closed.

**`PAPERCLIP_COMPANY_ID` is not in the profile `.env`.** It only exists in the wake payload. A company-scoped URL built from the empty env var collapses to `/companies//issues/.../attachments` and the board answers **`404 API route not found`** — which reads like a wrong endpoint, not a missing variable. Take the company id from the wake payload and set it yourself:

```bash
CID=0e2eb054-4cb6-4ea1-a2e7-2b1894285d8c   # from the wake payload
curl -s -X POST "${AUTH[@]}" -F "file=@$PNG;type=image/png" \
  "$API/companies/$CID/issues/$ISSUE_ID/attachments"
```

The 404 also fires on `GET /api/companies/$CID/issues?...` for the same reason. When a company-scoped route 404s on a path you copied from the docs, check the variable before you check the route.

Use `terminal` with `curl` for these calls: unattended runs refuse `execute_code`, so a Python HTTP client is not an option.

## Read the issue and comments

```bash
curl -s "${AUTH[@]}" "$API/issues/$ISSUE_ID" | jq '{id, identifier, title, status, assigneeAgentId}'
curl -s "${AUTH[@]}" "$API/issues/$ISSUE_ID/comments" | jq '.[] | {id, author, body}'
```

## See who touched an issue, and who is queued next

`GET /api/issues/<id>/activity` is the per-issue event log: it names every actor, the action and the run id, newest first. It answers "did another run already work this issue, and is one live right now" without a runs listing:

```bash
curl -s "${AUTH[@]}" "$API/issues/$ISSUE_ID/activity" \
  | jq '.[] | {action, runId, actorType, createdAt}'
```

Use it after creating a card to confirm nothing but your own run has touched it, and to tell a finished action from one still in flight. `GET /api/agents/me/inbox-lite` answers the other half: which issues are assigned to you and in what state, so you can confirm a freshly created card is queued for the next heartbeat.

## Comment

```bash
curl -s -X POST "${AUTH[@]}" -H 'Content-Type: application/json' \
  -d '{"body":"Submitted three variants: job ids ..."}' \
  "$API/issues/$ISSUE_ID/comments" | jq '{id, createdAt}'
```

To attach files, upload them first (below), then post a comment that carries their ids:

```bash
curl -s -X POST "${AUTH[@]}" -H 'Content-Type: application/json' \
  -d '{"body":"Round 1 renders attached.","attachmentIds":["<attachment-id>"]}' \
  "$API/issues/$ISSUE_ID/comments" | jq '{id, createdAt}'
```

Linking works, but the POST response does not prove it: `attachmentIds` comes back empty even when the files really are attached. Read the attachments back and check `issueCommentId` — that link is what makes the PNGs render in the thread, and it is the only reliable proof:

```bash
curl -s "${AUTH[@]}" "$API/issues/$ISSUE_ID/attachments" | jq '.[] | {id, originalFilename, issueCommentId}'
```

The `comment` field of `PATCH /issues/{id}` has no `attachmentIds`, so an upload made before the status PATCH stays unlinked (`issueCommentId: null`) and never renders in the thread. Post one short comment carrying the ids after the PATCH; it is the only call that links them.

## PATCH the status

Include the evidence comment in the same PATCH when the transition needs one (for example `done`):

```bash
curl -s -X PATCH "${AUTH[@]}" -H 'Content-Type: application/json' \
  -d '{"status":"in_review","comment":"Round 1 is on the verdict card."}' \
  "$API/issues/$ISSUE_ID" | jq '{id, status}'
```

Statuses used here: `in_progress` while rendering, `in_review` while the card is pending, `done` when every slot is approved, `blocked` when the board itself needs Wojtek (recipe below).

## Block to ask Wojtek for an action

`PATCH {"status":"blocked"}` on its own is rejected with **422** (`Entering blocked requires unresolved blockers, a pending interaction/approval, or unblockDescriptor`), and an agent may only name *itself* in `unblockDescriptor.owner` (403 otherwise) — so you cannot hand the block to the board or to Wojtek directly. For anything that needs him at the machine, open a confirmation card first, then the block is legal and the card is what wakes you back:

```bash
jq -n '{kind:"request_confirmation", resolverPolicy:"human_only", continuationPolicy:"wake_assignee",
  idempotencyKey:"<slug>-action-1", title:"<what he must do>",
  summary:"<one line: what is blocked and why>",
  payload:{version:1, prompt:"I did it — go ahead.", acceptLabel:"Done, go ahead",
    rejectLabel:"Not now", rejectRequiresReason:true, rejectReasonLabel:"What should I do instead?",
    detailsMarkdown:"<evidence: the error, what you ruled out, where the files are>"}}' > /tmp/ask.json
curl -s -X POST "${AUTH[@]}" -H 'Content-Type: application/json' --data-binary @/tmp/ask.json \
  "$API/issues/$ISSUE_ID/interactions" | jq '{id, kind, status, continuationPolicy}'
curl -s -X PATCH "${AUTH[@]}" -H 'Content-Type: application/json' -d '{"status":"blocked"}' \
  "$API/issues/$ISSUE_ID" | jq '{identifier, status}'
```

`resolverPolicy: "human_only"` keeps the card for Wojtek alone. A blocked issue carries no monitor, so do not set both: the card is the only thing that brings the work back. Verify by re-reading the issue (`status: blocked`) and the interactions list (`status: pending`).

## Schedule a monitor

The issue must be assigned to Matejko and be `in_progress` or `in_review`. Use `scheduledBy: "assignee"`, and take the wait from the last queued job's `eta_minutes` rather than a fixed number.

```bash
ETA=$(imagegen status "$JOB_LAST" | jq -r '.eta_minutes')
NEXT=$(ETA="$ETA" python3 -c 'import datetime, os; print((datetime.datetime.now(datetime.UTC)+datetime.timedelta(minutes=int(os.environ["ETA"])+5)).isoformat().replace("+00:00","Z"))')
BODY=$(printf '{"executionPolicy":{"monitor":{"nextCheckAt":"%s","scheduledBy":"assignee","notes":"render ETA"}}}' "$NEXT")
curl -s -X PATCH "${AUTH[@]}" -H 'Content-Type: application/json' -d "$BODY" \
  "$API/issues/$ISSUE_ID" | jq '{id, status, assigneeAgentId, assigneeUserId, monitorNextCheckAt}'
```

Confirm the response carries a non-null `monitorNextCheckAt` (or `executionPolicy.monitor.nextCheckAt`). If the field is null or the body is empty, the write failed; re-read the issue before ending the run. The monitor only fires when the issue has an agent assignee, a null user assignee, and is `in_progress` or `in_review`.

## Upload an attachment

`POST` multipart field `file` to the company-scoped endpoint, and keep the returned id. Use the path `imagegen fetch` printed: the fetched filename is `<slug>-<8 hex>.png`, so a hand-built `<slug>.png` path will not exist.

```bash
PNG="$PNG_A"   # the path imagegen fetch printed, e.g. .../2026-10-21/gitops-header-a-7f3a9c21.png
UPLOAD=$(curl -s -X POST "${AUTH[@]}" \
  -F "file=@$PNG;type=image/png" \
  "$API/companies/$COMPANY_ID/issues/$ISSUE_ID/attachments")
echo "$UPLOAD" | jq '{id, filename, contentType, size}'
AID=$(echo "$UPLOAD" | jq -r '.id // empty')
```

The returned `id` is the `attachmentId` used by the verdict card and by comment `attachmentIds`.

A `201` is not proof the file landed. Read it back before it goes on a card — this returns `200` and the byte count you just uploaded:

```bash
curl -s -o /dev/null -w 'HTTP=%{http_code} bytes=%{size_download}\n' "${AUTH[@]}" "$API/attachments/$AID/content"
```

## Create the item-verdict card

One card per round, one item per image. `items[].id` is a short stable key; `items[].label` is the slug; `items[].description` is the prompt summary plus the why.

```bash
cat >/tmp/verdict-card.json <<'JSON'
{
  "kind": "request_item_verdicts",
  "resolverPolicy": "human_only",
  "title": "Pick the header for the GitOps post",
  "summary": "Round 1: three variants, each 1216x832.",
  "continuationPolicy": "wake_assignee",
  "idempotencyKey": "verdicts:<issueId>:round-1",
  "payload": {
    "version": 1,
    "prompt": "Approve the image that fits the post, reject the rest.",
    "detailsMarkdown": "All three are in the issue attachments. Reject with a reason and I will revise that prompt.",
    "items": [
      {
        "id": "variant-a",
        "label": "gitops-forklift-a",
        "description": "Forklift lifting a server rack. Why: the post opens on the migration metaphor.",
        "attachmentId": "<attachment-id>"
      }
    ],
    "verdicts": ["approve", "reject", "defer"],
    "requireReasonOn": ["reject"],
    "reasonLabel": "What should change?"
  }
}
JSON

curl -s -X POST "${AUTH[@]}" -H 'Content-Type: application/json' \
  --data-binary @/tmp/verdict-card.json \
  "$API/issues/$ISSUE_ID/interactions" | jq '{id, kind, status, continuationPolicy, idempotencyKey}'
```

Replace `<issueId>` in the idempotency key with the real issue id, and increment `round-<n>` per round. Reuse the same key when retrying the same card; a new round gets a new key.

Two constraints on the payload that surface only as rejections:

- **`items[].description` is capped at 500 characters.** A longer one fails the whole POST with `400 Validation error` / `code: "too_big"` / `path: ["payload","items",0,"description"]`. Draft the prompt summary, the why and the self-check note to fit, then check before submitting: `jq -r '.payload.items[] | "\(.label) \(.description|length)"' /tmp/verdict-card.json`.
- **Set `resolverPolicy: "human_only"` on a verdict card.** The default is inherited `anyone`, which would let an agent resolve its own image verdict — the one thing your rules forbid.

**Build the payload with `scripts/build-verdict-card.py`, not by hand.** The card is frozen at the POST, so both failure modes above have to be caught before it goes up. The script takes a spec file (shape: `templates/verdict-card-spec.json`), bakes in `human_only`, `wake_assignee`, `allowBulkApprove`, `supersedeOnUserComment` and the `verdicts:<issueId>:round-<n>` key, asserts the 500-character cap per item, and exits non-zero without writing anything when a field is missing or a description is too long:

```bash
python3 ~/.hermes/profiles/matejko/skills/image-studio/scripts/build-verdict-card.py \
  "$SPEC" --out "$SCRATCH/verdict-card.json"
```

Read the printed per-item lengths before posting — they are the check that the cap was honoured.

## Read the verdicts back

```bash
curl -s "${AUTH[@]}" "$API/issues/$ISSUE_ID/interactions" \
  | jq '.[] | select(.kind=="request_item_verdicts") | {id, status, result}'
```

The interaction's `result.items[]` carries `verdict` for each resolved item, and a `reason` **only when the resolver gave one**. An approval with no reason has no `reason` key at all — read it as a missing key, never as an empty string to fill in, and never as licence to invent the reason he withheld. The wake payload lists the newly resolved item ids in `newlyResolvedItemIds`; handle only those, so an earlier round is not processed twice.

## Write an issue document (the runner's queue table)

`PUT /api/issues/{issueId}/documents/{key}` creates and updates alike. For an existing document, send the body with `baseRevisionId` set to the `latestRevisionId` from a `GET` of the same key; omit it for a new document.

**A document PUT needs the issue checked out by your run.** The write is scoped to the run, so a PUT to an issue another run holds — or one no run holds — answers `409` with `{"error":"Issue run ownership conflict","details":{... "checkoutRunId":null,"executionRunId":null ...}}`. That is **not** a stale-revision conflict, and no amount of re-fetching the revision fixes it. Claim the issue first:

```bash
curl -s -X POST "${AUTH[@]}" -H 'Content-Type: application/json' \
  -d '{"agentId":"'"$AGENT_ID"'","expectedStatuses":["todo","backlog","blocked","in_review","in_progress"]}' \
  "$API/issues/$ISSUE_ID/checkout" | jq '{identifier, status, checkoutRunId}'
```

The body needs **both** `agentId` and `expectedStatuses`; an empty `{}` answers `400 Validation error` naming `agentId` and `expectedStatuses` as the missing paths. A successful checkout answers `200` with the issue JSON and `checkoutRunId` set to your run. Re-read the issue and confirm `checkoutRunId` equals your run id before the PUT — a `200` on the checkout is the proof, not the absence of an error.

**There are two different `409`s on this route, and they have different fixes.** A stale `baseRevisionId` means someone else wrote the document since your GET: fetch the latest revision and merge, never overwrite blind. A run-ownership conflict means the issue is not yours to write: checkout the issue and PUT again. Read `error` in the response body to tell them apart — a run-ownership conflict names `Issue run ownership conflict` and carries a `details` object; a stale revision carries a revision conflict instead.

For the runner's `queue` document, `scripts/put-queue-doc.py --issue-id <runnerId> --run-id <runId>` does the whole thing: it builds the body from `queue.json` and the briefs, fetches the current revision, PUTs it and prints the new `latestRevisionId`. Use it instead of hand-building the payload; the manual shape is below for any other document key. **The script does not check the issue out for you** — when it answers `HTTP 409 error: None`, the runner is not held by your run, so claim the runner with the checkout call above and run the script again. A `409` from this script means "the runner is not yours right now", not "the document changed".

```bash
python3 ~/.hermes/profiles/matejko/skills/image-studio/scripts/put-queue-doc.py \
  --issue-id "$ISSUE_ID" --run-id "$RUN_ID"

python3 -c "
import json
body=open('/tmp/queue-body.md').read()
json.dump({'title':'Queue','format':'markdown','body':body,'baseRevisionId':'$REV'}, open('/tmp/queue-put.json','w'))
"
curl -s -X PUT "${AUTH[@]}" -H 'Content-Type: application/json' --data-binary @/tmp/queue-put.json \
  "$API/issues/$ISSUE_ID/documents/queue" | jq '{latestRevisionId}'
```

The `PUT` response carries the new `latestRevisionId` and the saved body — that response is the proof the document landed.

## Pitfalls

- **Creating an issue under a parent that the target assignee created is refused with `409` and a `delegation_cycle` error.** The board treats "issue whose ancestor was created by the agent I am assigning it to" as a delegation loop and rejects the create. The fix is not to hunt for a different parent: create the issue **without** `parentId` (keep `projectId` so it still lands in the right project) and say in the description what it serves. A follow-up PATCH to attach the parent afterwards is refused too — a write to an issue outside your run's live context answers `cross_iss` — so the parentless create is the shape that works, not a workaround for a failed one.
- **Always prefix paths with `/api`.** The bare origin returns the SPA as HTML with HTTP 200, which looks like success and is not.
- **A `409` on a document PUT is usually a run-ownership conflict, not a stale revision.** The response says `Issue run ownership conflict` and names `checkoutRunId`/`executionRunId` in `details`; the fix is to `POST /api/issues/{id}/checkout` with `{"agentId": ..., "expectedStatuses": [...]}` and PUT again, not to re-fetch the revision. An empty checkout body `{}` answers `400` naming `agentId` and `expectedStatuses` as the missing fields.
- **A 500 on attachment upload is usually the S3 store, not your request.** The attachments route writes to `storage.s3.endpoint` (MinIO on the OMV box). Read `~/.paperclip/instances/default/logs/service.log` for the `ERROR: POST .../attachments 500` line: `connect EHOSTUNREACH <ip>:9000` means the Paperclip process cannot reach MinIO, while `curl http://<endpoint>/minio/health/live` and a fresh `node` connect from your own shell still succeed. Confirm the field name is right first — `file` is the only accepted multipart field, other names return 400, not 500. Restarting Paperclip alone does not cure this, so do not promise that it will: macOS local-network privacy blocks the Homebrew `node` binary from LAN hosts even though `curl` and a fresh `node` launched from your own shell reach the same address, and the durable fix is a **localhost relay** — a launchd job (e.g. `io.paperclip.minio-proxy`) running the system `python3` on `127.0.0.1:9000` and forwarding to `<lan-host>:9000` — with `storage.s3.endpoint` in `~/.paperclip/instances/default/config.json` pointed at `http://127.0.0.1:9000`, then the service restarted. That is the board owner's change, never yours. Keep the renders in staging, comment the diagnosis with the log line, set one monitor for a retry, and if the retry still fails, block the issue with a `request_confirmation` (see the block recipe above). Never restart the board yourself, and never rebuild the same image hoping the store comes back.
- **Check the store before blaming your request.** Run `curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:9000/minio/health/live`. A 200 means MinIO and the relay are fine and the fault is inside the board process; a failure means the relay or the OMV box is down.
- **A `request_item_verdicts` item `description` is capped at 500 characters.** A longer one fails the whole card with `400 Validation error ... path: ["payload","items",0,"description"]`. Put the prompt summary, the why and the self-check note in those 500 characters, and check with `jq -r '.payload.items[] | "\(.label) \(.description|length)"'` before posting; the fuller story belongs in `detailsMarkdown` (20000 chars).
- **Cancel an interaction yourself with `withdraw`, not `cancel`.** `POST /api/issues/<id>/interactions/<interactionId>/cancel` is board-only and answers `403 Agent actors cannot cancel issue-thread interactions through this board-only route`. `POST .../withdraw` with `{"reason":"..."}` is allowed for the card's creator and the issue's current assignee, and settles it as `cancelled` — the right way to clear a card made moot by someone else's fix.
- **There is no PATCH route for an issue-thread interaction.** `GET /api/openapi.json` lists only `GET|POST /api/issues/{id}/interactions` and the per-interaction `accept`, `cancel`, `reject`, `resolve-from-comment`, `respond`, `skip`, `verdicts`, `withdraw` — no `PATCH /api/issues/{id}/interactions/{id}`. A `PATCH` there answers `404 API route not found`. So a card's `items[].description` and `detailsMarkdown` are **frozen once the card is created**: get the wording right before the POST, because there is no second edit. If you discover a needed correction after the card is live, put it in an issue comment instead — your own agent comment does not supersede the card (`supersedeOnUserComment` only fires for a board/user comment), so the card stays `pending` and the finding still reaches Wojtek in the thread. Re-creating the card with a new idempotency key would leave two open cards for one round. **Unless you withdraw the first one: a withdrawn card settles as `cancelled`, and a cancelled card is not a pending card, so withdraw-then-re-post leaves exactly one card open for the round.** That is the right path when the card's own text is wrong — a check note you later disproved, which Wojtek would otherwise judge from — and the wrong path for new information that merely adds context. Withdraw with a reason naming what changed, so the thread records the correction:

```bash
curl -s -X POST \"${AUTH[@]}\" -H 'Content-Type: application/json' \
  -d '{\"reason\":\"What was wrong and what the correction is\"}' \
  \"$API/issues/$ISSUE_ID/interactions/$CARD_ID/withdraw\" | jq '{id, status}'
```

Then post the corrected card under a new key (`verdicts:<issueId>:round-<k>-corrected`) and verify with `GET /interactions` that exactly one card is `pending` and the other `cancelled`.
- **A PATCH that answers 200 with the OLD status means the body never reached the server.** An empty or 0-byte body is not a validation error — the board answers 200 with the issue unchanged and no `error` field, so the response reads like a success. Always check that the echoed `status` is the status you sent, and re-read the issue when it is not. The usual cause is a payload file written by a script that failed: a python writer that raises leaves the redirect target 0 bytes, and the board then answers 400 with `id: null`.
- **Build JSON payloads with a `write_file` script, not a heredoc inside a shell script.** A heredoc python block inside a `terminal` call stalls and returns `BLOCKED`; inside a `.sh` file it runs, but its traceback scrolls past and the shell keeps going, so a broken payload gets posted anyway. Write the payload builder to the scratch directory with `write_file`, run it as its own call, and check the byte size of the file before POSTing it. When the builder prints JSON to stdout use `json.dump(obj, sys.stdout)` — `json.dump(obj, open(sys.stdout, 'w'))` raises `TypeError` on an already-open stream and writes nothing.
- **Unattended runs refuse `execute_code`.** Use `terminal` with `curl`, as above.
- **Monitor timestamps are ISO-8601 UTC with a `Z` suffix.** `datetime.isoformat()` returns `+00:00`; strip it before sending.
- **The run id is required on mutations.** A write without `X-Paperclip-Run-Id` is rejected or misattributed.
- **An agent cannot cancel or dismiss an interaction.** `POST .../interactions/<id>/cancel` is a board-only route (`403 Agent actors cannot cancel issue-thread interactions through this board-only route`). A confirmation card you opened for a blocker that later cleared stays `pending` and competes with the round's verdict card; say plainly on the issue that it is moot and ask the board to dismiss it, rather than opening a second card to cover the first.
- **`curl --data-binary @~/file` does not expand `~`.** curl takes the path literally and fails with `option --data-binary: error encountered when reading a file`. Use `$HOME/...` or an absolute path.
- **Multi-line shell commands and heredocs stall on an approval prompt.** A `terminal` call that mixes `set -a; . .env`, a `for` loop and a heredoc can block for a minute and return `BLOCKED` without running anything. Keep each call one line: extract the key with `KEY=$(sed -n 's/^PAPERCLIP_API_KEY=//p' ...)`, chain with `;`, and write JSON bodies with `write_file` then `curl --data-binary @<abs path>`. One call per attachment upload is fine.
- **A heredoc python block is the same stall in a new shape.** `python3 - <<'PY' ... PY` inside a `terminal` call blocks for a minute and returns `BLOCKED` with nothing executed. Put the script in the scratch directory with `write_file` and run it as a second call: `write_file` → `python3 /Users/paperclip/.hermes/profiles/matejko/cache/scratch/<name>.py`. The script may hold the API key, read it from the profile `.env`, and shell out to `curl` — that keeps the key out of the command line and out of the log.
- **`request_item_verdicts` defaults `supersedeOnUserComment` to `false`.** The parent brief's round-1 legend says "a comment closes the card"; if the card must behave that way, set `"supersedeOnUserComment": true` explicitly. With the default, a comment arrives as its own wake and the card stays `pending` — the milder, usually better behaviour, but then do not promise on the card that a comment closes it. Only a board/user comment supersedes: your own agent comment, including the attachment-linking one, leaves the card `pending`, so evidence comments on an open card are safe — re-read the interactions list to confirm it is still `pending` rather than assuming.
- **A user comment on a `done` issue reopens it.** The comment makes the issue `in_progress` and wakes you; it does not undo the work the issue already did. Answer the question on the issue and set the status back to `done` with the answer in the same PATCH — do not redo the closed work.
- **Comments come back newest-first.** `.[0]` is the latest comment; `.[-1]` is the oldest, which makes a comment you just posted look missing.
- **`$API` already ends in `/api`, so `$API/api/...` doubles the path and answers 404.** The auth block sets `API=http://127.0.0.1:3100/api` and every route here is written `$API/<route>`. A doubled path returns a 404 with a body of a few dozen bytes — that byte count, not the status alone, tells you the path was wrong rather than the attachment missing. Re-run the read-back as `$API/attachments/<id>/content` before believing an upload failed.
