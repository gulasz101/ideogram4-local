# Backlog review <nnn>/<total>, round <k> — <slot summary in one line>

The replacement for the earlier card on this post, which was withdrawn and cancelled because its images failed the acceptance bar. Nothing here needs a re-audit: the checks are done and the renders below passed them.

- **Post:** `tech_blog/<file>.md`, "<post title>"
- **Campaign:** the repair campaign issue that hands out these batches
- **Queue:** post <nnn> is `rendering`; this card's close runs `backlog.py card-done <nnn>`
- **Card shape:** one ideogram4 render per slot and, beside it, the flux2-klein render of the same composition carrying the photographed-print grain

## What this run must do

1. Upload every PNG below as an attachment, post **one** comment carrying `attachmentIds`, and verify on `GET /api/issues/<id>/attachments` that each attachment has a non-null `issueCommentId`.
2. Build the verdict card with `scripts/build-verdict-card.py` from a spec file: `human_only`, `wake_assignee`, `allowBulkApprove`, `supersedeOnUserComment` inside `payload`, one item per file with the id, label and description from the table below.
3. `PATCH` this issue to `in_review` with a comment naming the card id.
4. Do not re-render and do not re-check the pictures read here.

## Confirmed passing (staging root `<abs staging dir>/`)

| item id | file | bytes | sha256 | engine |
| --- | --- | --- | --- | --- |
| `<slot>-r2` | `<file>.png` | `<bytes>` | `<sha256>` | ideogram (`<job>`) |
| `<slot>-r3-flux` | `<file>.png` | `<bytes>` | `<sha256>` | flux (`<job>`, grain) |

**Every file passed** the grey-bar, palette-strip and blank-margin scripts with a full-frame content bbox, a full-frame read, and a 4x crop wherever a hand was in question. State here what the open item was if one slot had to wait, so the successor run knows the card is deliberately short.

## Item descriptions (one per item, under 500 characters)

- **`<slot>-r2`** — Why: which section it sits under and the idea it carries in that section's own terms. Check: lettering, panels, cast, hands, edge bands. Caveat: the one or two things the picture does not quite say, named rather than decided.
- **`<slot>-r3-flux`** — Why: the same composition from flux2-klein with the grain, for comparison with the ideogram above. Check: grain across the frame, no panels, no lettering, the beat still reading.

## After the verdicts

- Approved: copy the PNG to `tech_blog/assets/<date>/<slot>.png`, repoint the embed, rewrite the alt text from the picture, write the library record with the job id and a `superseded_by` on the September record.
- A rejection goes back to a re-render with his reason as the brief; it does not reopen this card.
- Then `backlog.py card-done <nnn>` and report in the campaign issue which items shipped.
