# Agent skill update notice: ideogram4-local

> Forward this message verbatim to any agent you want to update. They can act on it directly.

---

## Action required

Update your local copy of the `ideogram4-local` Hermes skill and your local checkout of the `gulasz101/ideogram4-local` repo. Several important corrections were made on 2026-07-10 based on the upstream `ideogram-oss/ideogram4` source code.

## Key changes

1. **Use the exact official JSON schema.** The `ideogram4_local.py` wrapper now auto-canonicalizes submitted prompts to the upstream schema. Your skill templates and examples must match it:
   - Top-level keys (exact order): `high_level_description`, `style_description`, `compositional_deconstruction`.
   - `style_description` may contain: `aesthetics`, `lighting`, `medium`, `photo` **or** `art_style`, `color_palette`.
   - `compositional_deconstruction` contains: `background` and `elements`.
   - Each element must have: `type: "obj"`, `bbox`, `desc`.
   - Bounding boxes are normalized `[y1, x1, y2, x2]` in the range 0–1000.
   - **No `canvas` or `layout` keys.** They are off-distribution.

2. **Fix the single-pass CFG schedule.** The old `single_pass` schedule was reversed. The correct `sd-cli` argument for 20 steps is:
   - `--extra-sample-args guidance_schedule=7.0x18+3.0x2`
   - This matches the official Ideogram 4 `V4_DEFAULT_20` preset: 18 high-CFG steps followed by 2 low-CFG polish steps.
   - `sd-cli` reads the schedule array reversed at runtime, so the string is written left-to-right as high-then-low.

3. **The grey-box problem is mostly prompt distribution, not magic sampler tricks.** Clean, canonical, in-distribution prompts render without any bypass for tech blog headers and even borderline cartoon/beach scenes. The bypass modes are only fallbacks for genuinely hard prompts.

4. **Use the lint command.** Before submitting a prompt, run:
   ```bash
   cd ~/git/ideogram4-local
   python3 ideogram4_local.py lint path/to/your-prompt.json
   ```
   Risk score should be 0 or very low. If it flags garments/anatomy/situations, remove those explicit keywords and describe the scene/activity instead.

## Files to update in your skill

- `SKILL.md`: bump version, fix the prompt-hygiene section, fix the `single_pass` schedule line to `7.0x18+3.0x2`.
- `templates/*.json`: rewrite to official schema, drop `canvas`/`layout`, use correct bbox order.
- `references/ideogram4-safety-filter.md`: update schedule explanation.
- `references/prompt-hygiene.md`: emphasize exact schema compliance.

## Verification

After updating, submit a test job with no bypass:

```bash
cd ~/git/ideogram4-local
python3 ideogram4_local.py submit \
  --prompt-json templates/prompt-blog-gitops-header.json \
  -o output/test-agent-update.png \
  -W 1216 -H 832 -v
```

Expected result: clean illustration, no grey placeholder.

## Reference materials

- Repo with embedded skill: https://github.com/gulasz101/ideogram4-local
  - Skill files under `skill/`
  - Updated templates under `templates/`
  - New edge-case prompts under `prompts/`
- Upstream schema source: https://github.com/ideogram-oss/ideogram4/blob/main/src/ideogram4/caption_verifier.py
- Upstream sampler source: https://github.com/ideogram-oss/ideogram4/blob/main/src/ideogram4/sampler_configs.py

## Questions?

If anything conflicts with your existing skill, update your skill to match the repo. The repo is the source of truth.

---

Forwarded by: Andrzej / gulasz101 ideogram4-local maintainer
Date: 2026-07-10
