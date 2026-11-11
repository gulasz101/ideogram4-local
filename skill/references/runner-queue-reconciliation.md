# Reconciling the runner's queue against the board

`queue.json` is a claim about the board, not a copy of it. Card runs close issues, ship renders and flip rows while the watchdog sleeps, and not every one of them records its close. The daily wake is therefore not "read the slot" — it is **row ↔ issue reconciliation**, then Advance, then the document.

Read `references/backlog-review.md` for the card-side procedure (batch mode, re-render rounds, stall shapes). This file is the runner-side checklist.

## Order of operations

1. Read the queue once, in one pass, and print the rows that are not `done`:

   ```bash
   python3 - <<'EOF'
   import json, collections
   q = json.load(open('/Users/paperclip/image-studio/backlog/queue.json'))
   print(dict(collections.Counter(p['state'] for p in q['posts'])))
   print('slot', q.get('slot'), 'ready', q.get('ready'), 'batch', q.get('batch'))
   for p in q['posts']:
       if p['state'] != 'done':
           print(p['n'], p['state'], p.get('issues'))
   EOF
   ```

2. Reconcile each non-`done` row against its issue (table below). Repair first, so the counts you report are the counts you verified.
3. Only then call `backlog.py next` — it **claims the slot as a side effect**, so a read before the repair can hand you a post you then have to release.
4. `scripts/put-queue-doc.py --issue-id <runner> --run-id <this run>`, re-arm the monitor, one comment.

## Row ↔ board table

| row says | board says | action |
| --- | --- | --- |
| `rendering`, no batch entry, not the slot, its last card is `done` | the post is finished, or every re-render of it is approved and shipped | `backlog.py card-done <n>` — the helper's third branch sets `done` and answers `closed_without_slot`, touching neither the slot nor other posts |
| `card`, issue `in_review`, verdict card answered, live run present | that run is applying the verdicts | leave it; do not apply anything twice |
| `card`, issue `in_review`, verdict card pending | waiting on the human | leave it; the 24-hour rule does not apply to a card that is answerable |
| slot holds the post, `issue: null` | the create never landed | `backlog.py opened <n> <ID>` if the issue exists, `backlog.py release` if it does not |
| `rendering` and a job is still in the lane | work in flight | leave it; arm a short hop monitor past the last ETA instead of a daily beat |

`card-done` **refuses** when the post is neither in `batch`, nor the slot, nor `rendering`. That refusal is information, not a bug: the post is already closed, and the usual cause is two runs closing the same card.

## Concurrency: the board moves while you read

- **Read once, decide once.** A queue read and an issue-status read taken seconds apart can disagree — a sibling run can close a card between them. When they do, take the later reading, then look for a live run on that issue before you call it drift. A run with `status: running` on the card is the mechanism, not a stall.
- **Never repair a row a live run is working.** The repair writes `queue.json` under the helper's lock and will happily overwrite state that run is about to set correctly.
- Another run holding the shared workspace is normal. The queue helper's lock is what protects `queue.json`; the workspace claim protects files, not queue state.

## A finished render with no card in front of it

Fetch nothing and open nothing until you know who owns the collect. A repair campaign's monitor usually owns the fetch-and-check for a round it submitted; its queue note says so in words ("do not open its card before that render is read"). Opening a second card for a post that already has a round in the vault splits the verdicts across two issues and makes the post unreachable by `card-done`.

## Cosmetic drift worth reporting, not fixing

- A post's `issues` list can carry the same identifier twice when a batch create deduplicated to the issue the slot had already made. Nothing reads that list by count; `fix-issue` replaces an identifier rather than de-duplicating.
- A card titled `Post <nnn>: …` instead of `Backlog review <nnn>/153: …` is a card the campaign created. It is a valid card; do not rename or recreate it.

## The comment

Lead with the work, one short line per repair with the reason it was needed, then the verified counts, the document revision, the monitor time, and the scan result. Do not narrate recovery.
