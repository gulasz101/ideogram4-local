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

Statuses used here: `in_progress` while rendering, `in_review` while the card is pending, `done` when every slot is approved.

## Schedule a monitor

The issue must be assigned to Matejko and be `in_progress` or `in_review`. Use `scheduledBy: "assignee"`.

```bash
NEXT=$(python3 -c 'import datetime; print((datetime.datetime.now(datetime.UTC)+datetime.timedelta(minutes=26)).isoformat().replace("+00:00","Z"))')
BODY=$(printf '{"executionPolicy":{"monitor":{"nextCheckAt":"%s","scheduledBy":"assignee","notes":"render ETA"}}}' "$NEXT")
curl -s -X PATCH "${AUTH[@]}" -H 'Content-Type: application/json' -d "$BODY" \
  "$API/issues/$ISSUE_ID" | jq '{id, status, executionPolicy}'
```

Confirm the response carries a non-null `monitorNextCheckAt` (or `executionPolicy.monitor.nextCheckAt`). If the field is null or the body is empty, the write failed; re-read the issue before ending the run.

## Upload an attachment

`POST` multipart field `file` to the company-scoped endpoint, and keep the returned id:

```bash
PNG=~/image-studio/staging/2026-10-21/gitops-header-a.png
UPLOAD=$(curl -s -X POST "${AUTH[@]}" \
  -F "file=@$PNG;type=image/png" \
  "$API/companies/$COMPANY_ID/issues/$ISSUE_ID/attachments")
echo "$UPLOAD" | jq '{id, filename, contentType, size}'
AID=$(echo "$UPLOAD" | jq -r '.id // empty')
```

The returned `id` is the `attachmentId` used by the verdict card and by comment `attachmentIds`.

## Create the item-verdict card

One card per round, one item per image. `items[].id` is a short stable key; `items[].label` is the slug; `items[].description` is the prompt summary plus the why.

```bash
cat >/tmp/verdict-card.json <<'JSON'
{
  "kind": "request_item_verdicts",
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

## Read the verdicts back

```bash
curl -s "${AUTH[@]}" "$API/issues/$ISSUE_ID/interactions" \
  | jq '.[] | select(.kind=="request_item_verdicts") | {id, status, result}'
```

The interaction's `result.items[]` carries `verdict` and `reason` for each resolved item. The wake payload lists the newly resolved item ids in `newlyResolvedItemIds`; handle only those, so an earlier round is not processed twice.

## Pitfalls

- **Always prefix paths with `/api`.** The bare origin returns the SPA as HTML with HTTP 200, which looks like success and is not.
- **An empty PATCH body means the write failed.** Investigate the response and re-read the issue; do not assume the status or monitor landed.
- **Unattended runs refuse `execute_code`.** Use `terminal` with `curl`, as above.
- **Monitor timestamps are ISO-8601 UTC with a `Z` suffix.** `datetime.isoformat()` returns `+00:00`; strip it before sending.
- **The run id is required on mutations.** A write without `X-Paperclip-Run-Id` is rejected or misattributed.
