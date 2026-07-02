---
name: ideogram4-local
description: Generate images locally with Ideogram 4 via stable-diffusion.cpp using an SQLite-backed job queue, a singleton worker, and a Mattermost progress watchdog on Apple Silicon.
author: Andrzej <andrzej@example.com>
date: 2026-07-02
version: 3.3.0
tags:
  - image-generation
  - ideogram4
  - stable-diffusion.cpp
  - local-ai
  - apple-silicon
  - sqlite
  - queue
  - launchd
  - mattermost
---

# ideogram4-local

Generate blog headers and other images locally using **Ideogram 4** via [stable-diffusion.cpp](https://github.com/leejet/stable-diffusion.cpp). Built for an Apple Silicon M1 Max with 32 GB unified RAM.

The system has three parts:
1. **SQLite queue + CLI** — agents submit jobs; one worker processes them serially.
2. **launchd LaunchAgent** — worker auto-starts on login and restarts on crash.
3. **Mattermost watchdog cron** — posts emoji-rich progress updates and finished images to a dedicated channel.

## When to use

- You need a custom blog header, diagram illustration, or concept art.
- The image must contain readable text labels or a specific multi-element composition.
- You want to run everything locally on the M1 Max instead of using an API.
- Multiple Hermes agents might ask for images; the queue serializes the heavy generation work.

## What is required

- A built copy of `leejet/stable-diffusion.cpp` at `~/sd.cpp`.
- ~16 GB of model files in `~/sd.cpp-models` (downloaded automatically by the worker).
- The public repo `gulasz101/ideogram4-local` cloned locally.

## Quick commands

### Build stable-diffusion.cpp (one-time)

```bash
cd ~
git clone --recursive https://github.com/leejet/stable-diffusion.cpp.git sd.cpp
cd sd.cpp
mkdir -p build && cd build
cmake .. -DSD_WEBP=OFF -DSD_WEBM=OFF
cmake --build . --config Release -j$(sysctl -n hw.ncpu)
```

Verify: `~/sd.cpp/build/bin/sd-cli --help` should print usage.

### Clone the wrapper

```bash
git clone https://github.com/gulasz101/ideogram4-local.git
cd ideogram4-local
```

### Submit a job

```bash
export IDEOGRAM4_MODELS_DIR=~/sd.cpp-models

JOB_ID=$(python3 ideogram4_local.py submit \
  --prompt-json prompts/homelab-toriyama.json \
  -o output/header.png \
  -W 1216 -H 832 -v)

echo "Job submitted: $JOB_ID"
```

The CLI prints **only the job ID to stdout**; logs go to stderr so shell capture works.

### Check status and wait

```bash
python3 ideogram4_local.py status "$JOB_ID"
python3 ideogram4_local.py list
python3 ideogram4_local.py wait "$JOB_ID"   # blocks until done/failed
```

### Start the worker manually

```bash
export IDEOGRAM4_MODELS_DIR=~/sd.cpp-models
python3 ideogram4_local.py worker
```

The worker uses a file lock so only one generation runs at a time. If another worker is already busy, extra workers queue politely.

## JSON prompt structure

Ideogram 4 is trained on structured JSON. The wrapper passes the JSON verbatim to `sd-cli`. Use this shape:

```json
{
  "high_level_description": "overall scene summary",
  "style_description": {
    "aesthetics": "...",
    "lighting": "...",
    "photo": "...",
    "medium": "...",
    "color_palette": ["#FF6B00", "#00D4FF"]
  },
  "compositional_deconstruction": {
    "canvas": "...",
    "background": "...",
    "layout": "...",
    "elements": [
      {"type": "obj", "desc": "a mechanic installing a server"},
      {"type": "text", "desc": "exact text 'homelab-2nd' on a sign"}
    ]
  }
}
```

The wrapper also accepts an optional top-level `"generation"` block for backend-only options. It is stripped before the prompt reaches `sd-cli`. See [Safety filter workaround](#safety-filter-grey-out-workaround) below for an example. Use `templates/prompt-with-safety-bypass.json` as a starting point.

See `prompts/homelab-toriyama.json` in the repo for the full working example that produced the `homelab-2nd` migration header.

## Queue design

- Jobs live in a SQLite database (`jobs.db` by default) with statuses: `pending`, `running`, `done`, `failed`.
- The worker picks the oldest pending job, marks it `running`, runs `sd-cli` under a file lock, then marks it `done` or `failed`.
- Multiple workers can run; extra workers queue politely with `fcntl` locking and log every 30 seconds.
- The queue backend is abstracted behind `SQLiteQueueBackend`. To plug in Turso (or any other backend), implement the same methods and change `QueueBackend = SQLiteQueueBackend` in `ideogram4_local.py`.

## macOS launchd auto-start and crash restart

The LaunchAgent at `~/Library/LaunchAgents/com.gulasz101.ideogram4-local.worker.plist` keeps the worker alive:
- `RunAtLoad` → starts at login.
- `KeepAlive.Crashed` → restarts if it crashes.
- `ThrottleInterval` → prevents crash loops.

Load:

```bash
launchctl unload ~/Library/LaunchAgents/com.gulasz101.ideogram4-local.worker.plist 2>/dev/null || true
launchctl load ~/Library/LaunchAgents/com.gulasz101.ideogram4-local.worker.plist
launchctl list | grep com.gulasz101.ideogram4-local.worker
```

Unload:

```bash
launchctl unload ~/Library/LaunchAgents/com.gulasz101.ideogram4-local.worker.plist
```

See `references/launchd-agent.md` for the full plist and environment variables.

## Mattermost progress watchdog

A Hermes cron job checks the queue every 5 minutes and posts to the dedicated channel:
- Emoji-rich progress updates when jobs are `running` or `pending`.
- A 🎉 completion message **with the finished image attached** when a job becomes `done`.
- Silent when idle, but keeps polling so it catches future jobs.

The implementation is `post_status.sh` in the repo. It uses the existing `MATTERMOST_TOKEN` and `MATTERMOST_URL` from the andrzej profile `.env` and posts directly via the Mattermost REST API. This avoids two Hermes gateway limitations:
1. `hermes send`/`cron deliver: mattermost:` cannot target a channel the gateway has not yet learned, and falls back to the home channel.
2. Cron responses with `MEDIA:` do not reliably attach local files.

See `references/mattermost-watchdog.md` for the original setup.
See `references/mattermost-channel-delivery.md` for the exact gotcha about making a new channel reachable and the API calls that work.

## Worker options

- **Default:** continuous poll with a 24-hour queue timeout.
- **One-shot:** `python3 ideogram4_local.py worker --one-shot`
- **No-wait/fail-fast:** `python3 ideogram4_local.py worker --no-wait`
- **Change timeout:** `python3 ideogram4_local.py worker --queue-timeout 1800`

## Performance expectations

On M1 Max with CPU offloading:
- 1216×832 image, 20 default steps
- **~21 minutes per image**

A queue of 3 images will keep the machine busy for over an hour. Do not expect instant results.

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `SD_CPP_DIR` | `~/sd.cpp` | Path to built stable-diffusion.cpp |
| `IDEOGRAM4_MODELS_DIR` | `~/sd.cpp-models` | Model download/lookup directory |
| `IDEOGRAM4_OUTPUT_DIR` | `./output` | Default output directory |
| `IDEOGRAM4_LOCK_FILE` | `./.lock` | Worker lock file path |
| `IDEOGRAM4_DB` | `./jobs.db` | SQLite queue database path |
| `IDEOGRAM4_SAFETY_BYPASS` | unset | Set to `1` to enable the safety-filter workaround on every generation |

## Pitfalls / lessons learned

1. **Always set `IDEOGRAM4_MODELS_DIR=~/sd.cpp-models`.** The old default `./models` made the worker re-download 10.6 GB of diffusion weights into the repo. The default is now `~/sd.cpp-models`, but always export it explicitly in scripts.
2. **Capture stdout correctly.** The `submit` command prints the job ID to stdout and logs to stderr. Use `JOB_ID=$(python3 ideogram4_local.py submit ... 2>/tmp/log.txt)`.
3. **Do not cancel a running job.** Once `sd-cli` has loaded models, killing it wastes the progress. Either wait for completion or accept the waste.
4. **Load the LaunchAgent after the current generation finishes.** Loading launchd while a manual worker is mid-generation can create lock confusion. Let the manual worker finish, kill it, remove the stale lock, mark the finished job `done` in SQLite if needed, then load the plist.
5. **Cron `MEDIA:` lines do not reliably attach images, and `hermes send` falls back to the home channel.** For a dedicated channel target, use a direct Mattermost API script (`post_status.sh`) that sources `~/.hermes/profiles/andrzej/.env` for `MATTERMOST_TOKEN`/`MATTERMOST_URL`. The file upload endpoint requires `channel_id` as a form field (`-F channel_id=...`), not just the file.
6. **Keep notification state outside the repo.** Put `.notified_done_jobs` under `~/.ideogram4-local/`, not inside the git repo, so it survives repo resets.
7. **Clean up test jobs before handing the queue to Florian.** Remove any accidental test submissions with `DELETE FROM jobs WHERE id='...';` so the first real job starts immediately.
8. **Verify the target channel is visible to the Mattermost bot account before relying on it.** `hermes send --list mattermost` shows the channels the gateway currently knows; if the new channel is absent, either have the bot user added to the channel or post a test message there so the gateway learns it.
9. **Safety bypass is built in, not bolted on.** Set `IDEOGRAM4_SAFETY_BYPASS=1` or add `"generation": {"safety_bypass": true}` to the JSON prompt. No agent CLI changes are needed. Use `two_pass` for persistent grey-outs; it costs roughly 2× generation time on the M1 Max. Use `single_pass` as a cheap desensitizer for borderline false positives.
10. **The filter watches your words, not your pixels.** The grey box is triggered by prompt vocabulary and JSON structure, not by the generated image. Use canonical JSON, avoid naming flagged garments/anatomy/situations, and describe the scene/location/mood instead. `python3 ideogram4_local.py lint` and `python3 ideogram4_local.py rewrite` help catch and fix risky prompts before generation.

## Safety filter grey-out workaround

Ideogram 4's local GGUF build can grey-out images with a "blocked by safety filter" message, even for ordinary prompts. The grey box is **primarily a prompt-vocabulary and JSON-structure filter baked into the weights**, not a pixel-level classifier. The fix starts with prompt hygiene; sampler workarounds are secondary.

### First, lint and rewrite the prompt

```bash
python3 ideogram4_local.py lint prompts/my-scene.json
python3 ideogram4_local.py rewrite prompts/my-scene.json -o prompts/my-scene-safe.json
```

### Prompt hygiene rules

- Use **canonical structured JSON** with `high_level_description`, `style_description`, and `compositional_deconstruction`.
- **Describe the situation, not the garment/anatomy/state.**
  - Instead of `"a woman in a bikini"` → `"a cheerful young woman having fun at the beach on a sunny day"`.
  - Instead of `"an unclothed adult human figure"` → `"a classical marble statue of a standing human figure in an art studio"`.
- Avoid flagged vocabulary in any text field.

### Backend workarounds (when prompt hygiene is not enough)

Enable globally:

```bash
export IDEOGRAM4_SAFETY_BYPASS=1
```

Or per-prompt in the JSON:

```json
{
  "high_level_description": "...",
  "style_description": { ... },
  "compositional_deconstruction": { ... },
  "generation": {
    "safety_bypass": true,
    "safety_bypass_mode": "two_pass",
    "safety_bypass_steps": 4,
    "safety_bypass_cfg": 1.0,
    "steps": 20
  }
}
```

Modes:

- `"two_pass"` (default): neutral prompt first pass → img2img second pass. Most reliable, ~2× time.
- `"single_pass"`: one generation with `guidance_schedule=1.0x4+7.0x16`. Cheaper, weaker.

See `references/ideogram4-safety-filter.md` for full details, tuning, and the underlying `guidance_schedule` syntax.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `sd-cli not found` | Build stable-diffusion.cpp or set `SD_CPP_DIR` |
| OOM / system hang | Make sure only one worker is generating at a time |
| Garbled text | Use structured JSON prompts and describe text elements explicitly |
| Job stays `pending` | Start the worker or check the LaunchAgent |
| Job stuck `running` but worker is dead | Mark it `done`/`failed` manually in SQLite, or delete the row if it actually finished |
| Queue times out | Increase `--queue-timeout` or wait for the current generation |
| launchd service not listed | Use `launchctl bootstrap gui/$(id -u) ...` on newer macOS |
| Cron post has no image or lands in wrong channel | Use direct Mattermost API script; see `references/mattermost-channel-delivery.md` |

## References

- Wrapper repo: https://github.com/gulasz101/ideogram4-local
- `templates/prompt-with-safety-bypass.json` — ready-to-use JSON prompt with the safety bypass block
- `scripts/verify-safety-bypass.sh` — smoke test that confirms the guidance schedule is injected
- `references/launchd-agent.md` — LaunchAgent plist details and migration from a manual worker
- `references/mattermost-watchdog.md` — Hermes cron watchdog prompt, `MEDIA:` limitation, and bot-token image-attachment fallback
- `references/mattermost-channel-delivery.md` — How to make a new Mattermost channel reachable to the bot and the exact API calls that work
- `references/queue-db-recipes.md` — SQLite snippets for cleaning up stuck `running` rows and test jobs
- `references/ideogram4-safety-filter.md` — Safety-filter grey-out workaround and CFG schedule tuning
- Ideogram 4 (official): https://github.com/ideogram-oss/ideogram4
- leejet GGUF weights: https://huggingface.co/leejet/ideogram-4-GGUF
- stable-diffusion.cpp: https://github.com/leejet/stable-diffusion.cpp
- Qwen3-VL GGUF: https://huggingface.co/unsloth/Qwen3-VL-8B-Instruct-GGUF
