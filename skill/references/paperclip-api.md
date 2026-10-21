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

Use `terminal` with `curl` for these calls: unattended runs refuse `execute_code`, so a Python HTTP client is not an option.

## Read the issue and comments

```bash
curl -s "${AUTH[@]}" "$API/issues/$ISSUE_ID" | jq '{id, identifier, title, status, assigneeAgentId}'
curl -s "${AUTH[@]}" "$API/issues/$ISSUE_ID/comments" | jq '.[] | {id, author, body}'
```

## Comment

```bash
curl -s -X POST "${AUTH[@]}" -H 'Content-Type: application/json' \
  -d '{"body":"Submitted three variants: job ids ..."}' \
  "$API/issues/$ISSUE_ID/comments" | jq '{id, createdAt}'
```

To attach files, upload them first (below), then add their ids to the same comment:

```bash
curl -s -X POST "${AUTH[@]}" -H 'Content-Type: application/json' \
  -d '{"body":"Round 1 renders attached.","attachmentIds":["<attachment-id>"]}' \
  "$API/issues/$ISSUE_ID/comments" | jq '{id, createdAt}'
```

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

## Read the verdicts back

```bash
curl -s "${AUTH[@]}" "$API/issues/$ISSUE_ID/interactions" \
  | jq '.[] | select(.kind=="request_item_verdicts") | {id, status, result}'
```

The interaction's `result.items[]` carries `verdict` and `reason` for each resolved item. The wake payload lists the newly resolved item ids in `newlyResolvedItemIds`; handle only those, so an earlier round is not processed twice.

## Pitfalls

- **Always prefix paths with `/api`.** The bare origin returns the SPA as HTML with HTTP 200, which looks like success and is not.
- **A 500 on attachment upload is usually the S3 store, not your request.** The attachments route writes to `storage.s3.endpoint` (MinIO on the OMV box). Read `~/.paperclip/instances/default/logs/service.log` for the `ERROR: POST .../attachments 500` line: `connect EHOSTUNREACH <ip>:9000` means the Paperclip process cannot reach MinIO, while `curl http://<endpoint>/minio/health/live` and a fresh `node` connect from your own shell still succeed. Confirm the field name is right first — `file` is the only accepted multipart field, other names return 400, not 500. Restarting Paperclip alone does not cure this, so do not promise that it will: macOS local-network privacy blocks the Homebrew `node` binary from LAN hosts even though `curl` and a fresh `node` launched from your own shell reach the same address, and the durable fix is a **localhost relay** — a launchd job (e.g. `io.paperclip.minio-proxy`) running the system `python3` on `127.0.0.1:9000` and forwarding to `<lan-host>:9000` — with `storage.s3.endpoint` in `~/.paperclip/instances/default/config.json` pointed at `http://127.0.0.1:9000`, then the service restarted. That is the board owner's change, never yours. Keep the renders in staging, comment the diagnosis with the log line, set one monitor for a retry, and if the retry still fails, block the issue with a `request_confirmation` (see the block recipe above). Never restart the board yourself, and never rebuild the same image hoping the store comes back.
- **Check the store before blaming your request.** Run `curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:9000/minio/health/live`. A 200 means MinIO and the relay are fine and the fault is inside the board process; a failure means the relay or the OMV box is down.
- **A `request_item_verdicts` item `description` is capped at 500 characters.** A longer one fails the whole card with `400 Validation error ... path: ["payload","items",0,"description"]`. Put the prompt summary, the why and the self-check note in those 500 characters, and check with `jq -r '.payload.items[] | "\(.label) \(.description|length)"'` before posting; the fuller story belongs in `detailsMarkdown` (20000 chars).
- **Cancel an interaction yourself with `withdraw`, not `cancel`.** `POST /api/issues/<id>/interactions/<interactionId>/cancel` is board-only and answers `403 Agent actors cannot cancel issue-thread interactions through this board-only route`. `POST .../withdraw` with `{"reason":"..."}` is allowed for the card's creator and the issue's current assignee, and settles it as `cancelled` — the right way to clear a card made moot by someone else's fix.
- **An empty PATCH body means the write failed.** Investigate the response and re-read the issue; do not assume the status or monitor landed.
- **Unattended runs refuse `execute_code`.** Use `terminal` with `curl`, as above.
- **Monitor timestamps are ISO-8601 UTC with a `Z` suffix.** `datetime.isoformat()` returns `+00:00`; strip it before sending.
- **The run id is required on mutations.** A write without `X-Paperclip-Run-Id` is rejected or misattributed.
- **An agent cannot cancel or dismiss an interaction.** `POST .../interactions/<id>/cancel` is a board-only route (`403 Agent actors cannot cancel issue-thread interactions through this board-only route`). A confirmation card you opened for a blocker that later cleared stays `pending` and competes with the round's verdict card; say plainly on the issue that it is moot and ask the board to dismiss it, rather than opening a second card to cover the first.
- **`curl --data-binary @~/file` does not expand `~`.** curl takes the path literally and fails with `option --data-binary: error encountered when reading a file`. Use `$HOME/...` or an absolute path.
- **Comments come back newest-first.** `.[0]` is the latest comment; `.[-1]` is the oldest, which makes a comment you just posted look missing.
