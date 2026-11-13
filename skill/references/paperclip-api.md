# Paperclip API for Matejko

Matejko's own key plus curl. Endpoint `http://127.0.0.1:3100/api`. Use `terminal` with curl; unattended runs refuse `execute_code` (python scripts run fine).

## Auth

```bash
API=http://127.0.0.1:3100/api
KEY=$(sed -n 's/^PAPERCLIP_API_KEY=//p' ~/.hermes/profiles/matejko/.env)
RUN_ID="<run id from the wake payload>"
COMPANY_ID="<company id from the wake payload>"
ISSUE_ID="<issue id from the wake payload>"
AUTH=(-H "Authorization: Bearer ***" -H "X-Paperclip-Run-Id: $RUN_ID")
```

Rules:
- Send `Authorization: Bearer ***` on every call and `X-Paperclip-Run-Id` on every mutation.
- Never echo `$KEY`, never in comments/logs/commits. `~/.paperclip/auth.json` stays closed.
- `404 {"error":"Issue not found"}` on a wake-payload uuid is usually a header bug: board answers 404 not 401 when identity unreadable. Check header name and `Bearer` prefix before re-reading payload. Bare `X-Api-Key`/`X-Paperclip-Api-Key` -> `GET /api/agents/me` returns `401 {"error":"Agent authentication required"}`. Same 404 on `/issues/<id>/attachments`. Prove key in same call: `GET /api/agents/me` printing id+name, plus non-empty `checkoutRunId` on issue.
- Source profile .env with `set -a`: `. ~/.hermes/profiles/matejko/.env` sets shell vars only; python child dies on KeyError. Use `set -a; . <file>; set +a`. Each terminal call is its own shell, repeat export. Prove: `python3 -c 'import os; print(os.environ.get("PAPERCLIP_API_URL"), len(os.environ.get("PAPERCLIP_API_KEY","")))'`.
- `~/.hermes/.env` is default profile and authenticates as Bill Cipher. Matejko key only in `~/.hermes/profiles/matejko/.env`. Sourcing default makes writes land under CEO with no failure. Source `$HERMES_HOME/.env` or spell profile path. Prove principal before first mutation:
```bash
curl -s "${AUTH[@]}" "$API/agents/me" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["id"], d["name"])'
# must print: 332563dd-7ce2-4bad-8bb9-6b61f3f7221e Matejko
```
Wrong key + own run id -> `403 cross_issue_influence_run_context_required` ("This request arrived without a valid run") on own issue. Re-uploading doesn't undo wrong-principal write: read `createdByAgentId`, `DELETE /api/attachments/<id>`, upload again, check `createdByAgentId`.
- `PAPERCLIP_COMPANY_ID` not in .env; only wake payload. Empty env -> `/companies//issues/...` -> `404 API route not found`. Set from wake payload.
```bash
CID=0e2eb054-4cb6-4ea1-a2e7-2b1894285d8c
curl -s -X POST "${AUTH[@]}" -F "file=@$PNG;type=image/png" "$API/companies/$CID/issues/$ISSUE_ID/attachments"
```
- Use terminal with curl; python scripts work via write_file then run.
- Unattended approval gate: `approvals.mode: manual`, 60s timeout. Compound commands (loops, heredocs in $()) refused with `BLOCKED`. One command per call; script file for multi-step; never re-run refused command expecting different. A refused mutation prints nothing and exits 0. Use `npx --yes paperclipai issue comment <issue> --body "$BODY" --api-base http://127.0.0.1:3100 --api-key "$KEY" --run-id <run> --json` for writes; `--api-base` must NOT carry `/api` (CLI appends). CLI has no `--body-file`; multi-line via `--body "$(cat <path>)"`; `--json` makes response readable.
- Wake can arrive with issue not checked out: `checkoutRunId: null`, `executionRunId: null`; writes answer `Issue run ownership conflict`. Read `checkoutRunId` first; if null, `POST /issues/<id>/checkout` with `{"agentId":...,"expectedStatuses":["todo","backlog","blocked","in_review","in_progress"]}` before first write. Moves to in_progress.

## Read the issue and comments

```bash
curl -s "${AUTH[@]}" "$API/issues/$ISSUE_ID" | jq '{id, identifier, title, status, assigneeAgentId}'
curl -s "${AUTH[@]}" "$API/issues/$ISSUE_ID/comments" | jq '.[] | {id, author, body}'
```

## Find an issue

`GET /api/companies/$CID/issues?limit=200` returns oldest 200, not newest. Recent issue via single status filter or offset: `?status=in_review&limit=50` newest-first; `?limit=50&offset=200`. Match on `identifier`, not `key`/`number`. Comma multi-value status + limit -> `{"error":"API route not found"}`; single-value works; `?q=<identifier>` returns issue plus loose matches; `?q=` full title may return empty. Bare list + client-side filter; keep key out of command line:
```python
p = subprocess.run(["curl","-s","-H",f"Authorization: Bearer ***", f"{API}/companies/{COMPANY}/issues"], capture_output=True, text=True)
items = json.loads(p.stdout)
items = items if isinstance(items, list) else items.get("issues", [])
for i in items:
    if i.get("identifier") == "GUL-72":
        print(i["id"], i["status"], i["title"])
```
Truncated uuid -> `404 {"error":"Issue not found"}`; resolve full id at list; read `identifier` back off single GET. Keep fetch inside script; don't save list to file and open from inline python3 -c (large file scan refused). Shell out to curl from script or pipe.

