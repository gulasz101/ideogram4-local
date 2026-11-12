# nano banana — the Gemini web image engine (GUL-893)

Third engine on the Image Studio queue. Deployed 2026-11-04 on `main` (`14a6625`), engine id
`nanobanana`.

```
imagegen submit --engine nanobanana --prompt "<natural language>" --name <slug> [--json]
imagegen status <job-id>
imagegen fetch <job-id>          # → ~/image-studio/staging/<YYYY-MM-DD>/<slug>-<token>.png
```

## Read this page again at the start of every hop

Sibling runs of the same campaign extend this file and `scripts/` while you are between hops, so a batch run that works from its memory of the skill re-invents things that already exist: list `scripts/` and re-read this page before writing a driver, a close-out or a probe wrapper by hand. The batch driver, the failure taxonomy and `scripts/ship-approved-batch.py` were all added mid-campaign while one run was still writing its own version of each.

## What it is

Gemini's own web image tool, reached through the `gemini-web2api-go` proxy on the Max
(`127.0.0.1:8083`, model `gemini-image`). The proxy drives a logged-in Gemini web session with a
Firefox cookie, so there is no Google API key and no per-image cost. The worker posts one chat
completion, the reply carries the picture inline as `data:image/jpeg;base64,…`, and the worker
decodes it to the job's output path.

## Measured

| | nanobanana | flux2-klein | ideogram4 |
|---|---|---|---|
| time | **20–55 s** (12 s when the model turn is warm) | ~173 s | ~21 min |
| size | 1376×768, seen 1584×672 | 1216×832 (`-W/-H`) | 1216×832 (`-W/-H`) |
| format | JPEG | PNG | PNG |
| prompt | natural language | natural language | canonical JSON |
| seed | none | integer | none |

Live job GUL-893 `bLnRpFS8X2g`: 1376×768 JPEG, 110,745 bytes, done in ~40 s wall clock including a
cold model turn; the engine call itself took 12 s when run directly.

## Rules

1. **One image a minute, 5-8 posts a wake.** Per-exit-IP rate limiting: a burst throttles the account
   for ~2 hours and takes the whole proxy down, not just this engine.
2. **The size is upstream's.** Do not promise a canvas size. Tell the post's layout what arrived.
3. **Prose instead of a picture = stale cookie or quota.** The `error` field carries the model's own
   words. Skip the post, report it, no retry loops.
4. **`unknown engine 'nanobanana'`** means the Max checkout is behind `main` — stop and say so, do not
   quietly fall back to Ideogram.
