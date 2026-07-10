# Uncensored VLM encoder swap for ideogram4-local

## When to use this

You keep getting false-positive "blocked by safety filter" grey boxes from local Ideogram 4 generations, even after applying prompt hygiene. The local GGUF build's safety attractor is baked into the weights and reacts to both prompt vocabulary/structure and the text encoder.

## What actually worked

Our A/B tests showed that **neither** encoder swap **nor** prompt hygiene alone was sufficient. The working combination is:

1. **HauhauCS Aggressive uncensored VLM encoder** as the `--llm` text encoder.
2. **Sparse, situation-based canonical JSON prompt** with no clothing/anatomy/state nouns, no `canvas`/`layout` fields, no fashion/accessory vocabulary applied to animals, and only 1-3 elements.

## Model files

| Key | Filename | Source | Size |
|---|---|---|---|
| `aggressive` | `Qwen3VL-8B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf` | `HauhauCS/Qwen3VL-8B-Uncensored-HauhauCS-Aggressive` | ~4.7 GB |
| `heretic` | `Qwen3-VL-8B-Heretic-1.3.0-Q4_K_M.gguf` | `DreamFast/Qwen3-VL-8B-Heretic-1.3.0` | ~4.7 GB |
| `instruct` | `Qwen3-VL-8B-Instruct-Q4_K_M.gguf` | `unsloth/Qwen3-VL-8B-Instruct-GGUF` | ~4.7 GB |

## Set the worker default

Edit `~/Library/LaunchAgents/com.gulasz101.ideogram4-local.worker.plist` and change:

```xml
    <key>IDEOGRAM4_LLM_MODEL</key>
    <string>aggressive</string>
```

Then reload:

```bash
launchctl unload ~/Library/LaunchAgents/com.gulasz101.ideogram4-local.worker.plist
launchctl load ~/Library/LaunchAgents/com.gulasz101.ideogram4-local.worker.plist
```

Any agent that submits to the same queue will now use the aggressive encoder by default.

## Per-prompt override

Inside the prompt JSON:

```json
{
  "generation": {
    "llm_model": "aggressive"
  }
}
```

Other valid values: `"heretic"`, `"instruct"`.

## Prompt structure that worked

Use `prompts/test-beach-minimal.json` as a template:

```json
{
  "high_level_description": "A candid lifestyle photograph of a cheerful young woman having fun at the beach on a sunny summer day.",
  "style_description": {
    "aesthetics": "candid lifestyle photography, authentic, warm, natural",
    "lighting": "bright natural daylight, soft",
    "photo": "35mm candid, shallow depth of field, eye-level",
    "medium": "photograph"
  },
  "compositional_deconstruction": {
    "background": "A bright sandy beach with turquoise sea and clear blue sky, soft golden sunlight, gentle waves.",
    "elements": [
      {
        "type": "obj",
        "desc": "A joyful young woman in her mid 20s with sun-kissed skin and windblown brown hair, laughing happily as she plays at the water's edge, carefree relaxed summer-holiday mood."
      }
    ]
  }
}
```

Rules:
- No clothing nouns (bikini, swimsuit, dress, lingerie, etc.).
- No anatomy nouns (breast, butt, nude, bare, etc.).
- No `canvas` or `layout` fields.
- 1-3 elements maximum.
- Use situation/persona/activity descriptions.

## What failed

- DreamFast Heretic 1.3.0 encoder alone on a dense beach prompt → grey box.
- HauhauCS Aggressive encoder on a dense beach prompt (with `canvas`/`layout`/clothing nouns) → grey box.
- Default Instruct encoder on the sparse situation-based prompt → grey box.

## Rollback

Set `IDEOGRAM4_LLM_MODEL=instruct` or remove the env var entirely to return to the default unsloth Instruct encoder. The wrapper default is `instruct` if the env var is absent.

## References

- Reddit thread: "How to bypass Ideogram 4's image blocked by safety filter" — `r/StableDiffusion/comments/1u11mrd/`
- Reddit thread: "Ideogram 4.0 with no Filter issues, you literally just need the KJ node" — `r/StableDiffusion/comments/1ub1fbh/`
- KJNodes source: `https://github.com/kijai/ComfyUI-KJNodes/blob/main/nodes/ideogram4_nodes.py`
- Local wrapper reference: `references/ideogram4-safety-filter.md`
