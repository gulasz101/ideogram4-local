#!/usr/bin/env bash
# Probe the nano banana engine DIRECTLY on the render host, bypassing the render queue.
#
# Use when the shared lane is deep (tens of pending Ideogram jobs, each ~21 min) and you
# need the engine's verdict in THIS minute -- e.g. its owner says the cookie was fixed and
# asks for a check render. A queued probe would answer hours later; this answers in seconds.
#
# It calls the worker's own generate_nanobanana(), so the request shape is exactly the one
# real renders use, and the proxy API key is read on the host by the worker's own code --
# no secret ever crosses into this file or into the Air.
#
# Output: one JSON line.
#   success -> {"ok": true, "path", "bytes", "dims": [w,h], "seconds", "magic"}
#   failure -> {"ok": false, "error": "<proxy body verbatim>"}      exit 3
#   busy    -> {"ok": false, "busy": true, "running": <n>}           exit 4
#
# Exit 4 is not a fault: a nanobanana job is already running, and a second concurrent
# request is the 429 ip_slot_full. Wait for that job; it measures the path for you.
#
# Usage:
#   scripts/probe-engine-direct.sh ["prompt"]
#   scripts/probe-engine-direct.sh "a flat grey server rack, no text"
#
# The image lands in /tmp on the host. Copy it back only when the probe is what you quote:
#   scp m1max:/tmp/nanobanana-probe-*.jpg ~/image-studio/staging/$(date +%F)/

set -uo pipefail

PROMPT="${1:-a plain grey server rack on a concrete floor, flat illustration, no text}"
HOST="${PROBE_HOST:-m1max}"
REMOTE_PY=/tmp/nanobanana-probe.py

TMPPY=$(mktemp -t nbprobe)
trap 'rm -f "$TMPPY"' EXIT

cat > "$TMPPY" <<'PY'
import base64, json, os, sqlite3, sys, time

sys.path.insert(0, "/Users/wojciechgula/git/ideogram4-local")
import ideogram4_local as m

DB = "/Users/wojciechgula/git/ideogram4-local/jobs.db"
try:
    conn = sqlite3.connect("file:%s?mode=ro" % DB, uri=True)
    running = conn.execute(
        "select count(*) from jobs where engine='nanobanana' and status='running'"
    ).fetchone()[0]
except Exception:
    running = 0
if running:
    print(json.dumps({"ok": False, "busy": True, "running": running}))
    sys.exit(4)

prompt = base64.b64decode(os.environ["PROBE_PROMPT_B64"]).decode("utf-8")
out = m.Path("/tmp/nanobanana-probe-%d.jpg" % int(time.time()))
started = time.time()
try:
    path = m.generate_nanobanana(prompt, out, 1376, 768, verbose=False)
except Exception as exc:
    print(json.dumps({"ok": False, "error": str(exc)[:800]}))
    sys.exit(3)

blob = path.read_bytes()
print(json.dumps({
    "ok": True,
    "path": str(path),
    "bytes": len(blob),
    "dims": m._image_size(blob),
    "seconds": round(time.time() - started, 1),
    "magic": blob[:4].hex(),
}))
PY

PROBE_PROMPT_B64=$(printf '%s' "$PROMPT" | base64 | tr -d '\n')

ssh -o ConnectTimeout=15 "$HOST" "cat > $REMOTE_PY" < "$TMPPY" || {
  echo '{"ok": false, "error": "could not stage the probe script on the host"}'
  exit 2
}

ssh -o ConnectTimeout=15 "$HOST" "PROBE_PROMPT_B64='$PROBE_PROMPT_B64' python3 $REMOTE_PY"
exit $?
