#!/usr/bin/env python3
"""
Progress notifier for the Ideogram 4 local worker.

Reads the worker log at `output/worker.log` looking for `stable-diffusion.cpp`
denoising progress lines like:

    |=====>                                            | 2/20 - 60.96s/it

Posts a Mattermost update at 25%, 50%, 75%, 90%, and done.

Intended to be run as a background watcher while the worker is active.
"""

import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
LOG_FILE = SCRIPT_DIR / "output" / "worker.log"
NOTIFIED_FILE = SCRIPT_DIR / ".notified_milestones"

MATTERMOST_CHANNEL_ID = os.environ.get("MATTERMOST_IDEOGRAM4_CHANNEL_ID", "mrnhuzmr63fuzrbky893j4if6c")
MATTERMOST_SERVER = os.environ.get("MATTERMOST_SERVER", "https://chat.voitech.dev")


def parse_progress(line: str) -> tuple[int, int] | None:
    m = re.search(r"\|\s*(\d+)/(\d+)\s*-", line)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def load_notified() -> set[int]:
    try:
        with NOTIFIED_FILE.open() as f:
            return {int(x) for x in f.read().split() if x.isdigit()}
    except FileNotFoundError:
        return set()


def save_notified(milestones: set[int]) -> None:
    NOTIFIED_FILE.write_text("\n".join(str(m) for m in sorted(milestones)))


def post_to_mattermost(message: str) -> None:
    token = os.environ.get("MATTERMOST_BOT_TOKEN")
    if not token:
        # Try to read from the Hermes config location if available.
        token_path = Path.home() / ".hermes" / "profiles" / "andrzej" / ".mattermost-token"
        if token_path.exists():
            token = token_path.read_text().strip()
    if not token:
        print(f"No Mattermost token available; would post: {message}", file=sys.stderr)
        return

    url = f"{MATTERMOST_SERVER.rstrip('/')}/api/v4/posts"
    payload = json.dumps({
        "channel_id": MATTERMOST_CHANNEL_ID,
        "message": message,
    }).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"Posted to Mattermost: {resp.status}", file=sys.stderr)
    except Exception as exc:
        print(f"Failed to post to Mattermost: {exc}", file=sys.stderr)


def maybe_notify(current: int, total: int, notified: set[int]) -> set[int]:
    if total == 0:
        return notified
    pct = int(current * 100 / total)
    milestones = {25, 50, 75, 90, 100}
    updated = set(notified)
    for m in milestones:
        if pct >= m and m not in updated:
            post_to_mattermost(
                f"🖼️ Ideogram 4 local worker progress: **{pct}%** ({current}/{total} denoising steps)"
            )
            updated.add(m)
    return updated


def main() -> None:
    print("Ideogram 4 progress notifier started", file=sys.stderr)
    notified = load_notified()
    last_step = 0
    last_total = 20

    # Notify start if no milestones yet.
    if not notified:
        post_to_mattermost("🖼️ Ideogram 4 local worker started. ETA ~21 minutes for the current image.")
        notified.add(0)
        save_notified(notified)

    while True:
        if LOG_FILE.exists():
            lines = LOG_FILE.read_text().splitlines()
            for line in lines:
                progress = parse_progress(line)
                if progress:
                    current, total = progress
                    if current > last_step:
                        last_step = current
                        last_total = total
                        print(f"Detected progress: {current}/{total}", file=sys.stderr)
                        notified = maybe_notify(current, total, notified)
                        save_notified(notified)

            # If we see the completion marker, post done and exit.
            if any("save result image" in line for line in lines):
                if 100 not in notified:
                    post_to_mattermost("🖼️ Ideogram 4 local worker finished an image.")
                    notified.add(100)
                    save_notified(notified)
                break

        time.sleep(30)

    print("Ideogram 4 progress notifier finished", file=sys.stderr)


if __name__ == "__main__":
    main()
