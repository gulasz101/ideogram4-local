# ideogram4-local

A small, reusable, queue-backed local image generator using **Ideogram 4** via [stable-diffusion.cpp](https://github.com/leejet/stable-diffusion.cpp). Built for an Apple Silicon M1 Max with 32 GB unified RAM.

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
| `flux2-vae.safetensors` | ~321 MB | `Comfy-Org/flux2-dev` |

Total: ~15.6 GB.

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

Ideogram 4 is trained on structured JSON captions. The wrapper passes the JSON verbatim to `sd-cli`. The canonical shape is:

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

See `prompts/homelab-toriyama.json` for the full working example that produced the `homelab-2nd` migration header.

The wrapper also accepts an optional top-level `"generation"` block for backend-only options. It is stripped before the prompt reaches `sd-cli`. See [Safety filter workaround](#safety-filter-grey-out-workaround) below.

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
| `IDEOGRAM4_SAFETY_BYPASS` | unset | Set to `1` to enable the safety-filter CFG schedule on every generation |

## Safety filter grey-out workaround

Ideogram 4's local GGUF build can grey-out images with a "blocked by safety filter" message, even for ordinary prompts. The filter appears to trigger mostly in the early denoising steps. The wrapper already uses `--uncond-diffusion-model ideogram4_uncond-Q4_0.gguf`, so the dual-model setup is present; the fix is about how sampling runs in the first 1–4 steps.

Enable it globally:

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
    "steps": 20,
    "safety_bypass_steps": 3,
    "safety_bypass_cfg": 1.0
  }
}
```

With the defaults above the wrapper passes `--extra-sample-args guidance_schedule=1.0x3+7.0x17`, which tells `sd-cli` to use CFG `1.0` for steps 1–3 and CFG `7.0` for steps 4–20.

All keys are optional. The wrapper strips the `"generation"` block before handing the JSON to `sd-cli`. This keeps the fix transparent to agents that submit jobs.

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
