# Ideogram 4 safety filter grey-out workaround

## Symptom

Local Ideogram 4 generations via `stable-diffusion.cpp` come out greyed out with a "blocked by safety filter" overlay, sometimes even on ordinary blog/tech prompts.

## Why it happens

The safety filter in the Ideogram 4 GGUF build seems to fire during the **early denoising steps**. The proven workaround (from the ComfyUI community) is to make those first few steps use a low CFG so the unconditional model dominates and the full prompt does not hit the safety classifier early.

## Important baseline check

The wrapper already passes `--uncond-diffusion-model ideogram4_uncond-Q4_0.gguf`, so the dual-model setup is present. If the filter triggers, the issue is **how sampling runs**, not missing files.

## How the wrapper now handles it

The backend applies a **CFG guidance schedule** via `sd-cli --extra-sample-args guidance_schedule=...`. This is a single-pass fix: **no img2img, no second model load, no 2× generation time penalty**. It is implemented entirely inside `ideogram4_local.py` and is transparent to agents using the queue.

### Default behavior

With safety bypass enabled, the first **3 of 20 steps** run at CFG `1.0`; the remaining **17 steps** run at the normal CFG `7.0`.

`sd-cli` logs this when verbose mode is on:

```
[DEBUG] stable-diffusion.cpp:1992 - using guidance schedule: [1.000000, 1.000000, 7.000000, 7.000000, 7.000000]
```

### Enable globally

Set the environment variable before submitting or before the worker runs:

```bash
export IDEOGRAM4_SAFETY_BYPASS=1
```

When this is set, **every** generation gets the workaround schedule unless a per-prompt config explicitly disables it.

### Enable per prompt (JSON)

Add a top-level `"generation"` block to the prompt JSON. This is the preferred way for an agent to opt in without changing CLI commands:

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

All keys are optional:

| Key | Default | Purpose |
|---|---|---|
| `safety_bypass` | `false` (or env default) | Enable/disable the workaround for this job |
| `steps` | 20 | Total denoising steps |
| `safety_bypass_steps` | 3 | Number of early steps to run at low CFG |
| `safety_bypass_cfg` | 1.0 | CFG value to use during the early steps |
| `guidance_schedule` | auto | Override the whole schedule, e.g. `"1.0x3+7.0x17"` |

The wrapper strips the `"generation"` block before passing the JSON to `sd-cli`, so the model never sees metadata it does not understand.

### Disable for one job even when env var is on

```json
{
  "generation": {
    "safety_bypass": false
  }
}
```

## The guidance schedule syntax

The underlying `sd-cli` parser expects `<cfg>x<count>` segments joined by `+`. Examples:

- `"1.0x3+7.0x17"` — first 3 steps at CFG 1.0, last 17 at CFG 7.0.
- `"1.5x4+6.5x16"` — first 4 steps at CFG 1.5, last 16 at CFG 6.5.

If you set `"guidance_schedule"` explicitly in the JSON, it is passed verbatim and the `safety_bypass_steps`/`safety_bypass_cfg` defaults are ignored.

## When to use this

- You get greyed-out images on otherwise safe blog/tech prompts.
- You want a transparent single-pass fix with no agent CLI changes.

## When not to use this

- If the prompt itself is genuinely NSFW or policy-violating. This workaround is for **over-sensitive local filters on legitimate content**, not for bypassing safety guardrails on harmful prompts.

## Trade-offs

- Slightly softer early guidance may subtly change image composition. If quality degrades, try `safety_bypass_steps: 2` or `safety_bypass_cfg: 1.5`.
- It is single-pass, so generation time stays the same as before.

## External references

- Reddit ComfyUI discussion: https://www.reddit.com/r/comfyui/comments/1txurpt/ideogram4_get_through_the_safety_filter/
- Tools4All summary (sigma-shift / increased initial noise): https://tools4all.ai/trends/workaround-discovered-to-bypass-ideogram-4-censorship-blocks
- `stable-diffusion.cpp` Ideogram 4 docs: https://github.com/leejet/stable-diffusion.cpp/blob/master/docs/ideogram4.md
- `stable-diffusion.cpp` guidance schedule parser: `src/runtime/guidance.cpp`
