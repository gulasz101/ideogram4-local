# ideogram4-local

A small, reusable, singleton-wrapped local image generator using **Ideogram 4** via [stable-diffusion.cpp](https://github.com/leejet/stable-diffusion.cpp). Built for an Apple Silicon M1 Max with 32 GB unified RAM.

## Why this exists

The [Ideogram 4 open-weights release](https://github.com/ideogram-oss/ideogram4) is extremely good at:
- **Structured JSON prompts** with per-area descriptions.
- **Readable in-image text**.
- **Compositional control**.

Running it locally avoids API credits, keeps prompts private, and turns the M1 Max into a blog-header factory. The wrapper prevents concurrent runs from OOM-killing the machine.

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

## Generate the default homelab header

```bash
./generate-header.sh
```

Output: `output/homelab-toriyama-ideogram4-header.png`

## Generate with a custom JSON prompt

```bash
python3 ideogram4_local.py \
  --prompt-json prompts/my-scene.json \
  -o output/my-image.png \
  -W 1216 -H 832 -v
```

## Generate with a plain text prompt

```bash
python3 ideogram4_local.py \
  --prompt "a red dragon flying over a cyberpunk city" \
  -o output/dragon.png \
  -W 1024 -H 1024 -v
```

Plain text works, but structured JSON gives far better control over composition and text.

## Singleton lock

Ideogram 4 is memory-hungry. `ideogram4_local.py` uses a file lock (`ideogram4-local/.lock` by default) so only one generation runs at a time. If another agent tries to run it while one is already generating, it gets a clear error:

```
RuntimeError: Another Ideogram 4 generation is already running ...
```

To override (dangerous on M1 Max):

```bash
python3 ideogram4_local.py --skip-lock ...
```

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `SD_CPP_DIR` | `~/sd.cpp` | Path to built stable-diffusion.cpp |
| `IDEOGRAM4_MODELS_DIR` | `./models` | Where to download/look for model files |
| `IDEOGRAM4_OUTPUT_DIR` | `./output` | Default output directory |
| `IDEOGRAM4_LOCK_FILE` | `./.lock` | Singleton lock file path |

## JSON prompt structure

Ideogram 4 is trained on structured JSON captions. The wrapper passes the JSON straight through to `sd-cli`. The canonical shape is:

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

See `prompts/homelab-toriyama.json` for a full working example.

## Expected generation time

On an M1 Max with CPU offloading:
- 1216×832 image, 20 default steps
- **~21 minutes per image**

It is slow, but reliable and fully local. GPU/Metal acceleration may come later in `stable-diffusion.cpp`.

## Troubleshooting

### `sd-cli not found`

Build stable-diffusion.cpp or set `SD_CPP_DIR`.

### OOM / system hang

Make sure you are not running another generation concurrently. Check Activity Monitor. The wrapper normally prevents this; use `--skip-lock` only if you are certain nothing else is running.

### Garbled text labels

Use structured JSON prompts and be very explicit in the `text` element descriptions. If text still fails, try increasing resolution or regenerating with a different seed.

## License

The code in this repository is MIT-licensed. Model files follow their original licenses (Ideogram 4 Non-Commercial for the base weights).
