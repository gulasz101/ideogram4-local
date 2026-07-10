#!/usr/bin/env python3
"""Static verification script for ideogram4-local prompt hygiene.

Run after changing the wrapper to confirm:
- Templates lint clean (risk score 0, no schema issues).
- build_guidance_schedule produces the official V4_DEFAULT_20 schedule.
- canonicalize_prompt drops canvas/layout and preserves the generation block.
"""

import json
import sys
from pathlib import Path

# Run from the wrapper repo root, not from the skill directory.
REPO = Path.cwd()
sys.path.insert(0, str(REPO))

from ideogram4_local import build_guidance_schedule, canonicalize_prompt
from ideogram4_prompt_tools import lint_prompt


def main() -> int:
    failures = 0

    for template in (REPO / "templates").glob("*.json"):
        text = template.read_text(encoding="utf-8")
        report = lint_prompt(text, "json")
        if report["score"] != 0 or report["schema_issues"]:
            print(f"FAIL: {template.name} score={report['score']} issues={report['schema_issues']}")
            failures += 1
        else:
            print(f"OK:  {template.name}")

    schedule = build_guidance_schedule({
        "safety_bypass": True,
        "safety_bypass_mode": "single_pass",
        "steps": 20,
    })
    expected = "7.0x18+3.0x2"
    if schedule != expected:
        print(f"FAIL: single_pass 20-step schedule is {schedule!r}, expected {expected!r}")
        failures += 1
    else:
        print(f"OK:  single_pass 20-step schedule = {schedule}")

    sample = '{"high_level_description":"x","style_description":{"aesthetics":"a","lighting":"l","medium":"m","art_style":"v"},"compositional_deconstruction":{"background":"b","elements":[],"canvas":"drop me","layout":"drop me"},"generation":{"llm_model":"aggressive"}}'
    canon = json.loads(canonicalize_prompt("json", sample))
    if "canvas" in canon.get("compositional_deconstruction", {}) or "layout" in canon.get("compositional_deconstruction", {}):
        print("FAIL: canonicalize_prompt kept canvas/layout")
        failures += 1
    else:
        print("OK:  canonicalize_prompt drops canvas/layout")
    if canon.get("generation", {}).get("llm_model") != "aggressive":
        print("FAIL: canonicalize_prompt dropped generation block")
        failures += 1
    else:
        print("OK:  canonicalize_prompt preserves generation block")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
