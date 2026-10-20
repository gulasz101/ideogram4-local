# Pre-v3.4.0 Prompt Migration Guide

## Context

Before the 2026-07-10 schema formalization (skill v3.4.0), prompt files in `prompts/` used a non-canonical format that pushes Ideogram 4 out-of-distribution. Images generated from these prompts often look "unfinished," garbled, or have mangled text. When a user asks to regenerate such an image, **check the prompt format first** — the fix is usually rewriting the prompt, not changing sampler settings.

## How to detect old-format prompts

A prompt file needs migration if it has ANY of these markers:

| Marker | Old format | Canonical format |
|---|---|---|
| Top-level wrapper | `"image_prompt": { ... }` | No wrapper — keys at root |
| Scene description key | `"scene_description": "..."` | `"high_level_description": "..."` |
| Style as a string | `"style_description": "aesthetics: ... lighting: ... medium: ..."` | `"style_description": { "aesthetics": "...", "lighting": "...", "medium": "...", "art_style": "..." }` |
| Element positioning | `"position": "left side"` | `"bbox": [y1, x1, y2, x2]` (0–1000) |
| Element types | `"type": "character"`, `"type": "effect"` | `"type": "obj"` (always) |
| Text elements | `"type": "text", "text": "DNS?"` | **Remove entirely** — describe the concept as an `obj` instead (see pitfall #17) |
| `canvas` / `layout` keys | Present in `compositional_deconstruction` | **Remove** — not in trained schema |

## Migration workflow

1. **Read the old prompt file** and identify all non-canonical markers.
2. **Rewrite as canonical JSON** with exactly three top-level keys:
   - `high_level_description` — one paragraph scene summary
   - `style_description` — object with `aesthetics`, `lighting`, `medium`, `art_style` (or `photo`), `color_palette`
   - `compositional_deconstruction` — object with `background` (string) and `elements` (array)
3. **Convert each element:**
   - Change `type` to `"obj"` for all elements
   - Replace `position` strings with `bbox: [y1, x1, y2, x2]` coordinates (0–1000 scale)
   - Convert `text` elements into `obj` elements describing the visual without specifying exact text (e.g., "a floating holographic sign panel with a glowing border" instead of `"text": "DNS?"`)
   - Merge `effect` elements into the `background` description or convert to `obj`
4. **Name the new file** `<original-name>-v2.json` (or `-v3` if v2 exists).
5. **Lint:** `python3 ideogram4_local.py lint prompts/<new-file>.json` — must show risk score 0, canonical JSON: True.
6. **Submit** with the same output path as the original (overwrites the bad image).

## Example: DNS confusion prompt migration

**Old** (`2026-06-26-docs-mcp-dns.json`):
- Had `image_prompt` wrapper
- Used `scene_description` instead of `high_level_description`
- Style was a single colon-delimited string
- Elements had `type: "character"`, `type: "effect"`, `type: "text"`
- Positions were strings: `"left side"`, `"center"`, `"right side"`
- Had a `"text": "DNS?"` element

**New** (`2026-06-26-docs-mcp-dns-v2.json`):
- Three canonical top-level keys at root
- `style_description` as proper object with `art_style`
- All elements are `type: "obj"` with `bbox` coordinates
- No `text` elements — the "DNS?" concept became "a floating holographic sign panel with a glowing border"
- Lint: risk score 0, canonical JSON: True

## Known old-format files in prompts/ (as of 2026-07-11)

These files were generated before the schema formalization and likely need migration if re-used:

- `2026-06-26-docs-mcp-dns.json` — migrated to v2 ✓
- `0628-docs-mcp-centralisation-header.json` — check format
- `0628-security-scan-filter.json` — check format
- `0628-security-scan-clean-v2.json` — check format
- `post1-two-boxes-architecture.json` — check format
- `post3-persistence-rabbit-hole.json` — check format
- `post3-otel-collector-plumbing.json` — check format
- `post4-cloudflare-403.json` — check format
- `post4-hermes-keys-header.json` — check format
- `post4-llm-hub-wife-chat.json` — check format
- `post7-omv-observability-bootstrap.json` — check format
- `post-favicon-investigation.json` — check format
- `post-favicon-header.json` — check format

Files with names containing `-v2` or later were likely already migrated to canonical format during the 2026-07-08 batch rewrite, but verify with `lint` before assuming.