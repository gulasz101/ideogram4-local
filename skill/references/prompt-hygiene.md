# Ideogram 4 prompt hygiene

Session: 2026-07-02 safety-filter investigation.

## Finding

The Ideogram 4 local GGUF grey box ("Image blocked by safety filter") is primarily a prompt-vocabulary and JSON-structure filter baked into the model weights, not a pixel-level classifier. Community experiments on r/StableDiffusion showed that plain text or non-canonical JSON drifts off-distribution, and naming flagged garments/anatomy/situations flips the safety attractor even for harmless scenes.

## Fix hierarchy

1. **Prompt hygiene first.** Rewrite the prompt to use sparse canonical JSON and describe situation/location/mood rather than naming items. Keep only `high_level_description`, `style_description`, `background`, and 1-3 `elements`. Drop `canvas` and `layout` fields; dense structured prompts can drift off-distribution.
2. **Encoder swap second.** Set `IDEOGRAM4_LLM_MODEL=aggressive` (HauhauCS) or `generation.llm_model: "aggressive"`. In our 2026-07-06 A/B tests, only the aggressive encoder rendered a clean image, and only with a sparse prompt.
3. **Sampler workarounds third.** If a clean prompt + aggressive encoder still greys out, enable `two_pass` (neutral-prompt first pass + img2img second pass) or the cheaper `single_pass` CFG schedule.

## Canonical JSON shape (schema-compliant)

```json
{
  "high_level_description": "one-line situation / persona",
  "style_description": {
    "aesthetics": "...",
    "lighting": "...",
    "medium": "...",
    "art_style": "...",
    "color_palette": ["#..."]
  },
  "compositional_deconstruction": {
    "background": "...",
    "elements": [
      {"type": "obj", "bbox": [y1, x1, y2, x2], "desc": "situation-based description, no clothing/anatomy nouns"}
    ]
  }
}
```

The exact schema is documented in `references/ideogram4-oss-schema.md`. The key rules from the official `ideogram-oss/ideogram4` code:

- Only three top-level keys in order: `high_level_description`, `style_description`, `compositional_deconstruction`.
- `style_description` must contain exactly one of `photo` (for photos) or `art_style` (for illustrations/renders/design), plus optional `aesthetics`, `lighting`, `medium`, `color_palette`.
- `compositional_deconstruction` must contain exactly `background` and `elements`.
- `canvas` and `layout` are **not** in the schema and should be removed.
- Use bboxes for important, individually placeable elements; omit them for dense unplaceable groups like crowds or starry skies.

The older dense shape with `canvas`/`layout`/many elements was a community experiment, but the official verifier rejects those keys.

## Reframing examples

| Risky | Safer |
|---|---|
| a woman in a bikini | a cheerful young woman having fun at the beach on a sunny day |
| an unclothed adult human figure | a classical marble statue of a standing human figure in an art studio |
| blood on the floor | a red hydraulic fluid spill on the datacenter floor |

## Tooling

The repo ships `ideogram4_prompt_tools.py` and `ideogram4_local.py lint`/`rewrite` commands:

```bash
python3 ideogram4_local.py lint prompts/my-scene.json
python3 ideogram4_local.py rewrite prompts/my-scene.json -o prompts/my-scene-safe.json
```

The linter returns a risk score and flags explicit garment/anatomy/situation/violence terms plus **density risk** (`canvas`/`layout` or many elements). The rewriter applies whole-phrase reframes, masks remaining flagged words, and now drops `canvas`/`layout` fields. It preserves canonical JSON structure when present.

## Sampler fallbacks

If prompt hygiene alone is not enough, add a `"generation"` block to the JSON:

```json
{
  "generation": {
    "safety_bypass": true,
    "safety_bypass_mode": "two_pass",
    "safety_bypass_steps": 4,
    "safety_bypass_cfg": 1.0,
    "steps": 20
  }
}
```

The wrapper strips this block before passing JSON to `sd-cli`. Modes:

- `two_pass` (default): neutral first pass → img2img second pass. ~2× generation time on M1 Max.
- `single_pass`: one pass with `--extra-sample-args guidance_schedule=1.0xN+7.0x(steps-N)`. Cheaper, weaker.

See `references/ideogram4-safety-filter.md` for backend details.

## Lesson

For this user, always try prompt hygiene first. Only fall back to `two_pass`/`single_pass` for persistent false positives on otherwise safe prompts. Do not rely on sampler tricks to bypass the actual safety guardrail on genuinely policy-violating prompts.
