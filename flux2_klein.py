#!/usr/bin/env python3
"""FLUX.2-klein-4B runner for the ideogram4-local queue (runs in the venv).

Copied from `star-office-ui-fork/scripts/flux_room_gen.py` (load_pipe and
generate) rather than imported across repos. The field results behind the
choices below are in ADR-060: klein loads in about 19 s and renders 512x512 at
4 steps in about 13 s, the pixel-art LoRA produces black frames (so it is never
loaded), and klein paints a checkerboard instead of alpha (so output is saved
as RGB).

The worker runs this file as `~/.venvs/sou-flux/bin/python flux2_klein.py` and
passes the prompt on stdin, so neither a long prompt nor one starting with
"-" ends up in argv. torch and diffusers are imported inside functions only:
the stdlib test runner imports this module without either installed.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

MODEL_ID = "black-forest-labs/FLUX.2-klein-4B"
STEPS = 4
GUIDANCE = 1.0  # ignored by the distilled model; kept for parity with ADR-060


def log(message: str) -> None:
    print(f"[flux2-klein] {message}", file=sys.stderr, flush=True)


def load_pipe():
    """Load the pipeline onto MPS, falling back to CPU with a warning."""
    import torch
    from diffusers import Flux2KleinPipeline

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    if device == "cpu":
        log("MPS unavailable - CPU fallback will be slow")

    # No LoRA: in diffusers the pixel-art LoRA collapses output to black
    # frames at every documented strength (ADR-060 field result).
    pipe = Flux2KleinPipeline.from_pretrained(MODEL_ID, torch_dtype=torch.bfloat16)
    pipe.to(device)
    return pipe, torch


def generate(pipe, torch, prompt, width, height, seed, steps=STEPS, guidance=GUIDANCE):
    """Render one image. The prompt must be a keyword argument.

    Flux2KleinPipeline's first positional parameter is `image` (klein is a
    unified generate+edit model), so positionally the prompt lands in `image`
    and the pipeline raises "Provide either `prompt` or `prompt_embeds`".
    """
    generator = torch.Generator(device="cpu").manual_seed(seed)
    t0 = time.time()
    image = pipe(
        prompt=prompt,
        height=height,
        width=width,
        num_inference_steps=steps,
        guidance_scale=guidance,
        generator=generator,
    ).images[0]
    log(f"generated {width}x{height} seed={seed} steps={steps} in {time.time() - t0:.1f}s")
    return image, time.time() - t0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render one image with FLUX.2-klein-4B; the prompt is read from stdin."
    )
    parser.add_argument("-o", "--output", type=Path, required=True, help="PNG to write")
    parser.add_argument("-W", "--width", type=int, default=1216)
    parser.add_argument("-H", "--height", type=int, default=832)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--steps", type=int, default=STEPS)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    prompt = sys.stdin.read().strip()
    if not prompt:
        log("empty prompt on stdin")
        return 2

    output = args.output.expanduser()

    t0 = time.time()
    pipe, torch = load_pipe()
    load_s = time.time() - t0
    log(f"loaded {MODEL_ID} in {load_s:.1f}s")

    image, gen_s = generate(
        pipe, torch, prompt, args.width, args.height, args.seed, args.steps
    )
    if image.size != (args.width, args.height):
        log(f"expected {args.width}x{args.height}, got {image.size[0]}x{image.size[1]}")
        return 1

    output.parent.mkdir(parents=True, exist_ok=True)
    # klein paints a checkerboard where alpha would be; RGB keeps that honest.
    image.convert("RGB").save(output, format="PNG")

    print(
        json.dumps(
            {
                "model": MODEL_ID,
                "seed": args.seed,
                "steps": args.steps,
                "width": args.width,
                "height": args.height,
                "load_s": round(load_s, 2),
                "gen_s": round(gen_s, 2),
                "output": str(output),
            }
        )
    )
    return 0


if __name__ == "__main__":
    os.environ.setdefault("PYTORCH_MPS_HIGH_WATERMARK_RATIO", "0.0")
    sys.exit(main())
