#!/usr/bin/env python3
"""
Ideogram 4 local image generator using stable-diffusion.cpp.

SQLite-backed job queue + file-lock worker.

Usage:
    # Submit a job
    python ideogram4_local.py submit --prompt-json prompts/homelab-toriyama.json -o output/header.png

    # Run the worker (singleton, picks up pending jobs)
    python ideogram4_local.py worker

    # Check job status
    python ideogram4_local.py status <job-id>

    # List recent jobs
    python ideogram4_local.py list

    # Wait for a job and print the result path
    python ideogram4_local.py wait <job-id>
"""

import argparse
import datetime
import fcntl
import json
import os
import secrets
import sqlite3
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ideogram4_prompt_tools import lint_prompt, rewrite_prompt, print_lint_report

# ---------------------------------------------------------------------------
# Defaults tuned for an Apple Silicon M1 Max with 32 GB unified RAM.
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_MODELS_DIR = Path("~/sd.cpp-models").expanduser()
MODELS_DIR = Path(os.environ.get("IDEOGRAM4_MODELS_DIR", DEFAULT_MODELS_DIR))
OUTPUT_DIR = Path(os.environ.get("IDEOGRAM4_OUTPUT_DIR", SCRIPT_DIR / "output"))
LOCK_FILE = Path(os.environ.get("IDEOGRAM4_LOCK_FILE", SCRIPT_DIR / ".lock"))
DB_PATH = Path(os.environ.get("IDEOGRAM4_DB", SCRIPT_DIR / "jobs.db"))

DEFAULT_SD_CPP = Path("~/sd.cpp").expanduser()
SD_CPP_DIR = Path(os.environ.get("SD_CPP_DIR", DEFAULT_SD_CPP))
SD_CLI = SD_CPP_DIR / "build" / "bin" / "sd-cli"

DEFAULT_WIDTH = 1216
DEFAULT_HEIGHT = 832
DEFAULT_SAMPLE_STEPS = 20

# Global kill-switch for the Ideogram 4 safety-filter workaround.
# Set IDEOGRAM4_SAFETY_BYPASS=1 to make every generation use a low-CFG
# guidance schedule for the first few denoising steps.
DEFAULT_SAFETY_BYPASS = os.environ.get("IDEOGRAM4_SAFETY_BYPASS", "").lower() in ("1", "true", "yes")

# Default LLM used by sd-cli as the vision-language/text encoder.
# The unsloth instruct model is the original default. The "Heretic" abliterated
# variant is a local-only, drop-in replacement that reduces the baked-in
# prompt-refusal attractor that Ideogram 4's local GGUF build can exhibit.
# Select it by setting IDEOGRAM4_LLM_MODEL=heretic in the worker environment.
DEFAULT_LLM_MODEL_NAME = "Qwen3-VL-8B-Instruct-Q4_K_M.gguf"

