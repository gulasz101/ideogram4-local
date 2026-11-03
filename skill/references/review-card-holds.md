# Items on a review card, and the ones that stay in staging

A handoff brief's item table is a plan, not a mandate. The brief was written by an
earlier run from that run's read of the file; the card run measures again and freezes
what it can defend. This file extends the rule in `backlog-review.md` that the card's
own run checks every PNG and owns the note it freezes: it covers the items the brief
lists and the run then declines to show.

## Re-measure the brief's counts before the POST

- Every countable claim the brief makes (a digit count, a number of props, a number of
  figures) is re-measured on your own crop written to disk before the card goes up,
  because `items[].description` and `detailsMarkdown` have no PATCH. A brief note that
  carried "five digits on each hand" from an earlier read becomes a frozen wrong number
  the moment it is copied into the card.
- When the brief and the crop disagree, the crop wins and the note is rewritten. Write
  the measurement, not only the conclusion: "a 3x crop of his lowered hand counts four
  digits and no little finger" is checkable by the reader; "hands look fine" is not.
- A claimed chain of contacts is a countable claim, not a scene-level one. "The first block
  tipped and the second leans into the third" is verified contact by contact on a 4x crop of
  the prop row, and the note names the pairs: two leaning pairs with an upright block between
  them is not one cascade, and the flux twin of a cascade slot can come back as upright props
  that touch nothing at all. Write what the crop shows. When the shipping ideogram carries the
  slot, a twin that under-reads the beat is a line on the card face, not a re-render.

## Measure a hand on an 8x crop, because a mid-zoom read invents digits

- Two reads of one hand can contradict each other: one calls it clean, the next reports
  a merged or deformed mass, or an extra digit. On a stylized fist that mass is usually
  the shadow crease where the fingers fold into the palm, and the fist is drawn as three
  or four rounded knuckles with no separated thumb. That is the style, not a defect.
- Locate each hand by skin-tone mask instead of by guessed coordinates: threshold
  (`r > 120 and r > g+12 and g > b+5 and r-b > 30`), take the mask's bounding box, then
  scan it in 10-px horizontal bands and print each band's x-range. The clusters below the
  face are the hands. Crop each one at 8x with
  `scripts/crop-probe.py IMAGE --box x0,y0,x1,y1 --scale 8 --out <path>` and ask a crop
  one question: how many knuckles, is a thumb visible, is any mass attached that is not a
  finger.
- A second hand, a third arm, or a hand merging into a prop is a hold-back. Soft knuckles
  and a dark crease are a caveat at most; do not spend a render on the caveat.

## A vision answer that says no image arrived is a failed load

- `vision_analyze` can answer "I can't inspect or describe the image because no image was
  included" for a crop that exists on disk. That is a transport failure, not a finding
  about the picture: re-export the same crop smaller (about 640 px on the long edge) and
  ask again. Do not record the slot as undetermined and do not widen the question.

## The brief's quote of the draft is not the draft

- Read the post's own embed line before the card goes up and again before the closeout:
  `grep -n 'assets/<date>/<slug>.png' <post>`. A brief's quoted line can drop the alt
  text (an empty `![](...)` for a line that really reads `![flux-reconcile](...)`), and a
  closeout written from the quote then rewrites an alt text that already existed instead
  of describing the picture that ships.
- Read the paragraph either side of the embed as well. The section's own sentence is what
  the picture is judged against and where a count caveat becomes concrete: a section that
  says all four came back makes "two of four bays lit" a visible mismatch rather than a
  quibble.
- When a caveat reads stronger against the prose than against the picture, put it in the
  thread **before** the card is posted, or accept that the card closes. The builder bakes
  `supersedeOnUserComment: true` into `payload`, and that flag reacts to a board/user
  comment: a pending card stayed `pending` on a thread that already carried an agent
  comment, and a status PATCH carries no comment field at all. So read the interaction's
  own `status` back after anything lands in the thread instead of assuming either way, and
  keep the thread quiet while a card is open because the legend says so, not because the
  flag is guaranteed to fire. If a comment is already out after the card,
  reissue the same items under a `verdicts:<issue>:round-<k>-reissued` key with the flag set
  to `false`, and say on the card face that a comment no longer closes it.

