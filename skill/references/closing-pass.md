# Closing an approved card

The verdict wake starts the close. `review-loop.md` §8–9 has the order (retain, copy, record, edit the post, close the queue and the issue); this file holds the decisions that order assumes, because each one has a second plausible answer that breaks something quiet.

The close produces five things and proves each: the vault copies (hash against staging), their records (`verify-slot.py`), the post's embed lines and alt texts (asserted from a fresh read), the queue's state, and one closing comment that names the paths and the checker counts.

## The vault name comes from the ship table, not the card's item ids

A card built from a campaign brief often prefixes item ids with the post's stem or topic (`alerts-absent`, `sso-header`) while the brief's own ship table and the draft's embed use the slot's plain name (`absent.png`). Ship to the ship-table name and leave the embed path as it is: the item id names the render, the slot names the file. Renaming the asset to the item id splits one post's pictures across two conventions and leaves the replaced file beside a differently-named replacement.

## The engine suffix marks the companion, never the only approved render

When both engines of a slot are approved the pair ships as `<slot>.png` and `<slot>-<engine>.png`, and the companion is not embedded. When only the second engine's render is approved, that render **is** the slot's picture: ship it as `<slot>.png`. The engine lives in the record's `engine:` and in the caveats, not in the filename — a `<slot>-flux.png` that has no `<slot>.png` beside it tells a reader the slot was never filled.

## Preserve the replaced file, then repoint the earlier record at it

Move the file being replaced to `<slot>.superseded-<old job>.png` before copying the new bytes in. Then patch the slot's earlier record in three places: `superseded_by` names the new job, `asset` names the preserved file, and the record's own `![[...]]` embed also points at the preserved file. The chain rule elsewhere asks only for `superseded_by`, which leaves a record whose `asset` points at bytes it never documented — a record's asset is a claim about its own render, so it follows the moved file, and an embed left on the shared name renders the new picture inside the old record. Say the edits in the closing comment, because the earlier record now differs from the one a backfill would write.

## A close does not wait for a re-read, and the record says what it has

When a fresh read is unavailable at the close, write the record's `## Why` from the check notes the render run and the card produced, and put one line in the closing comment naming which frames were read at close and which carry the card's note. Never fill the gap with an invented number, and never hold an approved close for a re-read: the verdict is what authorized the ship, a record with a named gap is honest, and a ship delayed for prose is not a better one. The corollary is that a number only the note supplies (`two crates where the ideogram draws three`) is written as the note's number, not as a measurement this run made.

## The `## Prompt` fence is the submitted file, and the job's stored prompt is not that file

`verify-slot.py` compares the fenced block against the `--prompt` file byte for byte, its final newline aside. The engine's stored `prompt_value` is the same prompt as compact JSON: parsing both and comparing the objects can answer equal while the byte lengths differ by a few hundred, so a block written from the job's string fails on formatting alone. Write the block from the prompt file's own text.

- **When the file and the job disagree as objects, the job is what was rendered and the file is what the checker measures.** Regenerate the prompt file from `imagegen status <job>` before writing the record, and say in the closing comment that the file was rebuilt from the stored prompt.
- **Read `created_at`, `finished_at`, `width`, `height` and `engine` from `imagegen status <job>` too.** The record filename's date prefix is that renderer `created_at`, not the day of the close, and the two timestamps are the only source of the ordering a later backfill would reproduce.

## A record filename is derived, so the checker's heading failure is usually the name

`verify-slot.py` derives the heading it expects by stripping the `created_at` date prefix and the `--<job>.md` suffix from the record's filename. A name written as the stem and job id only therefore fails `filename starts with the job's created_at date` and `heading is the stem (no date, no job id)` together, while the heading inside the file is correct: fix the filename and never the heading. Build the name from the record's own frontmatter date, which is the renderer's `created_at`, not the day the close runs.

## The queue state follows the post, not the card

A card that closes every slot the post has releases the post. A card that closes some of them — a header deferred to a campaign issue, a round-2 slot with no renders yet — closes with `card-done <n> --rendering`, so the post stays in the queue as work pending; a plain `card-done` reports a four-slot post as finished on three pictures and nothing later opens its remaining slots. Follow it with one `note <n>` that names what shipped, what remains, and the issue carrying each remainder.

## A card's job id can be a transcription of the real one

A job id copied onto a card or a brief drops characters and changes case, and `imagegen status <that id>` answers `Job not found`, which reads like a pruned job rather than a typo. Before concluding the render is gone, resolve the id from the collect brief's job table by the fetched PNG stem, and use the renderer's spelling in the record filename, the `job_id:` field and the closing comment, with one line saying the card's form was corrected. Treating the card's spelling as authority writes a record that the filename and `job_id` assertions both reject.

## Write the held-back attempts' records in the same pass, and verify them the other way round

Every render of the slot that never reached the card gets a record in the close that lands the slot: `verdict: "rejected"`, `asset: null`, `asset_location: "max-only"`, `asset_present: false`, `superseded_by` naming the job that shipped, no `![[...]]` embed, and one row reading `held back at the self-check, never shown to Wojtek` plus the defect and the measurement that showed it. Its issue column names the campaign or round issue where the hold-back was decided, never the approving card. The approved record's table carries that render too, with the attempt's stem as the row prefix — the stem already ends in the fetched 8-hex token, so leave the job id out of it.

Write the attempts first, or in the same pass. The approved record's duplicate guard counts every file in the library that names the shipped job id, so an attempt written after the approved record was checked adds itself to that set and the re-verification fails `job id appears in exactly this record plus its earlier records` on a healthy close.

Verify the attempt's own record with `--record`, `--job`, `--post` and `--prompt` and nothing else. No `--earlier`, because the slot's earlier records point at the shipped job and the chain check then fails `earlier points at the approved job`; and no `--asset-source`, because there is no vault copy. The run reports the five approval-shaped failures plus the embed check, which is the documented shape for a rejected render.

## Check the post's other slots before the closing comment promises anything

A render submitted before the card went up can land while the card is being closed. One `imagegen status <job>` per unclosed slot, taken just before the comment is written, decides what the comment may say: still running, or finished with a file in staging and a byte size. Name the job id, the staging file and the issue that opens that slot's card, normally the campaign issue that holds the collect, and close the post `card-done <n> --rendering` either way: that slot's card belongs to the campaign, so this issue still goes `done` on its own items.

## Close the issue `done` on the card's scope, not the post's

The issue's scope is the items the card carried. When the post still holds slots the card never had, the comment names them and the issue they ride, and the issue goes `done` on that scope — an issue left `in_review` to keep an unrelated slot alive strands the close and has no wake path of its own.