## Comment body scanning

A `python3 - <<'PYEOF'` block carrying comment text inline is one shell string; approval guard reads words as command. Body naming render filename with blocked word refused `BLOCKED (hardline): system shutdown/reboot`. Write body to file with write_file and script reads it, or rephrase.

## See who touched an issue, and who is queued next

`GET /api/issues/<id>/activity` per-issue event log: actors, action, run id, newest first. Use after creating card. `GET /api/agents/me/inbox-lite` issues assigned and state.

## Comment

Comment POST is issue-scoped; company-scoped attachment path gives 404. Only issue creation and attachment upload carry `/companies/{cid}`.
```bash
curl -s -X POST "${AUTH[@]}" -H 'Content-Type: application/json' -d '{"body":"..."}' "$API/issues/$ISSUE_ID/comments" | jq '{id, createdAt}'
```
Body with backticks/$ goes through file, not shell string. Build with write_file, POST `--data-binary @<path>`, read body back.

Attach files: upload first, then comment with ids:
```bash
curl -s -X POST "${AUTH[@]}" -H 'Content-Type: application/json' -d '{"body":"Round 1 renders attached.","attachmentIds":["<attachment-id>"]}' "$API/issues/$ISSUE_ID/comments" | jq '{id, createdAt}'
```
Linking works but POST response doesn't prove it: `attachmentIds` empty even when attached. Read attachments back and check `issueCommentId`:
```bash
curl -s -H "Authorization: Bearer ***" "$API/issues/$ISSUE_ID/attachments" | jq '.[] | {id, originalFilename, issueCommentId, byteSize, sha256}'
```
Read-back may carry byteSize/sha256; compare sha256 with `shasum -a 256 <png>` and byteSize with file size. If row only id+contentType, hash file: no single-get route (`GET /api/attachments/<id>` 404); download `curl -s "$API/attachments/<id>/content" -o /tmp/att.png -w 'HTTP:%{http_code} bytes:%{size_download}\n'` then shasum. Matching hash + non-null issueCommentId = whole check. Count attachments; second row for same PNG means earlier upload.

Run-origin mismatch: upload succeeds but linking comment answers `issue_attachment_run_origin_mismatch` or upload bound to comment answers `issue_attachment_parent_run_mismatch`. Check header comment was written with: run id in wake payload changes every wake; hardcoded id posts comment owned by finished run. Fix constant to current run id, delete orphan uploads (`DELETE /api/attachments/<id>` 200), post linking comment again with current run id, check issueCommentId on every row. Stale comment stays, cannot delete; don't narrate.

Attachment can only be linked by run that uploaded it. Later run cannot carry someone else's attachment ids: POST 400 `issue_attachment_run_origin_mismatch`, attachment keeps `issueCommentId: null`, invisible. Don't re-upload to "fix"; files intact, verdict card referenced by attachmentId. Say plainly PNGs attached but invisible in thread, name vault paths. Upload-and-link pair in same run. Sanctioned exception: thread visibility on card he judges: upload same bytes again in current run and link those ids; read-back shows two rows for one file (accepted cost). Match rows by sha256 when counting.

Same rule decides which run can upload. Run creating card for later round can be refused `Issue run ownership conflict` on POST attachments because that run has different issue checked out. Nothing broken; files on disk: say in new issue creation comment where PNGs sit with byte sizes and sha256; run that later wakes on that issue (owner) uploads and links. No workaround with other token.

`comment` field of PATCH /issues/{id} has no attachmentIds; upload ids only in status PATCH stay unlinked. Post one short comment carrying ids; order against status PATCH doesn't matter. Don't re-post link because brief says must come after PATCH.

Post card with `scripts/post-interaction.py`, not hand-built mutating curl. `paperclip-write.py` covers comment/patch/monitor/read but no interaction POST. Payload large JSON whose bytes must be checked on disk. `python3 scripts/post-interaction.py <issue-id> <payload.json> <run-id>` sends file as-is with run-id header, prints created card id, kind, status, resolverPolicy, item ids, stored supersedeOnUserComment. One python call survives unattended surface.

## PATCH the status

Include evidence comment in same PATCH when transition needs one:
```bash
curl -s -X PATCH "${AUTH[@]}" -H 'Content-Type: application/json' -d '{"status":"in_review","comment":"Round 1 is on the verdict card."}' "$API/issues/$ISSUE_ID" | jq '{id, status}'
```
Field is `comment`; PATCH ignores unknown field. `{"status":"done","body":"..."}` drops note. Repair with separate POST comment. Post closing comment first and flip status second, two calls where first proves itself: write body with write_file, POST, read returned id, then PATCH {"status":"done"}. CLI close one-call: `npx paperclipai issue update <issue> --status done --comment "$(cat <abs body path>)" --api-base http://127.0.0.1:3100 --api-key "$KEY" --run-id <run> --json`; response echoes created comment (body, createdAt) beside issue; confirm status done on GET. Use two-call curl when issue held by another run's lease or comment linked to attachments; CLI otherwise.

Statuses: in_progress while rendering, in_review whenever card pending (verdict or confirmation), done when all slots approved. Pending card always in_review, never blocked.

