# Queue maintenance recipes: the render database and the backlog

One-off snippets for fixing stale queue state, in either queue. The `sqlite3` recipes run from `~/git/ideogram4-local`; the backlog recipes go through `backlog.py`, which takes the lock itself.

**A card you build against an unclaimed post cannot be registered, so claim before you record.** `opened <n> <id>` answers `the slot is not held by post <n>: None` and `batch-opened <n> <id>` answers `post <n> is not a batch card: []`, and both read like a broken queue when they are only the missing claim. Two routes, two calls each, card built and uploaded between them:

- no card open and this post is next — `next` claims the slot, then `opened <n> GUL-<id>`;
- another post's card holds the slot — `batch-open 1`, check the `n` it returns is your post, then `batch-opened <n> GUL-<id>`.

What must precede what is the claim, not the card: creating and uploading first is fine, registering first is not. The refusal cases, the `wait` body that is your own claim, and the repairs for a post already in `rendering` or stranded on a dead card are all below.

## A backlog post that reads `card` while its card is cancelled

`state: card` means "a card is open and someone is reviewing this", so nothing else will ever pick the post up. When a card is withdrawn or cancelled — superseded images, a bad render set — its post keeps `card` and its `batch` entry keeps naming the dead issue, and the post silently leaves the campaign: it is not `todo`, so no runner can take it, and it is not `done`, so nobody counts it as finished.

Detect it by cross-checking `backlog.py status` against each open card's status: any non-done post whose every recorded issue is `cancelled` is stranded. A `card` state pointing at a cancelled or missing issue is invisible in `status` counts, so `grep` each post's `issues` against the live board and sweep for this before a batch run rather than after. Repair in this order:

```bash
cd ~/image-studio/backlog
python3 backlog.py card-done <n> --rendering   # drops the dead batch entry, post moves to the render lane
python3 backlog.py ready <n> <round> <brief>   # only once that round's prompts exist
python3 backlog.py batch-open-ready 1
```

`--rendering` is the honest state for a post whose replacement renders are still to come. `card-done <n>` without it sets `done` and loses the post for the campaign — that flag is the only difference between a repair and a false completion.

**A batch entry whose card came back approved is cleared the same way, and it is not a cancellation.** A post can carry a round-2 card that resolved while another of its slots is still open: the `batch` entry then names a `done` issue, the post reads `card`, and nothing is actually in review — so the campaign believes a card is open on it and no runner may take it. `card-done <n> --rendering` drops that entry and leaves the post in the render lane, which is the truth (the round closed; the post still has a slot to render). Read `batch`, the post's `state` and its `issues` before choosing, because an entry naming a `done` issue and one naming a `cancelled` issue look identical from `status` counts alone.

**Repair only posts you are working.** `backlog.py` rewrites the whole `queue.json`, so a repair issued while another runner is mid-round on the same post double-books it: one card, two rounds. Flag another run's stranded post in an issue comment and let the batch that owns it fix it.

## Another run can claim the post you have staged prompts for

An audit is not a claim. Between the hop that writes the prompts and the hop that submits them, a sibling run can take the post: its `state` flips `todo` → `card`, the identifier appears in both `issues` and `slot.issue`, and `slot.since` carries when it was claimed. **Re-read `slot` immediately before submitting a batch you staged earlier** — a batch sent for a post another run now holds is two rounds of renders for one slot, and it is invisible in `status` counts.

When that happens, do not render, do not re-audit and do not open a card. The prompt files are the useful thing you still own: put a note on the post naming every staged file with its path, word count and the one-line beat it carries, plus a clause that the post belongs to the other run's issue and you will not submit for it. One call saves the owning run the whole audit, and say the same in one sentence on your own issue comment so a reader of the campaign thread does not think the post fell out of the campaign.

**The note works, and the job table is how you prove it.** A sibling run that takes the post submits your staged files under their own `--name` slugs, so the confirmation is a new row whose `output_path` ends in `<your slug>-<hex>.png`:

```bash
ssh -o BatchMode=yes m1max 'sqlite3 ~/git/ideogram4-local/jobs.db \
  "select id,status,output_path from jobs where output_path like \"%<your slug>%\" order by created_at;"'
```

Read that before auditing the post a second time: a row with your slug and `status: done` means the hand-off landed and the picture belongs to the owning run's card, not yours. No row a few hours after a note means nobody read it and the post is still waiting, which is the case to report. Either way say which it is in one line on your own issue comment — a hand-off nobody confirms is indistinguishable from a post that was abandoned, and the next hop will re-audit it from scratch.

**`notes` is a list, not a string.** `p.get('note')` returns `None` on every post and reads exactly like a post whose notes were wiped; join `p['notes']` before grepping it, and confirm a note landed by reading it back out of `queue.json` rather than by the `{"ok": true}` the write returns.

**A record's prompt block is read with `sed -n '/^## Prompt/,+60p' <record>.md`.** `awk '/^## Prompt/,/^## /'` prints the heading alone, because the end pattern also matches the start line — which looks like a record whose prompt was never stored. That block is what the image was asked to be, so read it before rewriting anything.

## A queue note that names another post's draft is filed on the wrong post

`backlog.py note <n>` appends to whichever post number the run passed, and a run that misnumbers its own post leaves an audit note attached to the wrong draft. Judge a note by what it names, not by where it sits: if the body names a different draft path, or slots the post does not have, the note belongs to that other post and **that post's audit trail is missing it** — so the next card on it re-audits prompts that are already staged under a wrong-numbered filename. The tell is cheap to check, because the draft filename is in the note's own first lines and in the post's `post` field.

