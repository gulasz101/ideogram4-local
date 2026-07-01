#!/usr/bin/env bash
# Convenience wrapper for ideogram4_local.py.
# Generates a blog header image for the homelab-2nd migration post.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROMPT_FILE="${1:-$SCRIPT_DIR/prompts/homelab-toriyama.json}"
OUTPUT_FILE="${2:-$SCRIPT_DIR/output/homelab-toriyama-ideogram4-header.png}"

if [[ ! -f "$PROMPT_FILE" ]]; then
    echo "Prompt file not found: $PROMPT_FILE" >&2
    exit 1
fi

python3 "$SCRIPT_DIR/ideogram4_local.py" \
    --prompt-json "$PROMPT_FILE" \
    -o "$OUTPUT_FILE" \
    -W 1216 -H 832 \
    -v
