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

# ---------------------------------------------------------------------------
# Defaults tuned for an Apple Silicon M1 Max with 32 GB unified RAM.
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
MODELS_DIR = Path(os.environ.get("IDEOGRAM4_MODELS_DIR", SCRIPT_DIR / "models"))
OUTPUT_DIR = Path(os.environ.get("IDEOGRAM4_OUTPUT_DIR", SCRIPT_DIR / "output"))
LOCK_FILE = Path(os.environ.get("IDEOGRAM4_LOCK_FILE", SCRIPT_DIR / ".lock"))
DB_PATH = Path(os.environ.get("IDEOGRAM4_DB", SCRIPT_DIR / "jobs.db"))

DEFAULT_SD_CPP = Path("~/sd.cpp").expanduser()
SD_CPP_DIR = Path(os.environ.get("SD_CPP_DIR", DEFAULT_SD_CPP))
SD_CLI = SD_CPP_DIR / "build" / "bin" / "sd-cli"

DEFAULT_WIDTH = 1216
DEFAULT_HEIGHT = 832

MODEL_URLS = {
    "ideogram4-Q4_0.gguf": "https://huggingface.co/leejet/ideogram-4-GGUF/resolve/main/ideogram4-Q4_0.gguf",
    "ideogram4_uncond-Q4_0.gguf": "https://huggingface.co/leejet/ideogram-4-GGUF/resolve/main/ideogram4_uncond-Q4_0.gguf",
    "Qwen3-VL-8B-Instruct-Q4_K_M.gguf": "https://huggingface.co/unsloth/Qwen3-VL-8B-Instruct-GGUF/resolve/main/Qwen3-VL-8B-Instruct-Q4_K_M.gguf",
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
        "flux2-vae.safetensors": 336_213_556,
    }
    return hints.get(name, 1_000_000_000)


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
        return json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return prompt_value.strip()


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

    models = ensure_models()
    prompt = build_prompt(prompt_type, prompt_value)

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
