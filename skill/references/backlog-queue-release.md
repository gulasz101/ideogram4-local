# Releasing a backlog post in the queue

The release half of a backlog card: the images are approved and written into the vault, and `queue.json` still has the post open. State lives in `~/image-studio/backlog/queue.json` and only `backlog.py` mutates it (it takes a lock), so every change here is one command followed by a read-back.

## Read the queue before choosing the flag

`backlog.py card-done <n>` has three branches, and the post's current state decides which one runs:

| what `queue.json` holds | branch | effect |
| --- | --- | --- |
| an entry for `n` in `q["batch"]` | batch release | the entry is dropped, the post's state is set |
| `q["slot"]["n"] == n` | slot release | `q["slot"] = None`, the post's state is set |
| the post's state is already `rendering` | close without slot | the post's state is set, nothing else |

`--rendering` sets the state to `rendering` instead of `done` in all three. Both mistakes cost a post: passing it when nothing is rendering leaves the post `rendering` with no monitor and no card to finish it, and omitting it while a re-render is genuinely in flight marks a post done under a picture still on the Max.

**A brief's claim about queue state is a hint, not the authority — read the queue.** Print the three facts before the call:

```bash
cd ~/image-studio/backlog && python3 -c "
import json
q = json.load(open('queue.json'))
n = <post number>
p = [x for x in q['posts'] if x['n'] == n][0]
print('state:', p['state'])
print('in batch:', [(b['n'], b.get('round')) for b in q.get('batch', []) if b['n'] == n])
print('slot:', q.get('slot'))
"
```

A brief written when a round-2 card was opened can say the post is in `rendering`; the card open moves it to `card` with a batch entry, and `card-done` then takes the batch branch. Neither the state nor the branch is a defect — the stale sentence in the brief is. Run the branch the queue's own state implies and say which one ran in the closing comment, so the next reader is not surprised by a post that closed differently from its brief.

**A batch release never frees the live slot, so there is nothing to Advance after one.** The slot moves only from the card that holds it. Check `q["slot"]` after the call rather than assuming a batch close queued the next post.

## The claim half: a post still in `q["batch"]` cannot be claimed

`batch-open-ready <count>` builds a `taken` set from the live slot and every existing `q["batch"]` entry, then `continue`s past any post in it. It does not fail: it answers `{"ok": true, "opened": []}`. So a round queued with `ready` for a post that is still a batch card stays in `q["ready"]` while no card is opened, and the round looks queued from every other angle.

That is the shape whenever the previous round's card was itself a **batch** card that closed without `card-done` — its entry is still in `q["batch"]`, pointing at the card that just closed. **Read `opened` on every call and treat an empty list as a failed claim**; the exit status is zero either way, so nothing else reports it.

Release before you claim, in this order:

1. `backlog.py card-done <n> --rendering` — drops the stale entry, sets the post to `rendering`.
2. `backlog.py ready <n> <k> <brief>` — queues the round with its brief path.
3. `backlog.py batch-open-ready 1` — claims it; `opened` names the post.
4. POST the card issue with the brief byte-identical to its description.
5. `backlog.py batch-opened <n> <ID>` — records the identifier the POST returned.
6. `backlog.py status` — the post reads `card` and the batch entry's `issue` is the new card.

Step 6 is the check, not the footnote: a post whose batch entry still names the closed card is a post the next `card-done` will release out from under the new one. And a round with **nothing in flight** — a card blocked on the post's author, where the render count is zero — is not released at all: the post stays `card` and the release happens in the run that submits the renders once the answer is in.

## Advance can hand out a brief whose card belongs to another issue

`backlog.py next` answering `create` means the slot is now claimed and a brief is waiting at the path it printed — **read that brief before POSTing anything**. Some rounds are collected by a separate issue: the brief says so in its first lines (*the collection is owned by <issue>, which opens this card once both PNGs are fetched and checked*) and its slot table still carries `fill in from imagegen fetch` rows with blank bytes and hashes.

- **Do not create the card.** A brief whose rows are unfilled hands the reviewer a table of placeholders; the collecting issue creates the card once the renders exist and have been checked.
- **Do not `release` the slot either.** The Advance already popped the post's `ready` entry, so a release leaves the slot empty and the round with no path to a card: the brief is gone from `ready`, the post is not in `todo`, and nobody will open it. This is the same orphaning the *never end a run with a post in `rendering` and an empty ready queue* rule guards against, arriving from the other direction.
- **Leave the slot claimed with `issue: null` and tell the collecting issue the state it will find** — one comment there naming the slot's `n`, `round` and `since`, saying `next` now answers `wait` and the only call it needs when it creates the card is `backlog.py opened <n> <ID>` (guarded; it refuses unless the slot still holds that post, which it does). Without that note its own run reads a claimed slot as someone else's card and can open a second one or release it in confusion.
- Say on the runner that the slot moved and the `queue` document is one card behind live state, since the collect happens later and elsewhere.

