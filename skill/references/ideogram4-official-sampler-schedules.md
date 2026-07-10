# Ideogram 4 official sampler schedules

From `ideogram4/sampler_configs.py` in `ideogram-oss/ideogram4`.

## Important: loop-index order

The code comment is explicit:

> `guidance_schedule` is in loop-INDEX order: index 0 is the LAST (polish) step.

So a schedule tuple of `(3.0,) * 2 + (7.0,) * 18` means:

- First 18 sampling steps: CFG = 7.0
- Last 2 sampling steps: CFG = 3.0 (polish)

The body of generation uses high CFG; the final polish uses lower CFG.

## Official presets

| Preset | Steps | Guidance schedule (loop-index order) | Actual sampling |
|---|---|---|---|
| `V4_QUALITY_48` | 48 | `(3.0)*3 + (7.0)*45` | 45 steps @ 7.0, 3 steps @ 3.0 |
| `V4_DEFAULT_20` | 20 | `(3.0)*2 + (7.0)*18` | 18 steps @ 7.0, 2 steps @ 3.0 |
| `V4_TURBO_12` | 12 | `(3.0)*1 + (7.0)*11` | 11 steps @ 7.0, 1 step @ 3.0 |

## stable-diffusion.cpp syntax and indexing

`sd-cli` accepts `--extra-sample-args guidance_schedule=A x N + B x M`.

**Critical:** `sd-cli` parses the spec **left-to-right into an array**, and the runtime then indexes that array reversed:

```cpp
// stable-diffusion.cpp ~line 2235
guidance_schedule[guidance_schedule.size() - 1 - step]
```

So:

- Leftmost entries in the spec → early array indices → used at **later sampling steps** (polish).
- Rightmost entries in the spec → late array indices → used at **early sampling steps** (main denoise).

To match `V4_DEFAULT_20` in `sd-cli` syntax:

```
guidance_schedule=7.0x18+3.0x2
```

This is the **opposite** of the older community workaround that started with low CFG.

## Common mistake

A reversed schedule like `1.0x4+7.0x16` puts low CFG at the start of denoising. That is **not** the trained schedule and produces weak, desaturated, or off-distribution output.

## Customizing

If you override with `generation.guidance_schedule`, follow the same rule: put the high-CFG value first and the polish-CFG value last.

For `N` steps, use:

```
7.0x(N-2)+3.0x2
```

The wrapper's `build_guidance_schedule()` does this automatically for `single_pass` mode.

## Wrapper note

Our `ideogram4-local` wrapper has two safety-bypass-related paths:

- `two_pass` — neutral-prompt first pass, then img2img second pass. Still useful for persistent grey-outs, but ~2× generation time on the M1 Max.
- `single_pass` — as of 2026-07-10 the wrapper defaults to the official `V4_DEFAULT_20` schedule (`7.0x18+3.0x2` for 20 steps, or `7.0x(steps-2)+3.0x2` generally). This is the trained preset, not the older community low-CFG-first desensitizer.

The wrapper also auto-canonicalizes every JSON prompt on submit to the official `ideogram-oss/ideogram4` schema (drop `canvas`/`layout`, reorder keys, ensure exactly one of `photo`/`art_style`). See `references/ideogram4-oss-schema.md`.

## Test result

On 2026-07-10 a canonical GitOps header prompt rendered cleanly with `single_pass` and `guidance_schedule=7.0x18+3.0x2`, and the no-bypass version of the same prompt also rendered cleanly. The schedule correction alone did not bypass the safety fallback on a robot/key-card canary, but it produced clean images for in-distribution tech-header prompts.

For quality-first generation, rely on prompt hygiene + the official schedule; use `two_pass` only when the prompt is clean and still greys out.
