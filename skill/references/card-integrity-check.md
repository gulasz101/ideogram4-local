# Verifying a live verdict card before you trust it

## Half-built card (no interactions yet)

If the issue has **zero interactions** but a non-empty thread (especially a comment
claiming renders are "ready to upload"), the card is **unbuilt, not pending**. A
"ready to upload" comment is a handoff note from a run that stopped mid-card, not
an upload, and not a card. Do not run this verification checklist on it, and do
not treat the missing interaction as "card already pending."

The repair is the full build, done now:

1. Upload every staging PNG named in the comment (verify sha256 + byteSize match).
2. Build the `request_item_verdicts` payload from a spec (build-verdict-card.py).
3. POST the interaction.
4. PATCH the issue to `in_review` (no `reviewInteractionId` for `request_item_verdicts`).

Then stop: the card is pending and `wake_assignee` will resume this issue. This
file applies to the *next* wake, once the interaction exists.

## Verified card (the rest of this file)

Use this when a wake (`issue_assigned`, a resume, a monitor) lands on an issue that is
already `in_review` with a pending `request_item_verdicts` card. The renders are done and
the card is up. The work of that run is proof that the card shows the exact files you
reviewed. It is not a re-render, and not a second card.

A previous run's comment saying "hash-identical" is a claim. Check it against the server
before you tell Wojtek the card is ready.

## 1. Read the card from the control plane

```bash
set -a; . "$HERMES_HOME/.env"; set +a
K="Authorization: Bearer $PAPER..._KEY"
BASE="${PAPERCLIP_API_URL%/}"; BASE="${BASE%/api}"
curl -s -H "$K" "$BASE/api/issues/$ISSUE/interactions"
```

**Normalise the base once.** A profile `.env` may hold `PAPERCLIP_API_URL` with `/api` already on
it, so appending another answers `{"error":"API route not found"}` — that body reads like a missing
route, not a doubled prefix, and sends you hunting for the wrong fault. Strip a trailing `/api`
before appending. For the write side, `scripts/paperclip-write.py comment --issue <id> --body-file
<file> --run-id <run-id>` builds the base, reads the key from the profile `.env`, and sends the
run-id header; a chained `source .env; curl` command can stall on the unattended approval gate.

Take the entry with `kind: request_item_verdicts`. Keep `id`, `status`
(`pending` / `answered`) and `continuationPolicy` (`wake_assignee` is the review path).
Then read `payload.items[].attachmentId`, one per image.

There is no get-by-id route for an interaction — filter the list by `id` rather than concluding
the card vanished; the list entry carries the whole payload, `status` and `result` included.

## 2. Pull the bytes the card actually serves

```bash
curl -s -H "$K" "http://127.0.0.1:3100/api/attachments/$ATTACHMENT_ID/content" -o card-N.png
shasum -a 256 card-N.png
```

Compare three ways: card bytes against the staging render, against the hash quoted in
the issue description, and (for shipped slots) against the vault file. All three must
agree. Quote the short hash prefixes in the comment so the check is repeatable by hand.

**Start with the hash on the attachment row, because the list already carries `sha256`:**
hash each staging file and compare, and download `/content` only for a bare row or when step 3
needs the bytes. A matching row hash proves the card serves that file — not that its pixels
pass, which is what step 3 is for.

`/api/attachments/{id}` (metadata) and `/api/attachments/{id}/download` answer
`404 API route not found`; `/content` is the route that returns the image. Do not conclude
an attachment is missing because the metadata route 404s, and never describe a file as
"on the card" from its attachment id alone.

## 3. Re-run the defect checks on the served bytes

```bash
cd "$HERMES_HOME/skills/image-studio/scripts"
for f in card-0.png card-1.png card-2.png; do
  python3 check-grey-bars.py $f | tail -2
  python3 check-green-share.py $f | tail -2
  python3 check-blank-margin.py $f | tail -2
  python3 check-palette-strip.py $f | tail -2
done
```

Then one look per image for what scripts cannot see: limbs and fingers, readable text,
pasted panels, and whether the section's beat reads. State counts (canisters, posts,
hands) in the comment; a count that misses the post's number is a caveat, not a defect,
unless the beat itself stops reading.

## 4. Check the shipping side before you promise anything

- Every file the previous round shipped is hash-identical to its staging render.
- The file this card will replace still holds the old version (an unreplaced
  `gluetun.png` sitting next to `.superseded-<job>` files tells you round 1 never touched it).
- The draft's alt-text line still carries the old wording, so the card's promise to
  rewrite it from the shipping picture is real work, not already done.

## 5. Leave the state honest

Post one short comment: verdict first ("card is live, nothing needed a render"), then the
verified hashes and check numbers, then what you need (one verdict per item).

The PNGs already hang off the earlier card comment through their `issueCommentId`; do not upload or
re-link them under your verification note. The card binds by `attachmentId` and the thread renders by
`issueCommentId`, so they are visible where they are.

- An agent comment does not resolve or supersede the card. Re-read the interaction after
  posting: `status` must still be `pending`. Only a user comment supersedes, and only when
  the card sets `supersedeOnUserComment: true`.
- Do not create the card again. The `idempotencyKey` already exists; the pending card is
  the audit trail.
- Do not arm a monitor while the card is pending with `continuationPolicy: wake_assignee`.
  The resolve event is the wake. A pending interaction plus `in_review` already satisfies
  the disposition guard.
- If a served byte differs from staging, or a check fails on the served file, withdraw the
  card (`POST /api/issues/{id}/interactions/{interactionId}/withdraw`) and re-render. Never
  leave a broken image in front of Wojtek waiting for a verdict.
