> **Agent note:** This repo ships an embedded Hermes skill under [`skill/`](./skill). Load it with `skill_view(name="ideogram4-local")` (if installed) or read `skill/SKILL.md` directly. The skill contains ready-to-use templates, reference docs, and scripts for agents.

# ideogram4-local

A small, reusable, queue-backed local image generator using **Ideogram 4** via [stable-diffusion.cpp](https://github.com/leejet/stable-diffusion.cpp). Built for an Apple Silicon M1 Max with 32 GB unified RAM.

> **Agents:** this repo also ships a Hermes skill. Load it with `skill_view(name="ideogram4-local")` for the established prompt schema, safety-filter workarounds, and verified templates. The skill and the repo are kept in sync.

## Why this exists

The [Ideogram 4 open-weights release](https://github.com/ideogram-oss/ideogram4) is extremely good at:
- **Structured JSON prompts** with per-area descriptions.
- **Readable in-image text**.
- **Compositional control**.

Running it locally avoids API credits, keeps prompts private, and turns the M1 Max into a blog-header factory. Because Ideogram 4 loads ~16 GB of model weights, only one generation can run at a time. This repo wraps generation in an **SQLite-backed job queue** with a file-lock worker so multiple Hermes agents can submit jobs without OOM-ing the machine.

## Hardware assumptions

- Apple Silicon Mac (M1 Max 32 GB is what this was tested on).
- ~16 GB of free RAM at idle.
- Enough disk space for ~16 GB of model files.

## Requirements

- Python 3
- `wget`
- A built copy of `stable-diffusion.cpp` at `~/sd.cpp` (or set `SD_CPP_DIR`)

## Model files (downloaded automatically on first run)

| File | Size | Source |
|---|---|---|
| `ideogram4-Q4_0.gguf` | ~5.3 GB | `leejet/ideogram-4-GGUF` |
| `ideogram4_uncond-Q4_0.gguf` | ~5.3 GB | `leejet/ideogram-4-GGUF` |
| `Qwen3-VL-8B-Instruct-Q4_K_M.gguf` | ~4.7 GB | `unsloth/Qwen3-VL-8B-Instruct-GGUF` |
| `Qwen3-VL-8B-Heretic-1.3.0-Q4_K_M.gguf` | ~4.7 GB | `DreamFast/Qwen3-VL-8B-Heretic-1.3.0` |
| `Qwen3VL-8B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf` | ~4.7 GB | `HauhauCS/Qwen3VL-8B-Uncensored-HauhauCS-Aggressive` |
| `flux2-vae.safetensors` | ~321 MB | `Comfy-Org/flux2-dev` |

Total with the default instruct LLM: ~15.6 GB. Total if you also keep all three LLM variants: ~25.0 GB.

## Build stable-diffusion.cpp

```bash
cd ~
git clone --recursive https://github.com/leejet/stable-diffusion.cpp.git sd.cpp
cd sd.cpp
mkdir -p build && cd build
cmake .. -DSD_WEBP=OFF -DSD_WEBM=OFF
cmake --build . --config Release -j$(sysctl -n hw.ncpu)
```

Expected result: `~/sd.cpp/build/bin/sd-cli`.

## Install this repo

```bash
git clone https://github.com/gulasz101/ideogram4-local.git
cd ideogram4-local
python3 ideogram4_local.py --help
```

## Submit the default homelab header job

```bash
./generate-header.sh
```

This prints a `job_id` like `aB3dEf4...` and puts it in the queue.

## Run the worker

The worker holds the file lock and processes jobs one at a time:

```bash
# Run until interrupted, continuously polling for new jobs
python3 ideogram4_local.py worker

# Or process one pending job and exit
python3 ideogram4_local.py worker --one-shot
```

The worker uses `fcntl` file locking so only one instance actually generates images. If two agents both start workers, one queues politely and waits.

## Check job status

```bash
python3 ideogram4_local.py status <job-id>
```

## List recent jobs

```bash
python3 ideogram4_local.py list
```

## Wait for a job and get its output path

```bash
python3 ideogram4_local.py wait <job-id>
```

Typical output when done: a full path like `/Users/wojtek/git/ideogram4-local/output/.../homelab-toriyama-ideogram4-header.png`.

## Submit a custom JSON prompt

```bash
JOB_ID=$(python3 ideogram4_local.py submit \
  --prompt-json prompts/my-scene.json \
  -o output/my-image.png \
  -W 1216 -H 832 -v)

python3 ideogram4_local.py wait "$JOB_ID"
```

## Submit a plain text prompt

```bash
JOB_ID=$(python3 ideogram4_local.py submit \
  --prompt "a red dragon flying over a cyberpunk city" \
  -o output/dragon.png \
  -W 1024 -H 1024 -v)

python3 ideogram4_local.py wait "$JOB_ID"
```

Plain text works, but structured JSON gives far better control over composition and text.

## JSON prompt structure

Ideogram 4 is trained on a specific structured JSON caption schema. The wrapper passes the JSON verbatim to `sd-cli`, but it also **auto-canonicalizes** every JSON prompt on submit: it drops unknown keys like `canvas`/`layout`, reorders fields to the trained order, and preserves the wrapper-only `"generation"` block.

The canonical shape is:

```json
{
  "high_level_description": "overall scene summary",
  "style_description": {
    "aesthetics": "...",
    "lighting": "...",
    "medium": "...",
    "art_style": "...",
    "color_palette": ["#FF6B00", "#00D4FF"]
  },
  "compositional_deconstruction": {
    "background": "...",
    "elements": [
      {
        "type": "obj",
        "bbox": [y1, x1, y2, x2],
        "desc": "a mechanic installing a server"
      },
      {
        "type": "text",
        "bbox": [y1, x1, y2, x2],
        "text": "homelab-2nd",
        "desc": "exact text on a sign"
      }
    ]
  }
}
```

Key schema rules:

- Only three top-level keys are passed to the model: `high_level_description`, `style_description`, `compositional_deconstruction`.
- `style_description` must contain **exactly one** of `photo` or `art_style`.
  - Use `photo` for photographic prompts.
  - Use `art_style` for illustrations, cartoons, 3D renders, vector art.
- `compositional_deconstruction` must contain only `background` and `elements`.
- Each element needs `type` (`obj` or `text`).
- `bbox` is `[y1, x1, y2, x2]` normalized to `[0, 1000]`.
- `canvas` and `layout` are **not** in the trained schema — the wrapper strips them automatically, but it is better not to include them.

See `templates/prompt-blog-gitops-header.json` and `templates/prompt-blog-observability-header.json` for ready-to-use examples.

## How the queue works

- Jobs are stored in a SQLite database (`jobs.db` by default).
- Each job has a unique `id`, `status` (`pending`/`running`/`done`/`failed`), prompt/output metadata, and timestamps.
- The worker acquires a file lock (`.lock`) and processes one job at a time.
- If another worker is already generating, a second worker will **queue politely** and log every 30 seconds.
- Because only one generation runs, the M1 Max does not OOM from loading ~16 GB of weights twice.

### Queue/lock options

- **Default worker:** queue and wait up to `--queue-timeout` seconds (default 3600).
- **Fail immediately:** `python3 ideogram4_local.py worker --no-wait`
- **One-shot worker:** `python3 ideogram4_local.py worker --one-shot`
- **Change timeout:** `python3 ideogram4_local.py worker --queue-timeout 1800`

## Queue backend abstraction

The queue is implemented via a `QueueBackend` class. The default backend is **SQLite** (`SQLiteQueueBackend`). The class can be swapped for another backend (e.g. Turso) by changing the line:

```python
QueueBackend = SQLiteQueueBackend
```

and implementing the same methods (`submit`, `next_pending`, `get`, `list_jobs`, `update_status`). This keeps the door open for a Rust/Turso backend later without touching the worker logic.

## Performance expectations

On an M1 Max with CPU offloading:
- 1216×832 image, 20 default steps
- **~21 minutes per image**

Plan accordingly. A small queue of 3 images will keep the machine busy for over an hour.

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `SD_CPP_DIR` | `~/sd.cpp` | Path to built stable-diffusion.cpp |
| `IDEOGRAM4_MODELS_DIR` | `~/sd.cpp-models` | Model download/lookup directory |
| `IDEOGRAM4_OUTPUT_DIR` | `./output` | Default output directory |
| `IDEOGRAM4_LOCK_FILE` | `./.lock` | Worker lock file path |
| `IDEOGRAM4_DB` | `./jobs.db` | SQLite queue database path |
| `IDEOGRAM4_SAFETY_BYPASS` | unset | Set to `1` to enable the safety-filter backend workaround on every generation |

## Swapping the text encoder / VLM

`sd-cli` uses a Qwen3-VL GGUF as the `--llm` text encoder for Ideogram 4. The default is the stock `unsloth/Qwen3-VL-8B-Instruct-Q4_K_M.gguf`. You can swap in the abliterated `DreamFast/Qwen3-VL-8B-Heretic-1.3.0-Q4_K_M.gguf` model to reduce the baked-in prompt-refusal attractor that causes false-positive "blocked by safety filter" grey boxes.

This is a **local-only, drop-in model swap** — not a separate review stage, not an internet-exposed service, and easy to reverse.

### Enable Heretic globally

```bash
export IDEOGRAM4_LLM_MODEL=heretic
```

Or set it in the LaunchAgent environment block (`~/Library/LaunchAgents/com.gulasz101.ideogram4-local.worker.plist`) and restart the worker.

### Enable Heretic per job

Add to the JSON prompt's optional `generation` block:

```json
{
  "high_level_description": "...",
  "style_description": { ... },
  "compositional_deconstruction": { ... },
  "generation": {
    "llm_model": "heretic"
  }
}
```

Valid values are `"aggressive"` (HauhauCS uncensored, strongest anti-false-positive), `"heretic"` (DreamFast Heretic, milder), and `"instruct"` (unsloth, default).

### Recommended default

For real-world use — especially blog headers that may contain people, casual scenes, or clothing context — set the worker to `"aggressive"`. It is the only encoder we have found that lets situation-based prompts render instead of greying out.

### Switch back to the safe model

```bash
export IDEOGRAM4_LLM_MODEL=instruct
```

or set `generation.llm_model: "instruct"` per prompt.

## Safety filter grey-out workaround

Ideogram 4's local GGUF build can grey-out images with a "blocked by safety filter" message, sometimes even on ordinary prompts. The grey box is **primarily a prompt-vocabulary and JSON-structure filter baked into the model weights**, not a pixel-level classifier. Start with prompt hygiene; sampler workarounds are secondary.

### First, lint and rewrite the prompt

The wrapper now ships `lint` and `rewrite` commands:

```bash
python3 ideogram4_local.py lint prompts/my-scene.json
python3 ideogram4_local.py rewrite prompts/my-scene.json -o prompts/my-scene-safe.json
```

### Prompt hygiene rules

- Use **canonical structured JSON** with exactly these top-level keys:
  - `high_level_description`
  - `style_description`
  - `compositional_deconstruction`
- In `style_description`, use **exactly one** of `photo` or `art_style`:
  - `photo` for photographic prompts.
  - `art_style` for illustrations, cartoons, vector art, 3D renders.
- In `compositional_deconstruction`, use only `background` and `elements`.
- Use **bboxes** for important elements. Format is `[y1, x1, y2, x2]` normalized to `[0, 1000]`.
- **Do not use `canvas` or `layout`.** The wrapper strips them, but they drift the model off-distribution.
- Describe the situation, not the garment/anatomy/state.
  - Instead of `"a woman in a bikini"` → `"a cheerful young woman having fun at the beach on a sunny summer day"`.
  - Instead of `"an unclothed adult human figure"` → `"a classical marble statue of a standing human figure in an art studio"`.
- Avoid flagged vocabulary in any text field.
- Use the **HauhauCS Aggressive encoder** (`IDEOGRAM4_LLM_MODEL=aggressive` or `generation.llm_model: "aggressive"`). In our tests the default Instruct encoder and the DreamFast Heretic encoder still greyed out the same situation-based beach prompt; only the aggressive encoder rendered it.

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
- `"single_pass"`: one generation with the official Ideogram 4 `V4_DEFAULT_20` guidance schedule. For 20 steps this is `7.0x18+3.0x2` — high CFG for the main denoise, low CFG for the last two polish steps. This matches the trained preset rather than inventing a backwards schedule.

All keys in `"generation"` are optional. The wrapper strips the block before passing JSON to `sd-cli`, so agents do not need to change CLI commands.

## Testing the safety layer with a false-positive prompt

A good canary is a harmless summer/beach scene that uses vocabulary the filter often misreads. Use `prompts/test-beach-minimal.json` — it is the sparse, situation-based prompt that actually rendered in our tests:

```bash
python3 ideogram4_local.py submit \
  --prompt-json prompts/test-beach-minimal.json \
  -o output/test-beach-minimal-aggressive.png -W 832 -H 1216 -v
```

For comparison, the same prompt with the default Instruct encoder or the DreamFast Heretic encoder still greys out. With the worker set to `"aggressive"`, the above renders a clean beach scene.

You can also run an A/B comparison with different encoders:

```bash
# Instruct baseline (default)
JOB_BASE=$(IDEOGRAM4_LLM_MODEL=instruct python3 ideogram4_local.py submit \
  --prompt-json prompts/test-beach-minimal.json \
  -o output/test-beach-instruct.png -W 832 -H 1216 -v)

# HauhauCS Aggressive variant
JOB_AGGRESSIVE=$(IDEOGRAM4_LLM_MODEL=aggressive python3 ideogram4_local.py submit \
  --prompt-json prompts/test-beach-minimal.json \
  -o output/test-beach-aggressive.png -W 832 -H 1216 -v)
```

Then wait and inspect. In our testing only the aggressive encoder produced a clean image.

See `references/ideogram4-safety-filter.md` for full details, tuning, and the underlying `guidance_schedule` syntax.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `sd-cli not found` | Build stable-diffusion.cpp or set `SD_CPP_DIR` |
| OOM / system hang | Make sure only one worker is generating; check Activity Monitor |
| Garbled text | Use structured JSON prompts and describe text elements explicitly |
| Job stays `pending` | Start the worker: `python3 ideogram4_local.py worker` |
| First download 404 for Qwen3VL | The correct filename is `Qwen3-VL-8B-Instruct-Q4_K_M.gguf` (with dash) |

## License

The code in this repository is MIT-licensed. Model files follow their original licenses (Ideogram 4 Non-Commercial for the base weights).
