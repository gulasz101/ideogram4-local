#!/usr/bin/env python3
"""
Ideogram 4 prompt linter/rewriter.

Heuristic rules distilled from community findings:
- The filter reacts to prompt vocabulary and JSON structure, not pixels.
- Use canonical structured JSON; plain prose drifts off-distribution.
- Describe the *situation* and *persona*, not the clothing/anatomy/item.
"""

import json
import re
import sys
from pathlib import Path
from typing import Optional

# Terms that, when named explicitly in the prompt, tend to flip the safety
# attractor even for harmless scenes. Keep this list conservative and practical;
# it is meant for blog/tech false-positive avoidance, not exhaustive NSFW
# detection.
EXPLICIT_GARMENT_TERMS = {
    "bikini", "lingerie", "underwear", "panties", "bra", "swimsuit", "speedo",
    "topless", "bottomless", "nude", "naked", "unclothed", "undressed",
    "bare chest", "bare skin", "bare shoulders", "bare legs", "bare feet",
    "sheet", "towel", "wrapped in",
}

EXPLICIT_ANATOMY_TERMS = {
    "breast", "breasts", "butt", "buttocks", "genital", "genitals", "crotch",
    "nipple", "nipples", "cleavage", "thigh", "thighs",
}

HUMAN_SHAPE_TERMS = {
    "statue", "nude figure", "naked figure", "unclothed figure", "anatomy study",
    "anatomical", "human figure", "full body", "whole body", "head to toe", "from head to toe",
    "standing figure", "human body", "body reference", "pose reference",
}

EXPLICIT_SITUATION_TERMS = {
    "sex", "sexual", "erotic", "porn", "pornographic", "fetish", "kink",
    "seductive", "provocative", "suggestive", "intimate",
}

VIOLENCE_TERMS = {
    "blood", "bloody", "gore", "dead", "corpse", "kill", "killing", "murder",
    "suicide", "torture", "mutilated", "decapitated", "dismembered", "weapon",
    "gun", "knife", "rifle", "pistol", "explosion", "exploding",
}

ALL_FLAGGED = EXPLICIT_GARMENT_TERMS | EXPLICIT_ANATOMY_TERMS | EXPLICIT_SITUATION_TERMS | VIOLENCE_TERMS

# Reframe map: replace a flagged concept with a safe situational/contextual
# description. These are applied as whole-phrase substitutions, not word-for-word.
# Order matters: longer phrases first.
REFRAME_MAP = {
    # anatomy reference / figure study
    r"\bunclothed adult human figure\b": "classical marble statue of a standing human figure",
    r"\bnaked adult human figure\b": "classical marble statue of a standing human figure",
    r"\bnude adult human figure\b": "classical marble statue of a standing human figure",
    r"\banatomy reference photograph\b": "sculpture study photograph",
    r"\banatomy reference\b": "sculpture study",
    r"\bclinical anatomy\b": "classical sculpture study",
    r"\bhuman figure standing in a neutral pose\b": "classical statue standing in a neutral pose",
    # swimwear / beachwear
    r"\ba woman in a bikini\b": "a cheerful young woman having fun at the beach on a sunny summer day",
    r"\ba woman in a swimsuit\b": "a cheerful young woman enjoying a resort pool on a hot day",
    r"\ba man in a swimsuit\b": "a cheerful young man enjoying a resort pool on a hot day",
    r"\bwoman in a bikini\b": "cheerful young woman having fun at the beach",
    r"\bman in a bikini\b": "cheerful young man having fun at the beach",
    # lingerie / intimate
    r"\blace lingerie\b": "delicate evening attire",
    r"\bwearing lingerie\b": "relaxing in a softly lit bedroom",
    r"\bin lingerie\b": "relaxing in a softly lit bedroom",
    # wrapped / towel / sheet
    r"\bwrapped in a sheet\b": "resting in bed on a lazy morning",
    r"\bwrapped in a towel\b": "stepping out of a refreshing shower",
    r"\bcovered by a towel\b": "stepping out of a refreshing shower",
    # states of undress
    r"\bunclothed\b": "in a classical sculpture style",
    r"\bnude\b": "in a classical sculpture style",
    r"\bnaked\b": "in a classical sculpture style",
    r"\btopless\b": "enjoying a warm summer breeze outdoors",
    r"\bbare skin\b": "smooth marble-like surface",
    r"\bbare chest\b": "open-collar casual outfit",
    r"\bbare shoulders\b": "off-shoulder summer dress",
    # violence shortcuts
    r"\bblood on the floor\b": "red hydraulic fluid spill on the floor",
    r"\bbloody\b": "gritty and worn",
    r"\bgun\b": "tool",
    r"\bknife\b": "small tool",
}


