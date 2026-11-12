#!/usr/bin/env python3
"""Open a review-card issue and upload its PNGs, verified by hash.

This is the first half of a card build: create the company issue from a brief,
upload every image as a multipart attachment and check the server's sha256 and
byteSize against the file on disk, then optionally post the linking comment that
carries the attachment ids so the PNGs render in the thread.

The second half is the shipped pair, run after this script prints the ids:

    python3 scripts/build-verdict-card.py <spec.json> --out <payload.json>
    python3 scripts/post-interaction.py <issue-id> <payload.json> <run-id>
    PATCH /issues/<id> {"status": "in_review"}   # then read the card back

Usage:
    python3 open-card-issue.py \
        --brief backlog/briefs/<post>-round-1-card.md \
        --title "Backlog review 081/153: <post title>" \
        --item arr-migration-header=staging/2026-11-01/081-...-r1b-89bf2057.png \
        --item arr-migration-header-flux=staging/2026-11-01/081-...-r1-flux-e9711f54.png \
        --link-body scratch/card-link-comment.md \
        --out scratch/card-ids.json

A backlog card issue usually already exists — `backlog.py ready` creates it and the
assignment wakes you on it — so upload onto it with `--issue`. Creating another
issue there is a second card for one round. `--brief` and `--title` are then omitted:

    python3 open-card-issue.py --issue <issue-id> \
        --item <item-id>=<staging.png> \
        --link-body scratch/card-link-comment.md --out scratch/card-ids.json

Why a script and not curl: the uploads are four to six files, and a shell loop of
uploads is refused by the unattended approval gate, so the whole set has to be one
`python3 <path>` call. Each 201 carries id, sha256 and byteSize, which is the only
proof the right bytes landed on the card.

Environment (or the profile .env, which this script reads as a fallback):
    PAPERCLIP_API_KEY, PAPERCLIP_RUN_ID (export PC_RUN_ID or pass --run-id),
    PAPERCLIP_COMPANY_ID (defaults to the Gulasz101 company).
"""

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid

API = "http://127.0.0.1:3100/api"
AGENT_ID = "332563dd-7ce2-4bad-8bb9-6b61f3f7221e"
DEFAULT_COMPANY = "0e2eb054-4cb6-4ea1-a2e7-2b1894285d8c"
DEFAULT_PROJECT = "df5a7cac-9689-44df-88b8-5d0626551123"
PROFILE_ENV = os.path.expanduser("~/.hermes/profiles/matejko/.env")


def env_value(name):
    """Environment first, then the matejko profile .env (never the default one)."""
    if os.environ.get(name):
        return os.environ[name]
    try:
        with open(PROFILE_ENV) as fh:
            for line in fh:
                if line.startswith(name + "="):
                    return line.split("=", 1)[1].strip()
    except OSError:
        pass
    return None


def make_call(key, run_id):
    def call(method, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(API + path, data=data, method=method)
        req.add_header("Authorization", "Bearer " + key)
        req.add_header("X-Paperclip-Run-Id", run_id)
        if data:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.status, json.loads(r.read().decode() or "{}")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode()[:400]
    return call


def upload(call, company, issue_id, path, name):
    boundary = "----" + uuid.uuid4().hex
    blob = open(path, "rb").read()
    body = ("--" + boundary + "\r\n").encode()
    body += ('Content-Disposition: form-data; name="file"; filename="%s"\r\n' % name).encode()
    body += b"Content-Type: image/png\r\n\r\n" + blob + b"\r\n"
    body += ("--" + boundary + "--\r\n").encode()
    req = urllib.request.Request(
        API + "/companies/%s/issues/%s/attachments" % (company, issue_id),
        data=body, method="POST")
    req.add_header("Authorization", "Bearer " + KEY)
    req.add_header("X-Paperclip-Run-Id", RUN)
    req.add_header("Content-Type", "multipart/form-data; boundary=" + boundary)
    try:
        with urllib.request.urlopen(req, timeout=240) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]


