---
name: image-studio
description: "Make images for Wojtek's blog and LinkedIn posts with Ideogram 4 on the M1 Max: prompt variants, render via imagegen, self-check, Paperclip verdict card, taste memory, image library."
version: 4.1.0
author: Claude Code
date: 2026-10-21
---

# image-studio

Matejko's whole procedure for turning a Paperclip image request into an Ideogram 4 render, putting it in front of Wojtek, and learning from his verdicts. The generation stack runs on the M1 Max; `imagegen` submits and fetches from the Air.

## When to use

Use this skill on any of these branches:

- An issue asks for an image (a header, illustration, or diagram for a post).
- An issue monitor wakes you on a render (`monitorNextCheckAt` has arrived).
- An item-verdict wake arrives with a non-empty `newlyResolvedItemIds`.
- Wojtek asks about an image's prompt, history, or why it looks the way it does.

## The request workflow

1. **Read.** Read the issue's post, section, excerpt, and the intent behind them (the "why"); read the post file in `~/wojtek.second.brain.obsidian.vault/tech_blog/`; run `hindsight_reflect("What is Wojtek's image taste for <post topic>?")`, which reads the mental model **Wojtek's image taste**. *Done when you can state the post's idea in one sentence and list the taste rules that apply.*
   - **Fit the series first.** When the post already has images, read their library records' `## Prompt` JSON before writing a variant, and reuse the series' `style_description` block, its character descriptions and its world (workshop, racks, the grey boxy robot) as written. Reusing the series' prompt is what makes a new image belong to the set; matching its look from the PNG alone does not.
   - **An empty taste model is not a licence to invent taste.** When `hindsight_reflect` finds no verdicts for the topic there is simply no history yet: say so on the issue and build the variants from the existing series and the section's intent instead of presenting guessed rules as Wojtek's preferences.
   - **The records beat the taste memory, and one verdict is not a rule.** `hindsight_reflect` synthesizes across verdicts and will assert a history the records contradict — it has described a round-1 rejection on a slot whose round-1 items were both approved. Before a claim shapes a prompt, check it against the library record's `## Verdicts` table and the card's `result`, and follow the records where the two disagree. A single approval or rejection is one data point about his eye, not a preference: two variants approved on one card does not mean he always approves both, and the request's slot count still decides how many images ship.

2. **Write 2–4 variants** as Ideogram 4 JSON, starting from `templates/` and following `references/engine-pitfalls.md`. Validate each with `python3 ~/.local/share/ideogram4-local/ideogram4_local.py lint <file>`. Default size 1216×832. *Done when every variant passes `lint` with risk score 0 and no schema issues, and has a one-sentence why.*

3. **Submit** each with `imagegen submit --prompt-json <file> --name <slug>` (stdout is only the job id). **On a resumed or re-woken run, read `GET /issues/<id>/interactions` and the comments before submitting** — a card already open for this round, or a `verdicts:<issueId>:round-<n>` already answered, means those renders exist: handle them (fetch, self-check, verdicts) rather than spending another 21 minutes per image on duplicates. Comment the job ids and the prompt summaries on the issue. *Done when the comment lists one job id per variant.*

4. **Wait without polling.** Read `eta_minutes` from `imagegen status <last-job-id>`. Schedule an issue monitor at ETA + 5 minutes, keep the issue `in_progress`, and end the run. A render takes about 21 minutes and jobs queue one after another. Use the shapes in `references/review-loop.md` and `references/paperclip-api.md`. *Done when the PATCH response shows a non-null `monitorNextCheckAt`.*

5. **On a monitor wake**, run `imagegen status` for each job. If any job is still running, **fetch and self-check the ones already `done` first** — a variant that fails the step-6 check can then be re-submitted immediately, so it renders in the queue behind the job still running instead of costing a whole extra round — then reschedule the monitor and end the run. Otherwise run `imagegen fetch <job-id>`, which prints the local path of the fetched `<slug>-<8 hex>.png` under `~/image-studio/staging/<date>/`: keep that path in a variable and use it for every later check and upload. *Done when every PNG is local and over 1 MB.*

