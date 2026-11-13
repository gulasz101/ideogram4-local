# Monitor hops for render rounds

Every render round ends with a hop armed on the issue that owns the collect. This
file is the procedure for arming, auditing and repairing those hops. Read it on
any watchdog wake, any "the chain looks broken" report, and before every PATCH
that sets `executionPolicy.monitor`.

## Capture every job id before you move on

`imagegen submit --json` prints the job id, but on a busy terminal the output
scrolls past and the id is lost. Pipe it through python on the spot:

```bash
imagegen submit --prompt-json <file> --engine ideogram4 --name <slug> -W 1216 -H 832 --json \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['job_id'])"
```

**Do not re-submit to recover a lost id.** A second submit creates a second job
in the same lane, and the duplicate renders the same slot twice. If the output
was truncated, scroll back or re-run the submit with `--json` piped as above;
the first job is already in the queue and its id is on the worker's job table
(`ssh m1max 'cd ~/git/ideogram4-local && python3 ideogram4_local.py list'`),
reachable by its output filename stem.

**A crashed id pipe does not mean the submit failed.** There is no `--prompt-txt`: the flags are `--prompt-json` (ideogram4) and `--prompt-file` (flux2-klein, nanobanana). A flux submit given the wrong flag exits before it queues anything, while a *correct* submit whose id pipe then crashes on `json.load` has already queued the job. Tell them apart from the output: a `remote_output` / `submitted_at` block means the job exists. Re-running the same submit after that prints a second id and queues the slot twice — check `status` on the first id, or read the worker's job table, before submitting again.

## A job id that starts with `-` breaks `status` and `fetch`

Job ids are `token_urlsafe(8)`, so roughly one in sixty begins with a hyphen,
and `imagegen status <hyphen-id>` answers `error: the following arguments are
required: job_id` because argparse reads the id as an option. `--` does not fix
it: the remote `ideogram4_local.py` parses its own argv the same way, so the
`--` is consumed before the id is seen. Do not retry the flag and do not
re-submit — the job is queued and its id is on the worker.

- **Read the row from the worker's `jobs.db`**, passing the id as a Python string
  inside the remote command (the query under *Worker clocks* works unchanged), so
  the hyphen is data and not an option. `python3 ideogram4_local.py list` prints
  the same rows without sqlite3.
- **The arm time is unchanged arithmetic:** every active row created earlier,
  summed, plus your own — the same count `eta_minutes` would have given you,
  which `status` cannot produce for this id.
- **Collect it with scp on the `remote_output` the submit printed**
  (`m1max:git/ideogram4-local/<remote_output>`); that is the exact path `fetch`
  would copy, and it keeps the staging name the submit line reported.

## A `failed` job is a silent re-render, not a lost round

On every collect wake read `imagegen status` for **every** job in the round, not only the ones you expect to be finished. A job can come back `status: failed` while its siblings render, and `fetch` on it exits non-zero — so a loop that fetches only what looks done drops the slot instead of re-rendering it, and the card silently shrinks.

- Re-submit the same prompt file for the failed slot, keep the brief's item id on the card, and say in the issue comment which job failed and that the slot is re-rendering. A failed render has no PNG, so it never goes on a card; it is still worth one line in the slot's record chain ("failed on the worker, never shown").
- The re-submit joins the **back** of the shared FIFO, so on a busy day its ETA is hours, not the nominal 21 minutes. Arm 2 h hops (see below) and do not hold the whole card for it: the two or three slots that already passed the show bar stay ready, and the card goes up once every slot has one clean render.
- Keep the brief's item id on the re-submit and let the render name carry the attempt suffix. A failed job consumed no card round, so the round count is unchanged.

## Arm from a fresh ETA, never from the one at submit

1. When the round is submitted, run `imagegen status <job-id>` for every job and
   read `eta_minutes` from each. The arm time is **your own `date -u` plus the
   largest `eta_minutes` plus 5 minutes**.
