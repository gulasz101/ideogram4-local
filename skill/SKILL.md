---
name: image-studio
description: "Make images for Wojtek's blog and LinkedIn posts on the M1 Max (nano banana, Ideogram 4, FLUX.2-klein): prompt variants, render via imagegen, self-check, Paperclip verdict card, taste memory, image library."
version: 5.0.0
author: Claude Code
date: 2026-11-13
---

# image-studio

Matejko's procedure for turning a Paperclip image request into renders, putting them in front of Wojtek, and learning from his verdicts. The stack runs on the M1 Max; `imagegen` submits and fetches from the Air. The repo `ideogram4-local` is the single source; change the skill only by PR here, then `skill/sync.sh --apply`.

## The show bar (always on)

Only an image that passes all four clauses reaches a review card:

1. **Figures correct** — two hands, two arms, one head, one person unless the prompt says otherwise; correct anatomy.
2. **No colourful artifacts** — no pasted panel, badge, sticker, banner or swatch strip, nothing in another idiom from the frame, no photograph with vector graphics laid over it.
3. **Text only if readable English** — `Racoiving`, `HelmRelest`, `H16` are defects; no lettering at all is fine.
4. **The beat reads** — the picture tells the post's story.

A failure is not shown: rewrite the prompt and re-render. Full bar and repair recipe: `references/archive/bulk-library-triage.md`.

## Engine choice

- **`nanobanana` is the default** for blog and LinkedIn images. About 12 s per picture, natural language, no prompt-vocabulary filter, no grey-box dance. Sizes come back as the web tool returns them (1376x768, sometimes 1584x672); never promise a fixed canvas. No seed, no `--prompt-json`. Pace it: at most one image a minute, 5-8 posts per wake.
- **`flux2-klein` for drafts and companion panels.** About 3 min for 1216x832; natural language, 368-425 words.
- **`ideogram4` only when Wojtek asks for it or an exact canvas size is required**, and never with text in the image: an Ideogram prompt contains no lettering. JSON prompts, about 21 min per 1216x832.

Everything after the render is the same: review loop, verdict card, library record. `references/two-engines-flux2-klein.md`, `references/nanobanana-engine.md`.

## Text rule

No text in an image unless the prompt spells every word exactly (few, short words). Otherwise the prompt says `no text, no letters, no labels`. The self-check reads each word back before the card. A misspelt or garbled label is a defect, not a quirk. `references/text-in-images.md`, `references/prompt-hygiene.md`.

## Concept first

Before the first render, write the story of the picture in one sentence: who does what, and why it matters for the post. If it is not clear, ask Florian before rendering, not after a rejection. A prompt with no verb produces a render with no story.

## The request workflow

1. **Read.** Read the issue's post, section, excerpt and intent; read the post file in `~/wojtek.second.brain.obsidian.vault/tech_blog/`. Run `hindsight_reflect("Wojtek's image taste for <topic>")`. State the post's idea in one sentence and list the taste rules that apply. Fit the series first: reuse the series' `style_description`, character descriptions and world from its library records' `## Prompt` JSON. Taste and recall details: `references/taste-memory.md`.
2. **Write 2-4 variants** as Ideogram JSON from `templates/`, following `references/engine-pitfalls.md`. Validate each with `python3 ~/.local/share/ideogram4-local/ideogram4_local.py lint <file>` (risk score 0) and `python3 scripts/check-bboxes.py <file>`. Default size 1216x832. Each variant needs a one-sentence why. Prompt hygiene: `references/prompt-hygiene.md`.
3. **Submit** each with `imagegen submit --prompt-json <file> --name <slug>` (stdout is only the job id). On a resumed or re-woken run, read `GET /issues/<id>/interactions` and comments first; do not re-submit renders that already exist. Comment the job ids and prompt summaries. `references/air-wrapper.md`.
4. **Wait without polling.** Read `eta_minutes` from `imagegen status <last-job-id>`. Schedule an issue monitor at ETA + 5 min, keep the issue `in_progress`, end the run. PATCH body uses `nextCheckAt`. `references/archive/review-loop.md`, `references/paperclip-api.md`.
5. **On a monitor wake**, run `imagegen status` for each job. Fetch and self-check the ones already done first; reschedule if any still running. Otherwise `imagegen fetch <job-id>`; keep the path. Every PNG local and over 1 MB.
6. **Self-check** each image with `vision_analyze` (resolved paths; the vault is a symlink, so build paths from `readlink -f`). Text spelled exactly as prompted, including invented labels; no grey box (`scripts/check-grey-bars.py` with `~/image-studio/.venv-imgcheck/bin/python`); no colour-palette strip (`scripts/check-palette-strip.py`); no blank margin (`scripts/check-blank-margin.py`); matches intent. Only then build the verdict card. `references/verifying-image-details.md`.

## References

- `references/style-and-companions.md` — series look, accent colour, FLUX pairs.
- `references/engine-pitfalls.md` — numbered failure modes; read before writing or fixing any prompt.
- `references/figure-and-prop-prompts.md` — figure holding one object: limb count, contact, crop.
- `references/prompt-hygiene.md` — vocabulary and schema hygiene, negative clauses.
- `references/text-in-images.md` — text rules and label traps.
- `references/two-engines-flux2-klein.md` — FLUX engine notes.
- `references/nanobanana-engine.md` — nano banana engine notes.
- `references/air-wrapper.md` — deployment and smoke test.
- `references/ideogram4-oss-schema.md` — canonical JSON schema.
- `references/grey-border-bars.md` — empty-margin diagnosis.
- `references/library-records.md` — record path and exact format.
- `references/paperclip-api.md` — auth and curl shapes, monitors, verdict cards.
- `references/taste-memory.md` — reflect, recall, retain, curation.
- `references/verifying-image-details.md` — settle a small self-check claim before the card.
- `references/vision-route-fallbacks.md` — readers when the vision tool is down.
- `references/series-look.md` — series style and text handling.
- `references/series-style.md` — style notes.
- `references/state-vocabulary.md` — state terms.
- `references/asset-paths.md` — asset paths.
- `references/check-scripts.md` — check scripts.
- `references/counting-checks.md` — counting checks.
- `references/mechanical-probe-reads.md` — probe reads.
- `references/prompt-check-traps.md` — prompt check traps.
- `references/render-selection.md` — render selection.
- `references/1990s-anime-style.md` — series visual style.
- `references/launchd-agent.md` — worker LaunchAgent.
- `references/archive/review-loop.md` — Paperclip calls for each loop step.
- `references/archive/backlog-review.md` — backlog-review mode.
- `references/archive/bulk-library-triage.md` — full bar, prompt-repair recipe, batching.
- `references/archive/re-render-defect-persistence.md` — re-render repeating a defect.
- `references/archive/author-composition-handoff.md` — asking the post's author for a composition.
- `references/archive/disposition-repair.md` — parked issues and dispositions.

Scripts: `scripts/`. Templates: `templates/`.