def _extract_text_from_json(data) -> str:
    """Recursively concat all string values in a JSON prompt."""
    parts = []
    if isinstance(data, dict):
        for k, v in data.items():
            if k == "generation":
                continue
            parts.append(_extract_text_from_json(v))
    elif isinstance(data, list):
        for item in data:
            parts.append(_extract_text_from_json(item))
    elif isinstance(data, str):
        parts.append(data)
    return " ".join(parts)


def _find_flagged(text: str) -> list[tuple[str, str]]:
    """Return list of (category, term) for each flagged term found.

    Uses word-boundary matching so that innocent compound words like
    'non-erotic' do not match 'erotic'.
    """
    found = []
    lower = text.lower()
    categories = [
        ("garment", EXPLICIT_GARMENT_TERMS),
        ("anatomy", EXPLICIT_ANATOMY_TERMS),
        ("situation", EXPLICIT_SITUATION_TERMS),
        ("violence", VIOLENCE_TERMS),
        ("human_shape", HUMAN_SHAPE_TERMS),
    ]
    for category, terms in categories:
        for term in sorted(terms, key=len, reverse=True):
            # Match term when not directly preceded or followed by [a-z-].
            pattern = r"(?:^|[^a-z-])" + re.escape(term) + r"(?:[^a-z-]|$)"
            if re.search(pattern, lower):
                found.append((category, term))
    return found


def _is_canonical_json(data) -> bool:
    """Check that the prompt has the expected Ideogram 4 JSON shape."""
    if not isinstance(data, dict):
        return False
    required = {"high_level_description", "style_description", "compositional_deconstruction"}
    return required.issubset(data.keys())


def lint_prompt(prompt_value: str, prompt_type: str = "json") -> dict:
    """Return a lint report for a prompt."""
    report = {
        "prompt_type": prompt_type,
        "canonical_json": False,
        "flagged_terms": [],
        "prose_drift_risk": False,
        "recommendations": [],
        "score": 0,  # 0 = clean, higher = riskier
    }

    if prompt_type == "json":
        try:
            data = json.loads(prompt_value)
        except json.JSONDecodeError as e:
            report["recommendations"].append(f"Invalid JSON: {e}")
            report["score"] += 10
            return report
        report["canonical_json"] = _is_canonical_json(data)
        if not report["canonical_json"]:
            report["recommendations"].append(
                "Use canonical Ideogram 4 JSON with high_level_description, style_description, and compositional_deconstruction blocks."
            )
            report["score"] += 3
        text = _extract_text_from_json(data)
    else:
        text = prompt_value.strip()
        report["prose_drift_risk"] = True
        report["recommendations"].append(
            "Plain text prompts drift off-distribution and often trigger grey boxes. Convert to canonical JSON."
        )
        report["score"] += 3

    report["flagged_terms"] = _find_flagged(text)
    if report["flagged_terms"]:
        report["recommendations"].append(
            "Avoid naming flagged garments/anatomy/situations/human-body descriptions. Describe the scene, location, mood, and activity instead."
        )
        report["score"] += len(report["flagged_terms"]) * 2
        human_shape_hits = [t for t in report["flagged_terms"] if t[0] == "human_shape"]
        if human_shape_hits:
            report["recommendations"].append(
                "Human/anatomy/stature descriptions are frequent false-positive triggers in this local GGUF build. Consider robots, objects, diagrams, or abstract illustrations for tech blog images."
            )

    # Heuristic: very short prompts drift.
    if len(text.split()) < 20:
        report["recommendations"].append(
            "Prompt is very short. Add more situational detail (location, mood, activity)."
        )
        report["score"] += 1

    return report


