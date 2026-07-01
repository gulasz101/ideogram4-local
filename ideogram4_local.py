#!/usr/bin/env python3
"""
Ideogram 4 local image generator using stable-diffusion.cpp.

Singleton wrapper that prevents concurrent runs from killing the M1 Max.
Supports structured JSON prompts (recommended) and plain text prompts.

Usage:
    python ideogram4_local.py --prompt-json scene.json -o output.png
    python ideogram4_local.py --prompt "a cat wearing a wizard hat" -o output.png
"""

import argparse
import fcntl
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Defaults tuned for an Apple Silicon M1 Max with 32 GB unified RAM.
# Use Q4_0 GGUF weights and CPU offloading so generation fits without OOM.
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
MODELS_DIR = Path(os.environ.get("IDEOGRAM4_MODELS_DIR", SCRIPT_DIR / "models"))
OUTPUT_DIR = Path(os.environ.get("IDEOGRAM4_OUTPUT_DIR", SCRIPT_DIR / "output"))
LOCK_FILE = Path(os.environ.get("IDEOGRAM4_LOCK_FILE", SCRIPT_DIR / ".lock"))

MODEL_URLS = {
    "ideogram4-Q4_0.gguf": "https://huggingface.co/leejet/ideogram-4-GGUF/resolve/main/ideogram4-Q4_0.gguf",
    "ideogram4_uncond-Q4_0.gguf": "https://huggingface.co/leejet/ideogram-4-GGUF/resolve/main/ideogram4_uncond-Q4_0.gguf",
    "Qwen3-VL-8B-Instruct-Q4_K_M.gguf": "https://huggingface.co/unsloth/Qwen3-VL-8B-Instruct-GGUF/resolve/main/Qwen3-VL-8B-Instruct-Q4_K_M.gguf",
    "flux2-vae.safetensors": "https://huggingface.co/Comfy-Org/flux2-dev/resolve/main/split_files/vae/flux2-vae.safetensors",
}

DEFAULT_SD_CPP = Path("~/sd.cpp").expanduser()
SD_CPP_DIR = Path(os.environ.get("SD_CPP_DIR", DEFAULT_SD_CPP))
SD_CLI = SD_CPP_DIR / "build" / "bin" / "sd-cli"

DEFAULT_WIDTH = 1216
DEFAULT_HEIGHT = 832


def log(message: str) -> None:
    print(f"[ideogram4-local] {message}", flush=True)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def model_path(name: str) -> Path:
    return MODELS_DIR / name


def is_model_present(name: str) -> bool:
    path = model_path(name)
    if not path.exists():
        return False
    expected_bytes = _model_size_hint(name)
    actual_bytes = path.stat().st_size
    return actual_bytes >= expected_bytes * 0.99


def _model_size_hint(name: str) -> int:
    """Return expected bytes for each known model file."""
    hints = {
        "ideogram4-Q4_0.gguf": 5_643_820_832,
        "ideogram4_uncond-Q4_0.gguf": 5_643_820_832,
        "Qwen3-VL-8B-Instruct-Q4_K_M.gguf": 5_027_785_568,
        "flux2-vae.safetensors": 336_213_556,
    }
    return hints.get(name, 1_000_000_000)


def download_model(name: str) -> Path:
    """Download a missing model file with resume support."""
    ensure_dir(MODELS_DIR)
    path = model_path(name)
    url = MODEL_URLS[name]

    log(f"Downloading {name} -> {path}")
    log(f"URL: {url}")

    cmd = [
        "wget",
        "--progress=dot:giga",
        "-c",
        "-O",
        str(path),
        url,
    ]
    result = subprocess.run(cmd)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to download {name}")

    if not is_model_present(name):
        raise RuntimeError(f"{name} download seems incomplete")

    log(f"{name} ready ({path.stat().st_size} bytes)")
    return path


def ensure_models() -> dict:
    """Make sure all required model files exist, downloading if needed."""
    missing = [n for n in MODEL_URLS if not is_model_present(n)]
    if missing:
        log(f"Missing models: {missing}")
        for name in missing:
            download_model(name)
    else:
        log("All model files are present")

    return {name: model_path(name) for name in MODEL_URLS}


