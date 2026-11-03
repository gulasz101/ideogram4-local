# Monitor hops for render rounds

Every render round ends with a hop armed on the issue that owns the collect. This
file is the procedure for arming, auditing and repairing those hops. Read it on
any watchdog wake, any "the chain looks broken" report, and before every PATCH
that sets `executionPolicy.monitor`.

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

   Only the inner object is real: `kind` must be `external_service` (any other
   value answers 400), `nextCheckAt` is the field that arms the timer, and
   `timeoutAt`/`maxAttempts` arm nothing. Omitting `timeoutAt` is safer than
   setting it equal to `nextCheckAt`: a monitor stored with `timeoutAt` at its
   own check time is expired the moment it would fire.
4. **Read the PATCH response, do not assume it.** The body echoes the issue:
   `monitorNextCheckAt` non-null, `status` `in_progress` (or `in_review`),
   `assigneeAgentId` set, `assigneeUserId` null. A monitor stored on a
   user-assigned, `backlog`, `blocked` or closed issue never fires, so those four
   fields are the whole check.

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