2. **Re-read `imagegen status` immediately before the PATCH.** `eta_minutes`
   grows while sibling runners submit into the one shared queue, so an ETA taken
   at submit time can be 90 minutes short by the time you arm. A monitor armed
   before its own job can finish is not a live hop: it wakes, finds the job
   pending, and re-arms, which burns a whole run for nothing.
3. PATCH body:

   ```json
   {"executionPolicy":{"monitor":{
     "kind":"external_service","serviceName":"imagegen","externalRef":"<job-id>",
     "nextCheckAt":"<ISO 8601 Z, future>","scheduledBy":"assignee",
     "notes":"<the next wake's instructions>"}}}
   ```

   Only the inner object is real: `nextCheckAt` is the field that arms the timer,
   and `timeoutAt`/`maxAttempts` arm nothing. `kind` may be omitted — a body of
   `{"executionPolicy":{"mode":"normal","monitor":{"nextCheckAt":…,"scheduledBy":"assignee","notes":…}}}`
   answers 200 and reads back a non-null `monitorNextCheckAt`, which is the shape
   most of the recent arms use; a *wrong* `kind` value is what answers 400.
   Omitting `timeoutAt` is safer than setting it equal to `nextCheckAt`: a monitor
   stored with `timeoutAt` at its own check time is expired the moment it would fire.
3b. **Compute the ISO stamps with an hour 00–23; `T24:00:00Z` is invalid.** A monitor armed for "midnight" written as `2026-11-10T24:00:00Z` answers `400 Validation error` with `path: ["executionPolicy","monitor","timeoutAt"]` and `Invalid ISO datetime`, and the timer keeps its old value or stays unarmed while the call reads like a routine re-arm. Express the same instant as the next day's `T00:00:00Z` or as `T23:59:59Z`. Read the 400 body rather than the exit code: the field path is the only thing that says which stamp was rejected.

4. **Read the PATCH response, do not assume it.** The body echoes the issue:
   `monitorNextCheckAt` non-null, `status` `in_progress` (or `in_review`),
   `assigneeAgentId` set, `assigneeUserId` null. A monitor stored on a
   user-assigned, `backlog`, `blocked` or closed issue never fires, so those four
   fields are the whole check.

## Re-arm a monitor inherited from an earlier run

A monitor's `nextCheckAt` written by a previous run is a snapshot of that run's
ETA, not a schedule for the job now in flight. Before you trust it, read the
issue and the running job:

1. `GET /api/issues/<id>` for `monitorNextCheckAt`.
2. `imagegen status <running job id>` for `eta_minutes` and `status`.
3. If the stored time is null, later than `now + eta_minutes + 5`, or belongs
   to a job that has already finished, PATCH a fresh `nextCheckAt` computed from
   your own UTC clock plus the ETA plus 5 minutes, with a note naming the job
   and its ETA.
4. Verify the PATCH echoes a non-null `monitorNextCheckAt` and the four
   eligibility fields.

A stale monitor is worse than no monitor: it wakes after the render has waited
on the Max, or never wakes at all, and the card looks idle while paid-for work
sits uncollected.

## Re-arming after the monitor has already fired

Every fired monitor increments `monitorAttemptCount` on the issue. That counter
is cumulative across runs and **is not reset by clearing the hop** (`executionPolicy: null`
does not zero it). Two consequences:

- A re-arm body that carries bounds (`timeoutAt`, `maxAttempts`, or a `kind`/`serviceName`/
  `externalRef` block) answers `422` once `monitorAttemptCount` reaches 100, and the arm
  fails silently-ish. **Use the minimal body for every re-arm**: `nextCheckAt`,
  `scheduledBy`, `notes` only. Those three fields arm the timer at any attempt count.
- `nextCheckAt` accepts a string only (null is rejected with `400`), so "unset the timer"
  is `executionPolicy: null`, never a null stamp. See "Clearing a hop when a card takes
  over the wake path".

