#!/usr/bin/env python3
"""Image Studio client: queue and fetch Ideogram 4 images on the M1 Max.

The generation stack (models, jobs.db and the launchd worker) lives in
~/git/ideogram4-local on m1max. This wrapper runs from the Air and drives the
remote CLI over the LAN SSH key, so any Hermes agent can request an image
without a new service, port or secret.

Remote paths given to --prompt-json / -o on the Max are relative to
IMAGEGEN_REMOTE_DIR; the job rows the remote CLI stores carry absolute paths.

Environment:
    IMAGEGEN_HOST         SSH alias of the generation host (default: m1max)
    IMAGEGEN_REMOTE_DIR   repo dir relative to the remote home
                          (default: git/ideogram4-local)
    IMAGEGEN_STAGING      local download root (default: ~/image-studio/staging)
    IMAGEGEN_MIN_PER_JOB  minutes per queued job, for ETA (default: 21)
"""

import argparse
import json
import os
import posixpath
import re
import secrets
import shlex
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

DEFAULT_HOST = "m1max"
DEFAULT_REMOTE_DIR = "git/ideogram4-local"
DEFAULT_STAGING = "~/image-studio/staging"
DEFAULT_MIN_PER_JOB = 21
DEFAULT_WIDTH = 1216
DEFAULT_HEIGHT = 832
SUPPORTED_ENGINES = ("ideogram4",)

SSH_OPTS = ["-o", "BatchMode=yes", "-o", "ConnectTimeout=10"]
ACTIVE_STATUSES = ("pending", "running")


@dataclass
class Result:
    """Minimal stand-in for subprocess.CompletedProcess."""

    returncode: int
    stdout: str = ""
    stderr: str = ""


class RemoteError(Exception):
    """A remote command failed; the message is safe to show the user."""


@dataclass
class Config:
    host: str = DEFAULT_HOST
    remote_dir: str = DEFAULT_REMOTE_DIR
    staging: str = DEFAULT_STAGING
    min_per_job: int = DEFAULT_MIN_PER_JOB

    @classmethod
    def from_env(cls, env=None):
        env = os.environ if env is None else env
        raw_min = env.get("IMAGEGEN_MIN_PER_JOB", str(DEFAULT_MIN_PER_JOB))
        try:
            min_per_job = int(raw_min)
        except ValueError:
            raise ValueError(
                "IMAGEGEN_MIN_PER_JOB must be an integer, got {!r}".format(raw_min)
            )
        return cls(
            host=env.get("IMAGEGEN_HOST", DEFAULT_HOST),
            remote_dir=env.get("IMAGEGEN_REMOTE_DIR", DEFAULT_REMOTE_DIR),
            staging=env.get("IMAGEGEN_STAGING", DEFAULT_STAGING),
            min_per_job=min_per_job,
        )


def run_command(argv):
    """Run one local process. All ssh/scp traffic goes through here."""
    proc = subprocess.run(argv, capture_output=True, text=True, check=False)
    return Result(proc.returncode, proc.stdout, proc.stderr)


def slugify(value):
    """Lowercase ASCII slug limited to [a-z0-9-]."""
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "prompt"


def _today_str():
    return datetime.now().strftime("%Y-%m-%d")


def _now_str():
    return datetime.now().isoformat(timespec="seconds")


def remote_path(*parts):
    return posixpath.join(*[part for part in parts if part])


def ssh_argv(cfg, command):
    return ["ssh"] + SSH_OPTS + [cfg.host, command]


def scp_target(cfg, path):
    # SFTP-mode scp (OpenSSH >= 9.0) passes paths verbatim; only the ssh
    # command strings go through a remote shell, so do not quote here.
    return "{}:{}".format(cfg.host, path)


def scp_to_remote_argv(cfg, local_path, remote):
    return ["scp"] + SSH_OPTS + [str(local_path), scp_target(cfg, remote)]


