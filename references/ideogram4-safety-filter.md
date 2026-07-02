# Ideogram 4 safety filter grey-out workaround

## Symptom

Local Ideogram 4 generations via `stable-diffusion.cpp` come out greyed out with a "blocked by safety filter" overlay, sometimes even on ordinary prompts.

## What actually triggers it

Community experiments show the grey box is **not** a pixel-level classifier and **not** a simple early-sampling guardrail. It is baked into the model weights and reacts primarily to **prompt vocabulary and JSON structure**:

- **Plain text or non-canonical JSON** drifts off-distribution and often triggers the placeholder, even for innocent scenes.
- **Naming flagged garments, anatomy, or situations** (bikini, nude, unclothed, erotic, etc.) flips the safety attractor, even when the scene itself is harmless.
- **Describing human figures, statues, anatomy studies, or full-body poses** is also a frequent false-positive trigger in this local GGUF build.
- The model will happily draw context-appropriate content if you describe the **situation, location, mood, and activity** instead of naming the item.

## What we tested

| Test | Prompt | Backend mode | Result |
|---|---|---|---|
| Explicit anatomy reference | "unclothed adult human figure" | `single_pass` CFG schedule | Grey box |
| Explicit anatomy reference | "unclothed adult human figure" | `two_pass` neutral → full | Grey box |
| Rephrased as "classical marble statue" | "classical marble statue..." | `two_pass` | Grey box |
| Tech blog header (racks, Git icons) | `templates/prompt-blog-gitops-header.json` | default (no bypass) | Clean |

Conclusion: the local GGUF safety filter is **prompt-semantics driven** and hard to bypass with sampler tricks. The reliable fix is **prompt hygiene** — avoid human/anatomy/statue vocabulary and use objects, robots, diagrams, or abstract tech illustrations.

## First-line fix: prompt hygiene (use this first)

The repo ships `ideogram4_prompt_tools.py` and `ideogram4_local.py lint`/`rewrite` commands to catch and fix risky prompts before generation.

### Lint a prompt

```bash
python3 ideogram4_local.py lint prompts/my-scene.json
```

### Rewrite a prompt to safer phrasing

```bash
python3 ideogram4_local.py rewrite prompts/my-scene.json -o prompts/my-scene-safe.json
```

### Prompt design rules

1. **Use canonical structured JSON.** Expected top-level keys:
   - `high_level_description`
   - `style_description`
   - `compositional_deconstruction`
2. **Describe the scene, not the garment/anatomy/state.**
   - Instead of `"a woman in a bikini"` → `"a cheerful young woman having fun at the beach on a sunny day"`.
   - Instead of `"an unclothed adult human figure"` → don't use human figures at all; use `"a friendly robot standing in a server room"`.
3. **Avoid flagged vocabulary** in any text field (description, style, elements, background, layout).
4. **Prefer objects, robots, diagrams, and abstract illustrations** for tech blog images. Human/anatomy/stature descriptions grey out frequently in this local build.
5. **Keep it in distribution.** Short, vague, or prose-only prompts are more likely to grey-out.

### Safe templates

Ready-to-use canonical JSON templates for common blog headers:

- `templates/prompt-blog-gitops-header.json` — server racks, Git icons, blue/amber palette.
- `templates/prompt-blog-observability-header.json` — friendly robot at a monitoring console.

Copy and edit them for new posts.

## Backend workarounds (secondary)

When a clean prompt still greys out, the wrapper offers two sampler-level helpers. Both are opt-in and transparent to agents using the queue.

### `two_pass` mode (default when bypass is enabled)

Two separate `sd-cli` runs:

1. **Pass 1:** neutral prompt `"a neutral grey background"`, `safety_bypass_steps` steps (default 4), CFG `1.0`. Output is a temporary PNG.
2. **Pass 2:** `--init-img` from Pass 1, full prompt, `steps - safety_bypass_steps` steps, CFG `7.0`, strength `0.75`. Output is the requested final image.

This roughly **doubles generation time** on the M1 Max. It can help with stubborn false positives, but it is not a jailbreak.

### `single_pass` mode

A single `sd-cli` run with an explicit per-step CFG schedule:

```
--extra-sample-args guidance_schedule=1.0x4+7.0x16
```

First 4 steps use CFG `1.0`, remaining 16 use CFG `7.0`. Cheaper than `two_pass` but weaker. Use it for borderline cases where you cannot afford 2× time.

## How to enable the backend workaround

Globally:

```bash
export IDEOGRAM4_SAFETY_BYPASS=1
```

Per-prompt in JSON:

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

All keys are optional. The wrapper strips the `"generation"` block before passing JSON to `sd-cli`.

## When to use this

- You get greyed-out images on otherwise safe blog/tech prompts.
- You want a transparent fix with no agent CLI changes.

## When not to use this

- If the prompt itself is genuinely NSFW or policy-violating. These tools are for **over-sensitive local filters on legitimate content**, not for bypassing safety guardrails on harmful prompts.

## Trade-offs

| Approach | Time | Filter reliability | Use case |
|---|---|---|---|
| Prompt hygiene only | 1× | High for false positives | Always try this first |
| `single_pass` | ~1× | Medium | Borderline false positives, tight schedules |
| `two_pass` | ~2× | Medium-High | Persistent grey-outs on clean prompts |

## Tuning

If `two_pass` still greys out:
- Increase `safety_bypass_steps` to 6 or 8.
- Try a less specific neutral prompt (`"a blank canvas"`, `"a simple abstract pattern"`).
- Lower pass-2 `strength` (currently hard-coded at `0.75`) so the final prompt has more influence.

If `single_pass` degrades quality too much:
- Reduce `safety_bypass_steps` to 2.
- Raise `safety_bypass_cfg` to 1.5.

## Tool commands

```bash
# Lint a JSON prompt for filter risk
python3 ideogram4_local.py lint prompts/my-scene.json

# Rewrite it to safer phrasing
python3 ideogram4_local.py rewrite prompts/my-scene.json -o prompts/my-scene-safe.json

# Submit the safe version
JOB_ID=$(python3 ideogram4_local.py submit \
  --prompt-json prompts/my-scene-safe.json \
  -o output/my-scene.png -W 1216 -H 832 -v)
python3 ideogram4_local.py wait "$JOB_ID"
```

## External references

- Reddit /r/StableDiffusion prompt-vocabulary investigation: https://www.reddit.com/r/StableDiffusion/comments/1u11mrd/how_to_bypass_ideogram_4s_image_blocked_by_safety/
- Reddit /r/comfyui sampling workaround discussion: https://www.reddit.com/r/comfyui/comments/1txurpt/ideogram4_get_through_the_safety_filter/
- Tools4All summary (sigma-shift / increased initial noise): https://tools4all.ai/trends/workaround-discovered-to-bypass-ideogram-4-censorship-blocks
- `stable-diffusion.cpp` Ideogram 4 docs: https://github.com/leejet/stable-diffusion.cpp/blob/master/docs/ideogram4.md
- `stable-diffusion.cpp` guidance schedule parser: `src/runtime/guidance.cpp`
- `stable-diffusion.cpp` CLI: `sd-cli --help` (`--init-img`, `--strength`, `--cfg-scale`, `--extra-sample-args`)