On a long queue a single render can take 8+ hops; the minimal body is what keeps the
chain alive across all of them. Record each hop's jobs and ETAs in the note and in the
queue note (`backlog.py note`) so a wake does not have to re-derive them.

## A future-dated monitor is not a lost wake

When a report says "the monitor never woke me", **read `monitorNextCheckAt` on the
owning issue before you diagnose anything**. A render round armed at the true ETA
(10 hours out on a backed-up queue) reads exactly like a broken chain from the
outside, and a run that treats it as broken queues the same images a second time.
Then check the job, not the narration:

- `ssh m1max 'cd ~/git/ideogram4-local && sqlite3 jobs.db "select status, count(*) from jobs where status in (\"pending\",\"running\") group by status;"'`
  for the live queue depth, and the last ten `finished_at` rows for the real
  minutes per job (22 to 25 on ideogram4, not the 21 in the wrapper default).
- Count the jobs of the same engine created before yours: that count times the
  measured minutes, plus the job running now, is the ETA. `queue_ahead` from
  `imagegen status` counts every engine, so FLUX and nano banana entries ahead of
yours cost 3 minutes each, not 22.
- **Never re-queue a job that is pending.** It is alive; a second submit only
  lands at the back of the same queue, which on a congested day is ten hours
  behind where it already stood.

## Hopping when the ETA is longer than two hours

A `nextCheckAt` more than about two hours out is at risk of being silently
dropped (the ~7 hour case is documented as dropped; even ~2.4 hours is
borderline), and the scheduler's eligibility window only re-checks on its own
cadence. When the largest `eta_minutes` plus 5 minutes exceeds roughly two
hours, do not arm the whole wait in one PATCH:

1. Arm the hop at **two hours from now** instead, with a note that says which
   jobs are still running and that the next wake re-reads `imagegen status` and
   re-arms.
2. End the run. The hop wakes you inside the eligibility window; re-read the
   status, recompute the ETA from your own `date -u` plus the (now smaller)
   `eta_minutes` plus 5, and either collect or arm the next hop the same way.
3. Never chain more than one hop's worth of waiting into a single `nextCheckAt`.
   A single over-long timestamp that the scheduler ignores is worse than two
   short hops that both fire.

This is the same arithmetic as "Arm from a fresh ETA" above, applied more than
once: each hop is its own fresh ETA, and the note on each one names the jobs
still in flight so a wake that finds them finished does not re-arm a dead timer.

## The note inside the monitor is an instruction, not a memo

`executionPolicy.monitor.notes` is what the next wake reads first. Rewrite it on
**every** re-arm and delete the old instruction instead of appending to it. A
note that still says "queue round 2" after another run already opened that card
makes the wake redo settled work: re-open a card, re-submit renders, or fetch
images whose slot is already decided. State the jobs to collect, their ETAs at
arm time, and the exact next step.

**The note is capped at 500 characters, and over-length answers a bare 400.** A
note that spelled out the render check, the vault path, the record step and the
queue calls answered `400 {"error":"Validation error"}` with
`path: ["executionPolicy","monitor","notes"]` and nothing else, which reads like
a permissions or payload problem rather than a length limit. Compress to the job
id, the checks to run, the branch on the result, and the one queue call — the full
closeout recipe belongs in the queue note (`backlog.py note`) and in the skill,
not in the monitor.

## The post's queue state is not the card's state

`backlog.py card-done <n>` has three branches and only one of them matches the
word: on a post already in `rendering` with no batch entry and no slot it sets the
state to `done`, which is the *finished post* repair, not "open the card". Run it on
the run that opens a card and the runner counts the post as done while its card is
still waiting for verdicts, so the round disappears from the queue with no decision
on it.

- `card-done <n> --rendering` is for renders in flight: it sets `rendering` and
  frees the slot.