MODEL_URLS = {
    "ideogram4-Q4_0.gguf": "https://huggingface.co/leejet/ideogram-4-GGUF/resolve/main/ideogram4-Q4_0.gguf",
    "ideogram4_uncond-Q4_0.gguf": "https://huggingface.co/leejet/ideogram-4-GGUF/resolve/main/ideogram4_uncond-Q4_0.gguf",
    "Qwen3-VL-8B-Instruct-Q4_K_M.gguf": "https://huggingface.co/unsloth/Qwen3-VL-8B-Instruct-GGUF/resolve/main/Qwen3-VL-8B-Instruct-Q4_K_M.gguf",
    "Qwen3-VL-8B-Heretic-1.3.0-Q4_K_M.gguf": "https://huggingface.co/DreamFast/Qwen3-VL-8B-Heretic-1.3.0/resolve/main/gguf/qwen3-vl-8b-heretic-1.3.0-Q4_K_M.gguf",
    "Qwen3VL-8B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf": "https://huggingface.co/HauhauCS/Qwen3VL-8B-Uncensored-HauhauCS-Aggressive/resolve/main/Qwen3VL-8B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf",
    "flux2-vae.safetensors": "https://huggingface.co/Comfy-Org/flux2-dev/resolve/main/split_files/vae/flux2-vae.safetensors",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def log(message: str) -> None:
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [ideogram4-local] {message}", file=sys.stderr, flush=True)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Queue backend abstraction (SQLite today, Turso tomorrow)
# ---------------------------------------------------------------------------


def _init_sqlite_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            status TEXT NOT NULL DEFAULT 'pending',
            prompt_type TEXT NOT NULL,
            prompt_value TEXT NOT NULL,
            output_path TEXT NOT NULL,
            width INTEGER NOT NULL,
            height INTEGER NOT NULL,
            verbose INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            started_at TEXT,
            finished_at TEXT,
            pid INTEGER,
            error TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
        CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at);
        """
    )
    conn.commit()


class SQLiteQueueBackend:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        ensure_dir(db_path.parent)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            _init_sqlite_schema(conn)

    def submit(
        self,
        prompt_type: str,
        prompt_value: str,
        output_path: Path,
        width: int,
        height: int,
        verbose: bool,
    ) -> str:
        job_id = secrets.token_urlsafe(8)
        now = datetime.datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO jobs (id, status, prompt_type, prompt_value, output_path, width, height, verbose, created_at)
                VALUES (?, 'pending', ?, ?, ?, ?, ?, ?, ?)
                """,
                (job_id, prompt_type, prompt_value, str(output_path), width, height, int(verbose), now),
            )
            conn.commit()
        return job_id

    def next_pending(self) -> Optional[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                """
                SELECT * FROM jobs
                WHERE status = 'pending'
                ORDER BY created_at ASC
                LIMIT 1
                """
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def get(self, job_id: str) -> Optional[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def list_jobs(self, limit: int = 20) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
            return [dict(row) for row in cur.fetchall()]

    def update_status(self, job_id: str, status: str, pid: Optional[int] = None, error: Optional[str] = None) -> None:
        now = datetime.datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            if status == "running":
                conn.execute(
                    "UPDATE jobs SET status = ?, started_at = ?, pid = ?, error = NULL WHERE id = ?",
                    (status, now, pid, job_id),
                )
            elif status in ("done", "failed"):
                conn.execute(
                    "UPDATE jobs SET status = ?, finished_at = ?, pid = ?, error = ? WHERE id = ?",
                    (status, now, pid, error, job_id),
                )
            else:
                conn.execute(
                    "UPDATE jobs SET status = ?, pid = ?, error = ? WHERE id = ?",
                    (status, pid, error, job_id),
                )
            conn.commit()


QueueBackend = SQLiteQueueBackend

# ---------------------------------------------------------------------------
# Model handling
# ---------------------------------------------------------------------------


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
    hints = {
        "ideogram4-Q4_0.gguf": 5_643_820_832,
        "ideogram4_uncond-Q4_0.gguf": 5_643_820_832,
        "Qwen3-VL-8B-Instruct-Q4_K_M.gguf": 5_027_785_568,
        "Qwen3-VL-8B-Heretic-1.3.0-Q4_K_M.gguf": 5_027_785_568,
        "Qwen3VL-8B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf": 5_027_784_800,
        "flux2-vae.safetensors": 336_213_556,
    }
    return hints.get(name, 1_000_000_000)


def llm_model_name() -> str:
    """Return the selected Qwen3-VL GGUF filename for sd-cli --llm.

    Choices:
      - "instruct" (default) -> unsloth Qwen3-VL-8B-Instruct-Q4_K_M.gguf
      - "heretic"            -> DreamFast Qwen3-VL-8B-Heretic-1.3.0-Q4_K_M.gguf

    Override via environment: IDEOGRAM4_LLM_MODEL=heretic
    Per-prompt override via JSON: generation.llm_model = "heretic"
    """
    env = os.environ.get("IDEOGRAM4_LLM_MODEL", DEFAULT_LLM_MODEL_NAME).lower()
    if env in ("hauhaucs", "aggressive", "qwen3vl-8b-uncensored-hauhaucs-aggressive-q4_k_m.gguf"):
        return "Qwen3VL-8B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf"
    if env in ("heretic", "dreamfast", "qwen3-vl-8b-heretic-1.3.0-q4_k_m.gguf"):
        return "Qwen3-VL-8B-Heretic-1.3.0-Q4_K_M.gguf"
    if env in ("instruct", "unsloth", "qwen3-vl-8b-instruct-q4_k_m.gguf"):
        return "Qwen3-VL-8B-Instruct-Q4_K_M.gguf"
    # Allow a literal filename if it exists in MODEL_URLS (future proofing).
    if env in MODEL_URLS:
        return env
    log(f"Unknown IDEOGRAM4_LLM_MODEL value '{env}', falling back to default LLM")
    return DEFAULT_LLM_MODEL_NAME


def download_model(name: str) -> Path:
    ensure_dir(MODELS_DIR)
    path = model_path(name)
    url = MODEL_URLS[name]

    log(f"Downloading {name} -> {path}")
    log(f"URL: {url}")

    cmd = ["wget", "--progress=dot:giga", "-c", "-O", str(path), url]
    result = subprocess.run(cmd)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to download {name}")

    if not is_model_present(name):
        raise RuntimeError(f"{name} download seems incomplete")

    log(f"{name} ready ({path.stat().st_size} bytes)")
    return path


def ensure_models() -> dict:
    missing = [n for n in MODEL_URLS if not is_model_present(n)]
    if missing:
        log(f"Missing models: {missing}")
        for name in missing:
            download_model(name)
    else:
        log("All model files are present")
    return {name: model_path(name) for name in MODEL_URLS}


# ---------------------------------------------------------------------------
# Lock / singleton
# ---------------------------------------------------------------------------


class QueueLock:
    """File lock that lets multiple agents queue politely for one generation slot."""

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


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------


def build_prompt(prompt_type: str, prompt_value: str) -> str:
    if prompt_type == "json":
        data = json.loads(prompt_value)
        # Strip the internal "generation" config block before handing the
        # structured prompt to sd-cli; it is metadata for the wrapper only.
        data.pop("generation", None)
        return json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return prompt_value.strip()


def parse_generation_config(prompt_type: str, prompt_value: str) -> dict:
    """Extract wrapper-only generation options from JSON prompts.

    Supported JSON shape (all optional):

        {
          ...normal Ideogram 4 prompt fields...,
          "generation": {
            "safety_bypass": true,
            "safety_bypass_steps": 3,
            "safety_bypass_cfg": 1.0,
            "guidance_schedule": "1.0x3+7.0x17",
            "steps": 20,
            "llm_model": "heretic"   // or "instruct"
          }
        }

    For plain text prompts, only the env var defaults apply.
    """
    config: dict = {
        "safety_bypass": DEFAULT_SAFETY_BYPASS,
        "safety_bypass_mode": "two_pass",
        "safety_bypass_steps": 4,
        "safety_bypass_cfg": 1.0,
        "guidance_schedule": None,
        "steps": DEFAULT_SAMPLE_STEPS,
        "llm_model": llm_model_name(),
    }

    if prompt_type == "json":
        try:
            data = json.loads(prompt_value)
        except json.JSONDecodeError:
            return config
        gen = data.get("generation", {})
        if "safety_bypass" in gen:
            config["safety_bypass"] = bool(gen["safety_bypass"])
        if "safety_bypass_mode" in gen:
            config["safety_bypass_mode"] = str(gen["safety_bypass_mode"])
        config["safety_bypass_steps"] = int(gen.get("safety_bypass_steps", config["safety_bypass_steps"]))
        config["safety_bypass_cfg"] = float(gen.get("safety_bypass_cfg", config["safety_bypass_cfg"]))
        if "guidance_schedule" in gen:
            config["guidance_schedule"] = str(gen["guidance_schedule"])
        if "steps" in gen:
            config["steps"] = int(gen["steps"])
        if "llm_model" in gen:
            value = str(gen["llm_model"]).lower()
            if value in ("hauhaucs", "aggressive"):
                config["llm_model"] = "Qwen3VL-8B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf"
            elif value in ("heretic", "dreamfast"):
                config["llm_model"] = "Qwen3-VL-8B-Heretic-1.3.0-Q4_K_M.gguf"
            elif value in ("instruct", "unsloth"):
                config["llm_model"] = "Qwen3-VL-8B-Instruct-Q4_K_M.gguf"
            else:
                log(f"Ignoring unknown generation.llm_model value '{value}'")

    return config


def build_guidance_schedule(config: dict) -> Optional[str]:
    """Return an --extra-sample-args guidance_schedule string if safety bypass is enabled."""
    if not config.get("safety_bypass"):
        return None

    # two_pass mode uses img2img instead of a CFG schedule.
    if config.get("safety_bypass_mode") == "two_pass":
        return None

    # Respect an explicit schedule if the user provided one.
    explicit = config.get("guidance_schedule")
    if explicit:
        return str(explicit)

    total_steps = max(1, int(config.get("steps", DEFAULT_SAMPLE_STEPS)))
    bypass_steps = max(0, min(total_steps - 1, int(config.get("safety_bypass_steps", 4))))
    remaining = total_steps - bypass_steps
    bypass_cfg = float(config.get("safety_bypass_cfg", 1.0))
    normal_cfg = 7.0  # sd-cli default for Ideogram4-style CFG

    if bypass_steps <= 0:
        return None

    return f"{bypass_cfg}x{bypass_steps}+{normal_cfg}x{remaining}"


def _sd_cli_cmd(
    prompt: str,
    output: Path,
    width: int,
    height: int,
    steps: int,
    cfg_scale: Optional[float] = None,
    init_img: Optional[Path] = None,
    strength: Optional[float] = None,
    guidance_schedule: Optional[str] = None,
    llm_model: Optional[str] = None,
    verbose: bool = False,
) -> list:
    """Build the sd-cli command list."""
    models = ensure_models()
    chosen_llm = llm_model or llm_model_name()
    cmd = [
        str(SD_CLI),
        "--diffusion-model", str(models["ideogram4-Q4_0.gguf"]),
        "--uncond-diffusion-model", str(models["ideogram4_uncond-Q4_0.gguf"]),
        "--llm", str(models[chosen_llm]),
        "--vae", str(models["flux2-vae.safetensors"]),
        "-p", prompt,
        "-o", str(output),
        "-W", str(width),
        "-H", str(height),
        "--steps", str(steps),
        "--offload-to-cpu",
        "--diffusion-fa",
    ]
    if cfg_scale is not None:
        cmd.extend(["--cfg-scale", str(cfg_scale)])
    if init_img is not None:
        cmd.extend(["--init-img", str(init_img)])
    if strength is not None:
        cmd.extend(["--strength", str(strength)])
    if guidance_schedule:
        cmd.extend(["--extra-sample-args", f"guidance_schedule={guidance_schedule}"])
    if verbose:
        cmd.append("-v")
    return cmd


def generate(
    prompt_type: str,
    prompt_value: str,
    output: Path,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    verbose: bool = False,
) -> Path:
    ensure_dir(OUTPUT_DIR)

    if not SD_CLI.exists():
        raise RuntimeError(
            f"sd-cli not found at {SD_CLI}. "
            "Build stable-diffusion.cpp from https://github.com/leejet/stable-diffusion.cpp "
            "or set SD_CPP_DIR to point at an existing build."
        )

    prompt = build_prompt(prompt_type, prompt_value)
    gen_config = parse_generation_config(prompt_type, prompt_value)
    guidance_schedule = build_guidance_schedule(gen_config)
    sample_steps = int(gen_config.get("steps", DEFAULT_SAMPLE_STEPS))
    chosen_llm = gen_config.get("llm_model", llm_model_name())
    log(f"Using LLM for generation: {chosen_llm}")

    if gen_config.get("safety_bypass") and gen_config.get("safety_bypass_mode") == "two_pass":
        # Two-pass safety bypass:
        #   Pass 1: neutral prompt, low CFG, few steps -> temp init image.
        #   Pass 2: full prompt, img2img from temp, normal CFG -> final output.
        temp_output = output.with_suffix(".tmp_init.png")
        bypass_steps = max(1, min(sample_steps - 1, int(gen_config.get("safety_bypass_steps", 4))))
        bypass_cfg = float(gen_config.get("safety_bypass_cfg", 1.0))
        remaining_steps = max(1, sample_steps - bypass_steps)

        log(f"Safety bypass (two_pass): pass 1 neutral prompt, {bypass_steps} steps at CFG {bypass_cfg}")
        cmd1 = _sd_cli_cmd(
            prompt="a neutral grey background",
            output=temp_output,
            width=width,
            height=height,
            steps=bypass_steps,
            cfg_scale=bypass_cfg,
            llm_model=chosen_llm,
            verbose=verbose,
        )
        result1 = subprocess.run(cmd1)
        if result1.returncode != 0:
            raise RuntimeError(f"sd-cli pass 1 exited with code {result1.returncode}")
        if not temp_output.exists():
            raise RuntimeError(f"Expected temp init image not found: {temp_output}")
        log(f"Safety bypass (two_pass): pass 1 complete -> {temp_output}")

        log(f"Safety bypass (two_pass): pass 2 full prompt, img2img, {remaining_steps} steps")
        cmd2 = _sd_cli_cmd(
            prompt=prompt,
            output=output,
            width=width,
            height=height,
            steps=remaining_steps,
            cfg_scale=7.0,
            init_img=temp_output,
            strength=0.75,
            llm_model=chosen_llm,
            verbose=verbose,
        )
        result2 = subprocess.run(cmd2)
        # Clean up the temp init image regardless of pass 2 outcome.
        try:
            temp_output.unlink()
        except FileNotFoundError:
            pass
        if result2.returncode != 0:
            raise RuntimeError(f"sd-cli pass 2 exited with code {result2.returncode}")
    else:
        cmd = _sd_cli_cmd(
            prompt=prompt,
            output=output,
            width=width,
            height=height,
            steps=sample_steps,
            guidance_schedule=guidance_schedule,
            llm_model=chosen_llm,
            verbose=verbose,
        )
        if guidance_schedule:
            log(f"Safety bypass enabled: guidance_schedule={guidance_schedule}")

        log(f"Running generation ({width}x{height}, steps={sample_steps})...")
        log("This will take several minutes on CPU-only M1 Max.")

        result = subprocess.run(cmd)
        if result.returncode != 0:
            raise RuntimeError(f"sd-cli exited with code {result.returncode}")

    if not output.exists():
        raise RuntimeError(f"Expected output file not found: {output}")

    log(f"Generated image: {output} ({output.stat().st_size} bytes)")
    return output


# ---------------------------------------------------------------------------
# CLI commands
# ---------------------------------------------------------------------------


def cmd_submit(args) -> int:
    queue = QueueBackend(DB_PATH)
    output = args.output.expanduser().resolve()

    if args.prompt_json:
        prompt_type = "json"
        with open(args.prompt_json, "r", encoding="utf-8") as f:
            prompt_value = f.read()
    elif args.prompt:
        prompt_type = "text"
        prompt_value = args.prompt
    else:
        raise ValueError("Either --prompt or --prompt-json is required")

    job_id = queue.submit(
        prompt_type=prompt_type,
        prompt_value=prompt_value,
        output_path=output,
        width=args.width,
        height=args.height,
        verbose=args.verbose,
    )
    log(f"Submitted job {job_id}")
    print(job_id)
    return 0


def cmd_status(args) -> int:
    queue = QueueBackend(DB_PATH)
    job = queue.get(args.job_id)
    if not job:
        print(f"Job not found: {args.job_id}", file=sys.stderr)
        return 1
    print(json.dumps(job, indent=2))
    return 0


def cmd_list(args) -> int:
    queue = QueueBackend(DB_PATH)
    jobs = queue.list_jobs(limit=args.limit)
    print(json.dumps(jobs, indent=2))
    return 0


def cmd_wait(args) -> int:
    queue = QueueBackend(DB_PATH)
    log(f"Waiting for job {args.job_id}...")
    deadline = time.time() + args.timeout
    while True:
        job = queue.get(args.job_id)
        if not job:
            print(f"Job not found: {args.job_id}", file=sys.stderr)
            return 1
        if job["status"] == "done":
            print(Path(job["output_path"]).resolve())
            return 0
        if job["status"] == "failed":
            print(f"Job failed: {job.get('error', 'unknown error')}", file=sys.stderr)
            return 1
        if time.time() >= deadline:
            print(f"Timed out waiting for job {args.job_id}", file=sys.stderr)
            return 2
        time.sleep(args.poll_interval)


def _run_one_job(queue: QueueBackend, lock: QueueLock) -> bool:
    """Pick up one pending job, run it under the lock, return True if work was done."""
    job = queue.next_pending()
    if not job:
        return False

    job_id = job["id"]
    queue.update_status(job_id, "running", pid=os.getpid())
    log(f"Processing job {job_id}")

    try:
        output = Path(job["output_path"])
        generate(
            prompt_type=job["prompt_type"],
            prompt_value=job["prompt_value"],
            output=output,
            width=job["width"],
            height=job["height"],
            verbose=bool(job["verbose"]),
        )
        queue.update_status(job_id, "done", pid=os.getpid())
        log(f"Job {job_id} completed: {output}")
    except Exception as e:
        queue.update_status(job_id, "failed", pid=os.getpid(), error=str(e))
        log(f"Job {job_id} failed: {e}")

    return True


def cmd_worker(args) -> int:
    queue = QueueBackend(DB_PATH)
    log("Worker started; polling for pending jobs...")

    while True:
        job = queue.next_pending()
        if not job:
            if args.one_shot:
                log("No pending jobs; exiting.")
                return 0
            log("No pending jobs; sleeping 10s...")
            time.sleep(10)
            continue

        try:
            with QueueLock(LOCK_FILE, timeout=args.queue_timeout, no_wait=args.no_wait):
                _run_one_job(queue, QueueLock)
        except Exception as e:
            log(f"Worker error: {e}")
            if args.one_shot:
                return 1
            time.sleep(10)

        if args.one_shot:
            return 0


def cmd_lint(args) -> int:
    prompt_value = args.prompt_json.read_text(encoding="utf-8")
    report = lint_prompt(prompt_value, "json")
    print_lint_report(report)
    return 0 if report["score"] == 0 else 1


def cmd_rewrite(args) -> int:
    prompt_value = args.prompt_json.read_text(encoding="utf-8")
    rewritten = rewrite_prompt(prompt_value, "json")
    if args.output:
        args.output.write_text(rewritten, encoding="utf-8")
        log(f"Rewritten prompt written to {args.output}")
    else:
        print(rewritten)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Local Ideogram 4 image generation queue")
    sub = parser.add_subparsers(dest="command", required=True)

    # submit
    p_submit = sub.add_parser("submit", help="Submit a generation job to the queue")
    p_submit.add_argument("--prompt-json", type=Path, help="Path to structured JSON prompt file")
    p_submit.add_argument("--prompt", type=str, help="Plain text prompt")
    p_submit.add_argument("-o", "--output", type=Path, required=True)
    p_submit.add_argument("-W", "--width", type=int, default=DEFAULT_WIDTH)
    p_submit.add_argument("-H", "--height", type=int, default=DEFAULT_HEIGHT)
    p_submit.add_argument("-v", "--verbose", action="store_true")

    # lint
    p_lint = sub.add_parser("lint", help="Check a prompt for safety-filter false-positive risks")
    p_lint.add_argument("prompt_json", type=Path, help="Path to structured JSON prompt file")

    # rewrite
    p_rewrite = sub.add_parser("rewrite", help="Rewrite a prompt to reduce safety-filter false-positive risks")
    p_rewrite.add_argument("prompt_json", type=Path, help="Path to structured JSON prompt file")
    p_rewrite.add_argument("-o", "--output", type=Path, help="Output path for rewritten prompt JSON")

    # status
    p_status = sub.add_parser("status", help="Show job status")
    p_status.add_argument("job_id")

    # list
    p_list = sub.add_parser("list", help="List recent jobs")
    p_list.add_argument("--limit", type=int, default=20)

    # wait
    p_wait = sub.add_parser("wait", help="Wait for a job to finish and print its output path")
    p_wait.add_argument("job_id")
    p_wait.add_argument("--timeout", type=float, default=7200.0)
    p_wait.add_argument("--poll-interval", type=float, default=5.0)

    # worker
    p_worker = sub.add_parser("worker", help="Run the worker that processes pending jobs")
    p_worker.add_argument("--one-shot", action="store_true", help="Process one pending job and exit")
    p_worker.add_argument("--no-wait", action="store_true", help="Fail immediately if another worker is running")
    p_worker.add_argument("--queue-timeout", type=float, default=3600.0)

    args = parser.parse_args()

    if args.command == "submit":
        return cmd_submit(args)
    if args.command == "lint":
        return cmd_lint(args)
    if args.command == "rewrite":
        return cmd_rewrite(args)
    if args.command == "status":
        return cmd_status(args)
    if args.command == "list":
        return cmd_list(args)
    if args.command == "wait":
        return cmd_wait(args)
    if args.command == "worker":
        return cmd_worker(args)

    parser.error(f"Unknown command: {args.command}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