class QueueLock:
    """Queue-aware singleton lock.

    Only one Ideogram 4 generation can run at a time (the M1 Max cannot load
    ~16 GB of model weights twice). By default this class waits politely in
    queue until the lock becomes free, logging status every 30 seconds. Use
    no_wait=True to fail immediately instead of queuing.
    """

    def __init__(self, lock_path: Path, timeout: float = 3600.0, no_wait: bool = False, poll_interval: float = 5.0):
        self.lock_path = lock_path
        self.timeout = timeout
        self.no_wait = no_wait
        self.poll_interval = poll_interval
        self._file = None
        self._start_wait = None

    def __enter__(self):
        ensure_dir(self.lock_path.parent)
        self._file = open(self.lock_path, "w")

        if self.no_wait:
            try:
                fcntl.flock(self._file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                self._file.close()
                raise RuntimeError(
                    f"Another Ideogram 4 generation is already running (lock: {self.lock_path}). "
                    "Pass --no-wait=false or remove the lock file if you are sure it is stale."
                )
        else:
            self._start_wait = time.time()
            log(f"Queueing for generation lock (timeout: {self.timeout:.0f}s)...")
            while True:
                try:
                    fcntl.flock(self._file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    waited = time.time() - self._start_wait
                    if waited > 0.5:
                        log(f"Waited {waited:.0f}s in queue; lock acquired")
                    break
                except BlockingIOError:
                    elapsed = time.time() - self._start_wait
                    if elapsed >= self.timeout:
                        self._file.close()
                        raise RuntimeError(
                            f"Timed out after {self.timeout:.0f}s waiting for another Ideogram 4 generation to finish. "
                            f"Lock file: {self.lock_path}"
                        )
                    # Log every ~30 seconds so the user/agent sees it is queued.
                    if int(elapsed) % 30 < self.poll_interval:
                        remaining = self.timeout - elapsed
                        log(f"Still queued... ({elapsed:.0f}s elapsed, {remaining:.0f}s timeout remains)")
                    time.sleep(self.poll_interval)

        self._file.write(f"pid={os.getpid()}\nstarted={time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        self._file.flush()
        log("Acquired generation lock")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._file:
            try:
                fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)
            finally:
                self._file.close()
            try:
                self.lock_path.unlink()
            except FileNotFoundError:
                pass
        log("Released generation lock")


def build_prompt(args) -> str:
    """Return the final prompt string for sd-cli."""
    if args.prompt_json:
        with open(args.prompt_json, "r", encoding="utf-8") as f:
            data = json.load(f)
        return json.dumps(data, ensure_ascii=False, separators=(",", ":"))

    if args.prompt:
        # Plain text can be passed directly. Ideogram 4 has a magic-prompt
        # expansion on the server side in the official CLI, but the local
        # stable-diffusion.cpp build uses the prompt as-is. For best results,
        # use --prompt-json with a structured JSON prompt.
        return args.prompt.strip()

    raise ValueError("Either --prompt or --prompt-json must be provided")


def generate(
    prompt: str,
    output: Path,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    verbose: bool = False,
) -> Path:
    """Run the actual image generation."""
    ensure_dir(OUTPUT_DIR)

    if not SD_CLI.exists():
        raise RuntimeError(
            f"sd-cli not found at {SD_CLI}. "
            "Build stable-diffusion.cpp from https://github.com/leejet/stable-diffusion.cpp "
            "or set SD_CPP_DIR to point at an existing build."
        )

    models = ensure_models()

    cmd = [
        str(SD_CLI),
        "--diffusion-model", str(models["ideogram4-Q4_0.gguf"]),
        "--uncond-diffusion-model", str(models["ideogram4_uncond-Q4_0.gguf"]),
        "--llm", str(models["Qwen3-VL-8B-Instruct-Q4_K_M.gguf"]),
        "--vae", str(models["flux2-vae.safetensors"]),
        "-p", prompt,
        "-o", str(output),
        "-W", str(width),
        "-H", str(height),
        "--offload-to-cpu",
        "--diffusion-fa",
    ]
    if verbose:
        cmd.append("-v")

    log(f"Running generation ({width}x{height})...")
    log("This will take several minutes on CPU-only M1 Max. Do not start another generation.")

    result = subprocess.run(cmd)
    if result.returncode != 0:
        raise RuntimeError(f"sd-cli exited with code {result.returncode}")

    if not output.exists():
        raise RuntimeError(f"Expected output file not found: {output}")

    log(f"Generated image: {output} ({output.stat().st_size} bytes)")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Local Ideogram 4 image generation wrapper")
    parser.add_argument("--prompt-json", type=Path, help="Path to structured JSON prompt file")
    parser.add_argument("--prompt", type=str, help="Plain text prompt (less reliable than JSON)")
    parser.add_argument("-o", "--output", type=Path, required=True, help="Output image path")
    parser.add_argument("-W", "--width", type=int, default=DEFAULT_WIDTH)
    parser.add_argument("-H", "--height", type=int, default=DEFAULT_HEIGHT)
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument(
        "--skip-lock", action="store_true",
        help="Skip queue/lock entirely (dangerous on M1 Max; only use if you know no other generation is running)"
    )
    parser.add_argument(
        "--no-wait", action="store_true",
        help="Fail immediately if another generation is running instead of queuing"
    )
    parser.add_argument(
        "--queue-timeout", type=float, default=3600.0,
        help="Maximum seconds to wait in queue for the lock (default: 3600)"
    )
    args = parser.parse_args()

    if not (args.prompt or args.prompt_json):
        parser.error("Either --prompt or --prompt-json is required")

    if args.prompt_json and not args.prompt_json.exists():
        parser.error(f"Prompt JSON file not found: {args.prompt_json}")

    if args.skip_lock and args.no_wait:
        parser.error("--skip-lock and --no-wait are mutually exclusive")

    output = args.output.expanduser().resolve()
    ensure_dir(output.parent)

    prompt = build_prompt(args)

    if args.skip_lock:
        log("WARNING: running without any lock")
        generate(prompt, output, args.width, args.height, args.verbose)
    else:
        with QueueLock(LOCK_FILE, timeout=args.queue_timeout, no_wait=args.no_wait):
            generate(prompt, output, args.width, args.height, args.verbose)

    print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
