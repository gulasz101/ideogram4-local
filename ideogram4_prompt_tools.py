#!/usr/bin/env python3
"""
Ideogram 4 prompt linter/rewriter.

Heuristic rules distilled from the official ideogram-oss/ideogram4 repo and
community findings (2026-07):

- The local GGUF filter is an out-of-distribution fallback baked into the
  weights. Prompts that drift from the trained caption schema are more likely
  to grey-box.
- Use the exact canonical JSON caption schema:
    high_level_description
    style_description { aesthetics, lighting, medium, photo OR art_style, color_palette }
    compositional_deconstruction { background, elements }
- Describe the *situation* and *persona*, not the clothing/anatomy/item.
- Drop canvas/layout fields; they are not in the schema and drift the model.
- Use an uncensored Qwen3-VL encoder (HauhauCS Aggressive) for false-positive-prone prompts.
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

# ---------------------------------------------------------------------------
# Caption schema constants (mirrors ideogram4.caption_verifier.CaptionVerifier)
# ---------------------------------------------------------------------------

TOP_LEVEL_KEYS = ("high_level_description", "style_description", "compositional_deconstruction")
STYLE_ORDER_PHOTO = ("aesthetics", "lighting", "photo", "medium", "color_palette")
STYLE_ORDER_ART = ("aesthetics", "lighting", "medium", "art_style", "color_palette")
COMPOSITION_ORDER = ("background", "elements")
ELEMENT_ORDER_OBJ = ("type", "bbox", "desc", "color_palette")
ELEMENT_ORDER_TEXT = ("type", "bbox", "text", "desc", "color_palette")

STYLE_KEYS = frozenset({"aesthetics", "lighting", "photo", "art_style", "medium", "color_palette"})
ELEMENT_KEYS = frozenset({"type", "bbox", "text", "desc", "color_palette"})


def _ordered(d: dict, key_order: tuple) -> dict:
    """Return a new dict with keys in the requested order; unknown keys appended."""
    result: dict = {}
    for key in key_order:
        if key in d:
            result[key] = d[key]
    for key, value in d.items():
        if key not in result:
            result[key] = value
    return result


def _style_key_order(style: dict) -> tuple:
    has_photo = "photo" in style
    has_art = "art_style" in style
    if has_art and not has_photo:
        return STYLE_ORDER_ART
    return STYLE_ORDER_PHOTO


def _element_key_order(element: dict) -> tuple:
    return ELEMENT_ORDER_TEXT if element.get("type") == "text" else ELEMENT_ORDER_OBJ


def canonicalize_caption(data: dict, *, drop_generation: bool = True) -> dict:
    """Rewrite a caption dict to match the official Ideogram 4 schema.

    - Keeps only known top-level keys (drops canvas/layout; preserves generation unless asked).
    - Reorders style_description and compositional_deconstruction keys.
    - Reorders elements.
    - Strips empty/unset fields only when they are unknown keys.
    """
    if not isinstance(data, dict):
        return data

    top: dict = {}
    for key in TOP_LEVEL_KEYS:
        if key in data:
            top[key] = data[key]

    # generation is wrapper metadata, not part of the caption schema
    if not drop_generation and "generation" in data:
        top["generation"] = data["generation"]

    # style_description
    style = top.get("style_description")
    if isinstance(style, dict):
        # Drop unknown keys
        style = {k: v for k, v in style.items() if k in STYLE_KEYS}
        style = _ordered(style, _style_key_order(style))
        top["style_description"] = style

    # compositional_deconstruction
    comp = top.get("compositional_deconstruction")
    if isinstance(comp, dict):
        # Drop canvas/layout and any other unknown keys
        comp = {k: v for k, v in comp.items() if k in ("background", "elements")}
        elements = comp.get("elements")
        if isinstance(elements, list):
            reordered_elements = []
            for el in elements:
                if isinstance(el, dict):
                    el = {k: v for k, v in el.items() if k in ELEMENT_KEYS}
                    try:
                        el = _ordered(el, _element_key_order(el))
                    except Exception:
                        pass
                reordered_elements.append(el)
            comp["elements"] = reordered_elements
        comp = _ordered(comp, COMPOSITION_ORDER)
        top["compositional_deconstruction"] = comp

    return top


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
    """Return list of (category, term) for each flagged term found."""
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


def _check_schema_issues(data: dict) -> list[str]:
    """Return human-readable schema warnings for a parsed caption dict."""
    issues: list[str] = []
    if not isinstance(data, dict):
        issues.append("root: expected a JSON object")
        return issues

    extra_top = [k for k in data.keys() if k not in TOP_LEVEL_KEYS and k != "generation"]
    if extra_top:
        issues.append(f"root: unknown top-level keys will be dropped: {', '.join(extra_top)}")

    style = data.get("style_description")
    if isinstance(style, dict):
        extra_style = [k for k in style.keys() if k not in STYLE_KEYS]
        if extra_style:
            issues.append(f"style_description: unknown keys will be dropped: {', '.join(extra_style)}")
        has_photo = "photo" in style
        has_art = "art_style" in style
        if has_photo and has_art:
            issues.append("style_description: has both 'photo' and 'art_style'; keep exactly one")
        elif not has_photo and not has_art:
            issues.append("style_description: needs either 'photo' (for photos) or 'art_style' (for illustrations/3D)")

    comp = data.get("compositional_deconstruction")
    if isinstance(comp, dict):
        extra_comp = [k for k in comp.keys() if k not in ("background", "elements")]
        if extra_comp:
            issues.append(f"compositional_deconstruction: unknown keys will be dropped: {', '.join(extra_comp)}")
        if "background" not in comp:
            issues.append("compositional_deconstruction: missing required 'background'")
        if "elements" not in comp:
            issues.append("compositional_deconstruction: missing required 'elements'")
        elements = comp.get("elements", [])
        if isinstance(elements, list):
            for i, el in enumerate(elements):
                if not isinstance(el, dict):
                    issues.append(f"compositional_deconstruction.elements[{i}]: not an object")
                    continue
                extra_el = [k for k in el.keys() if k not in ELEMENT_KEYS]
                if extra_el:
                    issues.append(f"element[{i}]: unknown keys will be dropped: {', '.join(extra_el)}")
                if "type" not in el:
                    issues.append(f"element[{i}]: missing required 'type'")
                elif el.get("type") not in ("obj", "text"):
                    issues.append(f"element[{i}]: type must be 'obj' or 'text'")
                if el.get("type") == "text" and "text" not in el:
                    issues.append(f"element[{i}] (text): missing required 'text' field")

    return issues


def lint_prompt(prompt_value: str, prompt_type: str = "json") -> dict:
    """Return a lint report for a prompt."""
    report = {
        "prompt_type": prompt_type,
        "canonical_json": False,
        "schema_issues": [],
        "flagged_terms": [],
        "prose_drift_risk": False,
        "density_risk": False,
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
        report["schema_issues"] = _check_schema_issues(data)
        if report["schema_issues"]:
            report["recommendations"].append(
                "Schema issues detected; run 'rewrite' to auto-fix key order and drop unknown fields."
            )
            report["score"] += len(report["schema_issues"])
        text = _extract_text_from_json(data)

        # Heuristic: dense structures with many elements may drift off-distribution.
        comp = data.get("compositional_deconstruction", {}) if isinstance(data, dict) else {}
        if isinstance(comp, dict):
            extra_layout_keys = [k for k in ("canvas", "layout") if comp.get(k)]
            elements = comp.get("elements", [])
            if extra_layout_keys or (isinstance(elements, list) and len(elements) > 6):
                report["density_risk"] = True
                report["recommendations"].append(
                    "JSON is dense (canvas/layout or many elements). Use the official schema: background + elements."
                )
                report["score"] += 2
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
            cleaned.append("person in a relaxed everyday setting")
        else:
            cleaned.append(raw_word)
    return " ".join(cleaned)


def _fix_style_description(style: dict) -> dict:
    """Ensure style_description has exactly one of photo/art_style."""
    if not isinstance(style, dict):
        return {
            "aesthetics": "clean digital illustration, friendly technology blog art, no photorealism",
            "lighting": "soft even lighting",
            "medium": "digital illustration",
            "art_style": "flat vector illustration with clear shapes and soft gradients",
            "color_palette": ["#3B82F6", "#F59E0B", "#1F2937", "#F3F4F6"],
        }
    has_photo = "photo" in style
    has_art = "art_style" in style
    if not has_photo and not has_art:
        # Guess based on medium or default to art_style
        medium = str(style.get("medium", "")).lower()
        if "photo" in medium or "photograph" in medium:
            style["photo"] = "medium shot, clear readable shapes, simple background"
        else:
            style["art_style"] = "flat vector illustration with clear shapes and soft gradients"
    return style


def rewrite_prompt(prompt_value: str, prompt_type: str = "json") -> str:
    """
    Return a rewritten prompt string in canonical Ideogram 4 JSON.

    Strategy:
    1. Parse JSON if possible, canonicalize schema (drop unknown keys, reorder).
    2. Clean flagged phrases in text fields.
    3. If input is plain text or non-canonical JSON, wrap it into the minimal
       canonical schema and clean it.
    """
    data: Optional[dict] = None
    generation_block: Optional[dict] = None
    if prompt_type == "json":
        try:
            raw_data = json.loads(prompt_value)
            if isinstance(raw_data, dict):
                generation_block = raw_data.get("generation")
                data = canonicalize_caption(raw_data, drop_generation=False)
        except json.JSONDecodeError:
            data = None

    if data and _is_canonical_json(data):
        # Clean text fields
        hld = data.get("high_level_description", "")
        data["high_level_description"] = _clean_remaining_flagged_words(_reframe_text(hld))

        style = data.get("style_description", {})
        style = _fix_style_description(style)
        for key in ("aesthetics", "lighting", "photo", "art_style", "medium"):
            if key in style and isinstance(style[key], str):
                style[key] = _clean_remaining_flagged_words(_reframe_text(style[key]))
        data["style_description"] = style

        comp = data.get("compositional_deconstruction", {})
        if isinstance(comp, dict):
            comp["background"] = _clean_remaining_flagged_words(_reframe_text(comp.get("background", "")))
            elements = comp.get("elements", [])
            if isinstance(elements, list):
                for el in elements:
                    if isinstance(el, dict):
                        if "desc" in el:
                            el["desc"] = _clean_remaining_flagged_words(_reframe_text(el["desc"]))
                        if el.get("type") == "text" and "text" in el and isinstance(el["text"], str):
                            el["text"] = _clean_remaining_flagged_words(_reframe_text(el["text"]))
        data = canonicalize_caption(data, drop_generation=True)
        if generation_block is not None:
            data["generation"] = generation_block
        return json.dumps(data, ensure_ascii=False, indent=2)

    # Plain text or non-canonical JSON: reframe and wrap into the minimal canonical shape.
    cleaned = _clean_remaining_flagged_words(_reframe_text(prompt_value.strip()))
    rewritten = {
        "high_level_description": cleaned,
        "style_description": {
            "aesthetics": "clean digital illustration, friendly technology blog art, no photorealism",
            "lighting": "soft even lighting",
            "medium": "digital illustration",
            "art_style": "flat vector illustration with clear shapes and soft gradients",
            "color_palette": ["#3B82F6", "#F59E0B", "#1F2937", "#F3F4F6"]
        },
        "compositional_deconstruction": {
            "background": "simple neutral background",
            "elements": [{"type": "obj", "desc": cleaned}]
        }
    }
    if generation_block is not None:
        rewritten["generation"] = generation_block
    return json.dumps(rewritten, ensure_ascii=False, indent=2)


def print_lint_report(report: dict) -> None:
    print(f"Prompt type: {report['prompt_type']}")
    print(f"Canonical JSON: {report['canonical_json']}")
    print(f"Risk score: {report['score']} (lower is better)")
    if report["schema_issues"]:
        print("Schema issues:")
        for issue in report["schema_issues"]:
            print(f"  - {issue}")
    if report["flagged_terms"]:
        print("Flagged terms:")
        for category, term in report["flagged_terms"]:
            print(f"  - [{category}] {term}")
    else:
        print("Flagged terms: none")
    if report["prose_drift_risk"]:
        print("Prose drift risk: yes")
    if report["density_risk"]:
        print("Density risk: yes")
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