6. **Self-check** each image with `vision_analyze`: text is spelled exactly as prompted; there is no grey box and `scripts/check-grey-bars.py` passes; the image matches the intent. **Intent means the story beat reads, not that the objects are all present** — if the why says a cable joins the cheap machine to the proud robot, a clean render where the cable stops at the bench fails the check, and the repair is a prompt fix (the connector becomes its own element with a bbox spanning both ends, per `references/engine-pitfalls.md` #30), not a shrug. Re-render a failing variant once, silently, and say in the closing comment what you held back and why. Your check filters out defects; it never approves. *Done when each image has a pass/fail note, and every held-back render has a one-line reason.*

7. **Show the batch to Wojtek.** Upload the passing PNGs as issue attachments. Create one `request_item_verdicts` card with one item per image: `attachmentId`; `label` = the slug; `description` = the prompt summary, the why and the self-check note in **500 characters or fewer**; `resolverPolicy: "human_only"` so only Wojtek can resolve an image verdict. Use verdicts approve/reject/defer, `requireReasonOn: ["reject"]`, `continuationPolicy: "wake_assignee"`, and idempotency key `verdicts:<issueId>:round-<n>`. Set the issue to `in_review`. *Done when the card is `pending` and the issue is `in_review`.*

8. **On a verdict wake** (`newlyResolvedItemIds`), handle each newly resolved item:
   - `hindsight_retain` the verdict, the reason, the post, and the prompt traits that mattered, with tags `taste` and `verdict`.
   - **Approve:** copy the PNG into `~/wojtek.second.brain.obsidian.vault/tech_blog/assets/<YYYY-MM-DD>/<label>.png` and write the library record (`references/library-records.md`).
   - **Reject:** revise the prompt from the reason and start the next round at step 3.
   - **Defer:** leave the item.
   - Run at most 3 rounds per request. After round 3 with a slot still unapproved, ask Wojtek on the issue what to change instead of rendering again.
   - **On a comment wake, read the comment.** A user comment while the card is pending supersedes the rest of the card (`superseded_by_comment`); when that happens, open the next round's card with a new idempotency key, carrying the remaining items and revised by the comment.
   *Done when every newly resolved item is retained and handled.*

9. **Close** when every requested slot has an approved image. The closing comment is the audit trail, so it carries: the job id of every render per round, the vault asset path, every library record path, the self-check note for each image (held-back renders included, with the reason), and any `skill_manage` patch you made. Then set the issue to `done`. *Done when the issue is `done` and the comment carries every job id, asset path, record path and self-check note.*

## Rules

- **Let only Wojtek's verdict on the card approve an image.** He owns the taste; your self-check exists to remove defects, not to bless a render.
- **Act in Paperclip as yourself with `PAPERCLIP_API_KEY` from `~/.hermes/profiles/matejko/.env`.** That keeps every card and comment attributed to Matejko; `~/.paperclip/auth.json` is the board's token and stays closed.
- **Keep drafts in staging and let only approved images into the vault.** The published library then contains only work Wojtek has approved.
- **Report any `skill_manage` patch to this skill in the issue comment.** It keeps the procedure reviewable by the person who owns it.
- **Use `imagegen` for every render.** It is the one supported path from the Air to the M1 Max worker, with a single queue and ETA the board can monitor.
- **Never restart Paperclip or the Hermes gateway to clear a blocker.** Diagnose it from the server log, state what you ruled out, and open a `request_confirmation` for the board owner instead (`references/paperclip-api.md` carries the recipe and the storage-relay fix). You cannot cancel such a card once it is moot, so choose it deliberately and say on the issue when it no longer applies.

## References

- `references/engine-pitfalls.md` — 30 numbered failure modes; read before writing or fixing any prompt.
- `references/review-loop.md` — the Paperclip calls for each loop step; open when scheduling, uploading, or handling verdicts.
- `references/library-records.md` — record path and exact format; open when approving an image or revising a record.
- `references/paperclip-api.md` — auth and curl shapes; open when a call fails or you need an endpoint detail.
- `references/air-wrapper.md` — deployment and smoke test; open when `imagegen` is missing, stale, or misconfigured.
- `references/ideogram4-oss-schema.md` — the canonical JSON schema; open when a prompt's structure is in doubt.
- `references/prompt-hygiene.md` — vocabulary and schema hygiene; open when a prompt needs de-risking.
- `references/ideogram4-official-sampler-schedules.md` — the official CFG schedule; open when steps or guidance are questioned.
- `references/ideogram4-safety-filter.md` — how the filter behaves; open when a render greys out and the cause is not obvious.
- `references/grey-border-bars.md` — empty-margin diagnosis and fix; open when an image passes the safety filter but has grey bars.
- `references/heretic-encoder-swap.md` — encoder choices; open only when the encoder itself must change.
- `references/pre-v340-prompt-migration.md` — old prompt formats; open when regenerating a pre-v3.4.0 prompt.
- `references/2026-07-12-tech-prompt-vocabulary-fix.md` — technical vocabulary case study; open when words may be the trigger.
- `references/agent-update-notice-2026-07-10.md` — engine update notice; open when behavior changed after an update.
- `references/2026-07-10-schema-schedule-verification.md` — schema and schedule verification; open when checking those assumptions. The wrapper `python3 skill/scripts/verify-schema-and-schedule.py` is a repo-root regression check only: it globs `templates/`, so use `lint` for a single variant.
- `references/queue-db-recipes.md` — queue inspection and repair; open when a job is stuck or missing.
- `references/launchd-agent.md` — the worker LaunchAgent; open when the worker is not running on the Max.
- `references/ideogram4-cat-poster-reproduction.md` — a reproducible grey-box case; open when a similar composition fails.
- `references/hf-cat-poster-grey-box-repro.md` — the hosted-versus-local reproduction; open when a prompt worked online but not locally.

### Legacy references (Mattermost retired; review happens only in Paperclip)

- `references/mattermost-channel-delivery.md` — legacy Mattermost delivery; kept for history only.
- `references/mattermost-watchdog.md` — legacy Mattermost watchdog; kept for history only.
- `references/watchdog-notification-loop-recovery.md` — legacy duplicate-notification recovery; kept for history only.