- When the card goes up, the post's correct state is `card` with a batch entry
  naming the issue. Re-register it with `backlog.py ready <n> <round> <brief>` and
  then `backlog.py reopen-card <n> <GUL-id> <round>` — `reopen-card` rebuilds from a
  `ready` entry and exits with "no batch entry and no ready round to rebuild from"
  when there is none, so the two calls go together.
- Read the state back (`queue.json`, or a `note` that names it) after every queue
  call rather than trusting the `ok: true`.

## Clearing a hop when a card takes over the wake path

A pending verdict card is its own wake path, so a monitor left armed behind it buys
a second run on the same issue that can only verify the card and end — a whole run
for nothing. Clear the hop in the same PATCH that settles the issue.

- `{"executionPolicy":{"monitor":{"nextCheckAt": null}}}` is **rejected** with
  `400 Validation error … path ["executionPolicy","monitor","nextCheckAt"] expected
  string, received null`. `nextCheckAt` accepts a string only, so "unset the timer"
  is not expressible inside the monitor object.
- `{"executionPolicy": null}` answers `200`, drops the whole policy and reads back
  `monitorNextCheckAt: null` with `executionPolicy: null`. That, and only that, is a
  cleared hop; read it back rather than trusting the 200.
- Do not clear a hop whose job is still in flight: that monitor is what collects
  the render.

## Audit before you believe a chain is broken

A campaign issue quiet for a couple of hours is usually waiting, not stalled.
Before reporting a missing wake, `GET /api/issues/<id>` and read
`monitorNextCheckAt` (and `executionPolicy.monitor.nextCheckAt`). The two common
faults are both timing, not absence:

- armed earlier than its own job could finish, so it wakes on a pending job and
  re-arms: a wasted run that looks like a broken chain;
- a live timer whose note points at work already done: same wasted run.

To prove the scheduler is alive, pick the issue whose monitor is due within a
minute or two, wait, and read it again: a fired monitor leaves a fresh
`updatedAt`, a new collect comment, and a **new** `monitorNextCheckAt` it armed
itself. That observation is the evidence to put in the comment; do not claim a
chain works from the timestamp alone.

`GET /api/companies/<companyId>/issues?q=<GUL-id>` returns a **plain JSON
array**, not `{items: [...]}`; code that assumes the envelope crashes on the
first call of the run.

## Worker clocks

`imagegen status` timestamps (`started_at`, `finished_at`) come from the worker
host and can read well ahead of your UTC clock, so a `finished_at` "in the
future" is normal and is not a sign of a wrong job. Never compute an arm time
from them: use `eta_minutes` plus your own `date -u`. To show the queue is
moving, cite `queue_ahead` falling, or one job finishing and the next starting in
the same second.

**A running job can hold the same `eta_minutes` for half an hour and still be
working; the repeated number is not a stall and not a wrong ETA.** It is remaining
time re-estimated from a lane whose depth has not changed, so a `running` ideogram
that reads `eta 21` on three checks forty minutes apart is normal — it finishes
when it finishes. The one read that settles "is it moving" is the worker's own
row: `ssh m1max 'cd ~/git/ideogram4-local && sqlite3 jobs.db "select
id,engine,status,created_at,started_at,finished_at from jobs where id=\"<job>\";"'`
— a non-null `started_at` with `status=running` means it is rendering, and
`status,count(*) … group by status` says whether the lane is otherwise empty.
Remember those stamps are the Mac's local time (CET = UTC+1) and derive every
absolute time from your own `date -u`, never from the stamp.

## A queued job's wait is the whole lane's wait, whatever engine it runs on

`queue_ahead` counts every job in the lane, not every job of the same engine. A
twenty-second engine probe submitted behind two ideogram renders waits about two
hours of ideogram time before it starts, so "submit a small probe and know in a
minute" is false on a busy box: the probe is a cheap **job**, never a cheap
**wait**, and its arm time comes from the lane arithmetic, not from its own
duration.

