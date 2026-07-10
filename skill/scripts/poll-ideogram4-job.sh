#!/bin/bash
# Poll the ideogram4-local SQLite queue until a target job reaches a target status.
# Safe for zsh parent shell: no 'status' variable, explicitly invoked via bash.
#
# Usage: bash poll-ideogram4-job.sh <job_id> <target_status> [timeout_seconds]
#
# Examples:
#   bash poll-ideogram4-job.sh hcm6-GdZyhI running 3600
#   bash poll-ideogram4-job.sh hcm6-GdZyhI done 7200

set -euo pipefail

JOB_ID="${1:-}"
TARGET="${2:-done}"
TIMEOUT="${3:-7200}"

if [ -z "$JOB_ID" ]; then
  echo "Usage: $0 <job_id> <target_status> [timeout_seconds]" >&2
  exit 1
fi

cd ~/git/ideogram4-local || exit 1

elapsed=0
while [ "$elapsed" -lt "$TIMEOUT" ]; do
  job_status=$(python3 -c "
import sqlite3
c = sqlite3.connect('jobs.db')
r = c.execute('SELECT status FROM jobs WHERE id=?', ('$JOB_ID',)).fetchone()
print(r[0] if r else 'unknown')
")
  if [ "$job_status" = "$TARGET" ]; then
    echo "Job $JOB_ID reached status: $TARGET"
    exit 0
  fi
  sleep 30
  elapsed=$((elapsed + 30))
done

echo "Timeout waiting for $JOB_ID to reach $TARGET" >&2
exit 1