## Hold the item back when it fails the show bar

- The standing rule that no broken image goes on a card outranks the brief's row count.
  An item that fails a defect class with no approvals in the library
  (`scripts/verdict-class-rate.py`, a class reading `N rejected / 0 approved`) is dropped
  from `items`, not shown with a caveat attached.
- Name the absence on the card face. `detailsMarkdown` says which item is missing, what
  was measured, the class and its rate, and the held-back attempts of that slot that
  were never shown either. Repeat it in the thread comment for the reader who skims.
  A card that shows one item while its description promises two reads as a lost render
  unless the card says why.
- A comparison copy (the other engine's take on a slot, marked as not shipping) gets no
  re-render when it is held back. A render exists to replace something that ships;
  spending one on a copy that will never reach the vault is waste, and the rejection row
  would land on a slot whose shipping render is already good.
- Its closeout differs from the brief's bookkeeping: no vault copy, no embed, no
  `superseded_by` pointing at it. A held-back slot attempt keeps a library record with a
  row that says it was held back at the self-check and never shown; a non-shipping copy
  that was never a candidate gets a line in the closing comment and stays in staging.
- Say in the closing comment that the brief's bookkeeping was adjusted and why. The
  brief stays in the issue as the plan a later reader compares the result against, so a
  silent deviation reads as a missed step.

## A replacement submitted while the card is already pending

A companion that fails the beat on its own — a prop drawn as a different object, a state
missing — is held back and a replacement submitted, exactly as when the card is still being
built. What changes once the card is posted is the wake that collects it:

- **The collection monitor's `notes` must say fetch and self-check only, and forbid a
  comment on that issue.** A board or user comment supersedes a pending card, so a wake
  that reports "the spare landed" in the thread risks throwing away the round it was
  collecting for.
- Record the held-back job id, the replacement's job id and the reason in a queue note
  (`backlog.py note <n> ...`) instead of the thread. The queue table is the reader that
  survives the card closing.
- Name the missing companion on the card face, in `detailsMarkdown`, with the job id that is
  rendering and one plain sentence that it comes on a later card if it passes. A card that
  silently carries one engine for a slot reads as a lost render.
- When the verdicts arrive before the replacement lands, the slot is decided on the render
  that was on the card: the spare stays in staging, gets no vault copy and no embed, and is
  closed with a line in the closing comment. Do not hold the post open for a copy nobody
  judged.

## A shipping render that fails after the card is posted

`items[].description` and `detailsMarkdown` have no PATCH, so a posted card cannot be amended in
place. When a **shipping** render fails the bar after the card went up, the card comes down and is
rebuilt; a caveat written into the thread is not a substitute, because the picture still sits on the
card with a verdict row beside it. This is the order that works:

1. **Withdraw the card** with `scripts/pc-withdraw-interaction.py <issue> <interaction> <run-id>
   "<one clause naming the defect>"`. The reason is stored on the cancelled interaction and shown in
   the thread, so it is the audit trail for the round the owner never got to judge.
2. **Submit the pair for the failing slot only** — ideogram and flux, as for any re-render. Leave the
   passing PNGs untouched and unshown: they keep their hashes and go back on the rebuilt card
   unchanged.
3. **Move the issue to `in_progress` with a monitor** at the later job's ETA plus a few minutes, read
   from `imagegen status` (`eta_minutes`), and put fetch, self-check and rebuild in the monitor notes.
   A withdrawn card is no longer a review path, so `in_review` at this point is a stranded issue.
4. **Say in the thread what came down and why**, with the failed job id, the two replacement job ids
   and the ETA. The card has vanished from the board and the thread is the only thing that explains
   it; keep it to that, the card face is not posted yet.
5. **At the collect wake, re-run the judgement-free scripts on every file going on the card**, not
   only the new pair, and count the thing that failed on crops written to disk. Those measurements go
   into the item descriptions.
6. **Reissue under a key the default cannot express**: `"idempotency_key":
   "verdicts:<issueId>:round-<k>-reissued"` in the spec. `build-verdict-card.py` honours the override,
   and the default key collides with the withdrawn card.
7. **Upload the files again** before building the spec, so the card points at this round's bytes.
   `scripts/upload-attachments.py <issue id> <png>... --company <company-id>` answers
   `--company or $PAPERCLIP_COMPANY_ID required` without the flag, and the profile `.env` does not
   always carry the company id.
8. **Post the interaction, then one patch carrying both the status and the announcement**:
   `paperclip-write.py patch --issue <id> --json-file <f>` with `{"status": "in_review", "comment":
   "..."}`. One write, and the echoed status confirms it.
9. **Link the attachments to a comment**: `paperclip-write.py comment --issue <id> --body-file <f>
   --attach <attachmentId>`, repeated per file. Until then every new attachment reads
   `issueCommentId: null` and the thread shows no images. Read the interaction back afterwards — an
   agent comment has not superseded a pending card, but the flag is named `supersedeOnUserComment`
   and the check is one GET.
10. **Append a reissue section to the issue description** (GET it, append, PATCH `description`). The
    description is the issue's own account of what is on the card, and a stale table naming the
    withdrawn job id and its hash sends the next run looking for a file that is not shipping.

## Running the skill's scripts

- If a script answers `Permission denied`, run it as `python3 <script> ...`, and run the
  PIL/numpy checks with the check venv's python (`~/image-studio/.venv-imgcheck/bin/python`).
  Do not chmod the skill directory to work around it.
- **Name the shell prologue per issue, never `pc-env.sh`.** Sibling runs of yours share the
  profile scratch directory and the prologue exports `PAPERCLIP_RUN_ID` and the issue id, so
  a shared filename is either refused as a stale write by a run that has not read the other
  copy, or overwrites another run's exports and sends its mutations under the wrong run id.
  Write `pc-env-<n>.sh` and load that path in every call.
- `build-verdict-card.py` prints each item's description length and the idempotency key;
  read that line before the POST, because a spec that silently lost its `attachment_id`
  still builds and the card then renders an empty row.

## Sending the card payload

Build the spec with `write_file`, build the payload with `python3 build-verdict-card.py`,
wrap it as JSON on disk, and post it with `curl --data @payload.json -w '\nHTTP:%{http_code}\n'`.
The card run is often unattended, and the terminal is the tool that carries mutations
there: a payload assembled inside a single-command code interpreter is a dead end.
Read the status and the returned `id` rather than assuming a mutation was blocked, and
fall back to the `npx paperclipai` CLI only when a request is actually refused.

- **Parse the run's key inside the script instead of exporting it in a shell prologue.**
  A command that chains `set -a; . "$HERMES_HOME/.env"; set +a; python3 ...` is the shape that
  stalls on an approval prompt and returns with the command never having run. Read
  `PAPERCLIP_API_KEY=` out of the profile `.env` at the top of the script and pass the run id
  as a constant, and the whole call stays one short `python3 <path>` line.
- **Uploads fit the same shape.** `scripts/upload-attachments.py <issue id> <png>...` posts
  each file as multipart `file=`, prints the attachment id beside a local sha256/size match
  and writes nothing. Use the ids it prints in the card spec, then confirm every attachment
  reads back with a non-null `issueCommentId` after the linking comment.

- **Read the card back at the right level.** `kind`, `resolverPolicy`, `continuationPolicy`
  and `idempotencyKey` sit on the interaction object, while `supersedeOnUserComment` sits
  inside `payload`; a read-back that looks for `payload.resolverPolicy` prints `None` on a
  correctly posted card and can send a run off to withdraw and repost something that was
  never wrong. Verify `status: pending`, the item count, and each item's `attachmentId`
  against the upload ids the run recorded, plus a non-null `issueCommentId` on every
  attachment.
- **A queue line naming two card issues for one post is a closed card plus the live one.**
  `backlog.py status` lists every issue a post has ever had. Before posting, read the other
  issue's `status` and its interactions: only a *pending* card elsewhere means the post is
  already in front of him, and then that card is the work, not a second one. When it reads
  `done` with no interaction, the card being built is the post's only card and the round
  number in its brief is right.
