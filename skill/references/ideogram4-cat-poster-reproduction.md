# Reproduction: Ideogram 4 local GGUF grey-boxes on hosted-HF cat-poster prompts

## What happened

On 2026-07-09, several iterations of a "premium fashion magazine cover" cat poster grey-boxed deterministically, even though the same workflow, encoder, and sampler bypass had rendered clean images earlier in the week.

## Prompts tested (all failed)

All used canonical structured JSON with the `generation` block stripped by the wrapper before reaching `sd-cli`.

| Job | File | Key vocabulary |
|---|---|---|
| `vepV_aC2pJo` | `cat-poster-ideogram4-v3.png` | "luxury fashion magazine cover", "cat as the main model", "red silk scarf", "tiny black sunglasses", "gold collar charm", 9 elements, `canvas`/`layout` blocks |
| `plkvG4xbjeI` | `cat-poster-ideogram4-v4.png` | Same as v3, plus extra text elements and "LOOK WHAT I FOUND" headline |
| `fF6vyl2ExP8` | `cat-poster-ideogram4-v5.png` | Reduced to 6 elements, removed `canvas`/`layout`, but kept "red silk scarf", "tiny black sunglasses", "gold collar charm", and an explicit `"text"` element |
| `EcJh9L2SIeQ` | `look-what-i-found.png` | Brown tabby cat with "black sunglasses", "red bandana", "small shiny gold bell" |
| `_CmO_4lJqjk` | `look-what-i-found-v2.png` | Same scene with "premium product-poster composition" framing |

## Configuration for each failed run

- Diffusion model: `ideogram4-Q4_0.gguf`
- Unconditional model: `ideogram4_uncond-Q4_0.gguf`
- Text encoder: `Qwen3VL-8B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf`
- VAE: `flux2-vae.safetensors`
- Safety bypass: `two_pass`, 4 bypass steps, CFG 1.0
- Resolution: 1024×1024

The wrapper logged `Safety bypass (two_pass): pass 1 complete` for each, then the pass-2 output was the grey "Image blocked by safety filter" box.

## What did not fix it

| Change | Result |
|---|---|
| Swapped encoder to aggressive HauhauCS | Still grey |
| Enabled `two_pass` safety bypass | Still grey |
| Removed `canvas`/`layout` blocks, reduced from 9 to 6 elements | Still grey |
| Removed explicit `"text"` elements except one | Still grey |

## What rendered cleanly the same day

- `homelab-toriyama-ideogram4-header.png` — chibi mechanics, server racks, no fashion, no accessorized animals
- `odoo-rabbitmq-toriyama-header.png` — Goku-like mascot with a sign, no fashion accessories
- Earlier 2026-06-19 blog headers (MinIO, SOPS, Flux, etc.) — robots, server closets, tools

## Conclusion

The local GGUF safety attractor is triggered by a combination of:

1. **Fashion/garment/accessory vocabulary** even when applied to animals (sunglasses, scarf, bandana, collar charm, gold bell)
2. **Human-like fashion framing** ("model", "couture", "editorial", "premium product poster")
3. **Dense canonical JSON** with many `elements` and multiple `"type": "text"` entries (makes it worse, but not the sole cause)

Encoder swaps and two-pass samplers are not enough once the prompt has drifted into this semantic region.

## Recommended action

For tech blog images, avoid the problem entirely: use robots, tools, server rooms, diagrams, and abstract illustrations. If you must use an animal, keep it sparse and do not dress it up or describe garments/accessories.

## Why this matters for hosted-HF comparisons

A prompt that renders on the **hosted Hugging Face Ideogram 4 demo** can still grey-box locally. The local stack is not the same inference pipeline:

| | Hosted HF demo | Local `stable-diffusion.cpp` GGUF |
|---|---|---|
| Safety layer | Separate classifier on generated image | Baked into diffusion weights / prompt embedding attractor |
| Trigger | Actual harmful pixels | Prompt vocabulary + JSON structure |
| Text encoder | Ideogram's own conditioner | Qwen3-VL GGUF (wrapped in `<|im_start|>user\n...` chat template) |
| VAE | Ideogram's own | `flux2-vae.safetensors` |
| Quantization | Full / served | Q4_0 |

Therefore, **do not treat the HF demo as ground truth for local generations.** Test locally with sparse, object/robot/tech prompts; save fashion/animal-accessory ideas for the hosted API.

## References

- Worker log: `~/git/ideogram4-local/output/worker.log` (entries 2026-07-09 20:17–22:20)
- Queue DB: `~/git/ideogram4-local/jobs.db` (jobs listed above)
- Output files: `~/git/ideogram4-local/output/cat-poster-ideogram4-v{3,4,5}.png`, `look-what-i-found.png`, `look-what-i-found-v2.png`
- Barebones reproduction command: see `references/ideogram4-safety-filter.md` for the local sd-cli model paths and flags.