Do not move it: `queue.json` changes only through `backlog.py` and there is no subcommand that relocates a note, so a hand edit is the one thing forbidden here. Report it instead — on the runner, and in one line in your own closing comment — naming the post that holds it, the draft it actually names, its slots, and the absolute paths of any staged prompt files it points at. Whoever opens the real post's card then finds the staged work from the note's description rather than re-doing the audit, and the staged files keep their wrong-numbered names because renaming them is a second unrecorded edit.

**Read a post's notes against the brief before trusting either.** A note that says a header is live, or an audit is done, is about that post only if the draft path in it matches the post's own; and the brief is generated earlier than the notes, so the notes are usually the later fact — but the record's `verdict:` is the fact that decides whether anything is left to review.

## A slot claimed with nothing behind it is a stall, not a reservation

`backlog.py next` writes the slot the moment any runner asks, and the reservation carries no proof its run will ever use it. The shape is: `slot.n` names a post, that post's `state` is `card`, its `issues` list is **empty**, `slot.issue` is null, and nothing was submitted or rendered for it. Because `card` means "a card is open and someone is reviewing this", the render lane sits idle and no other post can advance while the phantom holds it.

Confirm the stall before filling it, since a genuine in-flight round looks identical from the queue alone. Ask the render host whether anything of this batch exists at all:

```bash
ssh m1max 'sqlite3 ~/git/ideogram4-local/jobs.db "select status,count(*) from jobs group by status; select id,status,created_at from jobs order by created_at desc limit 5;"'
```

No `pending` row, no `running` row and no row created since the claim means nothing is being rendered for that post, and an issue-list read finding no issue for its number means nothing will collect it either. Judge the age against one render cycle (about 21 minutes plus queue): a claim younger than that may still be an audit in progress, while a claim that has outlived it on an empty lane is stranded and the post is losing hours.

Repair it and take the batch in the same run: `python3 backlog.py card-done <n> --rendering` drops the phantom card state and returns the post to the render lane, then submit your prompts and `backlog.py note <n>` the job ids. Say on the issue comment that the slot was claimed with no issue and no renders and that you filled it — a silent takeover reads to the next hop like two runs on one post, and whoever claimed it first will look for their work.

**When the claim is your own and you are not taking that post, `release` is the repair — not `card-done`.** `next` is a write: calling it to see "what is queued" claims the next `todo` post, flips it to `card` and puts the post number in the live slot with `issue: null`. A run that then does other work leaves a slot that reads as a card nobody is reviewing, and every sibling run is blocked behind an audit you never intended to start. `python3 backlog.py release` is exactly this repair: it recognises a slot with no issue behind it, returns the post where it came from (round 1 to `todo`, a later round to `ready` with its brief kept), clears the slot and prints the entry it released. `card-done <n> --rendering` is the wrong tool here — it leaves a post you never audited sitting in the render lane, which is a different wrong state. So read the queue out of the file when you only want to know what is next, and call `next` only when you mean to claim the post; say in the same run if you had to release one, because a claim that existed for two minutes is invisible in `status` afterwards. **Do not reach for `backlog.py status` as the cheap read of board state: it prints every post's full notes, so on a long campaign one call returns hundreds of thousands of characters and the hop's context is gone before the audit starts.** Ask `queue.json` directly for the numbers the hop needs — `state`, `issues`, `slot`, `batch`, and `ready` — plus the one post's last note, and keep the whole-table dump for the rare run that genuinely has to sweep every post.

**Which repair depends on whether the pictures already exist.** With nothing rendered, `card-done <n> --rendering` is right: the post goes back to the lane and the batch renders. With the renders finished and checked in staging, the stall is only a missing card, and `card-done` would throw away the state you need. Fill it instead: create the card, then `python3 backlog.py opened <n> GUL-<id>` — that works precisely because the slot is still held by the post (`slot.issue` null, `slot.n` naming it), and it records the issue without touching the round or the state. Confirm with `backlog.py next`, which should then answer "wait — slot held by post <n> round <r>" with the issue named. Both posts that hit this in one day (080 and 081) were the second shape.

## A `todo` post with renders in flight has no state to move to, so its note carries the warning

Shape: the live slot is held by another post's card, the lane is empty, you audit the next post and submit its renders anyway. The post stays `todo`, and **there is no subcommand that moves a post to `rendering` without taking the slot**: `card-done <n> --rendering` needs either the slot or a `batch` entry, `next` answers `wait` while any card is open, and `ready` is the placeholder a sibling run pops into an empty card. Do not fake the state.

The honest end state is `todo` plus a **leading** note on the post, and it is the only control between a sibling runner and a duplicate batch:

- the job ids and the collect time, so the run that reads it can collect rather than resubmit;
- the words `DO NOT SUBMIT this post again` and `do not open a card for it before the collect` — in those words, not as a hint;
- one clause on why the state did not change (`the slot is held by post <n>`), so the next reader does not read the mismatch as a broken queue.

Then print the state before the run ends and say it in the issue comment as well: a comment that earlier claimed "no ready entry, on purpose" reads to the next hop as "nothing in flight", and the two together are what keep the post from being audited twice. `backlog.py status` lists a post by state, so a `todo` post with six jobs rendering is invisible in the table — the note is where the work lives.

## `ready` queues the post; only `batch-open-ready` turns it into a card entry

```bash
python3 backlog.py ready <n> <round> backlog/briefs/<slug>.md   # post -> ready, entry appended to "ready"
python3 backlog.py batch-open-ready 1                            # opens the OLDEST entry in "ready", prints it
python3 backlog.py batch-opened <n> <GUL-id>                     # records the issue id on that batch entry
```

