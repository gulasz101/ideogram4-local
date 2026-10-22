#!/usr/bin/env python3
"""Hindsight memory access without the reranker.

The ranked paths (hindsight_recall, hindsight_reflect) go through a reranker
that can time out. The bank's REST API serves the same memories without it,
and it is the only way to get a memory *id*: hindsight_retain returns a
receipt ("Memory queued for storage"), not an id.

Usage:
    hindsight-memory.py list [SUBSTRING] [--limit N] [--tag TAG]
    hindsight-memory.py get MEMORY_ID

`list` prints one memory per line as: <id>  <tags>  <text>
`get` prints the full JSON of one memory.

The key and the bank id come from the profile config; the key is never
printed. A reranker failure shows up as a 500 on the ranked path while this
list path still answers - that is the tell that the bank is reachable and
only the ranking is down.
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

PROFILE = os.environ.get("HERMES_PROFILE", "matejko")
HOME = os.path.expanduser("~")
CONFIG = os.path.join(HOME, ".hermes", "profiles", PROFILE, "hindsight", "config.json")
ENV_FILE = os.path.join(HOME, ".hermes", "profiles", PROFILE, ".env")


def die(msg, code=1):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def load_config():
    try:
        with open(CONFIG) as fh:
            cfg = json.load(fh)
    except FileNotFoundError:
        die(f"no hindsight config at {CONFIG}")
    except json.JSONDecodeError as exc:
        die(f"hindsight config is not valid JSON: {exc}")

    api = cfg.get("api_url") or cfg.get("apiUrl")
    if not api:
        die("hindsight config has no api_url")

    bank = cfg.get("bank_id_template") or cfg.get("bank_id") or cfg.get("bankId")
    if not bank:
        die("hindsight config has no bank_id_template")
    # Templates carry a {profile} placeholder; fill it with the profile name.
    bank = bank.replace("{profile}", PROFILE).format(profile=PROFILE)
    return api.rstrip("/"), bank


def load_key():
    key = os.environ.get("HINDSIGHT_API_KEY")
    if key:
        return key.strip()
    try:
        with open(ENV_FILE) as fh:
            for line in fh:
                line = line.strip()
                if line.startswith("HINDSIGHT_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    die("no HINDSIGHT_API_KEY in the environment or in the profile .env")


def call(url, key, method="GET", payload=None):
    req = urllib.request.Request(url, method=method)
    req.add_header("Authorization", f"Bearer {key}")
    req.add_header("Accept", "application/json")
    if payload is not None:
        req.add_header("Content-Type", "application/json")
        req.data = json.dumps(payload).encode()
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")[:400]
        die(f"HTTP {exc.code} from {url}\n{body}")
    except urllib.error.URLError as exc:
        die(f"cannot reach {url}: {exc.reason}")


def as_list(payload):
    """The list route returns a bare list or a {memories:[...]} envelope."""
    if isinstance(payload, list):
        return payload
    for key in ("memories", "items", "results", "data"):
        if isinstance(payload, dict) and isinstance(payload.get(key), list):
            return payload[key]
    return []


def cmd_list(api, bank, key, args):
    limit = 400
    tag = None
    needle = None
    rest = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--limit" and i + 1 < len(args):
            limit = int(args[i + 1]); i += 2; continue
        if a == "--tag" and i + 1 < len(args):
            tag = args[i + 1]; i += 2; continue
        rest.append(a); i += 1
    if rest:
        needle = " ".join(rest).lower()

    url = f"{api}/v1/default/banks/{urllib.parse.quote(bank)}/memories/list?limit={limit}&offset=0"
    memories = as_list(call(url, key))

    hits = 0
    for mem in memories:
        text = mem.get("text") or mem.get("content") or mem.get("memory") or ""
        tags = mem.get("tags") or []
        if isinstance(tags, str):
            tags = [tags]
        if tag and tag not in tags:
            continue
        if needle and needle not in text.lower():
            continue
        hits += 1
        one_line = " ".join(text.split())
        print(f"{mem.get('id', '?')}  [{','.join(tags)}]  {one_line}")
    print(f"--- {hits} of {len(memories)} memories listed", file=sys.stderr)
    if not hits and needle:
        print(
            "No match. The list is not ranked, so a memory whose text shares no "
            "words with the query is still present - try a distinctive phrase "
            "from the reason, or raise --limit.",
            file=sys.stderr,
        )
    return 0


def cmd_get(api, bank, key, args):
    if not args:
        die("get needs a memory id")
    mem_id = args[0]
    url = f"{api}/v1/default/banks/{urllib.parse.quote(bank)}/memories/{urllib.parse.quote(mem_id)}"
    mem = call(url, key)
    print(json.dumps(mem, indent=2, ensure_ascii=False))
    return 0


def main():
    if len(sys.argv) < 2:
        die(__doc__)
    cmd = sys.argv[1]
    args = sys.argv[2:]
    api, bank = load_config()
    key = load_key()
    if cmd == "list":
        return cmd_list(api, bank, key, args)
    if cmd == "get":
        return cmd_get(api, bank, key, args)
    die(f"unknown command {cmd!r}; expected 'list' or 'get'")


if __name__ == "__main__":
    sys.exit(main())
