# Bulk card opens: many review cards in one request

Wojtek asks for batches of review cards so he has work waiting on the board ("prepare another set of 25 tasks for review so tomorrow I have something to look at"). Batch mode is his exception to the one-card rule and the size is the number he names: open exactly that many, and never widen it on your own. The per-card procedure is unchanged — this file covers the mechanics of opening many at once, where the failure modes are about scale rather than about images.

## The other batch shape: one card across several posts

When the work is **you rendering new images** for a paced list of posts on one campaign issue, and not handing posts out to their own review runs, do not open one issue per post. Put a single `request_item_verdicts` card on the campaign issue with **one item per post**: `label` = `<post number>-<slug>`, `description` = why + check + caveat in roughly 270 to 340 characters, and the usual `verdicts:<issueId>:round-<k>` key. He answers the whole list in one place, each item separately, and the round costs one thread instead of eight.

The per-wake cap stays on **renders** (5 to 8 posts, one image a minute, a full minute between submits): that cap exists because the web backend rate-limits per exit IP, not because of how many items a card may carry.

Close each post with `backlog.py note <n>` naming the job id, the staging file and the card id. These posts sit in `todo` and are never claimed by `batch-open`, so no `card-done` branch applies; the note is the only record that the header exists and must not be re-rendered, and it travels in the runner's table where a later run reads it.

- **A card item id is the slot, never the attempt.** When a slot's second attempt is the one that ships, keep the item id at `<post number>-<slug>` and put the attempt in the render filename and in the description ("attempt two; the first had the android looking past the shield instead of through the window"). The vault copy and the library record both follow the item id, so an id carrying `-r2` embeds the post to a file named after an attempt and leaves the shipped render's provenance with nothing to hang on. The item description is where the reader learns which attempt they are judging.
- **A batch card is often answered before your next wake, and the wake may still list it as unresolved.** `unresolvedInteractionIds` in the wake payload is a hint, not a query: read `GET /issues/<id>/interactions` and the card's own `status` at the top of every hop. An `answered` card with `resolvedByUserId` set means the close belongs to that hop — two approved batches shipped without ever seeing a verdict wake, because the answer landed within a minute of the card going up and the next hop's payload still showed the card pending.

## 1. Claim the posts

```bash
~/image-studio/backlog/backlog.py batch-open <count> > batch.json
```

It returns `{"ok": true, "opened": [{n, round, brief, title}, …]}`. It takes only posts in state `todo`, skips anything already in `q["batch"]` or holding the live slot, and never touches the slot itself — the batch sits *beside* the live card, not instead of it.

## 2. Create one issue per entry

Loop the entries, building each body with `jq --rawfile` from that entry's brief so the description is the brief byte for byte:

```bash
jq -n --rawfile d "$brief" --arg t "$title" --arg k "backlog-card:$n:round-$k" \
  '{title:$t, description:$d, parentId:"<runner id>", projectId:"<project id>",
    assigneeAgentId:"<own agent id>", status:"todo", idempotencyKey:$k}' > payload.json
```

Read the `identifier` out of each POST response and record it in the same pass:

```bash
~/image-studio/backlog/backlog.py batch-opened <n> GUL-<id>
```

Check that each `batch-opened` answers `"ok": true`. A create that succeeds while its record fails leaves a card on the board that the queue cannot see, and nothing later repairs it.

## 3. Verify every description, never a sample

```bash
curl -s -H "Authorization: Bearer $PAPERCLIP_API_KEY" "$API/issues/$ident" | jq -j '.description' > desc.md
cmp "$brief" desc.md
```

`jq -j`, not `jq -r` — `-r` appends a newline and turns an identical copy into a one-byte diff. Report the identical/mismatch counts in the comment: across twenty-five cards a single truncated brief is invisible to the eye and changes what that card reviews.

## 4. What has to travel in the description, because the claim is instant

The harness claims a freshly created card for its own run almost at once — the issue reads `in_progress` with a `checkoutRunId` within seconds of the POST, long before that run has read anything. From that moment:

- **The description is frozen.** Put everything the card's run needs at creation time: absolute staging paths, byte sizes, sha256, the check notes, the named deviations, the approval bookkeeping.
- **Your upload of the PNGs will be refused** with `Issue run ownership conflict`. The refusal is not a failure to work around — it means the card's own run attaches its own files. Try the upload anyway (the claim is asynchronous and you sometimes win the race), but design as if you lose it: the paths go in the brief, and a comment on the new card names the files and tells that run the upload is its job.
- **The brief must not claim files are attached to the card it becomes.** That sentence is false the moment the create lands, and the description can never be edited afterwards.

## 5. Report and close out

- Comment on the card that carried the request with the post → card table and the real counts. A batch plus the live-slot card and any older open cards means more cards are open than the number he asked for; give the true total rather than the requested one.
- Comment a state line on the runner. A card run must not check the runner out and must not PUT its `queue` document, so the document is one batch behind until the runner's own wake rebuilds it; the comment carries the rows it needs.
- **Do not call `next` from a batch card.** It never holds the live slot, so the call either answers `wait` or claims a post the runner's wake also intends to create. The slot moves only from the card that holds it.
- Expect the batch cards to be worked by their own runs over the following hours. Do not work another card's issue and do not re-post its card.
- A batch card is released with `card-done <n>`, which takes the batch branch while an entry for that post sits in `q["batch"]` and never touches the live slot. The three branches, the `--rendering` flag and the queue state to read first are in `references/archive/backlog-queue-release.md`.

## Pitfalls

- **An interrupted bulk run is resumed, not restarted.** If it ends after the creates but before the `batch-opened` records, re-read `batch.json` and the created identifiers and finish the recording pass. Re-running `batch-open` claims a *second* set of posts for the same request.
- **The number he asks for is the number you open.** The one-card rule is the default, not a cap he has to argue with; when he names a number, opening fewer is your narrowing of his decision just as opening more would be your widening of it.
- **A create whose title matches an existing issue under the same parent returns that existing issue instead of creating a new one.** The response reads like a successful create — an identifier, a status, even a checkout — so the round's card silently lands back on the old issue's thread and the queue then records an id that belongs to the previous round. A fresh `idempotencyKey` does not defeat it. Qualify the title whenever the card repeats a post: `Backlog review <nnn>/153, round <k>: <post title>`, the form the parent description already allows, and compare the returned `identifier` and `id` against the ones you already hold before recording anything — a match is dedupe, not a create.
- **A batch request can arrive as a comment on a card that is mid-round.** Answer it on that card with the table, then carry on with the card's own work in the same run; the two are independent and the batch does not change the round it was asked on.
