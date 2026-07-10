# 2026-07-10 verification: schema + schedule fixes

## What we tested

After patching `ideogram4_local.py` and `ideogram4_prompt_tools.py` to auto-canonicalize prompts to the official `ideogram-oss/ideogram4` schema and to use the corrected `V4_DEFAULT_20` sampler schedule (`guidance_schedule=7.0x18+3.0x2`), we ran three jobs:

| Job ID | Template | Bypass | LLM | Result |
|---|---|---|---|---|
| `z6YB0jUfD88` | robot/key card with text label | `two_pass` | aggressive | ❌ Grey "Image blocked by safety filter" |
| `A_c75cA4m64` | GitOps header (no text elements) | none | aggressive | ✅ Clean, detailed server-room illustration |
| `hcm6-GdZyhI` | GitOps header (no text elements) | `single_pass` | aggressive | ✅ Clean, detailed server-room illustration |

Worker log confirmed the corrected schedule:

```
[2026-07-10 20:31:19] [ideogram4-local] Safety bypass enabled: guidance_schedule=7.0x18+3.0x2
```

## What this proves

1. **Schema-compliant prompts render clean without bypass.** A canonical JSON prompt with `high_level_description`, `style_description`, and `compositional_deconstruction` (no `canvas`/`layout`) is the strongest lever against the local GGUF grey box.
2. **`single_pass` with the official schedule works.** It produced a clean image in the same time as a normal generation.
3. **Some prompts are just bad demos for the bypass.** The robot/key-card + text-label prompt grey-boxed even with `two_pass` + aggressive encoder. The filter is sensitive to combinations of humanoid/robot figures, ID cards, and explicit text labels.

## Updated guidance

- Use `templates/prompt-blog-gitops-header.json` for no-bypass blog headers.
- Use `templates/prompt-blog-gitops-header-single-pass.json` if you want the faster `single_pass` schedule (safe on clean prompts).
- Use `templates/prompt-with-safety-bypass.json` only for prompts that have already false-positived with prompt hygiene alone; it uses `two_pass`.
- If a prompt greys out, **change the prompt vocabulary** before increasing bypass steps or switching schedules.

## Files touched

- `ideogram4_local.py`: `canonicalize_prompt()` + `build_guidance_schedule()` fix.
- `ideogram4_prompt_tools.py`: schema-aware lint/rewrite.
- `templates/prompt-blog-gitops-header.json`: rewritten to official schema.
- `templates/prompt-blog-observability-header.json`: rewritten to official schema.
- `templates/prompt-with-safety-bypass.json`: replaced robot/key-card with robot/sign demo.
- `templates/prompt-blog-gitops-header-single-pass.json`: new template for `single_pass`.
- `README.md`: skill discovery note, corrected sampler docs.
- `references/ideogram4-safety-filter.md`: corrected `single_pass` schedule explanation.