`batch-open-ready` takes from the **front of the `ready` list**, so it opens whichever post was queued first, not the one you just marked ready. When another post is already queued, the call returns `opened: [{n: <the other post>}]` and your post stays in `ready` with no batch entry — then `batch-opened` has nothing to write to and the card you are about to create is not tracked. Read the returned `opened` list every time and call `batch-open-ready 1` again until your post appears; each call moves exactly one entry, and it never touches the live `slot`.

Check the batch afterwards with:

```bash
python3 -c "import json;q=json.load(open('queue.json'));print([(b['n'],b.get('issue')) for b in q['batch']])"
```

An entry with `issue: None` is opened but has no card yet — that is the normal state for one or two minutes while the card is created, and a permanent one means the create failed. Before treating it as a failed create, read the post's own `issues` list: an `issue: None` batch entry whose post already carries a card id is a duplicate left behind by a re-open, and creating a card for it puts a second card on a post that is already in review. Flag that shape for the run that owns the post instead of creating another card.

**`batch-open-ready` does not create the Paperclip issue, so a card opened with it is not a card yet.** It appends a `batch` entry with `issue: null` and moves the post to `card`; the issue itself is a separate `POST /companies/<cid>/issues` whose `description` is the **content of the brief path recorded in that ready entry**, followed by `python3 backlog.py batch-opened <n> <GUL-id>`. Until that PATCH-able pair is done, `status` counts a card that nobody can open, and a sibling runner reading the empty entry cannot tell it from a failed create. So the order is: write the card brief **at the path the ready entry already names** (it inherits the round's audit brief path, so rewrite that same file as the card brief — paths, byte sizes, sha256, per-item why and check), then `batch-open-ready 1`, then create the issue, then `batch-opened`.

**A slot that `next` opened by itself has no `batch` entry, and it is recorded with `opened`, not `batch-opened`.** `python3 backlog.py opened <n> <identifier>` writes the identifier straight onto the slot and appends it to the post's `issues`; `batch-opened` only walks `batch` entries and has nothing to write to on such a post. **`opened` refuses with `the slot is not held by post <n>: None` whenever `next` has not claimed the slot yet** — so the order after a collect on a post whose renders you submitted with no `ready` entry is: `next` (it flips the post from `todo` to `card` and puts the post number in `slot`), then build and upload the card, then `opened <n> GUL-<n>`, then `note <n> "..."`. **`next` on a free slot claims it, and a successful claim reads exactly like a refusal.** With the slot empty it answers `{"action": "wait", "reason": "slot held by post <n> round <r>", "issue": null}` — the post number in that reason is *your* post, which it has just moved from `todo` to `card`, and `issue: null` is the slot it has just handed you. So "obey a `wait`" does not mean "stop": read the body. A `wait` that names a **different** post, or names your post with an `issue` some other run recorded, is the stop. A `wait` that names your post with `issue: null` is your own claim, and the next call is `opened <n> <GUL-id>`. The distinguishing read is `queue.json`'s `slot.n` before and after, not the `action` field. The card itself may be built before or after that claim, as long as `next` precedes `opened` in the same run.

Making `opened` the first call after the card exists reads like a broken queue state; it is only the missing claim. **The other order that records the same card without calling `next` first is `batch-open 1` then `batch-opened <n> <id>`**: it claims the post, flips it to `card` and writes the identifier in one pass, which is the shape to use when the card is already built and its post is the next `todo`. Read the returned `n` before the second call — `batch-open` claims the next post in queue order, not the one you have in mind — and confirm afterwards that the post reads `card` with your identifier in `issues`. The identifier is `issue.identifier` (`GUL-<n>` on the issue object) — `issue.key` is `null` on a freshly created issue, so a check that reads only `key` looks like the board never assigned one. The full create-then-upload-then-verdict order for that case is in `references/hold-back-or-ship.md`, under the placeholder section.

**An upload can answer `500 Internal server error` and succeed on an immediate retry.** One file of a five-file card did exactly that. Loop three times, and accept an attempt only when the response's `sha256` and `byteSize` match what you computed from the file on disk — a check on the status code alone accepts a truncated body, and the mismatch then surfaces later as a card showing the wrong picture. Keep the returned `id` per item so the verdict request can bind each item to its own attachment.

## The queue answers `wait`, but the renders are done and the card is the only missing piece

`next` refuses whenever any card is open, so a post whose six renders are collected and checked but whose card does not exist yet reads as blocked. It is not blocked: a card may go up **alongside** the held slot as a batch card, which is how a finished post gets delivered while another post's card sits with the owner.

```bash
python3 backlog.py batch-open 1     # -> {"opened": [{"n": <post>, "round": 1, "brief": ..., "title": ...}]}
# create the issue from the card brief, upload the passing files, write the verdict card
python3 backlog.py batch-opened <post> GUL-<id>
```

`batch-open <count>` picks the next post in queue order by itself — no `ready` entry and no `next` claim needed, which is what separates it from `batch-open-ready` (that one only drains entries you already queued in `ready`). **Read the returned `n` before creating anything.** If it names a post you have not finished, you are about to open the wrong card: stop and check that post's state rather than uploading six files onto a card that does not match. The entry it returns carries the round's *audit* brief path, so write the card brief at its own path and pass that as the issue description. Afterwards confirm with the `queue.json` check above that the entry names your identifier, and leave the live slot alone — the batch entry, not the slot, is what records this card.

**`batch-open` only ever claims a `todo` post, so it can never register a card for a post that is already `rendering` — and there is no undo.** Reaching for it to record a round-2 card on a post whose round 1 shipped gets the *next `todo` post* instead: the entry comes back naming a different post number, that post is now `card` with a brief you never wrote for it, and nothing returns a claimed batch entry to `todo` (`card-done <n>` would close it, `card-done <n> --rendering` would strand it as rendering with nothing in flight). Read the returned `n` before creating anything, and when it is not your post, stop and turn it into real work — audit that post, submit its batch, and say so on the issue — rather than leaving a phantom entry that reads to a sibling runner as a card about to open.

**An entry opened for a post you are not going to audit is cleared with `card-done <n> --rendering`, and there it is the release rather than a strand.** The entry leaves `batch`, the post reads `rendering` with no issue, `status` stops counting a card nobody built, and the rest of the board is untouched. Say in the run's comment that the post was released with nothing rendered for it, because a state change nobody explains reads to the next runner as a claim that was abandoned.

**Card order belongs to the queue, not to readiness.** A post whose frames are mostly clean with one slot still repairing does not get a card of its own out of turn: every route to a `batch` entry claims the next `todo` post, so the attempt either cards your post ahead of the order a sibling runner is working — two cards on one draft the moment they reach it — or spends the entry of a post ahead of it. Leave the clean frames in staging with a note naming the held slot and its repair prompt, and let `batch-open` reach the post; it then goes up whole, which is also the better shape for the owner's eye than two sittings on one draft.

**A post in `rendering` that carries a closed issue id is repaired with `fix-issue`, not `opened`.** After a round ships, the post stays `rendering` (its remaining slot still has to be rendered) while `issues` still names the finished card, and `opened <n> <new>` refuses with `the slot is not held by post <n>: None` because no card is holding the live slot. Point the record at the card you just built:

```bash
python3 backlog.py fix-issue <n> GUL-<closed> GUL-<new>
# -> {"ok": true, "post": n, "issues": ["GUL-<new>"]}
```

It rewrites the id in the post's `issues`, in any `batch` entry and in the slot, so the next run reads one card per post instead of a closed one. Confirm with the `queue.json` post dump — the state stays `rendering` and that is honest: the post is not done, its card is open, and its note should say both. `fix-issue` refuses with `post <n> does not record <old>` when the id is not there, which means the post was already re-registered by another run — read the post's `issues` before retrying.

**A round-2 card on a post that is neither `todo` nor already a batch card is registered with `ready` then `reopen-card`.** `batch-opened <n> <id>` refuses with `post <n> is not a batch card: []` when the post has no `batch` entry, and `opened <n> <id>` refuses because the live slot belongs to another post's card — so the card you just built for a post in `rendering` has no direct route to a record. The pair that works:

```bash
python3 backlog.py ready <n> <round> backlog/briefs/<card-brief>.md   # post -> ready, brief queued
python3 backlog.py reopen-card <n> GUL-<id> <round>                    # builds the batch entry FROM that brief
```

`reopen-card` builds the `batch` entry out of the `ready` brief, removes the ready entry, sets the post to `card` and appends the identifier to its `issues`. `batch-open-ready 1` writes the same entry but takes the **oldest** ready item whatever post it belongs to, so with any other round queued it opens the wrong post; `reopen-card` names the post itself, which is why it is the right call here even though its documented use is a repair. Run the two in one command (`&&`) with nothing between them: `ready` leaves the post briefly poppable by `next`, and that is the one window in which a sibling run could open a second card for the same round. Confirm afterwards that `batch` names your identifier and that `ready` is empty again.

**The same pair is the route for a round-1 card on a plain `todo` post whose slot you never claimed, and there it is the safe one.** When the card has already been created and uploaded and the queue still shows `state: todo`, `slot: None`, `issues: []` — the shape after a collect on a post whose renders went in with no `ready` entry — `opened <n> <id>` refuses with `the slot is not held by post <n>: None`, and the documented fix (call `next` first) claims whichever post is next in queue order, which is a different post whenever a sibling runner's audit is queued ahead of yours. `ready <n> 1 <card-brief>` followed by `reopen-card <n> GUL-<id> 1` writes the batch entry, sets the post to `card` and appends the identifier without touching the live slot at all, so the card built from staging is recorded in two calls and nothing else on the board moves. Verify with the `queue.json` dump: `state: card`, `batch` naming your identifier with the round you built, `ready` empty, `slot: None`.

**Rewriting the audit brief in place is the normal move and `write_file` will refuse it the first time:** the file was written by an earlier run, so read it fully and merge rather than overwriting blind, or the write answers `stale_write_blocked` and costs a round trip. **Read what is already there before deciding to replace it**: the path a batch entry names may hold a generated card brief from the campaign's own generator, carrying the per-item table and a line saying not to render anything for round 1 — replacing that loses the table, so append a dated section stating what is actually in flight (slots, both job ids, prompt paths, last ETA) and leave the generated half intact. **A partial read does not satisfy that guard** — `read_file --limit` or an offset read is refused again with `was last read with offset/limit pagination (partial view)`, so page the whole file once before overwriting; two refusals in a row means you read a slice and then a slice.

**The issue's own run claims it seconds after creation** — `checkoutRunId` is non-null and its attachments start appearing — and that run does the uploads and writes the verdict request from the description. **Your own agent comment does not supersede a pending card** (only a board/user comment does), so a follow-up comment is safe — but it cannot add an item or edit a description, because the payload is frozen, so everything the card must carry still belongs in the description. Two consequences of that claim, both met on one card: the holder can be a *different* run from the one that created it, and then your `PATCH {"status":"in_review"}` answers `409 Issue run ownership conflict` with `details.checkoutRunId` naming that run — the card is fine and lands `in_review` when the holder flips it, so do not rebuild it or re-POST the card; post one comment saying what is already in place (attachments hash-matched, one pending verdict request, N items) so the holder does not open a second one, and confirm the status on the next read. **The holder can also be dead, and then the card is empty AND sealed:** `activeRun` null, no attachments, no comments, no interactions, and only `issue.created` on the activity feed while `checkoutRunId` still names that run. From another run **checkout, release, the attachment upload, the monitor PATCH and `DELETE /comments/{id}` all answer `409`** while `POST /comments` still answers `201`, so the card cannot be finished or retired from outside. Do not open a second card: post the whole build note on it — absolute staging paths, byte sizes, full sha256, item ids, the beats and the caveats, and which script to run — leave the same lines in the post's queue note, and let the next wake re-read the lease before anything else. `POST /issues/{id}/checkout` needs `{"agentId": …, "expectedStatuses": ["in_progress","todo"]}`; `{}` and `{"runId": …}` both answer `400`. Verify afterwards by reading `/issues/<id>/attachments` (`byteSize`, `sha256`, `originalFilename`) against the brief and by listing the interaction's `payload.items` ids, which is what proves the right five files went up and nothing else did.

## The `submit` flags carry the engine, so the file flag is not interchangeable

```bash
imagegen submit --engine ideogram4   --prompt-json backlog/prompts/<slug>.json --name <slug>
imagegen submit --engine flux2-klein --prompt-file backlog/prompts/<slug>-flux.txt --name <slug>
```

`--prompt-json` is the structured JSON prompt and belongs to ideogram4; `--prompt-file` is plain UTF-8 text and belongs to flux2-klein. The slug flag is `--name`, not `--slug` — passing `--slug` fails with `unrecognized arguments` on a command that otherwise looks correct, which is easy to misread as a broken prompt file. **The path is the flag's value, so it comes after the flag; a path written before it fails as though the flag were empty.** `submit backlog/prompts/<slug>.json --engine ideogram4 --prompt-json --name <slug>` answers `argument --prompt-json: expected one argument`, because argparse finds no value for the flag and `submit` takes no positional file. Keep the order `--engine <engine> --prompt-json <path> --name <slug>` (and the `--prompt-file` form for flux) rather than moving the path to the front, which reads like the natural shape. `submit` prints the job id on stdout, so capture it in the same line rather than piping through `tail`. **With `--json` it prints a multi-line object and `| tail -1` comes back as `}`** — the id is inside the object, so either parse it as it arrives or submit the batch blind and read every id back in one query:

```bash
ssh -o BatchMode=yes m1max 'sqlite3 -separator "|" ~/git/ideogram4-local/jobs.db \
  "select id, engine, output_path, status, created_at from jobs where output_path like \"%<slug-prefix>%\" order by created_at;"'
```

The `--name` slug is in `output_path`, so one `like` catches the whole batch. A loop that submits three ideograms and then three flux renders comes back as two contiguous blocks in `created_at` order, and that single query replaces six `imagegen status` calls — it also proves the count (six rows, not five) before the monitor is armed and before any id goes into a brief.

## Collect a finished render

`imagegen fetch <job_id> --dest <dir>`. The destination flag is `--dest`; `--out` is rejected as an unrecognised argument, and the error looks like a broken job id rather than a wrong flag.

## Mark a finished job as `done`

Use this when the worker produced the output file but exited before updating the database row.

```bash
cd ~/git/ideogram4-local
python3 - <<'PY'
import sqlite3, datetime
conn = sqlite3.connect('jobs.db')
cur = conn.cursor()
job_id = 'REPLACE_WITH_ACTUAL_JOB_ID'
cur.execute(
    "UPDATE jobs SET status='done', finished_at=? WHERE id=?",
    (datetime.datetime.now().isoformat(), job_id)
)
conn.commit()
print(f"Updated {job_id} to done")
conn.close()
PY
```

## Delete a test/accidental job

```bash
cd ~/git/ideogram4-local
python3 - <<'PY'
import sqlite3
conn = sqlite3.connect('jobs.db')
cur = conn.cursor()
job_id = 'REPLACE_WITH_ACTUAL_JOB_ID'
cur.execute("DELETE FROM jobs WHERE id=?", (job_id,))
conn.commit()
print(f"Deleted {job_id}")
conn.close()
PY
```

## List all jobs

```bash
cd ~/git/ideogram4-local
python3 - <<'PY'
import sqlite3, json
conn = sqlite3.connect('jobs.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("SELECT * FROM jobs ORDER BY created_at")
for row in cur.fetchall():
    print(json.dumps(dict(row), indent=2, default=str))
conn.close()
PY
```

## A job id that starts with a dash

Job ids are random base64url, so roughly one in sixty begins with `-` (`-LTfR1wza28`). argparse reads it as an option and every `imagegen` subcommand answers `the following arguments are required: job_id` — `imagegen status -- -LTfR1wza28` fails too, because the wrapper re-passes the argument to the remote CLI without a separating `--` of its own. That error means "argparse ate the id", not "no such job": do not re-submit the render.

Reach it over ssh instead, from the Air:

```bash
ssh m1max 'cd ~/git/ideogram4-local && python3 ideogram4_local.py status -- -LTfR1wza28'
```

The remote CLI has no `fetch` subcommand (`submit, lint, rewrite, status, list, wait, worker`), so collect a dash job by its own `output_path` from that JSON:

```bash
scp m1max:/Users/wojciechgula/git/ideogram4-local/output/studio/<date>/<slug>-<hex>.png ~/image-studio/staging/<date>/
```

Then check and upload the PNG from staging as usual.

## Read `queue_ahead` before submitting, because the queue is shared

`imagegen status <job>` reports `queue_ahead` and `eta_minutes` for the job you just put in. On 2026-10-28 the queue went from 40 ahead to 84 within two minutes while concurrent campaign runners submitted their own batches, taking a six-render batch from a 3-hour estimate to 16 hours. A render that lands after the morning review window is worth nothing, so: submit, then immediately read the status, and if the ETA is past the next review window say so in the issue comment rather than adding another batch on top. One batch in flight across the whole campaign beats one per runner.

**A confirmed window outranks that cap, because the cap protects the queue and a window is about the path.** The six-render rule exists so a shared, deep queue does not starve every other card; when a fifteen-word probe answers and `queue_ahead` reads 0, the constraint has flipped and the whole staged set goes in — every post whose prompts are already written, repairs included, seconds apart in one run. Fifteen renders across seven posts cleared in four minutes on an empty lane, and the same set dripped one post per hop would have spent a day and lost the window at the next fault. Stop only when `queue_ahead` climbs on the first status read, because that is the shared queue coming back and the cap with it.

## Tell an engine-specific outage from a queue problem in one query

When your jobs come back `failed` while the lane looks busy, one query settles whether the queue, the worker and the other engines are fine and only your engine's upstream is broken:

```bash
ssh -o BatchMode=yes m1max 'sqlite3 -separator "|" ~/git/ideogram4-local/jobs.db \
  "select substr(created_at,12,8), engine, status, id, substr(coalesce(error,''),1,60) \
     from jobs where created_at > \"<window start>\" order by created_at;"'
```

Read it as one timeline. If a `flux2-klein` or `ideogram4` row reads `done` between two of your engine's `failed` rows, the worker, the queue and the output path are all working and the fault sits inside the failing engine's own proxy path — which is exactly the sentence the engine's owner needs, because it rules out the shared components they would check first. Quote both edges of the window (the last `done` row on your engine and the first `failed` one after it), not a single timestamp: an intermittent backend clears and returns, and the band is the only thing that can be checked against the proxy's own log.

**Date a failure by `started_at`, not `created_at`.** A job queued behind a long ideogram starts half an hour or more after it was submitted, so its creation time says nothing about when the engine was actually reached, and a window built from creation times can put a failure outside the band it really belongs to.

## Ask the queue whether a card may be opened at all

`python3 backlog.py next` is the authority on whether another card goes up, and it answers `{"action": "wait", "reason": "slot held by post <n> round <k>", "issue": "GUL-..."}` whenever a card is open or a re-render round is queued. Run it before every submission decision and obey a `wait` even when the render lane looks quiet to you: opening a card while the slot is held double-books the post, and the cost is two rounds of renders for one slot. It is also the evidence a run quotes when it ends without submitting — "the queue answers wait on <issue>" is a decision, where "the lane looked busy" is an impression. Judge the load by that answer plus `queue_ahead` on the jobs already in, not by counting posts in `rendering`.

**A post the queue already reads `done` was shipped by whoever held its card, so read the card before doing the work again.** On a monitor wake, re-read the card's status, its interaction `result` and the post's `state` first: another run can answer the verdicts and close the whole round while you sleep, and the vault copies, embeds, records and `card-done` are then already written. Verify them — attachments by `byteSize`/`sha256`, the embeds in the draft, the record filenames — and report the gap you found instead of re-running the close, because a second `card-done` or a second vault copy of the same item id is the defect this rule exists to prevent. **`card-done <n>` then answers `the slot is not held by post <n>: {...}` with the slot already naming the next post** — that is the queue confirming the close happened, not a failed command, so re-read `status` and stop rather than forcing a state back.

**When a re-render ships under an embed path that does not change, the alt text is the only prose the copy did not touch, and it can still describe the old frame.** Read the draft's line against the shipped PNG and rewrite it from the picture: a sentence written for the previous round survives a same-path copy untouched, and one approved pair went in behind an alt text that said `at night, cold light` for a warm panelled room.

## Reset the whole queue (dangerous — only when debugging)

```bash
cd ~/git/ideogram4-local
rm -f jobs.db .lock
```

This removes all job history. Do not do this if you care about the existing jobs.

## Recover a lost job id from the queue instead of re-submitting

`imagegen submit` prints the id on stdout, so a batch submitted through a pipeline that ends in `tail` can silently drop the first job's id, and nothing else in the run records it. Do not re-submit to get it back — that is a second 21-minute render for a job that is already queued. Read the rows off the generation host:

```bash
ssh -o BatchMode=yes m1max 'sqlite3 -header ~/git/ideogram4-local/jobs.db \
  "select id, engine, status, output_path, created_at from jobs order by created_at desc limit 8;"'
```

**The columns are `id`, `status`, `prompt_type`, `prompt_value`, `engine`, `output_path`, `seed`, `created_at`, `started_at`, `finished_at`, `error`** — and the two names that read as obvious are both wrong: the key is `id` (`no such column: job_id`) and the state is `status` (`no such column: state`). A failed guess here is a schema question, not a dead database, so write the query against that list instead of trying names. There is also no `name` column, so selecting one is the same wrong guess; the slug lives in `output_path`. Rows come back newest-first by `created_at`, so a batch submitted in one script appears as a contiguous block and the missing id is the row whose `output_path` carries your slug.

**When the submit's stdout was lost and no `--name` was passed, find the batch by a phrase from the prompt itself.** `prompt_value` holds the whole prompt, so one `like` on a distinctive phrase recovers the ids in creation order, which is the order the batch went in:

```bash
ssh -o BatchMode=yes m1max 'sqlite3 ~/git/ideogram4-local/jobs.db \
  "select id, status, created_at from jobs where prompt_value like \"%<a phrase only this batch uses>%\" order by rowid;"'
```

Map the rows to slots by that creation order and check the count before any id goes into a brief or a monitor note. `imagegen status` takes the **job id only** — the `--name` slug answers `Job not found`, which reads like a lost job rather than a wrong argument.

**The `jobs.db` on the Air is not the queue.** The local `~/image-studio/jobs.db` has no `jobs` table at all, so a run that queries it concludes there are no jobs anywhere; every read that has to survive a lost id goes through `ssh` to the Max.

**Read the queue's own notes before sshing.** The fetched filename carries a fetch token (`<slug>-<8 hex>.png`), not the job id, so a job id cannot be read off the PNG on disk — but the run that submitted the render normally wrote both the job ids and the engine into the post's notes: `json.load(open('~/image-studio/backlog/queue.json'))['posts']['<n>']['notes']`, grepped for the slug or the staging filename. A brief can name the fetched file and its sha256 and still not name the job, and the card's own table and the library record both need the id. `imagegen status <id>` then answers `created_at`, `finished_at`, `engine` and `seed` in one call, which is everything the record's timestamps need. The ssh route is for when no note names the id.

## `jobs.db` timestamps are local time, not UTC

`created_at`, `started_at` and `finished_at` are written by the Mac's clock, which is CET (UTC+1 in winter). Read them as UTC and every ETA you compute from them is an hour late — that cost a published card estimate and a monitor firing an hour after the renders finished. Two habits fix the clock. Take `queue_ahead` as reliable — it is a count of jobs ahead — and **`eta_minutes` as nominal only, and a snapshot at that**: it answers about one nominal render per job ahead, does not move when the worker is running slow, and can print the same value for an hour — a probe waiting behind a single ideogram answered `queue_ahead 1, eta_minutes 23` at 07:20Z and again, unchanged, at 08:21Z. A job quoted at 21 minutes can finish 66 minutes after it starts, so arm a monitor past the **front job's own elapsed time** rather than past either number, and treat a hop that finds its own job still `pending` as a normal hop rather than a fault.

**A wait held inside the run needs its timeout named, and usually should not be held at all.** The terminal's foreground default is 180 s, so a bare `sleep 240` dies with `Command timed out after 180s` and returns nothing — keep an in-run wait under about 170 s, or pass `timeout=` explicitly — but do not trust the nominal maximum: an unattended run has been killed at **420 s** with `timed out after 420.0s` on a call that asked for 600, so budget a chunk of work under about 400 s and let the next hop continue rather than stretching one call to the whole batch. Better still, do not sleep: a monitor wake costs nothing, and the hop spent sleeping is a hop that cannot audit the next post's prompts. Measure the box instead, off the last few rows' own timings:

```bash
ssh m1max 'sqlite3 /Users/wojciechgula/git/ideogram4-local/jobs.db \
  "select id,status,started_at,finished_at from jobs where status=\"done\" order by rowid desc limit 5;"'
```

A recent ideogram commonly shows 50–90 minutes from `started_at` to `finished_at` while a flux frame shows 3–7, so the tail of a batch is the ideogram's measured time and not the quoted one. Arm the monitor past that measured time, and if you need an absolute finish time take `date -u` on m1max in the same call as the row you are reading so both are on one clock.

## A long note or body goes in a file, never as one quoted shell argument

`backlog.py note <n> "<long multi-line text>"` folds the whole text into one enormous shell word, and the run's command-approval gate stalls on it: the call is refused without ever reaching `backlog.py`, so the note is never written and the post reads as unaudited to the next runner. **Write the text to a scratch file with `write_file`, then call `backlog.py` from a short python script that reads that file and passes it as one argv element** (`subprocess.run([BACKLOG, 'note', str(n), text])`). The same shape carries every other long body — a Paperclip comment, a card description, a brief — because the text lives in a file a tool reads rather than on the command line, and the command itself stays short enough to be approved. Never hand-edit `queue.json` as the fallback: the note is the only durable record of the job ids and the brief path.

**The same file-first shape is what gets an image-measurement script to run at all.** A `python3 - <<'PY'` heredoc whose body names a render (`Image.open("staging/…/<slug>-<hex>.png")`) is refused before python starts — `Blocked: the lifecycle guard could not scan this command or referenced script: <path> is larger than the scan cap (1048576 bytes)` — because every script a command executes must be a scannable text file under 1 MiB, and a 2.4 MB PNG is not. The block names the image, which reads like a corrupt render; it is only the heredoc. **A heredoc that only reads a JSON file can be refused too**, with `Blocked: the lifecycle guard could not scan this command or referenced script: the scan budget was exhausted (remote reads at depth 1)` — the guard gives up scanning a multi-line body that fans out through `json.load`, so that refusal is about the *shape* of the command, not about a file being too large. The fix is identical: write the logic to a `.py` file with `write_file` and run it by path. Neither refusal is a permissions problem and neither is fixed by re-quoting the same body. Write the measurement to `cache/scratch/<slug>-measure.py` with `write_file`, then run `.venv-imgcheck/bin/python <that file>` from the image-studio directory: the script is text, the PNG is opened at runtime rather than scanned, and per-row luminance, per-column dark-pixel profiles and the crop saves all work unchanged.

## A staged prompt's filename prefix is the post number at the time of writing, not the queue's

Post numbering drifts — a draft gets renumbered, or the queue is rebuilt — and a prompt written as `095-cpu-saturation-r2.txt` can end up belonging to post 100. Trusting the prefix either sends the prompt to the wrong post or sends the next run into a fresh audit of slots that are already written.

Identify a staged prompt by **the draft path and the slot name inside it**, never by the number in front of it: grep the draft for its embed lines, compare the slot names (`![cpu-saturation](assets/2026-08-16/cpu-saturation.png)`), and record in the post's queue note which prompt file serves which slot, with the draft path spelled out. Three prompts of ~280 words are an audit's worth of work, and a note that names them is one line.

## Re-arming a monitor answers 422 “Monitor bounds are already exhausted”

`PATCH /api/issues/{id}` with `{"executionPolicy":{"monitor":{"nextCheckAt":…,"scheduledBy":"assignee","maxAttempts":6}}}` is refused on a long-lived issue with `422 {"error":"Monitor bounds are already exhausted","details":{"clearReason":"max_attempts_exhausted"}}`, and the issue is left with **no monitor at all** (`executionPolicy.monitor` reads null afterwards — a hop with no wake is how a campaign goes quiet for hours). The count is cumulative over the issue's whole life, so a small `maxAttempts` is spent within a few days of hourly hops. The fix is to stop sending bounds at all: a re-arm takes only `nextCheckAt`, `scheduledBy` and `notes`, because a body with no `maxAttempts` has no budget left to exhaust. Keep the bounded shape for a **new** monitor and use the minimal one for every hop after it. **Any** bounded body is refused once `monitorAttemptCount` reaches the schema maximum of 100 — `maxAttempts` above 100 is a `400 too_big`, and 100 itself is `422 max_attempts_exhausted` — so the "resend with `maxAttempts: 100`" fallback only works while the count is still below 100. At the cap the minimal body is the only thing that arms: it answers `200` and the monitor fires normally with the counter left at 100, so a hundred-hop campaign is not over. Clearing with `{"monitor": null}` does not reset the counter. Then read the issue back and confirm `executionPolicy.monitor.nextCheckAt` is the timestamp you meant: a 200 on the PATCH is not proof the wake is armed, and a refusal that arms nothing leaves the issue with no wake at all.

**Arm the monitor before posting the comment that describes it, and keep `notes` short.** The notes string is the one field with a length limit — **500 characters**, and a longer body answers `400 Validation error` with `path: ["executionPolicy","monitor","notes"], maximum: 500` and arms nothing at all, so a note that reads like a paragraph silently leaves the campaign with no wake; a helper script that posts the issue comment first and PATCHes the monitor second can end with the comment saying "monitor at HH:MM" while the issue carries no wake — the campaign then waits on a human and the comment is a false claim. Order every closeout as: PATCH the monitor, read `nextCheckAt` back, then post the comment, and keep the notes in a small script of their own so a length refusal cannot swallow the re-arm. Write the notes in their short form — job ids, collect time, and the one instruction the next run must obey (`do not submit this post again`) — and leave the long table to the brief, which has no length limit.

**A poster that posts the comment first and arms second leaves a false claim on the issue when the notes assertion fires.** The length check runs on the PATCH, so the comment is already up saying "monitor at HH:MM" while the issue carries no wake. Do not re-run the poster: the second pass double-posts the comment on the campaign issue, which is the noise this section exists to prevent. Arm from a two-line script of its own, read `nextCheckAt` back, and only then decide whether the comment needs a correction — a comment whose timestamp is still right needs none. Build every closeout poster as two entry points, `arm` and `comment`, and run `arm` first: a failure in either half then leaves the other untouched, and a half-succeeded poster is a state to read rather than a script to run again.

## A continuation wake can arrive before anything has changed

`issue_monitor_due` and `issue_continuation_needed` are different triggers: the second fires when the previous run ends, and it can land a minute later with the monitor still pointing hours out. Nothing on the renderer can have moved in that time, so the wake has no collect and no ship in it — and re-PATCHing the same `nextCheckAt` spends a write to say nothing, so read `executionPolicy.monitor.nextCheckAt` first, confirm it is still in the future, and leave the timer alone.

What that wake is worth: read both cards' verdicts on `/issues/{id}/interactions`, read the job table once to confirm nothing failed, and put the rest of the run into the **next** post — its prompt audit at record level, then the prompts written, linted and box-checked, saved and **not submitted**. Your own six renders already fill the cap, and a second batch behind them pushes every queued render back while breaking the one-batch-per-run rule; a comment restating the state the last comment described costs the owner a read for nothing. Say only what changed — here, usually "nothing landed; the next post is written and ready" — or keep it to the queue note and let the armed monitor do the talking.

## A shipping run that copies only the embedded paths silently drops the flux copies

Four posts shipped on one approval batch and three of them were complete; the fourth was not. The
run that shipped it copied `header.png`, `root-cause.png` and `verification.png` — the three files
the draft embeds — and stopped there, so the two **approved flux comparison copies** on the same
card (2304486 and 2392774 bytes, both approved by the reviewer) never reached the vault at all.
Nothing errored. The draft was correct, the queue said `done`, and the only trace was two approved
images with library records and no file next to them.

So a shipping checklist is per **approved item**, not per embed: list every item on the resolved
card, and for each one confirm a vault file whose sha256 matches the staging render. Items that are
not embedded are copied as `<slot>-flux.png` beside the embedded file and are **not** added to the
draft. A `card-done` in the queue proves nothing about the vault: read `result.items` on the
resolved `request_item_verdicts` interaction (that is where the verdicts live — the `payload.items`
entries keep `verdict: null` forever) and walk every approved id against the vault.

## `verify-slot.py` takes flags, and its lineage check reads your own chain as a duplicate

`scripts/verify-slot.py` is `--record <md>` plus `--job <job-id>`, with optional `--earlier <md>`, `--post <md>` and `--prompt`. A bare `verify-slot.py <record.md>` positional answers `error: the following arguments are required: --record, --job` and exits non-zero, which reads like a broken or unreadable record rather than a wrong call.

At a closeout, expect the same single failure on every approved record: **`job id appears in exactly this record plus its earlier records`**, whose argument lists the held-back attempts. That is the chain being correct — each held attempt carries `superseded_by: "<approved job>"`, so the check finds the approved id in records it was not told about. Pass those files as repeated `--earlier` and it passes; never "repair" it by editing the held records' `superseded_by`, which is the one thing that makes the lineage unreadable. Read the failing check's name before reporting a count like `28 checks, 1 failed` as a defect: a real defect fails on the prompt block, the hash or the embed, not on its own ancestry.
