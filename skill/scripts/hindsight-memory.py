#!/usr/bin/env python3
"""Hindsight memory access without the reranker.

The ranked paths (hindsight_recall, hindsight_reflect) go through a reranker
that can time out. The bank's REST API serves the same memories without it,
and it is the only way to get a memory *id*: hindsight_retain returns a
receipt ("Memory queued for storage"), not an id.

Usage:
    hindsight-memory.py list [SUBSTRING] [--limit N] [--tag TAG] [--state STATE] [--all]
    hindsight-memory.py get MEMORY_ID
    hindsight-memory.py invalidate MEMORY_ID --reason "..."
    hindsight-memory.py edit MEMORY_ID --text "..."

`list` prints one memory per line as: <id>  <tags>  <type/state>  <text>
`get` prints the full JSON of one memory.
`invalidate` retires a fact into the curation archive; `edit` rewrites a
fact's text in place. Both accept world/experience facts only - an
observation is derived from its sources, so curate those instead.

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
                name, _, value = line.partition("=")
                if name == "HINDSIGHT_API_KEY":
                    return value.strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    die("no HINDSIGHT_API_KEY in the environment or in the profile .env")


class ApiError(Exception):
    """A failed API call, carrying the server's own message."""

    def __init__(self, code, body, url):
        super().__init__(f"HTTP {code} from {url}\n{body}")
        self.code = code
        self.body = body
        self.url = url


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
        raise ApiError(exc.code, body, url)
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
    state = None
    needle = None
    fetch_all = False
    rest = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--limit" and i + 1 < len(args):
            limit = int(args[i + 1]); i += 2; continue
        if a == "--tag" and i + 1 < len(args):
            tag = args[i + 1]; i += 2; continue
        if a == "--state" and i + 1 < len(args):
            state = args[i + 1]; i += 2; continue
        if a == "--all":
            fetch_all = True; i += 1; continue
        rest.append(a); i += 1
    if rest:
        needle = " ".join(rest).lower()

    base = f"{api}/v1/default/banks/{urllib.parse.quote(bank)}/memories/list"
    memories = []
    offset = 0
    while True:
        url = f"{base}?limit={limit}&offset={offset}"
        if state:
            url += f"&state={urllib.parse.quote(state)}"
        try:
            page = call(url, key)
        except ApiError as exc:
            die(str(exc))
        batch = as_list(page)
        memories += batch
        offset += len(batch)
        total = page.get("total") if isinstance(page, dict) else None
        if not fetch_all or not batch or (total is not None and offset >= total):
            break

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
        print(
            f"{mem.get('id', '?')}  [{','.join(tags)}]  "
            f"{mem.get('fact_type', '?')}/{mem.get('state', '?')}  {one_line}"
        )
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
    try:
        mem = call(url, key)
    except ApiError as exc:
        if exc.code == 404:
            die(
                f"no live memory with id {mem_id}. A swept observation answers 404 "
                "here too - that is how a curated observation looks, not a lost "
                "memory.",
            )
        die(str(exc))
    print(json.dumps(mem, indent=2, ensure_ascii=False))
    return 0


def _curate(api, bank, key, mem_id, payload):
    """PATCH one memory unit, turning the observation refusal into a route."""
    url = f"{api}/v1/default/banks/{urllib.parse.quote(bank)}/memories/{urllib.parse.quote(mem_id)}"
    try:
        return call(url, key, method="PATCH", payload=payload)
    except ApiError as exc:
        if "observation" in exc.body:
            die(
                "that memory is an observation, and the API refuses to curate "
                "those: they are derived and regenerate from their sources.\n"
                "Curate the world/experience facts it was consolidated from - "
                "invalidating or editing a source fact sweeps the observations "
                "built on it. The source ids are in `get <id>` -> "
                "source_memory_ids.",
            )
        die(str(exc))


def _report(unit, verb):
    if not isinstance(unit, dict):
        print(f"ok ({verb})")
        return
    print(
        f"{unit.get('id', '?')}  {verb}  state={unit.get('state')}  "
        f"reason={unit.get('invalidation_reason')}"
    )
    if unit.get("text"):
        print("  " + " ".join(unit["text"].split()))


def cmd_invalidate(api, bank, key, args):
    reason = None
    mem_id = None
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--reason" and i + 1 < len(args):
            reason = args[i + 1]; i += 2; continue
        if mem_id is None:
            mem_id = a
        i += 1
    if not mem_id:
        die("invalidate needs a memory id")
    if not reason:
        die("invalidate needs --reason: the reason is what makes the curation auditable")
    unit = _curate(api, bank, key, mem_id, {"state": "invalidated", "reason": reason})
    _report(unit, "invalidated")
    return 0


def cmd_edit(api, bank, key, args):
    text = None
    mem_id = None
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--text" and i + 1 < len(args):
            text = args[i + 1]; i += 2; continue
        if mem_id is None:
            mem_id = a
        i += 1
    if not mem_id or text is None:
        die("edit needs a memory id and --text")
    unit = _curate(api, bank, key, mem_id, {"text": text})
    _report(unit, "edited")
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
    if cmd == "invalidate":
        return cmd_invalidate(api, bank, key, args)
    if cmd == "edit":
        return cmd_edit(api, bank, key, args)
    die(f"unknown command {cmd!r}; expected 'list', 'get', 'invalidate' or 'edit'")


if __name__ == "__main__":
    sys.exit(main())
