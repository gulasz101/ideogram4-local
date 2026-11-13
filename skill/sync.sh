#!/usr/bin/env bash
# Keep the live image-studio skill identical to this repo copy.
#
#   skill/sync.sh --check   list every file that differs (repo vs live); exit 1 if any
#   skill/sync.sh --apply   rsync the repo copy over the live one (--delete)
#
# The repo is canonical. Change the skill by PR, then run --apply on the host
# after the merge. Matejko edits the live copy, so --check is the drift alarm.
#
#   --live <path>   override the live skill directory (or set IMAGE_STUDIO_LIVE)
set -u -o pipefail

REPO_SKILL="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIVE_SKILL="${IMAGE_STUDIO_LIVE:-/Users/paperclip/.hermes/profiles/matejko/skills/image-studio}"

# never compared or pushed: the tool itself and build noise
EXCLUDE_X=( -x '__pycache__' -x '*.pyc' -x 'sync.sh' )
EXCLUDE_RSYNC=( --exclude='__pycache__' --exclude='*.pyc' --exclude='sync.sh' )

usage() {
  echo "usage: $(basename "$0") --check | --apply   [--live <path>]" >&2
  echo "  repo: $REPO_SKILL" >&2
  echo "  live: $LIVE_SKILL" >&2
  exit 2
}

mode=""
while [ $# -gt 0 ]; do
  case "$1" in
    --check|--apply) mode="$1" ;;
    --live) shift; LIVE_SKILL="${1:-}" ;;
    -h|--help) usage ;;
    *) echo "unknown argument: $1" >&2; usage ;;
  esac
  shift
done
[ -n "$mode" ] || usage
[ -d "$LIVE_SKILL" ] || { echo "live skill not found: $LIVE_SKILL" >&2; exit 2; }

# every differing file, one line each:
#   M <path>  content differs
#   L <path>  live only (--apply deletes it)
#   R <path>  repo only (--apply creates it)
differences() {
  diff -rq "${EXCLUDE_X[@]}" "$REPO_SKILL" "$LIVE_SKILL" 2>/dev/null \
  | sed -e "s|^Files $REPO_SKILL/\(.*\) and $LIVE_SKILL/.* differ\$|M \1|" \
        -e "s|^Only in $LIVE_SKILL: \(.*\)\$|L \1|" \
        -e "s|^Only in $REPO_SKILL: \(.*\)\$|R \1|" \
        -e "s|^Only in $LIVE_SKILL/\([^:]*\): \(.*\)\$|L \1/\2|" \
        -e "s|^Only in $REPO_SKILL/\([^:]*\): \(.*\)\$|R \1/\2|"
}

case "$mode" in
  --check)
    diffs="$(differences)"
    if [ -z "$diffs" ]; then
      echo "OK: repo and live are identical"
      echo "  repo: $REPO_SKILL"
      echo "  live: $LIVE_SKILL"
      exit 0
    fi
    echo "DRIFT: repo and live differ ($(printf '%s\n' "$diffs" | wc -l | tr -d ' ') paths)"
    printf '%s\n' "$diffs"
    exit 1
    ;;
  --apply)
    diffs="$(differences)"
    if [ -z "$diffs" ]; then
      echo "OK: nothing to do, repo and live are identical"
      exit 0
    fi
    echo "applying repo -> live:"
    printf '%s\n' "$diffs" | sed -e 's/^M /  update /' -e 's|^L |  delete |' -e 's|^R |  create |'
    rsync -a --delete "${EXCLUDE_RSYNC[@]}" "$REPO_SKILL"/ "$LIVE_SKILL"/ || {
      echo "rsync failed" >&2
      exit 1
    }
    left="$(differences)"
    if [ -n "$left" ]; then
      echo "WARNING: still different after apply:" >&2
      printf '%s\n' "$left" >&2
      exit 1
    fi
    echo "applied: repo and live are identical"
    exit 0
    ;;
esac
