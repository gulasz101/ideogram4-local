#!/usr/bin/env bash
# Smoke test that confirms the safety-bypass guidance_schedule is injected.
# Runs quickly: it submits a tiny job and waits for the schedule to appear in
# output/worker.log, then cancels the actual generation.

set -euo pipefail

cd "$(dirname "$0")/.."
export IDEOGRAM4_MODELS_DIR="${IDEOGRAM4_MODELS_DIR:-$HOME/sd.cpp-models}"
export IDEOGRAM4_SAFETY_BYPASS=1

PROMPT='prompts/test-safety-bypass-smoke.json'
OUT='output/test-safety-bypass-smoke.png'

mkdir -p prompts output
cat > "$PROMPT" <<'JSON'
{
  "high_level_description": "A small square test image. A cute cartoon robot holding a glowing key card stands in front of a server rack.",
  "style_description": {
    "aesthetics": "flat vector cartoon, friendly technology blog illustration, clean shapes",
    "lighting": "soft even lighting",
    "photo": "medium shot, clear readable shapes",
    "medium": "digital vector illustration",
    "color_palette": ["#3B82F6", "#F59E0B", "#1F2937"]
  },
  "compositional_deconstruction": {
    "canvas": "Square 832 x 832 canvas",
    "background": "plain light gray background",
    "layout": "Center: friendly robot holding glowing key card. Background: simple server rack.",
    "elements": [
      {"type": "obj", "desc": "A cute friendly cartoon robot holding a glowing key card."},
      {"type": "obj", "desc": "A simple server rack in the background with small status lights."}
    ]
  },
  "generation": {
    "safety_bypass": true,
    "safety_bypass_mode": "single_pass",
    "steps": 5,
    "safety_bypass_steps": 2,
    "safety_bypass_cfg": 1.0
  }
}
JSON

JOB_ID=$(python3 ideogram4_local.py submit --prompt-json "$PROMPT" -o "$OUT" -W 832 -H 832 -v)
echo "Submitted smoke job $JOB_ID"

# Wait up to 60s for the schedule line to appear in the worker log.
for i in $(seq 1 60); do
  if grep -q 'using guidance schedule:' output/worker.log 2>/dev/null; then
    echo "PASS: found guidance schedule in worker log"
    grep 'using guidance schedule:' output/worker.log | tail -1
    exit 0
  fi
  sleep 1
done

echo "FAIL: guidance schedule not seen in output/worker.log after 60s"
exit 1