Read verdict from interaction's status/resolvedAt to know settled, result.items[] to know decided; never payload.items[]. payload.items[].verdict null even after answered with resolvedAt. Answer under result: `{"version":1,"outcome":"resolved","complete":true,"items":[{"id":...,"verdict":"approve",...}]}`. Dump once and read result.items[].verdict. Approval with no reason has no reason key at all; missing answer never blank. outcome resolved + complete true + non-null resolvedByUserId distinguishes his verdict from agent settling (resolvedByAgentId). Issue status done and completedAt second witness; neither says which item approved.

404 on comment POST to path that worked a minute ago is flake; retry once. Confirm path shape already succeeded; if new, suspect path. Never report 404 write as landed; read returned comment id.

## Ask Wojtek for an action at the machine

For anything needing him at machine, open confirmation card and set issue in_review; card wakes you back. Don't block: blocked issue whose only unresolved blocker is card is what recovery strands; Paperclip prefers in_review for confirmation waits. PATCH {"status":"blocked"} alone rejected 422; agent may only name itself in unblockDescriptor.owner, so card makes block legal.
```bash
jq -n '{kind:"request_confirmation", resolverPolicy:"human_only", continuationPolicy:"wake_assignee", idempotencyKey:"<slug>-action-1", title:"<what he must do>", summary:"<one line>", payload:{version:1, prompt:"I did it — go ahead.", acceptLabel:"Done, go ahead", rejectLabel:"Not now", rejectRequiresReason:true, rejectReasonLabel:"What should I do instead?", detailsMarkdown:"<evidence>"}}' > /tmp/ask.json
curl -s -X POST "${AUTH[@]}" -H 'Content-Type: application/json' --data-binary @/tmp/ask.json "$API/issues/$ISSUE_ID/interactions" | jq '{id, kind, status, continuationPolicy}'
curl -s -X PATCH "${AUTH[@]}" -H 'Content-Type: application/json' -d '{"status":"in_review"}' "$API/issues/$ISSUE_ID" | jq '{identifier, status}'
```
resolverPolicy human_only keeps card for Wojtek alone. Verify by re-reading issue (in_review) and interactions (pending).

## Schedule a monitor

Issue assigned to Matejko and in_progress or in_review. Use scheduledBy "assignee"; wait from last queued job's eta_minutes.

Do arithmetic on date -u, never job timestamps (render host local time hour ahead UTC). eta_minutes only: date -u plus eta_minutes plus five.
```bash
ETA=$(imagegen status "$JOB_LAST" | jq -r '.eta_minutes')
NEXT=$(ETA="$ETA" python3 -c 'import datetime, os; print((datetime.datetime.now(datetime.UTC)+datetime.timedelta(minutes=int(os.environ["ETA"])+5)).isoformat().replace("+00:00","Z"))')
BODY=$(printf '{"executionPolicy":{"monitor":{"nextCheckAt":"%s","scheduledBy":"assignee","notes":"render ETA"}}}' "$NEXT")
curl -s -X PATCH "${AUTH[@]}" -H 'Content-Type: application/json' -d "$BODY" "$API/issues/$ISSUE_ID" | jq '{id, status, assigneeAgentId, assigneeUserId, monitorNextCheckAt}'
```
Confirm non-null monitorNextCheckAt or executionPolicy.monitor.nextCheckAt. Monitor only fires when agent assignee, null user assignee, in_progress/in_review.

PATCH whose JSON never written clears monitor: write payload with write_file (lints JSON), PATCH --data @path, read monitorNextCheckAt; null = failed arm. A run ending null monitor with render in flight strands render.

One collect wake after last ETA beats fetch per job when batch lands close. Read eta_minutes on last job, one check at ETA+5; split only when spread long enough early failure costs full re-render.

Deep queue makes eta slide; hop count not wait. Long monitor times silently dropped while two-hour hop persists; schedule two-hour hops even when ETA ten hours; write each hop's notes from queue's own numbers; re-read monitorNextCheckAt after PATCH.

Hop finding nothing finished reports nothing on thread. Re-arm from remaining eta_minutes; put state in queue note (`backlog.py note <n> "..."`). Comment only for hop that fetched, held back, or changed wait.

Monitor notes capped 500 chars; over-long fails whole PATCH 400 (too_big, maximum 500, path executionPolicy.monitor.notes), and status/blocker fields in same body lost. Write long wake plan in issue comment, keep notes to job id plus four things wake does. Check length before call and require HTTP 200 with non-null monitorNextCheckAt.

Monitor block eight fields, only nextCheckAt required (from openapi). Fields: nextCheckAt (date-time, required), notes (<=500), scheduledBy (assignee|board), timeoutAt (date-time), maxAttempts (int 1-100), recoveryPolicy (wake_owner|create_recovery_issue|escalate_to_board), kind (nullable, only enum external_service). Leave kind null for local render check. Server accepts monitor with nextCheckAt alone, echoes others null.

Give monitor bounds:
```bash
BODY=$(printf '{"executionPolicy":{"monitor":{"nextCheckAt":"%s","scheduledBy":"assignee","timeoutAt":"%s","maxAttempts":6,"recoveryPolicy":"wake_owner","notes":"<which job ids> poll imagegen status, fetch when done"}}}' "$NEXT" "$TIMEOUT")
```
timeoutAt render ETA + generous margin; maxAttempts fetch cycles + retries; recoveryPolicy wake_owner for render.

