---
name: image-studio
description: "Make images for Wojtek's blog and LinkedIn posts with Ideogram 4 on the M1 Max: prompt variants, render via imagegen, self-check, Paperclip verdict card, taste memory, image library."
version: 4.0.0
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

2. **Write 2–4 variants** as Ideogram 4 JSON, starting from `templates/` and following `references/engine-pitfalls.md`. Validate each with `scripts/verify-schema-and-schedule.py`. Default size 1216×832. *Done when every variant passes the verifier and has a one-sentence why.*

3. **Submit** each with `imagegen submit --prompt-json <file> --name <slug>` (stdout is only the job id). Comment the job ids and the prompt summaries on the issue. *Done when the comment lists one job id per variant.*

4. **Wait without polling.** Read `eta_minutes` from `imagegen status <last-job-id>`. Schedule an issue monitor at ETA + 5 minutes, keep the issue `in_progress`, and end the run. A render takes about 21 minutes and jobs queue one after another. Use the shapes in `references/review-loop.md` and `references/paperclip-api.md`. *Done when the PATCH response shows a non-null `monitorNextCheckAt`.*

5. **On a monitor wake**, run `imagegen status` for each job. If any job is still running, reschedule the monitor and end the run. Otherwise run `imagegen fetch <job-id>`; files land in `~/image-studio/staging/<date>/`. *Done when every PNG is local and over 1 MB.*

6. **Self-check** each image with `vision_analyze`: text is spelled exactly as prompted; there is no grey box and `scripts/check-grey-bars.py` passes; the image matches the intent. Re-render a failing variant once, silently, with a fixed prompt. Your check filters out defects; it never approves. *Done when each image has a pass/fail note.*

7. **Show the batch to Wojtek.** Upload the passing PNGs as issue attachments. Create one `request_item_verdicts` card with one item per image: `attachmentId`; `label` = the slug; `description` = the prompt summary plus the why. Use verdicts approve/reject/defer, `requireReasonOn: ["reject"]`, `continuationPolicy: "wake_assignee"`, and idempotency key `verdicts:<issueId>:round-<n>`. Set the issue to `in_review`. *Done when the card is `pending` and the issue is `in_review`.*

8. **On a verdict wake** (`newlyResolvedItemIds`), handle each newly resolved item:
   - `hindsight_retain` the verdict, the reason, the post, and the prompt traits that mattered, with tags `taste` and `verdict`.
   - **Approve:** copy the PNG into `~/wojtek.second.brain.obsidian.vault/tech_blog/assets/<YYYY-MM-DD>/<slug>.png` and write the library record (`references/library-records.md`).
   - **Reject:** revise the prompt from the reason and start the next round at step 3.
   - **Defer:** leave the item.
   - Run at most 3 rounds per request. After round 3 with a slot still unapproved, ask Wojtek on the issue what to change instead of rendering again.
   *Done when every newly resolved item is retained and handled.*

9. **Close** when every requested slot has an approved image. Comment with the asset paths and the record links, then set the issue to `done`. *Done when the issue is `done` and the comment carries every asset path and record link.*

## Rules

- **Let only Wojtek's verdict on the card approve an image.** He owns the taste; your self-check exists to remove defects, not to bless a render.
- **Act in Paperclip as yourself with `PAPERCLIP_API_KEY` from `~/.hermes/profiles/matejko/.env`.** That keeps every card and comment attributed to Matejko; `~/.paperclip/auth.json` is the board's token and stays closed.
- **Keep drafts in staging and let only approved images into the vault.** The published library then contains only work Wojtek has approved.
- **Report any `skill_manage` patch to this skill in the issue comment.** It keeps the procedure reviewable by the person who owns it.
- **Use `imagegen` for every render.** It is the one supported path from the Air to the M1 Max worker, with a single queue and ETA the board can monitor.

## References

- `references/engine-pitfalls.md` — 29 numbered failure modes; read before writing or fixing any prompt.
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
- `references/2026-07-10-schema-schedule-verification.md` — schema and schedule verification; open when checking those assumptions.
- `references/queue-db-recipes.md` — queue inspection and repair; open when a job is stuck or missing.
- `references/launchd-agent.md` — the worker LaunchAgent; open when the worker is not running on the Max.
- `references/ideogram4-cat-poster-reproduction.md` — a reproducible grey-box case; open when a similar composition fails.
- `references/hf-cat-poster-grey-box-repro.md` — the hosted-versus-local reproduction; open when a prompt worked online but not locally.

### Legacy references (Mattermost retired; review happens only in Paperclip)

- `references/mattermost-channel-delivery.md` — legacy Mattermost delivery; kept for history only.
- `references/mattermost-watchdog.md` — legacy Mattermost watchdog; kept for history only.
- `references/watchdog-notification-loop-recovery.md` — legacy duplicate-notification recovery; kept for history only.
