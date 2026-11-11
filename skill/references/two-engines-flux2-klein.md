# Engines on one queue: Ideogram 4, FLUX.2-klein, and nano banana

Phase 6 of the Image Studio plan. `gulasz101/ideogram4-local` at `b047f9d` (PR #5) added
**FLUX.2-klein-4B** as a second engine on the same SQLite queue and the same worker.

> **Since phase 7 there is a third engine.** `nanobanana` (the Gemini web proxy) runs the same
> queue and the same review loop and is the current default engine — see
> `references/nanobanana-engine.md` and ADR-123. This file stays the FLUX.2-klein runbook and
> the comparison that justifies "draft on FLUX, commit the keepers to a slower engine".

| | Ideogram 4 | FLUX.2-klein |
|---|---|---|
| Engine id | `ideogram4` | `flux2-klein` |
| Prompt | structured JSON, Ideogram schema | plain natural language |
| Speed (1216x832) | ~21 min | ~2 min (89 s gen + 75 s model load) |
| Seed | always `NULL` | integer, stored in `jobs.seed` |
| Runtime | `sd-cli` (stable-diffusion.cpp) | `flux2_klein.py` in `~/.venvs/sou-flux` |
| Weights | `~/sd.cpp-models` | HF cache, 15 GB, already on the Max |

## The design

One queue, one worker, three engines. The worker dispatches on the `engine` column *before*
touching `sd-cli`, so a worker with no sd.cpp build can still run FLUX jobs. The generation
lock (`IDEOGRAM4_LOCK_FILE`) keeps the local engines off the GPU one at a time — the queue
serialises them properly, verified when a FLUX job released the lock at `16:36:19.639` and
the Ideogram job behind it took it at `16:36:19.653`.

The worker stays stdlib-only on Homebrew Python (no torch). For a `flux2-klein` job it runs
`flux2_klein.py` in the `~/.venvs/sou-flux` venv as a subprocess, exactly the way the
Ideogram path runs `sd-cli`.

## The migration is free

The worker migrates `jobs.db` in place on first use:

```sql
ALTER TABLE jobs ADD COLUMN engine TEXT NOT NULL DEFAULT 'ideogram4';
ALTER TABLE jobs ADD COLUMN seed INTEGER;
```

`NOT NULL DEFAULT 'ideogram4'` back-fills every existing row with no data rewrite and no
downtime. Verified on the Max: 647 pre-existing rows, all `ideogram4`, all with a `NULL`
seed (Ideogram jobs keep the `NULL` seed they always had). Check with:

```bash
sqlite3 jobs.db "select name from pragma_table_info(\"jobs\") where name in (\"engine\",\"seed\");"
sqlite3 jobs.db "select engine, count(*) from jobs group by engine;"
sqlite3 jobs.db "select count(*) from jobs where engine='ideogram4' and seed is not null;"   # expect 0
```

## Rules

1. **Restart the worker after pulling engine code.** The worker is a long-running process.
   Without a restart it keeps the old code and will treat a FLUX job as an Ideogram job.
2. **Restart only on an idle queue.** Never kill a running job — Ideogram renders are 21
   minutes each and the queue is shared with other agents' work. Check first:
   ```bash
   sqlite3 jobs.db "select status,count(*) from jobs group by status;"
   ```
   Zero `pending` and zero `running` means go. Also confirm from the log tail that the
   worker is printing `No pending jobs; sleeping 10s...`.
3. **Never `git clean` the Max checkout.** It carries untracked files (`EOF`, `PY`,
   `post-linux35*.sh`, `prompts/*.json`) that are not in git.
4. **If `git pull --ff-only` refuses over an untracked file**, do not delete it blind.
   Compare it with the upstream version first:
   ```bash
   F=path/to/file
   shasum -a 256 "$F" ; git show origin/main:"$F" | shasum -a 256
   diff <(cat "$F") <(git show origin/main:"$F") && echo IDENTICAL
   ```
   If identical, back it up outside the repo, remove the untracked copy, pull. If it
   differs, keep the local copy somewhere safe and reconcile by hand.
5. **`HF_HUB_OFFLINE=1` is set by the worker** so the pipeline never tries to re-download
   15 GB onto a nearly-full disk. The weights are already in the HF cache.
6. **FLUX prompts are natural language only.** There is no `lint` and no JSON for FLUX.
   `--prompt` or `--prompt-file`, exactly one. The text encoder truncates at 512 tokens.
7. **klein is a distilled model** — 4 steps, `guidance_scale=1.0` (ignored by the model,
   kept for parity). The pixel-art LoRA is never loaded: in diffusers it collapses output
   to black frames at every documented strength.
8. **klein paints a checkerboard where alpha would be**, so the output is saved as RGB.
9. **`Flux2KleinPipeline`'s first positional parameter is `image`**, not `prompt` — pass the
   prompt as a keyword or the pipeline raises "Provide either `prompt` or `prompt_embeds`".
10. **The prompt goes on stdin, not argv** — a long prompt or one starting with `-` is
    data, not a flag.

## Commands

```bash
# Submit a fast draft from the Air
imagegen submit --engine flux2-klein --name my-draft --json \
  --prompt "a cosy homelab corner at night, warm lamp light, editorial illustration"

# Or on the Max
python3 ideogram4_local.py submit --engine flux2-klein \
  --prompt "a fox in a server room" -o output/studio/2026-10-21/fox.png
```

## Verified field results (2026-10-21, M1 Max)

```
[flux2-klein] loaded black-forest-labs/FLUX.2-klein-4B in 75.2s
[flux2-klein] generated 1216x832 seed=1676037250 steps=4 in 89.4s
```

- Model load **75.2 s**, generation **89.4 s**, `started_at`->`finished_at` **173.3 s**
- Output: PNG, 1216x832, 8-bit RGB, ~1.5 MB
- `torch 2.14.1`, `diffusers 0.41.0`, MPS available, venv at `~/.venvs/sou-flux`
  (Python 3.13)

The FLUX render came out clean: a real night-time home-office scene with a server rack full
of amber status LEDs, a laptop on a wooden desk, and rain on the window. No grey
safety-filter box, no grey border bars. FLUX does not share Ideogram's prompt-structure
safety filter — a plain natural-language prompt is enough.

## Speed comparison

FLUX is ~7x faster end to end. Use it to explore compositions and commit the keepers to
Ideogram 4. But note FLUX is a 4B distilled model: it is a draft engine, not a keeper
engine. Do not publish a FLUX render as a final blog hero.
