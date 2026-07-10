# Ideogram 4 official caption schema

Distilled from `ideogram-oss/ideogram4` source (`caption_verifier.py`, `magic_prompt_system_prompts/v1.txt`) and verified on 2026-07-10.

## Allowed top-level keys (exactly these)

```json
{
  "high_level_description": "string",
  "style_description": { ... },
  "compositional_deconstruction": { ... }
}
```

No other top-level keys are accepted by the upstream verifier. In particular, **drop `canvas` and `layout`** — they are not in the trained schema and drift the local GGUF model toward grey-box outputs.

## `style_description`

Allowed keys:

- `aesthetics`
- `lighting`
- `medium`
- **`photo` OR `art_style` (exactly one of these two)**
- `color_palette`

Use `photo` for photographs, `art_style` for illustrations, cartoons, renders, vector art, etc.

Recommended order:

```json
{
  "aesthetics": "...",
  "lighting": "...",
  "medium": "...",
  "art_style": "...",
  "color_palette": ["#1E3A8A", "#3B82F6", "#F59E0B", "#F3F4F6"]
}
```

## `compositional_deconstruction`

Allowed keys:

- `background`
- `elements`

Keep `elements` focused: 1–4 objects described as a situation/mood. Do not name clothing, anatomy, or state vocabulary.

## Element format

```json
{
  "type": "obj",
  "bbox": [y1, x1, y2, x2],
  "desc": "situation-based description of the object",
  "color_palette": ["#3B82F6", "#F59E0B"]
}
```

For text labels:

```json
{
  "type": "text",
  "bbox": [y1, x1, y2, x2],
  "text": "label text",
  "desc": "description of label style/placement",
  "color_palette": ["#1F2937"]
}
```

## Bbox coordinates

Format: **`[y1, x1, y2, x2]`**, all values normalized to `[0, 1000]`.

Example for a wide 16:9 image, element in the left third:

```json
"bbox": [100, 50, 750, 350]
```

This means y from 100 to 750, x from 50 to 350.

## Key rule

The local GGUF safety/grey-box fallback is **out-of-distribution driven**. Prompts that follow the exact trained schema render more reliably than prompts that invent extra keys, dense layouts, or prose descriptions.

## References

- https://github.com/ideogram-oss/ideogram4
  - `src/ideogram4/caption_verifier.py`
  - `src/ideogram4/magic_prompt_system_prompts/v1.txt`