Re-arming monitor already fired takes minimal body, not bounded. Bounds already spent -> `Monitor bounds are already exhausted`, arms nothing, monitorNextCheckAt null. Re-arm send only nextCheckAt, scheduledBy, notes:
```bash
BODY='{"executionPolicy":{"mode":"normal","monitor":{"nextCheckAt":"<ISO 8601 UTC>","scheduledBy":"assignee","notes":"daily backlog watchdog"}}}'
```
Clearing monitor is not reset of budget. PATCH {"executionPolicy":{"monitor":null}} 200 leaves null, but budget belongs to issue; next bounded body still exhausted.

Read monitorAttemptCount back on every arm; long-lived issue spends budget across every wake. While room, re-arm with maxAttempts 100 so ceiling schema max. Once reaches, PATCH exhausted and null.

Monitor PATCH can answer 400 with empty body; cause body shape not schedule. Two shapes on long monitor history: top-level monitorNextCheckAt (field moved inside executionPolicy.monitor; unknown top-level key fails whole request) and maxAttempts near spent budget. When arm 400 no error string, send {"executionPolicy":{"monitor":{"nextCheckAt":...,"scheduledBy":"assignee","notes":"..."}}} with no maxAttempts or schema max 100; read executionState.monitor.nextCheckAt. Read accepted shape from openapi.

422 invalid_issue_disposition on in_review PATCH usually means card POST never landed. Board refuses agent-driven issue in_review when nothing owns next action. When fires right after card POST, re-read GET /interactions: 400 on card leaves card list empty; fix card body, never retry status PATCH. Send minimal body. Recurring monitor hits every tick: 24-hour reschedule never place for maxAttempts/timeoutAt. Whole watchdog tick in references/archive/runner-watchdog.md.

409 Issue run ownership conflict on in_review PATCH straight after card created means another run claimed new issue, not card wrong. Creator's uploads 201, linking comment 201, status PATCH 409 with details.checkoutRunId naming other run. Holder sets in_review when done. Post one comment stating what's in place; read status back next call. Recreating card/re-uploading/PATCHing different run id makes worse.

POST /issues/{id}/release usual reason to re-arm: drops monitor with checkout, released issue reads monitorNextCheckAt null, needs monitor written again not just assignee. Re-arm in second PATCH after one restoring status and assigneeAgentId; read issue back confirm non-null. Release doesn't always take monitor; read issue back after release and re-arm only if monitor actually null. PATCH carrying executionPolicy.monitor re-acquires issue's checkout, so re-arm undoes release.

## Upload an attachment

POST multipart field file to company-scoped endpoint; keep returned id. Use path imagegen fetch printed: fetched filename `<slug>-<8 hex>.png`, hand-built `<slug>.png` won't exist.
```bash
PNG="$PNG_A"
UPLOAD=$(curl -s -X POST "${AUTH[@]}" -F "file=@$PNG;type=image/png" "$API/companies/$COMPANY_ID/issues/$ISSUE_ID/attachments")
echo "$UPLOAD" | jq '{id, filename, contentType, size}'
AID=$(echo "$UPLOAD" | jq -r '.id // empty')
```
Returned id is attachmentId for verdict card and comment attachmentIds.

Upload helper shipped is one-call shape surviving approval gate, hands proof fields: `bash ~/agent-skills/hermes-paperclip/paperclip/scripts/paperclip-upload-artifact.sh <png> --no-work-product --output json` uploads; response carries id, sha256, byteSize, createdByAgentId. Export PAPERCLIP_COMPANY_ID, PAPERCLIP_TASK_ID, PAPERCLIP_RUN_ID first. --no-work-product keeps review render from creating artifact work product. List of four files in for loop still refused; run as several calls or script.

Whole round's uploads one python3 <script> call, not one curl per file. `scripts/open-card-issue.py` is that script - don't hand-write create-plus-upload per card. Takes --brief, --title, one --item <slot>=<png> per image, optional --link-body, writes {issue, identifier, ids} to --out:
```bash
python3 ~/.hermes/profiles/matejko/skills/image-studio/scripts/open-card-issue.py \
  --brief backlog/briefs/<post>-round-1-card.md \
  --title "Backlog review <n>/<total>: <post title>" \
  --item header=staging/<date>/<file>.png --item header-flux=staging/<date>/<file>.png \
  --link-body scratch/link-comment.md --out scratch/card-ids.json
```
Proves principal first, compares each 201's sha256/byteSize against file on disk, stops on mismatch, reads attachments back to confirm every row carries issueCommentId. Description compared with brief: create whose description not byte-identical to file means body came from elsewhere. A script building multipart body itself with urllib does whole set in single plain call and gets proof fields. Keep key out of output.

Upload can be bound to existing comment at creation time, fallback when comment POST refuses ids. Multipart body takes metadata field beside file: issueCommentId, a GUID. When linking POST run-origin error, post comment first, read id, then send each PNG with issueCommentId part ahead of file part; every 201 comes back with issueCommentId set and picture renders with no second linking call. Linking POST normal path; keep shape for retry.

Retry same file once before diagnosing 500 on upload. Bare 500 {"error":"Internal server error"} no details not yet store fault: multi-MB PNG refused once and identical bytes land 201 next call. First move same request again; only second failure go to service log for EHOSTUNREACH. Reporting "upload failed" after one 500 posts wrong diagnosis.

201 is not proof file landed. Read back before card:
```bash
curl -s -o /dev/null -w 'HTTP=%{http_code} bytes=%{size_download}\n' "${AUTH[@]}" "$API/attachments/$AID/content"
```

## Create the item-verdict card

