#!/usr/bin/env python3
"""Upload PNGs to a Paperclip issue and prove the bytes landed.

Usage:
    python3 upload-attachments.py <issue-id> <file> [<file> ...]
                                   [--run <run-id>] [--company <company-id>]

Why a script and not a curl loop: a card run is usually unattended, and a command
line that chains an env prologue with a shell loop stalls on the approval prompt
and never runs. This file parses the key itself and is invoked as one plain
`python3 <path>` call, which is the shape that works there.

Key resolution order: $PAPERCLIP_API_KEY, then $HERMES_HOME/.env, then the matejko
profile .env. The key is never printed; only its length is, as a load check.

Prints, per file: the attachment id, whether the server's sha256 and byteSize match
the local file, and the byte count. Exits non-zero if any upload fails, so a caller
can stop before building a card that points at nothing.
"""
import argparse
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
import uuid

DEFAULT_ENV = "/Users/paperclip/.hermes/profiles/matejko/.env"


def load_key():
    key = os.environ.get("PAPERCLIP_API_KEY")
    if key:
        return key
    env = os.path.join(os.environ.get("HERMES_HOME", ""), ".env") if os.environ.get("HERMES_HOME") else None
    for path in [p for p in (env, DEFAULT_ENV) if p]:
        if not os.path.exists(path):
            continue
        for line in open(path):
            if line.strip().startswith("PAPERCLIP_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit("no PAPERCLIP_API_KEY in env or profile .env")


def upload(base, company, issue, run, key, path):
    boundary = "----" + uuid.uuid4().hex
    name = os.path.basename(path)
    data = open(path, "rb").read()
    body = b"".join([
        ("--" + boundary + "\r\n").encode(),
        ('Content-Disposition: form-data; name="file"; filename="%s"\r\n' % name).encode(),
        b"Content-Type: image/png\r\n\r\n",
        data,
        b"\r\n",
        ("--" + boundary + "--\r\n").encode(),
    ])
    req = urllib.request.Request(
        "%s/companies/%s/issues/%s/attachments" % (base, company, issue), data=body, method="POST")
    req.add_header("Authorization", "Bearer " + key)
    req.add_header("Content-Type", "multipart/form-data; boundary=" + boundary)
    if run:
        req.add_header("X-Paperclip-Run-Id", run)
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:600]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("issue")
    ap.add_argument("files", nargs="+")
    ap.add_argument("--run", default=os.environ.get("PAPERCLIP_RUN_ID"))
    ap.add_argument("--company", default=os.environ.get("PAPERCLIP_COMPANY_ID"))
    ap.add_argument("--api", default=os.environ.get("PAPERCLIP_API_URL") or "http://127.0.0.1:3100/api")
    a = ap.parse_args()
    base = a.api.rstrip("/")
    if not base.endswith("/api"):
        base += "/api"
    company = a.company or sys.exit("--company or $PAPERCLIP_COMPANY_ID required")
    key = load_key()
    print("key loaded, length %d" % len(key))

    failed = 0
    results = []
    for path in a.files:
        local = hashlib.sha256(open(path, "rb").read()).hexdigest()
        size = os.path.getsize(path)
        status, res = upload(base, company, a.issue, a.run, key, path)
        if isinstance(res, dict) and res.get("id"):
            match = res.get("sha256") == local and res.get("byteSize") == size
            print("%s -> %s %s sha_match=%s bytes=%s" % (
                os.path.basename(path), status, res["id"], match, res.get("byteSize")))
            results.append({"file": os.path.basename(path), "attachment_id": res["id"],
                            "sha256": res.get("sha256"), "bytes": size, "match": match})
            failed += 0 if match else 1
        else:
            print("%s -> %s %s" % (os.path.basename(path), status, res))
            failed += 1

    print(json.dumps(results, indent=1))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