def scp_from_remote_argv(cfg, remote, local_path):
    return ["scp"] + SSH_OPTS + [scp_target(cfg, remote), str(local_path)]


def remote_cli(cfg, *args):
    """A shell command that runs the remote CLI from the repo dir."""
    cli = "python3 ideogram4_local.py " + " ".join(shlex.quote(str(a)) for a in args)
    return "cd {} && {}".format(shlex.quote(cfg.remote_dir), cli)


def status_command(cfg, job_id):
    return remote_cli(cfg, "status", job_id)


def list_command(cfg, limit):
    return remote_cli(cfg, "list", "--limit", limit)


def parse_json_output(text):
    """Parse JSON even when the remote printed log lines around it."""
    stripped = text.strip()
    if not stripped:
        raise ValueError("empty output")
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass
    starts = [i for i in (stripped.find("{"), stripped.find("[")) if i != -1]
    if not starts:
        raise ValueError("no JSON in output")
    decoded, _ = json.JSONDecoder().raw_decode(stripped[min(starts):])
    return decoded


def remote_json(cfg, runner, command):
    result = runner(ssh_argv(cfg, command))
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise RemoteError(detail or "remote command failed: {}".format(command))
    try:
        return parse_json_output(result.stdout)
    except ValueError as exc:
        raise RemoteError("could not parse remote JSON: {}".format(exc))


def cmd_submit(args, cfg, runner):
    if args.engine not in SUPPORTED_ENGINES:
        print(
            "Unsupported engine {!r}: only 'ideogram4' is available on the Max "
            "(FLUX support arrives in phase 6).".format(args.engine),
            file=sys.stderr,
        )
        return 1

    prompt_path = Path(args.prompt_json).expanduser()
    if not prompt_path.is_file():
        print("Prompt file not found: {}".format(prompt_path), file=sys.stderr)
        return 1

    slug = slugify(args.name if args.name else prompt_path.stem)
    token = secrets.token_hex(4)
    stem = "{}-{}".format(slug, token)
    incoming_dir = remote_path(cfg.remote_dir, "studio-incoming")
    remote_prompt_incoming = remote_path(incoming_dir, stem + ".json")
    remote_prompt = remote_path("studio-incoming", stem + ".json")
    remote_output = remote_path("output", "studio", _today_str(), stem + ".png")

    made = runner(ssh_argv(cfg, "mkdir -p " + shlex.quote(incoming_dir)))
    if made.returncode != 0:
        print(
            (made.stderr or made.stdout).strip()
            or "could not create {} on {}".format(incoming_dir, cfg.host),
            file=sys.stderr,
        )
        return 1

    copied = runner(
        scp_to_remote_argv(cfg, prompt_path.resolve(), remote_prompt_incoming)
    )
    if copied.returncode != 0:
        print(
            (copied.stderr or copied.stdout).strip()
            or "could not copy the prompt to {}".format(cfg.host),
            file=sys.stderr,
        )
        return 1

    submit = "cd {} && python3 ideogram4_local.py submit --prompt-json {} -o {} -W {} -H {}".format(
        shlex.quote(cfg.remote_dir),
        shlex.quote(remote_prompt),
        shlex.quote(remote_output),
        int(args.width),
        int(args.height),
    )
    submitted = runner(ssh_argv(cfg, submit))
    if submitted.returncode != 0:
        print(
            (submitted.stderr or submitted.stdout).strip() or "remote submit failed",
            file=sys.stderr,
        )
        return 1

    lines = [line.strip() for line in submitted.stdout.splitlines() if line.strip()]
    if not lines:
        print("remote submit printed no job id", file=sys.stderr)
        return 1
    job_id = lines[-1]

    if args.json:
        print(
            json.dumps(
                {
                    "job_id": job_id,
                    "engine": args.engine,
                    "remote_output": remote_output,
                    "submitted_at": _now_str(),
                },
                indent=2,
            )
        )
    else:
        print(job_id)
    return 0