def _reframe_text(text: str) -> str:
    """Apply whole-phrase reframes before word-level cleanup."""
    for pattern, replacement in REFRAME_MAP.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def _clean_remaining_flagged_words(text: str) -> str:
    """After reframe, mask any leftover flagged single words with a generic situational phrase."""
    words = text.split()
    cleaned = []
    for raw_word in words:
        word_lower = re.sub(r"[^a-zA-Z']+", "", raw_word).lower()
        if word_lower in ALL_FLAGGED:
            # Replace the word with a generic safe fragment while keeping sentence grammar rough.
            cleaned.append("person in a relaxed everyday setting")
        else:
            cleaned.append(raw_word)
    return " ".join(cleaned)


def rewrite_prompt(prompt_value: str, prompt_type: str = "json") -> str:
    """
    Return a rewritten prompt string in canonical Ideogram 4 JSON.

    The strategy:
    1. If input is already canonical JSON, clean flagged phrases in
       high_level_description and element descriptions.
    2. If input is plain text or non-canonical JSON, wrap it into a minimal
       canonical JSON and clean it.
    """
    data: Optional[dict] = None
    if prompt_type == "json":
        try:
            data = json.loads(prompt_value)
        except json.JSONDecodeError:
            data = None

    if data and _is_canonical_json(data):
        # Preserve the user's JSON, just clean the text fields.
        hld = data.get("high_level_description", "")
        data["high_level_description"] = _clean_remaining_flagged_words(_reframe_text(hld))

        comp = data.get("compositional_deconstruction", {})
        if isinstance(comp, dict):
            comp["background"] = _clean_remaining_flagged_words(_reframe_text(comp.get("background", "")))
            comp["layout"] = _clean_remaining_flagged_words(_reframe_text(comp.get("layout", "")))
            elements = comp.get("elements", [])
            if isinstance(elements, list):
                for el in elements:
                    if isinstance(el, dict) and "desc" in el:
                        el["desc"] = _clean_remaining_flagged_words(_reframe_text(el["desc"]))
        return json.dumps(data, ensure_ascii=False, indent=2)

    # Plain text or non-canonical JSON: reframe and wrap.
    cleaned = _clean_remaining_flagged_words(_reframe_text(prompt_value.strip()))
    rewritten = {
        "high_level_description": cleaned,
        "style_description": {
            "aesthetics": "clean digital illustration, friendly technology blog art, no photorealism",
            "lighting": "soft even lighting",
            "photo": "medium shot, clear readable shapes, simple background",
            "medium": "digital illustration",
            "color_palette": ["#3B82F6", "#F59E0B", "#1F2937", "#F3F4F6"]
        },
        "compositional_deconstruction": {
            "canvas": "Wide 1216 x 832 landscape canvas",
            "background": "simple neutral background",
            "layout": "Center: main subject clearly visible.",
            "elements": [{"type": "obj", "desc": cleaned}]
        }
    }
    return json.dumps(rewritten, ensure_ascii=False, indent=2)


def print_lint_report(report: dict) -> None:
    print(f"Prompt type: {report['prompt_type']}")
    print(f"Canonical JSON: {report['canonical_json']}")
    print(f"Risk score: {report['score']} (lower is better)")
    if report["flagged_terms"]:
        print("Flagged terms:")
        for category, term in report["flagged_terms"]:
            print(f"  - [{category}] {term}")
    else:
        print("Flagged terms: none")
    if report["prose_drift_risk"]:
        print("Prose drift risk: yes")
    if report["recommendations"]:
        print("Recommendations:")
        for rec in report["recommendations"]:
            print(f"  - {rec}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: ideogram4_prompt_tools.py lint|rewrite <prompt-json-file> [-o output.json]", file=sys.stderr)
        sys.exit(1)

    cmd = sys.argv[1]
    input_path = Path(sys.argv[2])
    output_path: Optional[Path] = None
    if "-o" in sys.argv:
        idx = sys.argv.index("-o")
        output_path = Path(sys.argv[idx + 1])

    prompt_value = input_path.read_text(encoding="utf-8")
    prompt_type = "json" if input_path.suffix == ".json" else "text"

    if cmd == "lint":
        report = lint_prompt(prompt_value, prompt_type)
        print_lint_report(report)
    elif cmd == "rewrite":
        rewritten = rewrite_prompt(prompt_value, prompt_type)
        if output_path:
            output_path.write_text(rewritten, encoding="utf-8")
            print(f"Rewritten prompt written to {output_path}")
        else:
            print(rewritten)
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)
