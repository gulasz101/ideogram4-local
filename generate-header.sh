#!/usr/bin/env bash
# Convenience wrapper to submit the default homelab header job to the queue.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROMPT_FILE="${1:-$SCRIPT_DIR/prompts/homelab-toriyama.json}"
OUTPUT_FILE="${2:-$SCRIPT_DIR/output/homelab-toriyama-ideogram4-header.png}"

if [[ ! -f "$PROMPT_FILE" ]]; then
    echo "Prompt file not found: $PROMPT_FILE" >&2
    exit 1
fi

python3 "$SCRIPT_DIR/ideogram4_local.py" submit \
    --prompt-json "$PROMPT_FILE" \
    -o "$OUTPUT_FILE" \
    -W 1216 -H 832 -v

echo "Job submitted. Run 'python3 $SCRIPT_DIR/ideogram4_local.py worker' to process it."