5. **The queue is shared and serialised.** A worker restart kills the running job ("killed by signal
   15"). If you need a restart, do it only on a queue with zero pending and zero running.
6. **A repair of a draft image on the backlog lane is one render on this engine, not an ideogram + flux
   pair.** The pair belongs to the campaign-era instruction, when the comparison was the point; the
   backlog engine call now spends one render a slot, and the pair is for a slot that genuinely needs an
   exact canvas or legible in-image text, where the JSON prompt and the fixed 1216×832 are what buys it.
   When a brief still writes `ideogram4` + `flux2-klein` for a broken slot, the engine call outranks it,
   and the card names the engine that shipped.

## A job id that starts with a dash

Job ids are random and sometimes begin with `-` (seen: `-oEoW0NxTFI`). `imagegen status -oEoW0NxTFI` is then parsed as an option and answers argparse's usage error instead of the job, and `imagegen status -- -oEoW0NxTFI` still swallows it on this build. Do not fight the CLI: read the row from the renderer's own database over SSH — `ssh m1max "sqlite3 -json …/jobs.db \"select id,status,substr(coalesce(error,''),1,90) e,output_path from jobs where output_path like '%<slug>%' order by created_at desc limit 2\""` — and quote the id as the database returns it. A leading-dash id also breaks `grep` in any shell recipe that passes it unquoted.

## Proving an outage in one query

Before blaming a prompt, read the shared queue on the Max. The live database is
`/Users/wojciechgula/git/ideogram4-local/jobs.db`; `~/ideogram4-local/jobs.db` is an older schema with no
`engine` column, and its query fails with `no such column: engine`.

```bash
ssh m1max "sqlite3 -separator ' | ' /Users/wojciechgula/git/ideogram4-local/jobs.db \
 \"select id,engine,status,substr(created_at,12,8),substr(coalesce(finished_at,''),12,8),substr(coalesce(error,''),1,40) from jobs where created_at > '2026-11-04T18:00' order by created_at desc limit 14;\""
```

**Both the database and `imagegen status` print host-local time (CET, UTC+1); neither reports UTC.** A job submitted at 20:52Z reads `21:52:15` in `started_at`, so subtract an hour before comparing either source with your own `date -u` — and convert again before a band goes to the proxy's owner, whose own log is UTC: a table copied straight off these rows and labelled `Z` is an hour off the evidence they will check it against. When a correction is needed, name the clock the number came from, not just the corrected value.

**Convert at the moment you write, not at the moment you read.** `imagegen submit --json` prints `submitted_at` on that same local clock, and that number is what ends up in a comment, a post note and a `monitorNextCheckAt`. Read `date -u` in the same breath as the row, do the subtraction before the sentence is written, and read `date -u` again just before the monitor PATCH — a published time an hour off reads perfectly plausible to everyone except the person who checks it against the table, so the error survives review and gets copied into the next hop.

**`jobs.db` has no `name` column.** The `--name` label a submit was given cannot be queried, and the attempt answers `no such column: name`:

```bash
# fails: no such column: name
# select id,status from jobs where name like 'probe-r1%'

ssh m1max "sqlite3 /Users/wojciechgula/git/ideogram4-local/jobs.db \
  \"select id,status,created_at,finished_at,substr(coalesce(error,''),1,120) \
    from jobs where created_at>='<local HH:MM of the submit>' order by created_at;\""
```

Filter on `created_at` using the local-clock `submitted_at` the submit just printed. That is also how a job id is recovered when the submit output was truncated or the wrapper lost it.

If a job from another run failed before yours on the same error, the engine is broken and the prompt is
fine. That is stronger evidence than a 15-word probe, and it costs no render. Say it in the comment: it
is the difference between "my prompt is bad" and "your proxy is down".

## Reading a failure

- **`HTTP 429 {"code":"ip_slot_full","message":"direct IP slot full: concurrent limit reached"}` is the per-exit-IP concurrency limit, and the fix is spacing, not prompting.** It is a third failure mode next to the 502 retrieval bug and the dead-port error: the engine works, but only one request from this IP runs at a time, and another run's batch can hold the slot for minutes. On 2026-11-04 three submits a minute apart all 429'd while a sibling run's jobs finished in the same window; retrying the same prompt one post at a time after ~150 s took five posts through in six minutes. So: submit one, wait for its own result, retry that same prompt after two to three minutes when the slot is full, and never fire the whole batch while the slot is contended. If a post still fails after three attempts (429, 429, then a 502 when the slot opens), skip it and say so — that is the issue's no-loop rule.
- **The vision reader shares that exit IP, so `vision_analyze` 429s in the same minutes as the renders.** Fall back to `scripts/vread.py` (llm.voitech.dev, `qwen3.8-flash`) for the self-check; it is a different route and it answers while the proxy is saturated. Say in the check note which reader produced it.

- **Before you touch your own prompt, submit a fifteen-word probe on the same engine.** `imagegen submit --engine nanobanana --prompt "a plain grey server rack on a concrete floor, flat illustration, no text" --name probe`, then read the probe's `error`. If the probe fails the same way, the fault is the engine or its backend and no rewording clears it — your long prompt was never on trial, so do not spend an hour rewriting it. If the probe succeeds, the fault is in your prompt, and the diff between the two prompts is the search space. One probe costs seconds and settles a question that otherwise gets argued from the error text alone; when the probe is what proved it, say so in the report to the engine's owner, because "a fifteen-word prompt fails too" is the clause that ends the discussion.
- **`connection refused` / `Remote end closed connection without response` = the backend was down, not your prompt.** The Gemini proxy runs as its own container on the Max and an ops run can recreate it under you; on 2026-11-04 two submits failed this way inside one minute because GUL-896 was rebuilding the container, and both landed on a single re-submit after about 90 seconds. Retry once, and if it fails a second time wait longer and report rather than looping.
- **Prose instead of a picture = stale cookie or quota.** That is the case the issue's "skip the post, do not retry" rule is for: the `error` field carries the model's own words.
- **`HTTP 502 … cookie 池里 1 个账号都不可用（最后一个：fetch /app: HTTP 302 -> www.google.com/sorry/index）` = the account's cookie is dead, and no retry reaches it.** The proxy's cookie pool has one account and Google now answers `/app` with a redirect to `www.google.com/sorry`, its bot check, so the session is refused before anything is generated. Six posts failed with this one after another inside ten minutes on 2026-11-05, six for six, while the same prompts had rendered fine five hours earlier. Read it as a human task, not an engine hiccup: report the exact text and the job ids to the proxy's owner, say a fresh login in the panel is the fix, skip the posts, and arm a monitor. Do not spend a probe on it — the error already names the cause, and a probe is just another refused login. **Read the whole message, not the first line:** the full text carries the remedy the proxy offers, `到面板「Cookie 池」用「检测」按钮逐个排查，或打开 fallback_anon 降级匿名` — a **Cookie Pool** tab in the proxy panel with a **Test** button per account, or switching on `fallback_anon` to degrade to anonymous use. Hand both to the owner as an either/or, and say plainly that `fallback_anon` is a quality decision for the blog's owner, not a switch an agent flips to unblock itself.
- **`HTTP 502 … media generation succeeded but artifact retrieval failed: 响应里没有图片 CDN 链接` = the proxy could not pull the finished image out of Gemini's response.** The picture was generated (so the cookie and the quota are fine and the prompt is irrelevant) and the proxy found no image link to download, which is a response-parsing fault on the proxy side, not something a reword can fix. Three submits inside three minutes failed identically with this text. Retry **once** to rule out a single bad turn, then stop the batch, comment the exact error and the job ids on the proxy's own issue (the `gemini-web2api` one), and arm a monitor — every engine path on this box is behind that same proxy, so a loop of retries only burns the rate limit. Do not fall back to Ideogram silently: the backlog engine is Wojtek's call (GUL-893).
- **A fix on the engine's own side is not evidence the fault cleared — probe before you resume renders.** A container recreate, a version pin or a release note that names the symptom all read as progress; none of them proves the path works, and one fifteen-word probe either returns pixels or it does not. Resume real renders only on a probe that comes back with an image. Until then the shape of an outage hop is: one probe, then the work that does not need the engine.
- **When the error names a delivery path the engine does not use, hand the owner that mismatch instead of another retry.** This engine's documented path is the picture arriving inline in the reply as `data:image/jpeg;base64,…`; an error complaining that the response carried *no image CDN link* therefore says the reader and the reply shape disagree, not that generation failed. One sentence of that in the report gives the owner a lead that a stack of retries never would.
- **An engine outage is work on the prompts, not a stopped run.** Audit the next post at prompt level and stage its prompt files so the moment a probe returns pixels the batch is submissions only — audit, writing and staging are the expensive part and none of them needs the renderer. Say in the comment which prompts are staged and where, so the next hop does not re-audit them.
- **`imagegen status` reports the requested canvas, not the file.** Every status line on a nano banana job reads `width: 1216, height: 832` while the file is 1376×768. Read the real size off the PNG (`PIL.Image.open(...).size`) for the record, the card and the post's layout, never off `status`.

## Checks that false-alarm on this engine

- **`check-grey-bars.py` prints `FULL GREY-BOX (safety filter): file 0.19 MB < 0.4 MB threshold` on a perfectly good nano banana render.** The script's grey-box test is a file-size heuristic tuned to Ideogram, and this engine writes a 1376×768 JPEG at 0.19–0.23 MB. Read the size line as "smaller than an Ideogram PNG", not as a defect, and settle the frame with `check-blank-margin.py` and a vision read instead. Every nano banana file trips it, so a note that quotes the grey-box verdict as a failure is quoting the heuristic. Name the warning in one line on the review card as well, so the reviewer does not read it as a defect.
- **The engine often closes a frame with a thin dark vignette (7–32 px, rounded corners).** `check-blank-margin.py` reports it as `BLANK MARGIN: 2 band rows / 2 band cols` with strips of 7–16 px. That is a film-still vignette, not a pasted banner: name it on the card as a quirk and judge the frame on its content. **The same border trips `check-palette-strip.py`, and through it the coverage audit:** the script prints `flat band on the top edge` with `a single hue` over the `#010101` frame, and `card-embed-coverage.py` counts that as a failing embed — so an approved header can read as an uncovered gap on a post whose card is complete. Read the hue count, not the band: the frame edge reports **0–1 distinct hue groups in one flat run**, while the palette-strip defect is several hues side by side (5–7 groups in one row). Subtract the frame-edge cases by hand before reporting a coverage gap or a flagged count.
- **Settle a suspected letterbox with per-row mean luminance before re-rendering.** This engine's frame edge is thin and dark; a letterbox is thick and usually repeated at the opposite edge. Measure `lum.mean(axis=1)` and find the first and last row over about 12/255: one measured render had rows 0–11 at 0.1–2.3 (a 12 px vignette on the top edge only) while its bottom edge never dropped below 1.0 because the floor was in shadow — one vignette, not a pair of bars. Quote the row numbers in the check note so the next round does not re-measure the same frame.

## Prompting

Write it like a brief, not like an Ideogram caption: subject, composition, palette, lighting, style
("flat-vector editorial illustration, dark navy background, amber accents, no text"). The web model
follows adjectives and mood well, and it does not need schema hygiene. Ask for no text/lettering and
overlay any title in the layout instead.

**When the post already has an approved image, open the new prompt with that record's own register
sentence and cast description, word for word.** A prose prompt carries its series in the first two
sentences — the medium and palette clause, then "a stocky bearded man in a grey work shirt and
glasses" — so copying those from the approved record is what makes the new slots sit with it, exactly
as reusing a JSON `style_description` does on Ideogram. Writing a fresh opening for every slot of one
post is how a batch ships in four registers.

**Length: measure the approved record of the same post, then `wc -w` your own draft — approved prompts on this engine have landed anywhere from 178 to 310 words, and the three most recent full-scene headers measured 248, 268 and 270, so aim at 250–300 and treat anything past about 330 as drift the encoder pays for by trimming the negative clause.** A draft that lands at 320–335 is inside the engine's tolerance but at the edge of the register: trim it under 320 rather than carrying it as a named exception, because an exception has to be re-explained in the post note, on the card and in the comment, and that bookkeeping costs more than folding two clauses.
The model follows one paragraph of scene plus the negative clause; the 400-word flux-style briefs that
exist to hold every JSON-era clause are the wrong shape here, and the extra lines buy nothing.
Measure it before submitting — `wc -w <prompt.txt>` — because a prompt written from an approved
record's register copies the length as well as the voice, and the drift is upward.

The floor is about 175 words: the register block at the front carries the look, so the length only has to hold the scene. Below that the scene clause starts dropping props, which is the failure this engine punishes — it draws what it reads and nothing else. **A first draft that overshoots is trimmed by folding clauses, never by deleting an element:** collapse an adjective chain into one noun, merge two short sentences that describe one surface, and re-run `wc -w` after the first full draft rather than after the polishing pass, because the count drifts up as the prose improves and the last trim is always the one that cuts the clause carrying the beat.

## The model reads a description as the subject, not as material

This engine substitutes a default for a vaguely described object, and the default is usually wrong for the series. Two recurring cases:

- **A sheet or surface described by its paint becomes a swatch.** "Four sheets carrying broad soft-edged shapes of ochre, cream and indigo paint" rendered as four hanging cards of three-colour paint blobs — the palette read as the subject. Describe what the sheet **shows** (small complete painted scenes, tiny landscapes and machines), and forbid the literal reading in the same sentence ("no swatches, no flat colour blocks").
- **Hardware described by material or colour becomes a retro PC.** "A tall brushed-grey computer tower" rendered as a 1990s beige tower with floppy drive and CD-ROM bays. Name the object by what it is ("a compact silver aluminium computer box, an M1 Max workstation") and forbid the default in the same sentence ("no drive bays, no beige plastic, no floppy slot, no monitor"), with one small amber indicator as the only detail.

The rule in both cases: name the object by identity, then forbid the default the model would substitute. A material adjective alone (brushed-grey, soft-edged) is not an identity, and the engine fills the gap from its training prior.

## The model invents text-bearing surfaces unless you name them as bare

A global ban on text ("no lettering, no numerals, no signs, no labels, no screens, no text on any surface") does not stop the model from drawing a pinned note, a wall paper with squiggles, or a garbled logo on a smooth panel — it reads the ban as "no readable text" and fills the surface with pseudo-text. Name the surfaces as absent or unmarked in the same sentence:

- "The boards are completely bare: no pinned papers, no notes, no sketches, no marks, no wall hangings."
- "The computer's front panel is completely smooth and unmarked except for the amber indicator, with no logo, no brand mark, no text, no symbols."

A surface the prompt never describes is a surface the model will decorate; a surface described as bare stays bare.

## Proving a 502 is the proxy and not the cookie

Before reporting, read the proxy's own log — it separates the two failure families by itself:

```
ssh m1max 'export PATH=/usr/local/bin:/opt/homebrew/bin:$PATH; \
  docker logs gemini-web2api 2>&1 | grep -E "取回产物失败|RotateCookies" | tail -20'
```

The `export PATH` is not decoration: a non-login `ssh m1max '<cmd>'` gets a shell with no `docker`
and answers `zsh:1: command not found: docker`, which reads like the daemon is gone. It is the PATH,
not the machine — prefix it on every remote docker call.

`[media] 取回产物失败: 响应里没有图片 CDN 链接` is the artifact-retrieval step: generation
succeeded upstream, the reader found no image link, the picture is discarded. `RotateCookies …
HTTP 429` lines are the cookie keep-alive and are followed immediately by a successful rotate, so
they are noise, not the cause. One command turns "not the cookie, not the quota" from a guess into a
reading. Logs are read-only; do not exec into the container, restart it or edit its compose file —
that is the proxy owner's work, and the fault is reported on its own issue.

## Check whether the owner's fix is actually in flight before planning around it

Before you write "the proxy will answer and then the batch goes in", read the proxy issue's own
thread and its `status`. A host that has been rebuilt, pinned and watched over can still carry a
card that is **waiting on the owner's verdict or merge**, which means no code change is queued and
the outage is not ending on its own tonight. Two different situations look the same from your side:
"a fix is in flight, hold the batch" and "their work is parked on a human, so nothing will move".

When it is parked, plan for the outage to last: keep one neutral probe per hop, keep staging
prompts, and say in the comment which of the two situations the proxy is in, in one sentence — the
owner of the campaign reads that and can decide whether to unblock the merge or change engines.
Do not spend the hop re-diagnosing what the thread already settles, and do not treat a healthy
container with a clean `/health` and a full model list as evidence that the image path works.

## A decision the owner has left open is restated as two options, never three

When an unanswered question has kept a slot unrendered across several hops, do not explain it
again in full. Give the choice as a binary with one line each — "one attempt with the light through
a narrow high gap, or the post ships with no new header and the frames stay in staging" — and keep
the rest of the comment on work that moved. A question written as a paragraph reads as a report and
gets skimmed; a question written as two options is answerable in one word, and answering it is the
only thing that unblocks the slot.

## When the probe finally returns pixels

The engine can come back with **nothing changed on either side** — same container, same pinned
digest, same host, no edit by anyone — so a recovery is never evidence about who fixed what.
Confirm it off the job row rather than the wrapper: one id in sixty starts with a dash and argparse
eats it, so `imagegen status` answers `the following arguments are required: job_id` for a job that
is perfectly healthy.

```
ssh m1max 'sqlite3 /Users/wojciechgula/git/ideogram4-local/jobs.db \
  "select id,status,error from jobs where id=\"<probe-id>\";"'   # done + empty error
```

A `done` row still is not proof of pixels: fetch the file and read its real size and mode off the
PNG before any real render goes in behind it.

Then **spend that window in one pass** — every prompt staged during the outage goes in together,
oldest post first, because the staging is the expensive part and the window may be short. The
six-render cap counts **slots**, not posts, and this engine spends one render a slot: two posts of
two and three slots are five renders, inside the cap, where the same two posts on two engines
would be ten and outside it. Re-check that the lane is empty immediately before submitting — the
first idle lane in hours can fill within minutes of the engine returning, and a batch that lands
behind somebody else's after an outage is worth what a batch that never went in was worth.

The one-probe-per-hop cadence is what makes this safe: each hop costs seconds, so the hop that
that returns pixels finds the batch written and staged rather than starting an audit.

**Renders first, cards second — the window pays for pixels, not for uploads.** Everything the engine
needs goes in while the window is open; everything the card needs (the issue, the hash-matched
uploads, the payload, the `in_review` PATCH) is engine-free and can happen after it has closed. A
whole post's batch plus its repairs is nine or ten jobs at 20–55 s each, so the renders cost a few
minutes of the window, while building two cards costs ten to fifteen minutes of the run. Order a hop
as: probe → every staged render and every held slot's repair → fetch and check → only then the card.
A run that builds the card first watches a four-minute window shut with five prompts still unwritten.

**A repair belongs to the window it was discovered in.** When a frame fails its beat in the same hop
that the engine is answering, rewrite the clause and resubmit inside that window rather than arming a
monitor for the next one — the same half-minute render, against a whole hop of waiting if it misses. A
third attempt on one slot is the same arithmetic and worth taking while the window holds, provided the
overage is named on the card in words against the round's two-attempt budget rather than left for the
job list to imply.

## Run the batch from one driver, not six hand-timed calls

Submit, poll and fetch from a single script so the pace is a loop condition rather than your attention:

```python
last = 0.0
for n, slug in JOBS:
    gap = time.time() - last
    if gap < 65:
        time.sleep(65 - gap)
    job = submit(n, slug); last = time.time()          # pace is measured between submits
    deadline = time.time() + 25 * 60                   # a long horizon, not a 2-minute one
    while time.time() < deadline:
        time.sleep(8)
        st = status(job)
        if st["status"] in ("done", "failed"): break
    if st["status"] == "done":
        fetch(job)
        print(json.dumps({"n": n, "job": job, "status": "done", "path": path}))
        continue
    if st["status"] == "failed":
        print(n, st["status"], st.get("error"))        # the failure names its own job id
        continue
    # still pending at the horizon: the lane is loaded. Stop submitting, keep the queue.
    print(json.dumps({"n": n, "job": job, "status": "pending"}))
    break                                              # arm a monitor and end the run
```

- **The poll loop must not have a short iteration cap.** A `for _ in range(18)` at 8 s is about two minutes, and a job sitting behind somebody else's ideogram stays `pending` for twenty; the loop then falls through to the next submit and leaves that job queued and unfetched. It does not fail loudly — the batch looks submitted, no render is on disk, and a later run has to reconcile six ids against `jobs.db`. Poll on a wall-clock horizon long enough for the job ahead of you, and when the horizon expires **stop the batch and arm a monitor** rather than submitting the rest.

Use **65 s, not 60**: the wrapper's handshake drifts and a 60 s loop lands at 56–58 s often enough to matter. Six submits spaced 66–85 s landed first try on a healthy proxy, and every failure in the two batches came from the backend rather than the spacing.

**A six-post driver outlives one foreground command call.** Six submits at 65–85 s plus polling is seven to ten minutes of wall clock, past the foreground command budget, so the call is killed mid-loop with jobs already submitted and none fetched. Run the driver in the background with a notify-on-exit, or chunk it at three posts per call and let each chunk fetch its own three before the next starts; never let the chunk boundary abandon submitted jobs unfetched, and say in the comment which ids came back pending so the next hop fetches instead of re-submitting.

- **Print one JSON row per job** (`{n, job, status, path}`) as it goes. That summary is what the card spec and the record pass read; without it a later step globs the staging folder and picks another post's render, because two posts of one batch share a slug prefix.
- **Never submit the next post while the previous job is still `pending`.** One render in flight is the whole point of the cap, and it is also what makes the failure legible: a `failed` status with the proxy's own words, not a queue of half-started jobs.

## The gesture drops and the prop stays

When a slot's beat is an ACTION — peering through a slot, listening at a grille, reaching into a cage — this model draws the prop faithfully and quietly swaps the action for a generic pose: the figure stands beside the window instead of looking through it, or rests a mitt on the frame instead of reaching in.

- **The prop carries the beat, so ship the prop and name the gesture as a residual** rather than spending a third render on a pose. Make the aperture explicit on the second attempt (`one small square window with no glass, cut at the figure's eye height`) and expect the figure to still stand at the frame; put that sentence in the item description and let the owner judge it.
- **Two attempts a slot, then the card.** A second render is worth it when the first lost the prop as well as the action. When the prop already reads, a third buys a pose and costs a hop.
- **Prefer a still prop to a held one.** Where the beat allows, put the evidence in the object's state — the door swung open, the key hanging on its hook, the slip half swallowed by the box — so the frame never depends on a gesture landing.

## The record this engine writes

`prompt_type: "text"`, `engine: "nanobanana"`, `generation: {"model": "gemini-image", "seed": null}` — the proxy's model id, with the seed null because this engine takes none. `width` and `height` come off the file (`PIL.Image.open(p).size`), never off `imagegen status`, which reports the requested 1216x832 canvas on every job.

- **On the current path the shipped copy is byte-identical to the staged file: `shasum -a 256` both and compare.** Nine files of one shipped batch hashed equal to their staging renders, so a hash pair that agrees is the cheapest proof and a mismatch means the wrong file was copied. Some earlier vault copies had been re-saved JPEG→PNG, which can never agree on a hash; for those, prove the bytes by decoded pixels instead (`numpy` max difference 0 across the frame) and say in the note which comparison was used.
- **`ship-approved-batch.py` writes the approved row and nothing else, so three edits remain after it.** The superseded record keeps `verdict: "unreviewed"` and its `![[…]]` embed still points at the filename that now holds the new pixels: set the verdict, add one Verdicts row naming why that render was replaced, and repoint the embed at the `.superseded-<job>` copy. An earlier render that was held back at the prompt audit is `rejected` (it never reached a card), never `unreviewed`, and that row is repeated as the first row of the new record so the slot's history reads in one place — both rows carry the same round number, because a replacement inside a round is not a new round. The generated `From [[post]]` line also carries no section, which fails the provenance check: make it `From [[post]], section "<heading>":`.
- **Check the pass with `scripts/verify-slot.py`, whose `--earlier` takes a PATH, not a job id.** `--record <new record> --job <job> --earlier <path to the old record> --post <draft> --prompt <file> --asset-source <staging png>`; a job id in `--earlier` answers two failures that read like missing records and cost a second run. Expect **exactly one** FAIL on a re-saved frame: this engine stages a JPEG, so the vault PNG can never hash-match it and the decoded-pixel identity line beside it is the proof. Any second FAIL is real.
- **When a shipped frame replaces a file the post already embeds, repoint the old record in the same pass.** Rename the old file to `<stem>.superseded-<old job>.png`, write the new bytes at the original filename so the embed line never moves, then patch the old record's `asset:` to the superseded name and its `superseded_by:` to the new job id. A record left pointing at the original path now documents a file holding another job's pixels, and nothing else in the library flags it. Do the whole pass with `scripts/ship-approved-batch.py <spec.json>`: it takes one JSON row per item (post, day, asset, old job, staged file, job, timestamps, prompt path, alt, quote, why), renames and patches as above, writes the record with the measured size, asserts each embed appears exactly once and each new alt landed, and finishes with the decoded-pixel identity check — so the five hand-written steps that go wrong on a six-item batch are one spec file and one call.

## The 502 is intermittent, and the clean window is the evidence

The artifact-retrieval 502 (`media generation succeeded but artifact retrieval failed: 响应里没有图片 CDN 链接`) does not mean the engine is down for the night once it appears. It has been observed failing six times over 2.5 hours, clearing by itself with nothing changed on the host or in the prompt, and then returning 3.5 hours later — three failures inside four minutes — with the identical body. Treat the fault as **flaky, not fixed and not broken**, and let that shape the pacing:

- **One 15-word probe per hop, never a loop.** A probe is the cheapest fact available; six real submits in one night is the cap, after that each one only burns the per-exit-IP rate limit.
- **On a card waiting for one slot, space the hops to the account's refill time, not to the render ETA.** There is no batch to rush, so the one real submit a hop is the whole measurement — and a 30–40 minute cadence spends the allowance faster than a quiet account refills it (measured recoveries follow roughly two hours with no traffic, and every attempt restarts that clock). Arm the next check an hour or more out, say in the comment that the gap is deliberate, and read a sibling's failed job from the same window as the hop's measurement instead of spending your own submit. The hop that finally gets pixels is then a fetch, a check and a card in one run, with the card machinery already staged.
- **Never report a recovery as a fix.** The honest sentence is "it cleared on its own between X and Y, nothing differed on our side", and the fault's return is the thing that tells the owner whether a restart was ever the answer.
- **A probe queues behind whatever is in the lane, so wait on the front job, not on the clock.** `imagegen status` gives `queue_ahead` but an `eta_minutes` that does not move while the job ahead runs — a probe can read `queue_ahead 1, eta_minutes 23` for an hour behind one ideogram. Arm the monitor past the front job's own elapsed time plus the engine's real render time (see `references/queue-db-recipes.md`), and treat a hop that finds its own probe still `pending` as a normal hop rather than a fault.
- **When the lane is loaded, submit the real renders behind the probe instead of hopping on the probe alone.** A render on this engine takes 20 to 55 seconds, so the whole point of the probe — not spending a render on a broken path — costs almost nothing anyway when the path is broken: put the real jobs in the queue behind the probe, let the probe answer first, and the round resolves in one wake instead of two. Behind a sibling's hour-long ideogram the alternative is a hop chain that learns only what a failed 30-second job would have said. Hopping on a probe alone is right only when the lane is otherwise free or the batch is large enough that the wasted submissions matter. **Put the probe at the FRONT of the lane, before the batch, not after it.** A queued job's fate is decided when the worker starts it, not when you submit it: six real jobs put in behind a sibling's twenty-minute ideogram are still sitting unstarted when the path breaks, and every one of them then dies on the way in, so the whole cap of slots is spent on a fault one fifteen-word submit at the head of the queue would have measured. Submit the probe first, and only after it returns pixels put the real jobs in behind it.
- **Do not spend the wait.** While the path is down, the free work is the prompt audit and the rewrite of the next post's slots. Staged prompts with a note naming them are what let the next hop submit within a minute of the engine returning.
- **One probe answers the whole lane, not just your slot.** Other runners' real jobs often queue behind your probe, so their fate is the same fact you are already waiting for: read the probe rather than adding a second submission to learn it twice, and say in the comment that their jobs sit behind yours so nobody spends a third. **The reverse works the same way: when a sibling's nano banana job is already `pending` in the lane, that job measures the path for you and a probe of your own only queues behind it.** On such a hop spend no submission at all — read their job's own row (status, `started_at`, `error`) at the next hop and say in the comment that the measurement is theirs, because one queue can only tell one story at a minute.

## A probe's answer is valid for the minute it ran, not for the hour

Measured on one campaign night: three nano banana jobs returned real PNGs between **09:02:51Z and 09:06:24Z**, and eight jobs that ran between **09:54:11Z and 09:56:28Z** all failed with `502 … media generation succeeded but artifact retrieval failed: 响应里没有图片 CDN 链接`, each dying **fifteen seconds** after it started. So the clean window was at most four minutes wide and it closed between those two bands.

What that means for planning:

- a probe that returns pixels proves the path **at that minute**; do not treat it as a licence to spend a whole batch in the sure knowledge it will render — submit, and expect the submit itself to be the next measurement;
- work queued behind an ideogram hides the state: seven of those eight jobs were created 30 to 45 minutes before they ran, so their creation time says nothing and only `started_at` does. Read `started_at`, not `created_at`, when dating a failure;
- when a batch dies this way, one report with both edges of the window is worth more than a retry: the timestamp band is the only thing an owner of the proxy can check against their own log;
- never call the second failure a prompt problem. Fifteen seconds between start and the identical `artifact retrieval` body across eight jobs is the engine talking, not the picture.

## The fifteen seconds is the retrieval retry loop, not a render half-done

A failed job reports 15 to 35 seconds of wall time, and it is tempting to read that as "the picture was being made and the collection step fell over". It is not. The upstream call itself answers in about a second (measured: 1193 ms); the artifact step then polls the service's own history six times, two seconds apart, before giving up, so about twelve of those seconds are failure handling inside the same request. The loop only runs on the failure path, which is why a failure and a success look so different in duration and why the duration varies.

So the number says one thing only: the job reached the step where a picture was supposed to be collected. Never quote it as evidence about generation, and do not build a theory on jobs that "died halfway" — the variation is the retry loop, not progress.

## Four hypotheses have been spent on this fault, so report the bands and read the host's thread first

A container restart, the pinned image, a cookie rotation and a fresh session have each been tried against the artifact-retrieval 502 and none of them cleared it. Read the restart case closely: the container came back healthy in four seconds, a text request succeeded in about six seconds, and the image request answered 502 in about 1193 ms — and the failures went on, six of them inside the same band **after** the restart.

- **Read the engine's own issue thread before you describe the host's state.** Writing "the container is untouched, up the whole time" after someone else has restarted it is a public correction waiting to happen, and the correction is worth less than the sentence would have been had it been checked first.
- **Name the hypotheses already killed in the report.** "A restart, a version pin, a cookie rotation and a fresh session have all been tried by other hands and none cleared it" saves the owner from re-suggesting them and stops the campaign from planning a recovery that is not coming.
- **The bands are still the whole measurement.** Give run times for the success band and the failure band, name the probe that ran in a verified-empty lane, and let the owner match them against the proxy's log. That part survives every correction above.

## A shipped header is not re-judged on the backlog card

The campaign's card and the runner's `Backlog review` card are two cards over the same file, and the second does not re-ask what the first already settled. Decide it from the record, not from the queue note: `verdict:` is `"approved"` and the Verdicts table carries a row naming the campaign card. That file is then **not a row on the post's backlog card** — the card's debt is the post's other images, so a three-image post's card can legitimately carry two items.

- **When the post's only image is that header, the card has zero items, and a zero-item card is not a card.** Open no verdict card: post a closing comment that names the live job id, the record path and the file the draft embeds, says plainly that nothing was rendered and that no job id or vault copy belongs to it, `backlog.py note <n>` the stale brief, then `card-done <n>` and Advance. Asking him to rule on a file he approved the same day spends exactly the click this rule exists to save; end the comment with the one-line offer to put it on a card if he wants a second look at its post.
- **The brief still names the superseded job and its back-filled record.** When the card does carry other items, put the file the draft actually embeds on it (the `.png` with no `.superseded-` marker) and name the stale job id in the card's `detailsMarkdown` and in a `backlog.py note`. These back-filled records' `## Why` is often the single word "header", so judge the PNG against the record's `## Prompt` and the draft's section, never against that line.

## A 429 `ip_slot_full` is a second, different fault: the engine is healthy and the slot is taken

The path can be open and still refuse the job. A submit that dies **within a second** with `HTTP 429 {"error":{"code":"ip_slot_full"}}` is not the artifact-retrieval 502 and not a prompt:

- **It is contention, not a fault.** The proxy holds one concurrency slot per exit IP, and while another job owns it every submit answers 429 instantly. Prove it by reading the lane at the same minute: when other runs' nano banana jobs fail with the same code in those same minutes, the slot is saturated campaign-wide and nothing on this side is wrong.
- **A 429 costs nothing to retry, and nothing to wait for.** The job never starts, so no render time and no picture is spent. Pause about two minutes, resubmit once; repeat while it clears. Do not read a 429 as the engine going down and do not fall back to another engine over it.
- **Distinguish it from the 502 by duration.** A 429 dies in well under a second with no `started_at` of consequence; the 502 runs 15 to 48 seconds because the artifact step polls six times before giving up. Duration is the cheapest discriminator between them.
- **Name the class on the card's thread, not the campaign's.** A run of 429s is not worth a fault report to the proxy's owner unless it lasts more than a hop; the owner's own jobs are hitting it too, and they will see it first.

**The two alternate within minutes on one engine, so a single failure tells you nothing.** A lane can produce a run of refusals, then a run of successes, then refusals again, then the artifact-retrieval fault — same account, same exit IP, same build. The error body, not the fact of the failure, decides the move:

- **A clean window is minutes wide, not hours.** A run of six successes inside eight minutes is the shape: when the path opens, submit the whole staged batch at once rather than one slot and a check, because the window can close before the next hop.
- **Two attempts a slot is the budget either way, and only a 502 spends one.** A 429 never starts the job, so it does not use up an attempt; count attempts off `artifact retrieval` failures alone.

## An idle lane is not an open engine

A verified-empty render lane was the right signal while the queue was the constraint: 0 pending / 0 running meant the next submit started at once. It is the **wrong** signal when the proxy is at fault, because an empty lane then means only that every runner has given up.

Check the newest success before submitting:

```bash
ssh m1max "sqlite3 /Users/wojciechgula/git/ideogram4-local/jobs.db \
  \"select max(finished_at) from jobs where status='done'\""
```

If that timestamp is more than about fifteen minutes old, treat the path as down and spend one fifteen-word probe instead of a batch. A failure run stays live until a success clears it: the proxy has been seen to recover for a window under half an hour and then be shut again an hour later, with nothing changing on this side in between.

Book the attempt honestly when this happens. Renders spent on a closed path are attempt 1 of 2 for each slot they touched, so the post note has to carry the job ids and the error body and say "prompt is not at fault, do not rewrite it" — otherwise the next run submits the same prompts as a first attempt and the round's budget is gone with no card to show for it. `jobs.db` timestamps are the render host's local time, an hour ahead of UTC here.

## A queued probe's ETA is the lane depth, so probe the host when the answer is needed now

`imagegen submit` is one FIFO, not one queue per engine: the worker takes the oldest `pending` row whatever engine it names, and an ideogram job holds the worker for about twenty-one minutes. A fifteen-word probe therefore costs a job's worth of waiting, not seconds. Read the depth before spending it:

```bash
ssh m1max "sqlite3 -separator ' | ' /Users/wojciechgula/git/ideogram4-local/jobs.db \
  \"select engine,status,count(*) from jobs where status in ('pending','running') group by engine,status;\""
```

Thirty-eight pending Ideogram jobs is about thirteen hours: a probe put in behind them answers tomorrow morning, which is the one thing a hop cannot wait for. Cheap in quota, expensive in the only resource the hop has.

- **When the engine's owner says it is fixed and asks for a check render, that is the case for a direct probe.** `scripts/probe-engine-direct.sh [prompt]` runs the worker's own `generate_nanobanana()` on the Max over ssh — one request, no queue slot, the proxy key read on the host by the worker's own code. It prints `{"ok": true, "path", "bytes", "dims", "seconds", "magic"}` and the proxy's error body verbatim on failure.
- **It refuses while a nanobanana job is already `running`** (exit 4, `{"ok": false, "busy": true}`), because a second concurrent request is the 429 `ip_slot_full` you would then have to explain. Read the busy line as "the lane is already measuring for me" and spend no submission.
- **Two probes a couple of minutes apart separate one bad turn from a dead path**, and neither spends a render or an attempt.
- **Paste the body, not a paraphrase.** The owner checks it against the pool panel: `no SNlM0e in page (cookie expired or not signed in)` and `fetch /app: HTTP 302 -> www.google.com/sorry/index` are different diagnoses, and a paraphrase loses the only text they can act on.
- **A direct probe proves the engine, not the pipeline.** It delivers no job row, no stamped output path and no `--name`, so nothing may be recorded, carded or chained off it; the real render still goes through `imagegen submit`.
- **The file it leaves behind is on the host, not on the Air.** `scp m1max:/tmp/nanobanana-probe-*.jpg ~/image-studio/staging/$(date +%F)/` when the probe is what you quote, then run `file` on the local copy — a `file` run against the remote path answers for the wrong machine in the report.

## A repair that waits in the queue meets the engine as it is when the worker starts it

A submit is not a promise. `bFBX1Y9GIUU` sat `pending` for 12 h 09 min behind ideogram4 traffic, then its row read `started_at` 18:57:29.628 and `finished_at` 18:57:29.701 — 0.07 s dead — with the empty-pool 400 body (`gemini-image is unavailable without a Google account cookie … silently downgraded to a plain "Are you signed in?" text reply`). The hop before it said "7 ahead, ETA 131 min", which read as a normal wait.

- **The queue position says nothing about the engine.** Read the job's own `error` at collect before writing the note; when it already names the pool, no probe is needed.
- **Three slots already fetched and passing plus one dead slot is a normal collect-wake shape for a repair.** Do not re-submit blind: that spends an attempt on a closed path. The prompt file stays as it is — the picture failed to exist, not to fit.
- **Hand the fix to the pool's owner, then ask the blog owner one question with the options spelled out**: refill the cookie in the Cookie Pool panel, one render off-lane (`flux2-klein`, no Google session), or keep hopping until the fault clears. Say which is the quality decision and whose it is; do not pick a lane engine on your own.
- **When he takes the off-lane render, carry the deviation in three places, not one.** Re-cut the prompt into that engine's shape — flux2-klein reads a plain natural-language file of about 250 words, and takes `-W -H` so hand it the sibling renders' canvas (grab it with `PIL.Image.open(...).size`) rather than a flux default, or the slot lands at a different aspect from its neighbours. Switch the brief's engine line and that slot's `generation` block to the flux record (`engine: "flux2-klein"`, `prompt_type: "text"`, `generation: {"model": "black-forest-labs/FLUX.2-klein-4B", "steps": 4, "seed": <job row>}`). And say in the check note that flux adds no film grain, so that frame is the one on the post without it. A deviation named in all three places reads as a decision; the same deviation only in a comment reads as an accident.

## The cookie pool fails with its own body — and the read path fails with it

A third fault class, different from both the artifact-retrieval 502 and the 429. It names its own cause:

```
502 {"error":{"message":"upstream error: cookie 池里 1 个账号都不可用（最后一个：fetch /app: HTTP 302
-> www.google.com/sorry/index）；到面板「Cookie 池」用「检测」按钮逐个排查，或打开 fallback_anon 降级匿名"}}
```

- **It means the pool is empty of usable sessions, not that generation failed.** The pool holds one account; its last fetch of `/app` came back as an HTTP 302 to `www.google.com/sorry/index`, Google's bot check. Nothing is rendered at all.
- **It dies in one to five seconds**, where the artifact-retrieval 502 runs 15 to 48 s and a real render runs 14 to 80 s. Duration separates all three.
- **The same body comes back from the image-reading route on this host.** One dead cookie takes out the render path and the read path together, so a failed `vision_analyze` and a failed submit in the same minute are one event, not two. When both are down, do not spend a probe to learn what the read already told you.
- **It costs no render and no attempt**, like a 429: the job never reaches generation, so a slot keeps its budget.
- **The two named fixes belong to the pool's owner:** re-check the account from the pool panel, or turn on `fallback_anon`. Never restart the container, never re-authenticate an account, never switch engines over it.
- **A second body of the same fault, seen after a claimed fix:** `cookie 池里 1 个账号都不可用（最后一个：no SNlM0e in page (cookie expired or not signed in)）`. `SNlM0e` is the signed-in marker Gemini embeds in the page, so its absence means the fetch got an anonymous page — the session is not merely throttled, it is gone. Same disposition as the 302 body: owner's job, no probe spent, no prompt rewritten.
- **`GET /v1/models` answering `200` is not evidence the engine works.** The proxy serves its model catalogue from memory and does that with an empty cookie pool. Only a generation reply carries the picture. So a check render is the test, never a health route — a 200 there has already been read as "fixed" and cost a whole wake on a dead engine.

A healthy window can end in this fault within ten minutes of a full clean batch — fifteen renders done at 05:42Z, the first cookie-pool failure at 05:52Z — which is the same lesson as the idle-lane section below: the path's state is a fact about minutes, and the newest success is the only evidence worth acting on.

## The cookie fault clears by itself, and the body is what tells you which fault you are in

The empty-pool fault is not terminal: it goes away on its own, hours later, with nothing restarted. When it does, the next probe does not fail faster or slower — it fails with a **different body and a longer death**, which is the only reliable signal that the fault changed under you. Measured pair, one hour apart, both fifteen-word probes into an empty lane:

| time (UTC) | duration | body |
| --- | --- | --- |
| 07:53 | **10 s** | `cookie 池里 1 个账号都不可用（最后一个：fetch /app: HTTP 302 -> www.google.com/sorry/index）` |
| 08:51 | **17 s** | `media generation succeeded but artifact retrieval failed: 响应里没有图片 CDN 链接` |

So: read the error text before quoting the fault, and do not re-report an outage as the same one when its body has changed. A short death that names the pool is a wait; a longer death that says the picture was generated is the artifact fault and worth the proxy's own thread. Neither justifies a real submission — one probe per hop either way.

## Rule 371 — Engine outage recovery

After an artifact-retrieval 502 outage, the fault may clear on its own with no container or prompt changes. **Why**: The proxy's internal state determines the fault, not host-side modifications; the same error body can repeat across restarts with no actual fix. **Action**: One 15-word probe into an empty lane confirms recovery; on success, submit all staged renders and repairs immediately before the window closes (typically 2–5 minutes). On failure, arm a monitor and wait for the next hop. Never report a recovery as a fix — the honest sentence is 'it cleared on its own between X and Y, nothing differed on our side.' This session's recovery at 10:00:20Z after ~4 hours of outage confirms the pattern: the fault cleared naturally, and the probe that returned pixels was the enabler for submitting the whole batch.

## A failed off-lane render hands the slot back to the lane

When a slot was moved off the backlog lane (flux2-klein) because the pool was dead, and that render then fails self-check on text-bearing surfaces while the pool has recovered, do not keep the slot off-lane out of inertia. Move it back:

- **Re-render on nanobanana once the pool answers a probe.** The failure was pseudo-text on a wall paper and a logo on a smooth panel, not the scene; the pool's recovery is the condition, not the prompt. A direct probe that returns pixels is the gate.
- **Strengthen the text ban by naming the surfaces as bare**, not by repeating "no text": "the boards are completely bare: no pinned papers, no notes, no sketches, no marks" and "the computer's front panel is completely smooth and unmarked, with no logo, no brand mark, no text, no symbols". A global ban reads as "no readable text" and the model fills the surface with pseudo-text.
- **Keep the failed render in staging as evidence** and name it on the card; do not delete it or hide it behind the passing one. The card carries the passing nanobanana render and one line on why flux was tried and dropped.

## The output extension lies about the format

A finished job stores `engine = "nanobanana"` and `seed = NULL`, and the output file is written to the `-o` path the job was given — which is not necessarily the format the tool returned. `imagegen submit` passes `-o <name>-<8hex>.png`, so a JPEG reply lands in a `.png` filename; verified 2026-11-04 (GUL-895): `file` says `JPEG image data … 1376x768`, 208 072 bytes, and the Paperclip attachment then records `contentType: image/png`. Run `file` on the output before quoting a format: the web tool decides the format, the extension does not. The library back-fill reads the engine column, so a nano banana image is labelled by its engine, not as an Ideogram render, whatever the filename says.