- **Read what is ahead from the worker's job table, not from the probe's own
  numbers.** `ssh m1max 'cd ~/git/ideogram4-local && python3 ideogram4_local.py
  list'` prints every recent job with `status`, `engine`, `created_at`,
  `started_at` and `finished_at`, newest first. Queue order is that list read in
  reverse, with the single `running` row at the head, so the job you are waiting
  on starts after the running row's own duration plus each `pending` row ahead
  of it. (The `jobs.db` query in `hold-back-or-ship.md` answers the same
  question; `list` needs no sqlite3 on the worker.)
- **The same `queue_ahead` for twenty minutes is a render, not a stall.** One
  ideogram takes about an hour, so a job behind it holds the identical number
  while that render works. Compute the arrival once from the running row's
  `started_at` plus its engine's duration and stop re-polling; a poll loop on a
  queued job only spends the run.
- **Arm the hop on that arrival and end the run.** Sleeping through a wait the
  lane owns is how a run burns its wall clock for a job it could have collected
  in one wake, and the probe's result is still valid when the hop fires.

## Collecting across issues: do not do a sibling's collect

When one issue has a finished render and also has its own monitor due within
minutes, leave it. That run will fetch and self-check it, and two runs doing the
same collect write the same staging file and pay the check twice. Only collect
another issue's render when its monitor is far out, dead, or the issue is
reassigned to you.

## Writing to an issue you do not have checked out

A comment or monitor PATCH on a sibling issue attaches that issue to your run
(`checkoutRunId` and `executionRunId` become your run id). It clears when the run
ends, so the next wake checks out normally. Do **not** tidy it with
`POST /api/issues/<id>/release`: for an `in_progress` issue release returns it to
`todo` and clears the agent assignee, which makes its own monitor ineligible and
drops the card off the assignee's queue. Leave the lock alone.

## Reconciling several hops in one run

The order that keeps a multi-issue run honest:

1. `GET` each issue; note `monitorNextCheckAt`, `status`, `checkoutRunId`.
2. `imagegen status` every job still outstanding, and write down each ETA.
3. PATCH each issue's monitor with a note that names its own jobs and ETAs.
4. `GET` all of them back and quote the read-back in the comment, plus the one
   issue that fired a monitor on its own.
5. Record the hop in `~/image-studio/backlog/queue.json` with `backlog.py note`
   so the next wake does not have to re-derive it.

## Partial collect on a monitor wake

A monitor wake often finds only some of the round's renders finished. Fetch and
self-check the finished ones in this run; do not wait for the rest before acting
on the ones you have.

- Fetch every job whose status is `done`; leave `pending`/`running` jobs in the
  queue.
- Self-check each fetched PNG (mechanical scripts plus `vision_analyze` or
  `vread.py`). A render that fails self-check is silently re-rendered once now,
  with an attempt suffix on the render name only (`-r2b`, prompt
  `<item>-r2b.json`), per skill step 6. Do not hold the whole round for the slow
  jobs.
- A render that passes is staged and noted; it does not get a record or a vault
  copy until the round's card approves it.
- Re-arm the monitor at the new last ETA (the slowest remaining job, or the new
  silent re-render's ETA) plus 5 minutes, and put the job ids and their states in
  the note so the next wake knows which are collected and which are still running.
- Only write the handoff brief when every render of the round has been fetched
  and self-checked. A brief written early points at a render that is not the one
  that ships.

## Do not bundle `status` and `executionPolicy.monitor` in one PATCH

A single PATCH body that carries both a `status` change and an `executionPolicy.monitor`
object can answer `400 {"error":"Invalid JSON body"}` even when the body parses as
valid JSON locally; the same two changes sent as two separate PATCHes (monitor
first, then status, or the other way round) both answer 200 and read back correctly.
When a combined PATCH fails with `Invalid JSON body` — distinct from the
`Validation error` family, which names a field — read it as "do not bundle" rather
than "fix the JSON", and split it. Do not retry the same combined body: the
failure is on the bundle, not on a typo, and re-sending it only spends the run.
