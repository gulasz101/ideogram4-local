# Review loop

The Paperclip side of `SKILL.md`. Each section names the loop step, the call, and the evidence that the step is done. Auth, headers, and the full curl shapes live in `references/paperclip-api.md`; this file is the order to use them in.

Start every run the same way:

```bash
API=http://127.0.0.1:3100/api
KEY=$(sed -n 's/^PAPERCLIP_API_KEY=//p' ~/.hermes/profiles/matejko/.env)
RUN_ID="<run id from the wake payload>"
COMPANY_ID="<company id from the wake payload>"
ISSUE_ID="<issue id from the wake payload>"
AUTH=(-H "Authorization: Bearer $KEY" -H "X-Paperclip-Run-Id: $RUN_ID")
```

## 1. Read the request

```bash
curl -s "${AUTH[@]}" "$API/issues/$ISSUE_ID" | jq '{identifier, title, status, description}'
curl -s "${AUTH[@]}" "$API/issues/$ISSUE_ID/comments" | jq '.[] | {id, author, body}'
```

Find the post path, section, excerpt, and the reason for the image. Then read the post file and the taste memory, as step 1 of `SKILL.md` says.

**Done:** one sentence for the post's idea, plus the taste rules that apply.

## 2–3. Submit and comment the job ids

**Check before you render, on any run that is not the request's very first.** `GET /interactions` together with the comments tells you whether this round already exists: a `pending` card for `round-<n>`, or a card already resolved, means those renders have been paid for once. Handle them (step 5 or 8) instead of submitting duplicates — each image is about 21 minutes of queue, so a blind re-submit costs an hour and gives Wojtek two cards for one slot.

Submit locally, then post once with all job ids and prompt summaries:

```bash
JOB_A=$(imagegen submit --prompt-json /tmp/gitops-a.json --name gitops-forklift-a)
JOB_B=$(imagegen submit --prompt-json /tmp/gitops-b.json --name gitops-forklift-b)

curl -s -X POST "${AUTH[@]}" -H 'Content-Type: application/json' \
  -d "{\"body\":\"Round 1\\n\\n- gitops-forklift-a: $JOB_A — forklift and rack, warm light. Why: migration metaphor.\\n- gitops-forklift-b: $JOB_B — an empty platform, cool light. Why: the post's calm tone.\"}" \
  "$API/issues/$ISSUE_ID/comments" | jq '{id}'
```

**Done:** the comment lists one job id per variant.

## 4. Schedule the monitor and end the run

Read the ETA for the last job, then add five minutes:

```bash
JOB_LAST=$JOB_B   # the last variant you submitted
ETA=$(imagegen status "$JOB_LAST" | jq -r '.eta_minutes')
NEXT=$(ETA="$ETA" python3 -c 'import datetime, os; print((datetime.datetime.now(datetime.UTC)+datetime.timedelta(minutes=int(os.environ["ETA"])+5)).isoformat().replace("+00:00","Z"))')
BODY=$(printf '{"executionPolicy":{"monitor":{"nextCheckAt":"%s","scheduledBy":"assignee","notes":"render ETA"}}}' "$NEXT")
curl -s -X PATCH "${AUTH[@]}" -H 'Content-Type: application/json' -d "$BODY" \
  "$API/issues/$ISSUE_ID" | jq '{id, status, assigneeAgentId, assigneeUserId, monitorNextCheckAt}'
```

Use the last job you submitted (`$JOB_LAST`), not a fixed number: with three variants queued the last ETA is about 63 minutes, and a hard-coded wait fires the monitor early.

`imagegen` has three subcommands — `submit`, `status`, `fetch`. There is no queue listing: each `status` reply already carries `queue_ahead` and an `eta_minutes` that includes the queue ahead of that job, so hold the job ids and ask about them rather than looking for a list command.

Keep the issue `in_progress`. Do not poll `imagegen status` in a loop; the monitor is the wake. End the run after the PATCH.

**Done:** the PATCH response shows a non-null `monitorNextCheckAt`.

## 5. Monitor wake: check, fetch, or reschedule

```bash
for JOB in "$JOB_A" "$JOB_B"; do imagegen status "$JOB" | jq -r '"\(.id) \(.status) \(.eta_minutes)"'; done
```

- Any `pending` or `running` → PATCH the monitor again and end the run.
- All `done` → fetch each one. `fetch` prints the local path on stdout and the filename keeps the random token:

