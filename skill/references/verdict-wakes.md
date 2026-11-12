# Verdict wakes

The wake that closes a backlog card. The per-verdict actions are in the parent runner's "Verdict wakes" table; this file covers the wake shapes, the record date, and the batch-card bookkeeping around them.

## A verdict wake arrives in two shapes

- `payload.newlyResolvedItemIds` plus `payload.itemVerdicts` — the classic item-verdict wake.
- `reason: issue_commented` carrying `interactionOutcomes`, where a `request_item_verdicts` interaction has `status: answered` and `result.items` — the same event. Treat it as a verdict wake: read each item's `verdict`, apply the table, and do not rebuild or re-issue the card. The answered interaction is the card; a second one would duplicate the verdicts.

A partial wake resolves only some items: handle those, leave the issue `in_review`, and keep waiting. The card is complete when every item has a verdict (`result.complete: true`).

## The record row uses the verdict's date, not the run's date

Approved existing image: set `verdict: "approved"`, add one row, and delete the line `Back-filled from jobs.db; not reviewed yet.` Leave `source`, `asset`, `superseded_by` and everything else alone.

```
| <round> | <YYYY-MM-DD> | approved | Approved on review. | [<issue>](/GUL/issues/<issue>) |
```

`<YYYY-MM-DD>` is the verdict's own `resolvedAt` date in UTC, not the run's local date. A verdict submitted just after midnight UTC can land on the next day while the run still reads yesterday; copying the run date writes the wrong day into the record. Read the record back and confirm the `verdict:` line and the new row before calling the card done.

## Closing a card with no re-renders

1. Post one closing comment: every item's verdict, the record paths, and "no re-renders, no vault changes, post untouched".
2. PATCH the same issue to `done`; the comment can ride on that PATCH.
3. Run `backlog.py card-done <n>`.
4. Run `backlog.py next`. On a batch card it can answer `{"action":"wait","reason":"re-renders still running"}` because other batch renders are in flight — that is expected, do nothing, and do not call `card-done` again.

## Run ownership on a verdict wake

The issue is often still checked out by the run that armed the monitor or opened the card, not the run that received the verdict wake. Every mutating call then answers `409 Issue run ownership conflict`. Read `checkoutRunId` on the issue first and use that run's id for the upload, the interaction PATCH, the issue PATCH, and every `--run-id` passed to a CLI tool. Do not retry with your own run id; the ownership conflict is correct, not a failure to work around.

## Approved comparison twins

When a card pairs an ideogram with its flux comparison twin and both are approved, the twin still gets a vault copy and a library record, but it does not replace a post embed — the post embeds only the shipping winner. The twin's record therefore has no embed target in the post, and `verify-slot.py`'s embed check fails for it by design. That failure is expected and correct; do not treat it as a defect or re-run the close. The twin's `superseded_by` stays `null` unless it was itself a replacement for an earlier render.

## Superseded_by on verdict wake

When a replacement render is approved, patch the original (now superseded) record's `superseded_by` to the approved job id in the same pass. Do this for every approved replacement, not only the shipping winner — a rejected comparison twin that was an earlier attempt of the same slot also carries the approved job id. Leave `superseded_by: null` on records whose replacement is still in flight.

- `card-done` on a batch card answers `{"ok":true,"state":"done","batch":<remaining>}` and drops that post's batch entry; it does not touch the live `slot`.
- Read `queue.json` (`state`, `batch`, `slot`) before calling it, so a batch card is not mistaken for a rendering slot and `next` is not expected to name a new post.

## Card creation in an unattended run

These pass arguments as inert argv and do not hit the terminal approval gate:

```bash
npx paperclipai issue attachment:upload <issueId> --file <png> --company-id <id> \
  --api-base <host> --api-key "$PAPERCLIP_API_KEY" --run-id <run> --json
npx paperclipai issue interaction:create <issueId> --payload-json "$(cat payload.json)" \
  --api-base <host> --api-key "$PAPERCLIP_API_KEY" --run-id <run> --json
```

Take each attachment `id` from the upload response and put it in the item's `attachmentId`. Do not bind a `request_item_verdicts` card through `reviewInteractionId` on the issue PATCH: only `request_confirmation`/`request_checkbox_confirmation` accept it, and the whole PATCH answers 422. The pending item-verdict interaction is the review path on its own; set the issue to `in_review` without that field.

## After the verdicts

Retain one Hindsight memory per card for its approvals: what the approved images have in common (the composition or prop that carried the beat). A single card is one data point, not a rule.
