#!/usr/bin/env python3
"""Image Studio client: queue and fetch images on the M1 Max.

The generation stack (models, jobs.db and the launchd worker) lives in
~/git/ideogram4-local on m1max. This wrapper runs from the Air and drives the
remote CLI over the LAN SSH key, so any Hermes agent can request an image
without a new service, port or secret.

Two engines share the one queue and worker: `ideogram4` (the main engine, JSON
prompts) and `flux2-klein` (fast natural-language drafts, 1216x832 in about three
minutes). Remote paths given to --prompt-json / --prompt-file / -o on the Max
are relative to IMAGEGEN_REMOTE_DIR; the job rows the remote CLI stores carry
absolute paths.

Environment:
    IMAGEGEN_HOST              SSH alias of the generation host (default: m1max)
    IMAGEGEN_REMOTE_DIR        repo dir relative to the remote home
                               (default: git/ideogram4-local)
    IMAGEGEN_STAGING           local download root (default: ~/image-studio/staging)
    IMAGEGEN_MIN_PER_JOB       minutes per Ideogram 4 job, for ETA (default: 21)
    IMAGEGEN_FLUX_MIN_PER_JOB  minutes per FLUX.2-klein job, for ETA (default: 3)
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
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

DEFAULT_HOST = "m1max"
DEFAULT_REMOTE_DIR = "git/ideogram4-local"
DEFAULT_STAGING = "~/image-studio/staging"
DEFAULT_MIN_PER_JOB = 21
DEFAULT_FLUX_MIN_PER_JOB = 3
DEFAULT_WIDTH = 1216
DEFAULT_HEIGHT = 832
SUPPORTED_ENGINES = ("ideogram4", "flux2-klein")

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
    flux_min_per_job: int = DEFAULT_FLUX_MIN_PER_JOB

    @classmethod
    def from_env(cls, env=None):
        env = os.environ if env is None else env
        return cls(
            host=env.get("IMAGEGEN_HOST", DEFAULT_HOST),
            remote_dir=env.get("IMAGEGEN_REMOTE_DIR", DEFAULT_REMOTE_DIR),
            staging=env.get("IMAGEGEN_STAGING", DEFAULT_STAGING),
            min_per_job=_minutes_from_env(
                env, "IMAGEGEN_MIN_PER_JOB", DEFAULT_MIN_PER_JOB
            ),
            flux_min_per_job=_minutes_from_env(
                env, "IMAGEGEN_FLUX_MIN_PER_JOB", DEFAULT_FLUX_MIN_PER_JOB
            ),
        )


def _minutes_from_env(env, name, default):
    raw = env.get(name, str(default))
    try:
        return int(raw)
    except ValueError:
        raise ValueError("{} must be an integer, got {!r}".format(name, raw))


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


def _engine_error(args):
    """Return one plain sentence for a bad submit, or None when it is valid."""
    if args.engine == "ideogram4":
        if args.prompt_json is None:
            return "ideogram4 needs --prompt-json"
        if args.prompt is not None:
            return "--prompt is for flux2-klein; use --prompt-json for ideogram4"
        if args.prompt_file is not None:
            return "--prompt-file is for flux2-klein; use --prompt-json for ideogram4"
        if args.seed is not None:
            return "--seed is only used by flux2-klein"
        return None

    if args.prompt_json is not None:
        return "flux2-klein takes a natural-language prompt, not --prompt-json"
    if (args.prompt is None) == (args.prompt_file is None):
        return "flux2-klein needs exactly one of --prompt or --prompt-file"
    return None


def _submit_reply(args, config, runner, remote_prompt, remote_output):
    """Run the remote submit and print the job id (or the --json payload)."""
    # The Ideogram argv stays byte-for-byte what phase 1 sent (no --engine), so
    # a new wrapper still works against a Max running an older CLI.
    if args.engine == "ideogram4":
        argv = ["submit", "--prompt-json", remote_prompt]
    else:
        argv = ["submit", "--engine", "flux2-klein", "--prompt-file", remote_prompt]
    argv.extend(
        ["-o", remote_output, "-W", int(args.width), "-H", int(args.height)]
    )
    if args.seed is not None:
        argv.extend(["--seed", int(args.seed)])

    submitted = runner(ssh_argv(config, remote_cli(config, *argv)))
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


def cmd_submit(args, cfg, runner):
    if args.engine not in SUPPORTED_ENGINES:
        print(
            "Unsupported engine {!r}: choose ideogram4 or flux2-klein".format(
                args.engine
            ),
            file=sys.stderr,
        )
        return 1

    error = _engine_error(args)
    if error:
        print(error, file=sys.stderr)
        return 1

    if args.prompt_file is not None:
        prompt_path = Path(args.prompt_file).expanduser()
        if not prompt_path.is_file():
            print("Prompt file not found: {}".format(prompt_path), file=sys.stderr)
            return 1
        prompt_text = prompt_path.read_text(encoding="utf-8")
    elif args.prompt_json is not None:
        prompt_path = Path(args.prompt_json).expanduser()
        if not prompt_path.is_file():
            print("Prompt file not found: {}".format(prompt_path), file=sys.stderr)
            return 1
        prompt_text = None
    else:
        prompt_path = None
        prompt_text = args.prompt

    if prompt_text is not None and not prompt_text.strip():
        print("prompt is empty", file=sys.stderr)
        return 1

    # Slug: --name, else the prompt-file stem, else the first six prompt
    # words (capped at 40 characters), then slugify.
    if args.name:
        slug = slugify(args.name)
    elif prompt_path is not None:
        slug = slugify(prompt_path.stem)
    else:
        slug = slugify(" ".join(prompt_text.split()[:6])[:40])
    token = secrets.token_hex(4)
    stem = "{}-{}".format(slug, token)
    suffix = ".json" if args.engine == "ideogram4" else ".txt"
    incoming_dir = remote_path(cfg.remote_dir, "studio-incoming")
    remote_prompt_incoming = remote_path(incoming_dir, stem + suffix)
    remote_prompt = remote_path("studio-incoming", stem + suffix)
    remote_output = remote_path("output", "studio", _today_str(), stem + ".png")

    made = runner(ssh_argv(cfg, "mkdir -p " + shlex.quote(incoming_dir)))
    if made.returncode != 0:
        print(
            (made.stderr or made.stdout).strip()
            or "could not create {} on {}".format(incoming_dir, cfg.host),
            file=sys.stderr,
        )
        return 1

    if prompt_path is not None:
        local_prompt = prompt_path.resolve()
        copied = runner(
            scp_to_remote_argv(cfg, local_prompt, remote_prompt_incoming)
        )
    else:
        # --prompt: upload a temp .txt so the text never touches a command
        # line, then remove it whatever scp does.
        handle = tempfile.NamedTemporaryFile(
            "w", suffix=".txt", encoding="utf-8", delete=False
        )
        local_prompt = Path(handle.name)
        try:
            with handle:
                handle.write(prompt_text)
            copied = runner(
                scp_to_remote_argv(cfg, local_prompt, remote_prompt_incoming)
            )
        finally:
            local_prompt.unlink(missing_ok=True)

    if copied.returncode != 0:
        print(
            (copied.stderr or copied.stdout).strip()
            or "could not copy the prompt to {}".format(cfg.host),
            file=sys.stderr,
        )
        return 1

    return _submit_reply(args, cfg, runner, remote_prompt, remote_output)


def _minutes_for(job, cfg):
    """Minutes a row costs the queue; a row without engine is an Ideogram job."""
    if str(job.get("engine") or "ideogram4") == "flux2-klein":
        return cfg.flux_min_per_job
    return cfg.min_per_job


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
    ahead = [
        other
        for other in listing
        if isinstance(other, dict)
        and other.get("id") != job_id
        and other.get("status") in ACTIVE_STATUSES
        and str(other.get("created_at") or "") < created_at
    ]
    queue_ahead = len(ahead)

    if job.get("status") in ACTIVE_STATUSES:
        eta_minutes = sum(_minutes_for(other, cfg) for other in ahead) + _minutes_for(
            job, cfg
        )
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
        description=(
            "Submit and fetch Ideogram 4 and FLUX.2-klein jobs on the M1 Max "
            "from the Air."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_submit = sub.add_parser("submit", help="Queue a generation job")
    p_submit.add_argument(
        "--prompt-json",
        type=Path,
        default=None,
        help="structured JSON prompt, uploaded as .json (ideogram4)",
    )
    p_submit.add_argument(
        "--prompt",
        default=None,
        help="natural-language prompt, uploaded as .txt (flux2-klein)",
    )
    p_submit.add_argument(
        "--prompt-file",
        type=Path,
        default=None,
        help="UTF-8 text prompt file (flux2-klein)",
    )
    p_submit.add_argument("--seed", type=int, default=None, help="FLUX seed")
    p_submit.add_argument("--name", default=None, help="Slug (default: prompt file stem)")
    p_submit.add_argument("-W", "--width", type=int, default=DEFAULT_WIDTH)
    p_submit.add_argument("-H", "--height", type=int, default=DEFAULT_HEIGHT)
    p_submit.add_argument(
        "--engine",
        default="ideogram4",
        help="ideogram4 (main) or flux2-klein (fast drafts)",
    )
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