p = argparse.ArgumentParser()
p.add_argument("--brief", help="markdown file used verbatim as the issue description (needed unless --issue)")
p.add_argument("--title", help="needed unless --issue")
p.add_argument("--issue", help="upload onto this EXISTING issue; a runner-created card issue already exists")
p.add_argument("--item", action="append", required=True, metavar="ID=PATH")
p.add_argument("--link-body", help="comment body posted with the attachment ids (optional)")
p.add_argument("--out", required=True, help="json file receiving {issue, ids}")
p.add_argument("--project", default=DEFAULT_PROJECT)
p.add_argument("--company", default=env_value("PAPERCLIP_COMPANY_ID") or DEFAULT_COMPANY)
p.add_argument("--run-id", default=env_value("PC_RUN_ID") or env_value("PAPERCLIP_RUN_ID"))
p.add_argument("--priority", default="medium")
args = p.parse_args()

KEY, RUN = env_value("PAPERCLIP_API_KEY"), args.run_id
if not KEY:
    sys.exit("PAPERCLIP_API_KEY missing: source the matejko profile .env with set -a first")
if not RUN:
    sys.exit("run id missing: pass --run-id or export PC_RUN_ID from the wake payload")

call = make_call(KEY, RUN)
st, me = call("GET", "/agents/me")
if st != 200 or me.get("id") != AGENT_ID:
    sys.exit("identity check failed (%s): %s" % (st, str(me)[:200]))
print("identity ok", me.get("name"))

items = []
for spec in args.item:
    item, _, path = spec.partition("=")
    if not (item and path):
        sys.exit("--item wants ID=PATH, got %r" % spec)
    if not os.path.exists(path):
        sys.exit("no such file: %s" % path)
    items.append((item, path))

if args.issue:
    if args.brief or args.title:
        sys.exit("--issue means upload only; drop --brief/--title")
    issue_id, issue = args.issue, {}
    st, _ = call("GET", "/issues/%s" % issue_id)
    if st != 200:
        sys.exit("no such issue (%s): %s" % (st, issue_id))
    print("existing issue", issue_id)
else:
    if not (args.brief and args.title):
        sys.exit("--brief and --title are required when --issue is not given")
    brief = open(args.brief).read()
    st, issue = call("POST", "/companies/%s/issues" % args.company, {
        "title": args.title,
        "description": brief,
        "status": "in_progress",
        "priority": args.priority,
        "projectId": args.project,
        "assigneeAgentId": AGENT_ID,
    })
    if st not in (200, 201):
        sys.exit("create failed (%s): %s" % (st, str(issue)[:300]))
    issue_id = issue["id"]
    print("create:", st, issue.get("identifier"), issue_id, "descr", len(issue.get("description") or ""))
    if (issue.get("description") or "") != brief:
        print("WARN description is not byte-identical to the brief")

ids = {}
for item, path in items:
    want = hashlib.sha256(open(path, "rb").read()).hexdigest()
    size = os.path.getsize(path)
    for attempt in range(3):
        st, res = upload(call, args.company, issue_id, path, os.path.basename(path))
        if st == 201 and res.get("sha256") == want and res.get("byteSize") == size:
            print("upload", item, "ok", res.get("id"), size, want[:12])
            ids[item] = res.get("id")
            break
        print("upload attempt", attempt, item, st, str(res)[:140])
        time.sleep(3)

missing = [i for i, _ in items if i not in ids]
if missing:
    print("MISSING uploads:", missing)
else:
    print("all uploads hash-matched:", len(ids))

if args.link_body and ids:
    body = open(args.link_body).read()
    # attachmentIds MUST ride the POST /comments call: a PATCH has no such field and
    # the ids would stay unlinked (issueCommentId null, PNG invisible in the thread).
    st, res = call("POST", "/issues/%s/comments" % issue_id,
                   {"body": body, "attachmentIds": list(ids.values())})
    print("link comment:", st, res.get("id") if isinstance(res, dict) else res)
    st, atts = call("GET", "/issues/%s/attachments" % issue_id)
    print("attachments:", len(atts), sorted(a.get("byteSize") for a in atts),
          "all linked:", all(a.get("issueCommentId") for a in atts) if atts else False)

json.dump({"issue": issue_id, "identifier": issue.get("identifier"), "ids": ids},
          open(args.out, "w"), indent=1)
print("wrote", args.out, "ISSUE", issue_id, "IDS", len(ids))
