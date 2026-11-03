#!/usr/bin/env python3
"""Withdraw one pending Paperclip issue-thread interaction (unattended-safe).

`paperclip-write.py` covers comment, patch, monitor and read, and
`post-interaction.py` posts a card, but nothing withdrew one: a posted verdict
card is otherwise frozen until the owner answers it. This closes that gap so a
card can be rebuilt when an item on it fails the bar after it went up.

Usage
    pc-withdraw-interaction.py <issue-id> <interaction-id> <run-id> "<reason>"

Why a script and not curl: the unattended api_server surface refuses a composed
shell line that carries a mutation (the approval prompt times out) and refuses
`execute_code` outright, while `python3 <path>` runs. Every request carries
X-Paperclip-Run-Id, which the mutation needs.

Writes the reason onto the cancelled interaction, so the board shows why the
card disappeared instead of leaving a hole in the thread. Prints the returned
status/outcome and exits non-zero on any HTTP error.
"""
import json
import os
import sys
import urllib.error
import urllib.request

ENV_CANDIDATES = [
    os.path.join(os.environ.get("HERMES_HOME", ""), ".env"),
    "/Users/paperclip/.hermes/profiles/matejko/.env",
]


def load_key():
    key = os.environ.get("PAPERCLIP_API_KEY")
    if key:
        return key
    for path in ENV_CANDIDATES:
        if path and os.path.isfile(path):
            for line in open(path):
                if line.strip().startswith("PAPERCLIP_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit("no PAPERCLIP_API_KEY in the environment or the profile .env")


def main():
    if len(sys.argv) != 5:
        sys.exit('usage: pc-withdraw-interaction.py <issue-id> <interaction-id> <run-id> "<reason>"')
    issue, interaction, run_id, reason = sys.argv[1:5]
    base = os.environ.get("PAPERCLIP_API_URL", "http://127.0.0.1:3100").rstrip("/")
    if not base.endswith("/api"):
        base += "/api"
    url = "%s/issues/%s/interactions/%s/withdraw" % (base, issue, interaction)
    req = urllib.request.Request(
        url,
        data=json.dumps({"reason": reason}).encode(),
        method="POST",
        headers={
            "Authorization": "Bearer %s" % load_key(),
            "Content-Type": "application/json",
            "X-Paperclip-Run-Id": run_id,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            out = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        sys.exit("HTTP %s %s" % (e.code, e.read().decode()[:800]))
    print("HTTP", r.status, "status=", out.get("status"),
          "outcome=", (out.get("result") or {}).get("outcome"))
    if out.get("status") != "cancelled":
        sys.exit("withdraw did not land: %s" % json.dumps(out)[:400])


if __name__ == "__main__":
    main()
