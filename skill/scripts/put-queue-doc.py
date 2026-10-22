#!/usr/bin/env python3
"""Rebuild the backlog runner's `queue` issue document and PUT it in one go.

Wraps scripts/build-queue-doc.py and the Paperclip document PUT so the runner
wake is a single command instead of a hand-typed body, a baseRevisionId lookup
and a JSON payload. The key is read from the profile .env and never printed.

Usage:
    python3 put-queue-doc.py --issue-id <runnerIssueId> --run-id <runId>

Prints: HTTP status, the new latestRevisionId and the live-slot line.
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ENV = os.path.expanduser("~/.hermes/profiles/matejko/.env")
API = os.environ.get("PAPERCLIP_API_URL", "http://127.0.0.1:3100/api").rstrip("/")
if not API.endswith("/api"):
    API += "/api"


def api_key():
    with open(ENV) as f:
        for line in f:
            if line.startswith("PAPERCLIP_API_KEY="):
                return line.split("=", 1)[1].strip()
    sys.exit("no PAPERCLIP_API_KEY in the profile .env")


def curl(args):
    return subprocess.run(["curl", "-s", *args], capture_output=True, text=True).stdout


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--issue-id", required=True, help="the runner issue that holds the document")
    ap.add_argument("--run-id", required=True, help="run id for the X-Paperclip-Run-Id header")
    ap.add_argument("--backlog-dir", default=os.path.expanduser("~/image-studio/backlog"))
    args = ap.parse_args()

    body = subprocess.run(
        [sys.executable, os.path.join(HERE, "build-queue-doc.py"), "--backlog-dir", args.backlog_dir],
        capture_output=True, text=True, check=True).stdout

    key = api_key()
    doc_url = f"{API}/issues/{args.issue_id}/documents/queue"
    cur = json.loads(curl(["-H", f"Authorization: Bearer {key}", doc_url]))
    base = cur.get("latestRevisionId")

    payload = {"title": "Queue", "format": "markdown", "body": body, "baseRevisionId": base}
    path = "/tmp/queue-put.json"
    with open(path, "w") as f:
        json.dump(payload, f)

    out = curl(["-w", "\nHTTP=%{http_code}", "-X", "PUT",
                "-H", f"Authorization: Bearer {key}",
                "-H", f"X-Paperclip-Run-Id: {args.run_id}",
                "-H", "Content-Type: application/json",
                "--data-binary", f"@{path}", doc_url])
    code = out.rsplit("\nHTTP=", 1)[-1]
    raw = out.rsplit("\nHTTP=", 1)[0]
    try:
        j = json.loads(raw)
    except json.JSONDecodeError:
        print("HTTP", code, "RAW", raw[:500])
        return 1
    if j.get("error") or str(j.get("code", "")).startswith("conflict"):
        print("HTTP", code, "error:", j.get("message") or j.get("code"),
              "- fetch the document, merge, retry")
        return 1
    print("HTTP", code, "| latestRevisionId", j.get("latestRevisionId"),
          "| chars", len(j.get("body") or ""))
    for line in (j.get("body") or "").split("\n"):
        if line.startswith("**Live slot:**") or line.startswith("**Needs a render"):
            print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
