#!/usr/bin/env bash
# Ideogram 4 local worker status publisher.
# Posts progress updates and finished-image attachments to the dedicated
# Mattermost channel using the Hermes andrzej profile's MATTERMOST_TOKEN.

set -euo pipefail

REPO_DIR="$HOME/git/ideogram4-local"
STATE_DIR="$HOME/.ideogram4-local"
STATE_FILE="$STATE_DIR/.notified_done_jobs"

CHANNEL_ID="ygs1pwhzi7grurg9poui33oqja"
WORKER_LOG="$REPO_DIR/output/worker.log"

# Load Mattermost credentials from the andrzej profile .env.
set -a
source "$HOME/.hermes/profiles/andrzej/.env"
set +a

if [[ -z "${MATTERMOST_TOKEN:-}" || -z "${MATTERMOST_URL:-}" ]]; then
    echo "MATTERMOST_TOKEN and MATTERMOST_URL must be set" >&2
    exit 1
fi

BASE="${MATTERMOST_URL%/}"

mkdir -p "$STATE_DIR"
touch "$STATE_FILE"

cd "$REPO_DIR"
export IDEOGRAM4_MODELS_DIR="${IDEOGRAM4_MODELS_DIR:-$HOME/sd.cpp-models}"

# Fetch jobs as JSON
JOBS_JSON=$(python3 - <<'PY'
import json, sqlite3
conn = sqlite3.connect('jobs.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("SELECT * FROM jobs ORDER BY created_at")
rows = [dict(r) for r in cur.fetchall()]
conn.close()
print(json.dumps(rows))
PY
)

NOTIFIED=$(sort -u "$STATE_FILE")

pending=$(echo "$JOBS_JSON" | jq '[.[] | select(.status == "pending")] | length')
running=$(echo "$JOBS_JSON" | jq '[.[] | select(.status == "running")] | length')
done=$(echo "$JOBS_JSON" | jq '[.[] | select(.status == "done")] | length')
failed=$(echo "$JOBS_JSON" | jq '[.[] | select(.status == "failed")] | length')

worker_alive=0
if pgrep -q -f 'ideogram4_local.py worker'; then worker_alive=1; fi
sdcli_alive=0
if pgrep -q -f 'sd-cli'; then sdcli_alive=1; fi

progress=$(tail -3 "$WORKER_LOG" 2>/dev/null | tail -1 || echo "no log")

# Helper: post plain message
post_message() {
    local msg="$1"
    curl -s -o /dev/null -w "%{http_code}" \
        -H "Authorization: Bearer $MATTERMOST_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"channel_id\":\"$CHANNEL_ID\",\"message\":$(echo "$msg" | jq -Rs .)}" \
        "$BASE/api/v4/posts"
}

# Helper: upload file and return file id
upload_file() {
    local path="$1"
    local resp
    resp=$(curl -s -H "Authorization: Bearer $MATTERMOST_TOKEN" \
        -F "channel_id=$CHANNEL_ID" \
        -F "files=@$path" \
        "$BASE/api/v4/files")
    echo "$resp" | jq -r '.file_infos[0].id // empty'
}

# Announce newly done images
new_done_ids=$(echo "$JOBS_JSON" | jq -r '.[] | select(.status == "done") | .id')
while IFS= read -r job_id; do
    [[ -z "$job_id" ]] && continue
    if ! echo "$NOTIFIED" | grep -qxF -- "$job_id"; then
        output_path=$(echo "$JOBS_JSON" | jq -r --arg id "$job_id" '.[] | select(.id == $id) | .output_path')
        width=$(echo "$JOBS_JSON" | jq -r --arg id "$job_id" '.[] | select(.id == $id) | .width // "?"')
        height=$(echo "$JOBS_JSON" | jq -r --arg id "$job_id" '.[] | select(.id == $id) | .height // "?"')

        file_id=""
        if [[ -f "$output_path" ]]; then
            file_id=$(upload_file "$output_path") || true
        fi

        msg=$(cat <<EOF
🎉 **Ideogram 4 finished an image!**
- Job: \`$job_id\`
- Output: \`$output_path\`
- Dimensions: ${width}x${height}
EOF
)
        if [[ -n "$file_id" ]]; then
            status=$(curl -s -o /dev/null -w "%{http_code}" \
                -H "Authorization: Bearer $MATTERMOST_TOKEN" \
                -H "Content-Type: application/json" \
                -d "{\"channel_id\":\"$CHANNEL_ID\",\"message\":$(echo "$msg" | jq -Rs .),\"file_ids\":[\"$file_id\"]}" \
                "$BASE/api/v4/posts")
        else
            status=$(post_message "$msg")
        fi

        if [[ "$status" == "201" ]]; then
            echo "$job_id" >> "$STATE_FILE"
            echo "Posted completion for $job_id"
        else
            echo "Failed to post completion for $job_id (HTTP $status)" >&2
        fi
    fi
done <<<"$new_done_ids"

# Progress update
if [[ "$pending" -gt 0 || "$running" -gt 0 ]]; then
    msg=$(cat <<EOF
🖼️ **Ideogram 4 worker status**
- ⏳ Pending: $pending | 🏃 Running: $running | ✅ Done: $done | ❌ Failed: $failed
- 🧠 Worker process: $([[ $worker_alive -eq 1 ]] && echo alive || echo not found)
- ⚙️ sd-cli process: $([[ $sdcli_alive -eq 1 ]] && echo alive || echo not found)
- 📝 Latest worker log: \`$progress\`
EOF
)
    while IFS= read -r line; do
        msg="$msg
$line"
    done <<<"$(echo "$JOBS_JSON" | jq -r '.[] | select(.status == "running") | "- 🏃 `\(.id)`: `\(.output_path // "unknown")` (\(.width // "?")x\(.height // "?"), started \(.started_at // "?"))"')"
    while IFS= read -r line; do
        msg="$msg
$line"
    done <<<"$(echo "$JOBS_JSON" | jq -r '.[] | select(.status == "pending") | "- ⏳ `\(.id)`: `\(.output_path // "unknown")` (\(.width // "?")x\(.height // "?"))"')"

    status=$(post_message "$msg")
    if [[ "$status" == "201" ]]; then
        echo "Posted progress update"
    else
        echo "Failed to post progress (HTTP $status)" >&2
    fi
fi

exit 0
