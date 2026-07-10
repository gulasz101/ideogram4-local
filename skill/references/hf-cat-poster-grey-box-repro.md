# Hugging Face "cat fashion poster" prompt — local GGUF reproduction

## Context

The official Hugging Face page for `ideogram-4-GGUF` includes an example structured JSON prompt that describes a luxury fashion-magazine cover with a chubby cat wearing sunglasses and a red scarf, plus text elements (`LOOK WHAT I FOUND`, `ideogram4.cpp`, `tiny paws, big compile energy`).

When that exact prompt is run through the local `stable-diffusion.cpp` GGUF build on Apple Silicon, it does not render. Instead it produces a flat grey image with the text **"Image blocked by safety filter."**

This document records the exact reproduction so future sessions do not waste time assuming the prompt is safe or that the filter is stochastic.

## Environment

- Host: Apple M1 Max, 32 GB unified RAM, macOS.
- `sd-cli`: leejet/stable-diffusion.cpp built at `~/sd.cpp`.
- Diffusion: `ideogram4-Q4_0.gguf` + `ideogram4_uncond-Q4_0.gguf`.
- VAE: `flux2-vae.safetensors`.
- Text encoder: `Qwen3VL-8B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf` (the "aggressive" uncensored swap).
- Generation: 1024×1024, 20 steps, `--offload-to-cpu`, `--diffusion-fa`.
- Safety bypass: `two_pass` (4 neutral steps at CFG 1.0, then 16 img2img steps at CFG 7.0).

## Reproduction

1. Submit the exact JSON prompt from the HF page through the queue:

```bash
cd ~/git/ideogram4-local
export IDEOGRAM4_MODELS_DIR=~/sd.cpp-models

python3 ideogram4_local.py submit \
  --prompt-json prompts/hf-cat-fashion-poster.json \
  -o output/hf-cat-poster-repro.png \
  -W 1024 -H 1024 -v
```

2. Run the worker (or wait for the launchd worker):

```bash
python3 ideogram4_local.py worker --one-shot
```

3. Result (reproduced twice, same 310289-byte output both times):

- Job status: `done`.
- Output file: generated PNG, 1024×1024.
- Visual content: solid grey rectangle with centered text **"Image blocked by safety filter."**
- No cat, no sunglasses, no nameplate, no rendered text.

## What does and does not matter

- The safety filter is **deterministic for this prompt structure**, not random.
- The `aggressive` uncensored encoder **does not rescue** this prompt.
- The `two_pass` safety bypass **does not rescue** this prompt.
- The issue is almost certainly prompt vocabulary / JSON structure, not pixel content. Likely triggers include:
  - dense `compositional_deconstruction` with both `canvas` and `layout` fields,
  - multiple explicit `"type": "text"` elements,
  - fashion/photography terminology (`luxury fashion magazine cover`, `pet couture`, `high-end`, `model`, `body`, `neck`, `collar`, etc.),
  - words that describe garments/accessories on an animal (`silk scarf`, `sunglasses`, `collar charm`).

## Working contrast

Earlier successful cat images in the same queue used:

- No `canvas` or `layout` fields.
- 1–3 sparse `"type": "obj"` elements.
- No explicit `"type": "text"` elements.
- Situation-based descriptions rather than garment/anatomy nouns.

See `prompts/homelab-toriyama.json` and the earlier `look-what-i-found` jobs in the queue DB for examples.

## Recommended next tests

If you still want this visual, try one change at a time:

1. Strip `canvas` and `layout` entirely.
2. Remove the top headline and footer text elements; keep only the nameplate.
3. Replace accessory nouns (`silk scarf`, `sunglasses`, `collar charm`) with situation phrases (`a stylish cat at a fashion shoot, surrounded by soft studio props`).
4. Remove all text elements and plan to overlay text in an image editor afterward.

## Takeaway

The local GGUF build of Ideogram 4 ships with a baked-in prompt-structure safety attractor that is far more aggressive than the hosted Ideogram 4 API. A prompt that works on the Hugging Face demo page is **not guaranteed** to work locally. Always test locally with the queue and expect to iterate on prompt hygiene.