## Order the writes so a failure leaves an honest post

`card-done` is the second-to-last write, not the first: a post marked `done` that then loses a vault copy or a record is invisible to the queue and nobody revisits it. The approval pass is vault copy and byte check, then the post embed and its alt text, then the new record, then the `superseded_by` chain on the slot's earlier records, then the queue release, then one closing comment naming every path (the procedure for each of those steps is in `references/library-records.md`).

The alt text in that pass is checked mechanically: at least four words and not a placeholder (`header`, `image`, `img`, `illustration`, empty), which `verify-slot.py` enforces at the very end of a long close. Write the sentence out of the shipped picture's own props (`a lit server rack in a small room at night, both fists up`) — padding a one-word caption into four words passes the assertion and still tells a screen reader nothing.

## A batch card closing while the post still needs a later round

A card can approve all of its own items and still not finish the post: the draft's other embeds may fail the bar, or a slot of this round may already be queued for the next. The post is then released from this card and re-queued, in that order:

1. `backlog.py card-done <n>` — **without** `--rendering`. Nothing is rendering when the next round is only queued waiting for the render lane, and `rendering` is a state with a monitor expectation behind it; `ready` is the state that means "brief written, waiting for a card".
2. `backlog.py ready <n> <k+1> <brief>` — queues that round and sets the post `ready`.
3. Read the state back: no batch entry for the post, `q["slot"]` untouched, and the post reads `ready` with its round in `q["ready"]`.

**The order is the rule, because `ready` only appends and sets the state.** Run it before `card-done` and the release overwrites the post to `done`, leaving a round sitting in `q["ready"]` for a post the runner counts as finished — the exact opposite of what the call was for. Released first, the post ends in the one honest shape: the closed card's entry gone, the post not counted done, and its next round queued for `next` or `batch-open-ready`.

Say both facts in the closing comment — the card is done, and the post is unfinished by design with the round queued and why it is not on a card yet. A reader who finds `ready` on a post whose card closed cannot tell that shape from a stalled release without that sentence.

## A post released `done` while one of its slots is still unapproved

The card that closes a post does not always carry every slot of it. When a slot's renders keep
failing, its next card can be owned by another issue — the campaign that is re-working that
slot — and the post's own card closes on the slots it did carry. `card-done <n>` without
`--rendering` is still the right call: this card is finished and nothing of *it* is in flight.
But `done` then means "the slots this card carried", and the post goes on embedding the old,
never-reviewed asset for the rest.

Say that limit in all three places — the closing comment, the `backlog.py note`, and the runner
comment — and name the card that owns the remaining slot in the same sentence. Why: post state
is a single flag the runner counts as finished, so the unreviewed embed sitting under it reads as
reviewed to every later reader; the `unreviewed` verdict in that slot's library record is the only
other place the difference survives, and nobody cross-reads a post against its records without
being told there is a gap.

## Note the post

```bash
python3 backlog.py note <n> "Closed <date> on <card>: <item> APPROVED, reason/no reason. Vault <path> (<bytes>, <sha256 prefix>); post line <k> embed and alt rewritten; record <path>; superseded_by <job id> on <earlier record>; <siblings> untouched. card-done took the <branch> branch, <slot state>. Still open: <anything a card could not fix>."
```

The note is what the runner reads when it rebuilds the queue document, so it carries the job id and the branch — the two facts nothing else in the queue records.

## Recording a card whose slot was already released

`backlog.py opened <n> <ID>` writes only to a **held** slot, so it refuses with `the slot is not held by post <n>: None` when a `card-done <n> --rendering` already freed it during a long render round and the card is created afterwards. Do not hand-edit `queue.json` and do not call `next`, which hands out the first `todo` post instead of this one. The supported repair goes through the batch lane, which ends in the same `card-done <n>` branch:

```bash
python3 backlog.py ready <n> 1 <brief.md>      # post -> ready, round queued
python3 backlog.py batch-open-ready 1          # post -> card, batch entry created
python3 backlog.py batch-opened <n> <GUL-id>   # the card's id lands on the entry
```

Check all three answer `ok`, then read `queue.json` back: the post `state` is `card`, `batch` holds the entry with its identifier, and the counts read `done <k> / card 1 / todo <m>`. Say the repair in the closing comment, because the counts a reader expects (the release branch's `card 0 / todo <m+1>`) are not what the file shows.

## Verify the release

Read the state back rather than trusting the command's own output: the post's `state`, the absence of its batch entry, the unchanged `slot`, and `backlog.py status` counts. A release that answered `ok` and left the post `card` is the failure this read catches.