```bash
PNG_A=$(imagegen fetch "$JOB_A")
PNG_B=$(imagegen fetch "$JOB_B")
printf '%s\n%s\n' "$PNG_A" "$PNG_B"
ls -l "$PNG_A" "$PNG_B"
```

A `fetch` exit of 3 means still active; exit 4 means the job failed. On failure, read `imagegen status` for the error and decide whether a prompt fix or a re-render is justified.

**Done:** every PNG is local and over 1 MB.

## 6. Self-check before showing anything

Run `vision_analyze` on each PNG and check text spelling, grey box/margins, and intent. Run the margin diagnostic with the check venv, because the system `python3` is PEP 668 managed and has no Pillow or numpy (`--user` installs are refused, so a bare `python3 scripts/check-grey-bars.py` fails with `ERROR: Pillow and numpy required`):

```bash
~/image-studio/.venv-imgcheck/bin/python ~/.hermes/profiles/matejko/skills/image-studio/scripts/check-grey-bars.py "$PNG_A"
```

Create it once with `python3 -m venv ~/image-studio/.venv-imgcheck && ~/image-studio/.venv-imgcheck/bin/pip install Pillow numpy` if it is missing. Keep the venv inside the studio workspace so there is one path to remember and no second copy that drifts out of sync with the skill.

A failed variant gets one silent re-render with a corrected prompt; it does not go on the card. Your check may remove an image, never approve one.

**Done:** each image has a written pass/fail note.

## 7. Upload and open the verdict card

Upload each passing PNG, keep the id, then create one card for the round:

```bash
UPLOAD=$(curl -s -X POST "${AUTH[@]}" \
  -F "file=@$PNG_A;type=image/png" \
  "$API/companies/$COMPANY_ID/issues/$ISSUE_ID/attachments")
AID_A=$(echo "$UPLOAD" | jq -r '.id // empty')
```

Build `/tmp/verdict-card.json` exactly as in `references/paperclip-api.md`, with one item per passing image, then:

```bash
curl -s -X POST "${AUTH[@]}" -H 'Content-Type: application/json' \
  --data-binary @/tmp/verdict-card.json \
  "$API/issues/$ISSUE_ID/interactions" | jq '{id, status, continuationPolicy}'

curl -s -X PATCH "${AUTH[@]}" -H 'Content-Type: application/json' \
  -d '{"status":"in_review","comment":"Round 1 is on the verdict card."}' \
  "$API/issues/$ISSUE_ID" | jq '{id, status}'
```

The card payload uses `verdicts: ["approve","reject","defer"]`, `requireReasonOn: ["reject"]`, `continuationPolicy: "wake_assignee"`, and `idempotencyKey: "verdicts:<issueId>:round-<n>"`.

**Done:** the card is `pending` and the issue is `in_review`.

## 8. Verdict wake: retain and handle

The wake payload's `newlyResolvedItemIds` names the items to handle. Read them back:

```bash
curl -s "${AUTH[@]}" "$API/issues/$ISSUE_ID/interactions" \
  | jq '.[] | select(.kind=="request_item_verdicts") | {id, status, result}'
```

For each newly resolved item:

1. `hindsight_retain` the verdict, the reason, the post, and the prompt traits that mattered; tags `taste`, `verdict`.
2. **approve** → copy the PNG to `~/wojtek.second.brain.obsidian.vault/tech_blog/assets/<YYYY-MM-DD>/<label>.png` (the label slug, without the token) and write the record (`references/library-records.md`).
3. **reject** → revise the prompt from the reason and go back to step 3 with `round-<n+1>`.
4. **defer** → leave the item untouched.

A user comment while the card is pending supersedes the rest of the card with `superseded_by_comment`. On a comment wake, read the comment first; if the card was superseded, open the next round's card with a new idempotency key, carrying the remaining items and revised by the comment.

After round 3, if a slot is still unapproved, post a comment asking Wojtek what to change and stop rendering. Do not open an endless sequence of cards.

**Done:** every id in `newlyResolvedItemIds` is retained and handled.

## 9. Close

When every requested slot has an approved image:

```bash
curl -s -X PATCH "${AUTH[@]}" -H 'Content-Type: application/json' \
  -d '{"status":"done","comment":"Approved: tech_blog/assets/2026-10-21/gitops-forklift-a.png. Record: 3-resources/image-library/2026-10/2026-10-21-gitops-forklift-a-7f3a9c21--<job-id>.md"}' \
  "$API/issues/$ISSUE_ID" | jq '{id, status}'
```

**Done:** the comment carries the asset paths and record links, and the issue is `done`.