def cmd_status(args, cfg, runner):
    try:
        job = remote_json(cfg, runner, status_command(cfg, args.job_id))
        listing = remote_json(cfg, runner, list_command(cfg, 200))
    except RemoteError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if not isinstance(job, dict):
        print("unexpected status output", file=sys.stderr)
        return 1
    if not isinstance(listing, list):
        listing = []

    created_at = str(job.get("created_at") or "")
    job_id = job.get("id")
    queue_ahead = 0
    for other in listing:
        if not isinstance(other, dict) or other.get("id") == job_id:
            continue
        if other.get("status") in ACTIVE_STATUSES and str(
            other.get("created_at") or ""
        ) < created_at:
            queue_ahead += 1

    if job.get("status") in ACTIVE_STATUSES:
        eta_minutes = (queue_ahead + 1) * cfg.min_per_job
    else:
        eta_minutes = 0

    job["queue_ahead"] = queue_ahead
    job["eta_minutes"] = eta_minutes
    print(json.dumps(job, indent=2))
    return 0


def cmd_fetch(args, cfg, runner):
    try:
        job = remote_json(cfg, runner, status_command(cfg, args.job_id))
    except RemoteError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if not isinstance(job, dict):
        print("unexpected status output", file=sys.stderr)
        return 1

    status = job.get("status")
    if status == "failed":
        print(job.get("error") or "job {} failed".format(args.job_id), file=sys.stderr)
        return 4
    if status in ACTIVE_STATUSES:
        print("job {} is still {}".format(args.job_id, status), file=sys.stderr)
        return 3
    if status != "done":
        print("job {} has unexpected status {!r}".format(args.job_id, status), file=sys.stderr)
        return 1

    remote_output = job.get("output_path")
    if not remote_output:
        print("job {} has no output_path".format(args.job_id), file=sys.stderr)
        return 1

    if args.dest:
        dest_dir = Path(args.dest).expanduser()
    else:
        dest_dir = Path(cfg.staging).expanduser() / _today_str()
    dest_dir.mkdir(parents=True, exist_ok=True)
    local_path = dest_dir.resolve() / posixpath.basename(remote_output)

    fetched = runner(scp_from_remote_argv(cfg, remote_output, local_path))
    if fetched.returncode != 0:
        print(
            (fetched.stderr or fetched.stdout).strip() or "scp failed",
            file=sys.stderr,
        )
        return 1
    if not local_path.is_file() or local_path.stat().st_size == 0:
        print("fetched file is missing or empty: {}".format(local_path), file=sys.stderr)
        return 1

    print(local_path)
    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        prog="imagegen",
        description="Submit and fetch Ideogram 4 jobs on the M1 Max from the Air.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_submit = sub.add_parser("submit", help="Queue a generation job")
    p_submit.add_argument("--prompt-json", required=True, type=Path)
    p_submit.add_argument("--name", default=None, help="Slug (default: prompt file stem)")
    p_submit.add_argument("-W", "--width", type=int, default=DEFAULT_WIDTH)
    p_submit.add_argument("-H", "--height", type=int, default=DEFAULT_HEIGHT)
    p_submit.add_argument("--engine", default="ideogram4")
    p_submit.add_argument("--json", action="store_true")

    p_status = sub.add_parser("status", help="Show a job with queue position and ETA")
    p_status.add_argument("job_id")

    p_fetch = sub.add_parser("fetch", help="Download a finished job")
    p_fetch.add_argument("job_id")
    p_fetch.add_argument("--dest", default=None, help="Local destination directory")

    return parser


def main(argv=None, runner=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        cfg = Config.from_env()
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    runner = runner or run_command

    if args.command == "submit":
        return cmd_submit(args, cfg, runner)
    if args.command == "status":
        return cmd_status(args, cfg, runner)
    if args.command == "fetch":
        return cmd_fetch(args, cfg, runner)

    parser.error("unknown command: {}".format(args.command))
    return 1


if __name__ == "__main__":
    sys.exit(main())