One card per round, one item per image. items[].id short stable key; label slug; description prompt summary plus why.

Build items from post's embeds, not brief's table - brief snapshot and draft keeps moving. Another campaign can replace picture hours before card opens, leaving brief naming job whose file now under `.superseded-<job>` while post points at new render. Before writing spec, `grep -n 'assets/' <post>` and read each named record's superseded_by; put job and record post actually embeds into item and table row; say in description and detailsMarkdown brief named superseded job and where picture kept. Card showing file post no longer uses collects verdict on nothing.

Image already in draft goes on card even if fails bar. no-broken-image rule governs renders submitted as candidates; doesn't license hiding what draft contains; round 1 gets verdict on those files. Show it, name defect class in check note, say in detailsMarkdown what re-render would be. Hiding strands post.

Measure suspect frame with shipped probes before check note, mind argument shapes. `check-blank-margin.py IMAGE [IMAGE ...]` prints dominant fill share, blank strip per edge, content bbox. `check-palette-strip.py IMAGE` exactly one path, ends `no palette strip on either edge`. Hand-rolled numpy loop duplicates both; run scripts then read result against crop before claim.

Build with three shipped scripts rather than bespoke, keep descriptions in JSON not Python source. `scripts/open-card-issue.py` -> `scripts/build-verdict-card.py` (spec from templates/verdict-card-spec.json) -> `scripts/post-interaction.py` is whole chain; each proves own half. Hand-rolled card script recurring failure. When bespoke unavoidable, let it read `{"title","summary","items":[{"id","file","desc"}]}` JSON spec.

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
curl -s -X POST "${AUTH[@]}" -H 'Content-Type: application/json' --data-binary @/tmp/verdict-card.json "$API/issues/$ISSUE_ID/interactions" | jq '{id, kind, status, continuationPolicy, idempotencyKey}'
```
Replace <issueId> in idempotency key with real issue id; increment round-<n> per round. Reuse same key retrying same card; new round new key.

Two constraints surface only as rejections:
- items[].description capped 500 chars. Longer fails whole POST 400 Validation error / code too_big / path payload.items.0.description. Draft prompt summary, why, self-check to fit; check before submitting.
- Measure length before writing spec, not after build refuses. Put detail that doesn't fit into detailsMarkdown (room).
- Set resolverPolicy human_only on verdict card. Default inherited anyone lets agent resolve own image verdict - forbidden.
- Item description is check note, written from PNG you looked at, not brief. When brief's count and picture disagree, card states picture's count and says brief wrong. On defect turning on hands/arms/fingers, decide on crop of contact point rather than full frame. Expect same false positive second place. Split count from shape.

Build payload with `scripts/build-verdict-card.py`, not by hand. Card frozen at POST. Script takes spec file (shape: templates/verdict-card-spec.json), bakes in human_only, wake_assignee, allowBulkApprove, supersedeOnUserComment and the verdicts:<issueId>:round-<n> key, asserts 500 cap per item:
```bash
python3 ~/.hermes/profiles/matejko/skills/image-studio/scripts/build-verdict-card.py "$SPEC" --out "$SCRATCH/verdict-card.json"
```

The spec's item key is `attachment_id`; the posted payload's is `attachmentId`. Build the spec from `templates/verdict-card-spec.json` rather than from the payload. Read printed per-item lengths before posting. Builder also prints each item's `attach=<id>`, compare with id upload returned. Script prints supersedeOnUserComment value.

The builder writes `payload.supersedeOnUserComment: true`, and a review card usually wants `false`. After build, flip in payload file then POST. true means any board comment settles whole still-pending card as superseded_by_comment; false leaves card pending and delivers comment as own wake. Legend in detailsMarkdown and posted field must agree. Decide flag together with legend in one pass.

A corrected card needs a key the default shape cannot express. The spec takes optional idempotency_key overriding computed - corrected card posts under `verdicts:<issueId>:round-<k>-corrected`, and `templates/verdict-card-spec-corrected.json` is spec shape.

The issue object does not report its attachments - read `/issues/{id}/attachments`. GET /issues/{id} on card with three PNGs returns empty/absent attachments, and same object answers comments: 0 on issue carrying well over a hundred. List route authority. verdict card payload.items[].attachmentId is join: match each item's id against upload ids and each row's byteSize/sha256 against brief, then read issue object only for status.

## Read the verdicts back

```bash
curl -s "${AUTH[@]}" "$API/issues/$ISSUE_ID/interactions" | jq '.[] | select(.kind=="request_item_verdicts") | {id, status, responses, result}'
```
GET /interactions answers bare JSON array, same as /attachments, /comments and company issues list - not {"items":[...]}. Guard shape. No single-interaction GET: GET /api/issues/{id}/interactions/{interactionId} 404. Filter array by id. Read resolvedByUserId before calling verdict human's: resolvedByAgentId set means agent settled card it shouldn't.

Card assigned to you may already be in another run's hands, thread says so. Backlog runner creates cards with this agent as assigneeAgentId, so unbuilt card being yours proves nothing. Read createdByRunId and card's comments before first upload. Tell arrives before read: write_file refusing to create prompt because path already exists is another run's work discovered.

Card already exists verified field by field, never rebuilt. Read interactions list before any other work on card issue and confirm:
- status pending with outcome null
- effectiveResolverPolicy human_only with resolverPolicyProvenance explicit
- continuationPolicy wake_assignee
- payload.supersedeOnUserComment - false unless brief wants board comment close round
- payload.allowBulkApprove, payload.verdicts containing approve/reject/defer, payload.requireReasonOn containing reject
- idempotencyKey verdicts:<issueId>:round-<n> matching brief round
- one item per slot, id slot name, attachmentId actually uploaded. Prove with bytes.
- prompt, detailsMarkdown, each item description filled. Read lengths.

Wrong field repaired by withdrawing card and posting again. Missing sentence in otherwise complete honest card is not: rebuilding shows Wojtek cancelled card plus duplicate. When missing line context earlier card already gave, put in issue comment same issue and leave card pending.

Resolved payload sits on interaction object under responses on this board build - dict carrying outcome, complete, items[] with each item's verdict, resolvedByUserId, resolvedAt - where older notes call same field result. response (singular) empty object even fully answered card. Take first of responses, result that is dict holding items. Read from result, never payload. status answered plus resolvedAt proof resolved; result.items[].verdict what decided. Approval with no reason no reason key at all. Wake payload lists newly resolved item ids in newlyResolvedItemIds; handle only those.

Issue that reads done proves card answered, not every item approved. Status one signal for whole card; item list can carry defer or reject beside approvals. Compose as N items, M approved plus every reason. When per-item read empty/unreadable, re-read /interactions printing only [{id, verdict, reason}], don't present issue status as verdict in closing comment.

## A wake with no new verdict

Run can be woken on card whose verdict card still pending and thread unchanged: after posting run ends, harness re-assigns issue, so reason: issue_assigned not news. Pending interaction with continuationPolicy wake_assignee is live path - don't re-post card, re-upload PNGs, or arm monitor beside it.

Run still owes audit, four reads:
1. GET /issues/<id>/interactions - card pending resolvedAt null.
2. GET /issues/<id>/attachments - every payload.items[].attachmentId resolves to row, and every row carries non-null issueCommentId.
3. shasum -a 256 and ls -l on each staging PNG equal row's sha256 and byteSize.
4. ~/image-studio/backlog/queue.json - slot still names post and this issue.

Read issue's checkoutRunId and executionRunId before first write: re-assigned wake can arrive checkoutRunId null while executionRunId your run, and comment still lands on that shape.

Then end run where it was. One short comment says card unchanged, what verified, verdicts next thing; no status PATCH, no second card, no re-render. Comment audit trail for wake that did no work.

Attachment row's filename reads null on this uploader on every card, old and new. Compare older card's rows before reading as broken upload.

## Write an issue document (the runner's queue table)

PUT /api/issues/{issueId}/documents/{key} creates and updates alike. For existing document, send body with baseRevisionId set to latestRevisionId from GET same key; omit for new.

Document PUT needs issue checked out by your run. Write scoped to run, so PUT to issue another run holds or no run holds -> 409 {"error":"Issue run ownership conflict","details":{... checkoutRunId null, executionRunId null ...}}. Not stale-revision conflict. Claim issue first:
```bash
curl -s -X POST "${AUTH[@]}" -H 'Content-Type: application/json' -d '{"agentId":"'"$AGENT_ID"'","expectedStatuses":["todo","backlog","blocked","in_review","in_progress"]}' "$API/issues/$ISSUE_ID/checkout" | jq '{identifier, status, checkoutRunId}'
```
Body needs both agentId and expectedStatuses; empty {} 400 naming agentId and expectedStatuses missing. Successful checkout 200 with issue JSON and checkoutRunId set to your run. Re-read issue and confirm checkoutRunId equals your run id before PUT.

Two different 409s on route, different fixes. Stale baseRevisionId means someone else wrote doc since GET: fetch latest revision and merge. Run-ownership conflict means issue not yours to write: checkout and PUT again. Read error in response body to tell apart.

For runner's queue document, `scripts/put-queue-doc.py --issue-id <runnerId> --run-id <runId>` does whole thing: builds body from queue.json and briefs, fetches current revision, PUTs, prints new latestRevisionId. Script does not check issue out for you. On wake on issue itself harness usually claimed it: read checkoutRunId first and call checkout only when null or belongs to another run.
```bash
python3 ~/.hermes/profiles/matejko/skills/image-studio/scripts/put-queue-doc.py --issue-id "$ISSUE_ID" --run-id "$RUN_ID"
python3 -c "
import json
body=open('/tmp/queue-body.md').read()
json.dump({'title':'Queue','format':'markdown','body':body,'baseRevisionId':'$REV'}, open('/tmp/queue-put.json','w'))
"
curl -s -X PUT "${AUTH[@]}" -H 'Content-Type: application/json' --data-binary @/tmp/queue-put.json "$API/issues/$ISSUE_ID/documents/queue" | jq '{latestRevisionId}'
```
PUT response carries new latestRevisionId and saved body - proof document landed.

Documents list is bare array, document keyed by key, not name/title. GET /issues/{id}/documents answers [{"key":"queue","title":"Queue","latestRevisionId":...,"body":...}], so reader filtering on x["name"]=="queue" matches nothing. Match on key, keep body out of any python3 -c printed. GET /api/issues?companyId=...&limit=500 other envelope: answers {"issues": null}, not 404; list lives at /companies/$CID/issues.

## Pitfalls

- Creating issue under parent target assignee created refused 409 delegation_cycle. Board treats issue whose ancestor created by agent assigning as delegation loop. Fix not hunt different parent: create issue without parentId (keep projectId) and say in description what it serves. Follow-up PATCH to attach parent refused too (cross_iss). Create route company-scoped: POST /api/companies/$CID/issues carrying title, description, projectId, assigneeAgentId, status todo and idempotencyKey. POST /api/issues answers {"error":"API route not found"}. Build body with python from brief file and POST with --data-binary @<abs json path>, then read description back and compare to brief with ==. Take identifier from create response for backlog.py batch-opened <n> <GUL-id>. Response can already carry another run's checkoutRunId before first upload, so claim normal create outcome.
- API error code whose name doesn't explain answered by installed server bundle. `grep -rn '<the code>' ~/.paperclip/cli/installs/npm/*/node_modules/@paperclipai/server/dist/*.js | head` prints statement that threw. Read comparison, fix input it names, don't edit bundle.
- Always prefix paths with /api. Bare origin returns SPA HTML 200.
- 409 on document PUT usually run-ownership conflict not stale revision. Response says Issue run ownership conflict and names checkoutRunId/executionRunId in details; fix POST checkout with {"agentId":...,"expectedStatuses":[...]} and PUT again, not re-fetch revision. Empty checkout body {} 400 naming agentId and expectedStatuses.
- 500 on attachment upload usually S3 store, not request. Attachments route writes to storage.s3.endpoint (MinIO on OMV box). Read ~/.paperclip/instances/default/logs/service.log for ERROR: POST .../attachments 500: connect EHOSTUNREACH <ip>:9000 means Paperclip process cannot reach MinIO, while curl http://<endpoint>/minio/health/live and fresh node connect from your shell still succeed. Confirm field name right first - file only accepted multipart field, other names 400 not 500. Restarting Paperclip alone doesn't cure; durable fix localhost relay - launchd job (io.paperclip.minio-proxy) running system python3 on 127.0.0.1:9000 forwarding to <lan-host>:9000 - with storage.s3.endpoint in config pointed at http://127.0.0.1:9000, then service restarted. Board owner's change, never yours. Keep renders in staging, comment diagnosis with log line, set one monitor retry, if retry still fails open request_confirmation and set issue in_review. Never restart board yourself, never rebuild same image hoping store comes back.
- Check store before blaming request. Run `curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:9000/minio/health/live`. 200 means MinIO and relay fine and fault inside board process; failure means relay or OMV box down.
- Fuller story of item belongs in detailsMarkdown (20000 chars), not 500-char description.
- Cancel interaction yourself with withdraw, not cancel. POST /interactions/<id>/cancel board-only 403. POST .../withdraw with {"reason":"..."} allowed for card creator and issue current assignee, settles cancelled.
- No PATCH route for issue-thread interaction. openapi lists only GET|POST /interactions and per-interaction accept/cancel/reject/resolve-from-comment/respond/skip/verdicts/withdraw - no PATCH. PATCH 404. Card items[].description and detailsMarkdown frozen once created: get wording right before POST. If correction discovered after live, put in issue comment; own agent comment does not supersede card (supersedeOnUserComment only fires for board/user comment), so card stays pending and finding reaches Wojtek in thread. Re-creating card with new idempotency key leaves two open cards. Unless withdraw first: withdrawn settles cancelled, cancelled not pending, withdraw-then-re-post leaves exactly one card open. Right path when card's own text wrong; wrong path for new info adding context. Withdraw with reason naming what changed. Then post corrected card under new key and verify GET /interactions exactly one pending and other cancelled. `scripts/withdraw-interaction.py <issue> <interaction> <run-id> "<reason>"` sends withdraw from script file, exits non-zero unless response status cancelled.
- Closing issue clears monitor, never null monitor in same PATCH. Closing body bundling "executionPolicy":{"monitor":{"nextCheckAt":null}} with status rejected 400 and whole write lost. PATCH status alone {"status":"done"}; board drops monitorNextCheckAt and executionPolicy to null when reaches closed. Re-read issue afterwards confirm status and null monitor.
- reviewInteractionId refused for item-verdict card. PATCHing onto card issue 422 invalid_review_interaction. Pending card is review path on its own, so PATCH {"status":"in_review"} only. Failed PATCH writes nothing; re-send status without field.
- State brief describes is snapshot of runner's view, queue.json is state. Brief can say post reads rendering and card-done ran, while queue still has post in card with live batch entry - different card-done branches at closeout. Read post's state, issues list, slot/batch membership from ~/image-studio/backlog/queue.json before choosing branch; log disagreement with backlog.py note <n> "...". Neither licenses card-done while card open.
- "nextCheckAt": null is schema violation, monitor cannot be retired by nulling. Sending "executionPolicy":{"monitor":{"nextCheckAt":null}} 400 Validation error path executionPolicy.monitor.nextCheckAt expected string, whole write lost including status. Retire monitor by PATCHing status alone. Monitor already fired reads back null anyway.
- PATCH answering 200 with OLD status means body never reached server. Empty/0-byte body not validation error - board answers 200 issue unchanged no error. Always check echoed status equals sent; re-read issue when not. Usual cause payload file written by script that failed.
- Capture HTTP code on every mutating curl, list thread before re-posting comment that seemed to fail. Without -w '\nHTTP=%{http_code}' empty stdout looks same for dropped connection, 4xx, 5xx. Before retrying comment POST, GET /issues/{id}/comments?order=asc and look for body meant.
- Build JSON payloads with write_file script, not heredoc inside shell script. Heredoc python block inside terminal stalls and returns BLOCKED; inside .sh runs but traceback scrolls past and shell keeps going. Heredoc wrapped in command substitution fails parse time unexpected EOF. Take file route. One-liner that works for comment: `jq -n --rawfile body <abs path> '{body:$body}' > payload.json`, then POST --data-binary @payload.json. Write payload builder to scratch with write_file, run as own call, check byte size before POST. When builder prints JSON to stdout use json.dump(obj, sys.stdout). Markdown body with backticks must go through file not shell string.
- Unattended runs refuse execute_code. Use terminal with curl.
- Monitor timestamps ISO-8601 UTC with Z suffix. datetime.isoformat() returns +00:00; strip before sending.
- PAPERCLIP_RUN_ID unset in tool shell, empty run-id header 401 - not key problem. Run id only wake payload. Export from wake payload before first mutation. Every mutation needs header. Helper script with run id written into it goes stale next wake. Run id different every run, so pc.sh-style wrapper saved with id of run that wrote it sends previous run's header to later calls. Reads keep working, then first mutation 409 / Issue run ownership conflict. details block tells apart: checkoutRunId and executionRunId equal current run while actorRunId names older one is stale header. Fix helper read id from environment with current run fallback, or script takes run id as sys.argv[1]. Changing constant in place (sed -i) is write unattended run fights approval gate.
- curl argument `@~/file` does not expand ~, whichever flag. curl takes path literally and fails reading file. Use $HOME/... or absolute. Read failure as possibly-unsent write, not bad response; downstream json.load dies on empty body. On any decode error from mutation, check thread for thing meant to post, confirm response echoed id.
- Multi-line shell commands and heredocs stall on approval prompt. Keep each call one line. A read-only bash -c wrapper trips same gate. Put script in scratch and run bash <path>. Refusal's own wording "do not retry, stop the workflow" is about command shape, not task.
- Heredoc python block same stall new shape. Put script in scratch with write_file and run second call.
- request_item_verdicts defaults supersedeOnUserComment to false, and flag lives inside payload. Parent brief round-1 legend says "a comment closes the card"; if card must behave that way, set "supersedeOnUserComment": true inside payload object. Copy at interaction top level silently dropped. Only board/user comment supersedes: own agent comment leaves card pending. With default false, comment arrives as own wake and card stays pending.
- User comment on done issue reopens it. Comment makes issue in_progress and wakes you; doesn't undo work already done. Answer question on issue and set status back to done with answer in same PATCH.
- Comments come back newest-first, and status PATCH's comment returns no id. .[0] latest; .[-1] oldest. Dangerous case close: comment field riding PATCH returns only issue, no id, reading [-1] returns thread's oldest comment. Verify PATCH-carried comment by scanning whole list for body or newest createdAt. POST /comments returns new id, check against id given.
- $API already ends in /api, so $API/api/... doubles path and 404. Auth block sets API=.../api. Doubled path returns 404 body few dozen bytes. Re-run read-back as $API/attachments/<id>/content before believing upload failed. Shared paperclip skill "Hermes profile env gotcha" paragraph contradicts this (says append /api) - right only for profile whose PAPERCLIP_API_URL carries no /api. Derive base idempotently: `B="${PAPERCLIP_API_URL%/}"; B="${B%/api}"` then call "$B/api/...". Prove base with GET <base>/api/agents/me. Doubled prefix can look like empty issue rather than error: python reader doing .get('status') on bad response prints every field null.
- Card created by run that then ended is empty AND leased, lease blocks every repair route except comment. Sibling run creates card, claimed by harness for own run, ends before uploading: issue reads in_progress with checkoutRunId naming dead run, activeRun null, no attachments, no comments, no interactions, one issue.created on activity. From another run checkout 409, release 409, attachment upload 409, monitor PATCH 409, DELETE comments 409 all refuse, but POST /comments still 201. Recovery: post whole build note on card (absolute staging paths, byte sizes, full sha256, item ids, beats, caveats, which script to run) so run inheriting lease finishes in minutes. POST /issues/{id}/checkout needs {"agentId":...,"expectedStatuses":["in_progress","todo"]} both required. Re-read card before build/open anything beside it: next wake lease-holder may have finished work itself.
- Probe comment is permanent write when issue belongs to another run. POST /comments succeeds on issue your run does not hold and DELETE then 409. Probe with read; if probe already out there, name it in next comment.
- Run-ownership gate covers some writes and not others, and one it lets through is one human reads. On issue another run holds, POST /comments still succeeds while attachment upload, PATCH, DELETE comments all Issue run ownership conflict. Comment cannot be taken back. Post comment you mean to post; probe route with read.
- Comment on issue YOUR run holds can be deleted, repair for garbled one. DELETE /api/issues/{id}/comments/{commentId} with run id header 200 soft-deletes: record keeps id and createdAt, body emptied, deletedAt set. Delete it, post correct text, say in next comment what corrected. Gate is run not issue. Probe comment posted to test route is deleted, not explained. Moment link test-style comment lands by mistake on issue your own run holds, DELETE in same run.
- Issue detail carries no attachments, so issue.attachments always null and always lies. Card read from GET /issues/<id> shows no pictures even when PNGs uploaded, linked and visible in thread; list lives only at GET /issues/<id>/attachments. Concluding "card went up empty" from detail object costs duplicate upload and replaced verdict card. Read attachments endpoint before judging card's pictures, check each payload's attachmentId against that list.
