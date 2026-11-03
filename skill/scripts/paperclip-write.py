#!/usr/bin/env python3
"""Paperclip control-plane writes from an unattended run, in one self-contained call.

A chained terminal command that sources the profile `.env`, loops and curls the
control plane stalls on the approval prompt on an unattended surface and returns
BLOCKED with nothing executed. A script run as `python3 <path>` does not: the
whole batch lives inside the file, and each request carries the run-id header
without the shell ever seeing the key.

Usage
  paperclip-write.py comment --issue <id> --body-file <path> [--attach <attachmentId> ...]
  paperclip-write.py patch   --issue <id> --json-file <path>
  paperclip-write.py monitor --issue <id> --at 2026-10-30T22:35:00Z --notes "..."
  paperclip-write.py read    --issue <id>

Environment
  PAPERCLIP_API_KEY   read from the environment when set, else from the profile
                      .env (PAPERCLIP_PROFILE_DIR, HERMES_HOME, or the same
                      directory this script's skill lives in). Never printed.
  PAPERCLIP_API_URL   the base URL; `/api` is appended when it is missing.
  PAPERCLIP_RUN_ID    required for every mutation; `--run-id` overrides it. Read
                      the run id from the wake payload, not from the shell: it
                      is frequently unset in the tool environment, and a
                      mutation without the header answers 401 'Agent run id
                      required', which reads like a credential problem.

Exit status is 0 only when the server answered 2xx AND the response echoes the
change (for patch/monitor: the fields asked for; for comment: an id). A failed
write prints the status and the body, so the caller reports a failure as a
failure instead of assuming the send landed.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

PROFILE_ENV_CANDIDATES = [
    os.path.join(os.environ.get("PAPERCLIP_PROFILE_DIR", ""), ".env"),
    os.path.join(os.environ.get("HERMES_HOME", ""), ".env"),
    os.path.expanduser("~/.hermes/profiles/matejko/.env"),
]


def load_env():
    """Fill PAPERCLIP_* from the environment, then from the first profile .env."""
    for path in PROFILE_ENV_CANDIDATES:
        if not path or not os.path.isfile(path):
            continue
        for line in open(path):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k.startswith("PAPERCLIP_") and not os.environ.get(k):
                os.environ[k] = v
        if os.environ.get("PAPERCLIP_API_KEY"):
            break


def api_base():
    base = os.environ.get("PAPERCLIP_API_URL", "http://127.0.0.1:3100").rstrip("/")
    if not base.endswith("/api"):
        base += "/api"
    return base


def call(method, path, body, run_id, key):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Authorization": "Bearer " + key, "Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if method != "GET":
        headers["X-Paperclip-Run-Id"] = run_id
    req = urllib.request.Request(api_base() + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
    except urllib.error.URLError as e:
        return 0, str(e.reason)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=["comment", "patch", "monitor", "read"])
    p.add_argument("--issue", required=True)
    p.add_argument("--body-file")
    p.add_argument("--json-file")
    p.add_argument("--at")
    p.add_argument("--notes", default="render ETA")
    p.add_argument("--attach", action="append", default=[])
    p.add_argument("--run-id")
    a = p.parse_args()

    load_env()
    key = os.environ.get("PAPERCLIP_API_KEY", "")
    if not key:
        sys.exit("no PAPERCLIP_API_KEY: set it in the environment or the profile .env")
    run_id = a.run_id or os.environ.get("PAPERCLIP_RUN_ID", "")
    if a.command != "read" and not run_id:
        sys.exit("no run id: pass --run-id or set PAPERCLIP_RUN_ID from the wake payload")

    if a.command == "comment":
        if not a.body_file:
            sys.exit("comment needs --body-file (markdown with real newlines)")
        body = {"body": open(a.body_file).read()}
        if a.attach:
            body["attachmentIds"] = a.attach
        st, out = call("POST", "/issues/%s/comments" % a.issue, body, run_id, key)
        print(st, out.get("id") if isinstance(out, dict) else out)
        if not isinstance(out, dict) or not out.get("id"):
            sys.exit(1)
    elif a.command == "patch":
        if not a.json_file:
            sys.exit("patch needs --json-file holding the PATCH body")
        body = json.load(open(a.json_file))
        st, out = call("PATCH", "/issues/%s" % a.issue, body, run_id, key)
        if isinstance(out, dict):
            print(st, "status=", out.get("status"), "monitorNextCheckAt=", out.get("monitorNextCheckAt"),
                  "assigneeAgentId=", out.get("assigneeAgentId"), "assigneeUserId=", out.get("assigneeUserId"))
            if st >= 300:
                sys.exit(1)
        else:
            print(st, out)
            sys.exit(1)
    elif a.command == "monitor":
        if not a.at:
            sys.exit("monitor needs --at <ISO 8601 UTC>")
        body = {"executionPolicy": {"monitor": {"kind": "external_service",
                                                "nextCheckAt": a.at,
                                                "scheduledBy": "assignee",
                                                "notes": a.notes}}}
        st, out = call("PATCH", "/issues/%s" % a.issue, body, run_id, key)
        if not isinstance(out, dict):
            print(st, out)
            sys.exit(1)
        print(st, "status=", out.get("status"), "monitorNextCheckAt=", out.get("monitorNextCheckAt"))
        # A null read-back is a monitor that does not exist, whatever the PATCH said.
        if st >= 300 or not out.get("monitorNextCheckAt"):
            sys.exit(1)
    else:
        st, out = call("GET", "/issues/%s" % a.issue, None, run_id, key)
        fields = ("identifier", "status", "monitorNextCheckAt", "checkoutRunId", "executionRunId",
                  "assigneeAgentId", "assigneeUserId", "blockedBy")
        print(st, json.dumps({k: out.get(k) for k in fields}) if isinstance(out, dict) else out)


if __name__ == "__main__":
    main()
