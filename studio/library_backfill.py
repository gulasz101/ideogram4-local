#!/usr/bin/env python3
"""Back-fill the Obsidian image library from the Ideogram 4 jobs queue.

One record per successful job, plus a regenerated index.  Standard library
only: the vault lives on the owner's laptop and the script may be run there.
"""

from __future__ import annotations

import argparse
import json
import posixpath
import re
import sqlite3
import sys
import urllib.parse
from pathlib import Path

DEFAULT_VAULT = "~/wojtek.second.brain.obsidian.vault"
DEFAULT_MAX_VAULT_ROOT = "/Users/wojciechgula/wojtek.second.brain.obsidian.vault"
LIBRARY_SUBDIR = "3-resources/image-library"
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}

# FLUX.2-klein jobs carry no JSON generation block; these are the values that
# produced the image, so they go in the record instead (phase 6, decision D2).
FLUX_MODEL_ID = "black-forest-labs/FLUX.2-klein-4B"
FLUX_STEPS = 4

EMBED_RE = re.compile(r"!\[\[([^\]]+)\]\]|!\[([^\]]*)\]\(([^)]+)\)")
HEADING_RE = re.compile(r"^##(?!#)\s+(.*?)\s*$")


def _json(value) -> str:
    return json.dumps(value, ensure_ascii=False)


def _yaml_scalar(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    return _json(value)


def parse_frontmatter_status(text: str):
    """Return the frontmatter ``status:`` value, or None."""
    text = text.lstrip("\ufeff")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        if line.strip() == "---":
            break
        match = re.match(r"^status:\s*(.*)$", line)
        if match:
            value = match.group(1).strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            return value or None
    return None


def _nearest_heading(lines, index: int):
    for line in reversed(lines[:index]):
        match = HEADING_RE.match(line)
        if match:
            return match.group(1).strip()
    return None


def _first_paragraph_after(lines, index: int) -> str:
    """First prose paragraph after an embed, skipping headings and blocks."""
    cursor = index + 1
    while cursor < len(lines):
        stripped = lines[cursor].strip()
        if not stripped:
            cursor += 1
            continue
        if stripped.startswith(("```", "~~~")):
            # Skip the whole fenced block, not just its opening line.
            fence = stripped[:3]
            cursor += 1
            while cursor < len(lines) and not lines[cursor].strip().startswith(fence):
                cursor += 1
            cursor += 1
            continue
        if stripped.startswith(("#", "!", "---", "|", ">", "- ", "* ")):
            cursor += 1
            continue
        block = [stripped]
        cursor += 1
        while cursor < len(lines):
            continuation = lines[cursor].strip()
            if not continuation:
                break
            if continuation.startswith(("#", "!", "```", "|", ">", "- ", "* ")):
                break
            block.append(continuation)
            cursor += 1
        return " ".join(block)
    return ""


def _is_image(target: str) -> bool:
    return posixpath.splitext(target)[1].lower() in IMAGE_EXTENSIONS


def _candidates(post_rel: str, kind: str, target: str):
    """Vault-relative paths an embed may resolve to."""
    target = target.strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    if not target:
        return []
    target = urllib.parse.unquote(target).lstrip("/")
    directory = posixpath.dirname(post_rel)
    candidates = []
    if kind == "markdown":
        # Posts use paths relative to tech_blog/; also accept note-relative paths.
        candidates.append(posixpath.normpath(posixpath.join("tech_blog", target)))
        candidates.append(posixpath.normpath(posixpath.join(directory, target)))
    else:
        candidates.append(posixpath.normpath(target))
        candidates.append(posixpath.normpath(posixpath.join(directory, target)))
        candidates.append(posixpath.normpath(posixpath.join("tech_blog", target)))
        if "/" not in target:
            candidates.append(target)
    seen = []
    for candidate in candidates:
        candidate = candidate.lstrip("./")
        if candidate and candidate not in seen:
            seen.append(candidate)
    return seen


def scan_posts(vault: Path):
    """Scan every markdown post under ``tech_blog/`` for image embeds."""
    posts = []
    tech_blog = vault / "tech_blog"
    if not tech_blog.is_dir():
        return posts
    for path in sorted(tech_blog.rglob("*.md")):
        rel = path.relative_to(vault).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace").lstrip("\ufeff")
        lines = text.splitlines()
        embeds = []
        for index, line in enumerate(lines):
            for match in EMBED_RE.finditer(line):
                if match.group(1) is not None:
                    kind = "wiki"
                    target = match.group(1).split("|", 1)[0].split("#", 1)[0]
                    alt = ""
                else:
                    kind = "markdown"
                    alt = match.group(2)
                    raw_target = match.group(3).strip()
                    if raw_target.startswith("<") and ">" in raw_target:
                        target = raw_target[1 : raw_target.index(">")]
                    else:
                        target = raw_target.split()[0] if raw_target else ""
                if not target or not _is_image(target):
                    continue
                embeds.append(
                    {
                        "kind": kind,
                        "alt": alt,
                        "candidates": _candidates(rel, kind, target),
                        "section": _nearest_heading(lines, index),
                        "excerpt": _first_paragraph_after(lines, index),
                    }
                )
        posts.append(
            {
                "rel": rel,
                "stem": path.stem,
                "status": parse_frontmatter_status(text),
                "embeds": embeds,
            }
        )
    return posts


def read_jobs(db: Path):
    """Read successful jobs from a read-only snapshot of the queue database."""
    uri = db.resolve().as_uri() + "?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    try:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(jobs)")}
        if "engine" in columns and "seed" in columns:
            engine_column, seed_column = "engine", "seed"
        else:
            # A snapshot taken before phase 6: every job was an Ideogram 4 job
            # with no seed, so the old schema still renders the same records.
            engine_column, seed_column = "'ideogram4' AS engine", "NULL AS seed"
        rows = connection.execute(
            f"""
            SELECT id, status, prompt_type, prompt_value, output_path,
                   width, height, created_at, finished_at,
                   {engine_column}, {seed_column}
            FROM jobs
            WHERE status = 'done'
            ORDER BY created_at, id
            """
        ).fetchall()
    finally:
        connection.close()
    return rows


def classify_asset(output_path: str, max_vault_root: str):
    prefix = max_vault_root.rstrip("/") + "/"
    if output_path.startswith(prefix):
        return output_path[len(prefix) :], "vault"
    return output_path, "max-only"


def _prompt_fields(prompt_type: str, prompt_value: str):
    if prompt_type != "json":
        return None, None
    try:
        parsed = json.loads(prompt_value)
    except (TypeError, ValueError):
        return None, None
    if not isinstance(parsed, dict):
        return None, parsed
    return parsed.get("generation"), parsed


def build_records(db: Path, vault: Path, max_vault_root: str):
    rows = read_jobs(db)
    records = []
    for (
        job_id,
        _status,
        prompt_type,
        prompt_value,
        output_path,
        width,
        height,
        created_at,
        finished_at,
        engine,
        seed,
    ) in rows:
        asset, location = classify_asset(output_path, max_vault_root)
        generation, parsed_prompt = _prompt_fields(prompt_type, prompt_value)
        if engine == "flux2-klein":
            # Text prompts have no generation block; record what rendered.
            generation = {
                "model": FLUX_MODEL_ID,
                "steps": FLUX_STEPS,
                "seed": seed,
            }
        stem = posixpath.splitext(posixpath.basename(output_path))[0]
        records.append(
            {
                "job_id": job_id,
                "engine": engine,
                "seed": seed,
                "prompt_type": prompt_type,
                "prompt_value": prompt_value,
                "parsed_prompt": parsed_prompt,
                "output_path": output_path,
                "width": width,
                "height": height,
                "created_at": created_at,
                "finished_at": finished_at,
                "asset": asset,
                "asset_location": location,
                "asset_present": location == "vault" and (vault / asset).is_file(),
                "generation": generation,
                "stem": stem,
                "superseded_by": None,
                "posts": [],
                "post_embeds": [],
                "post_status": None,
            }
        )

    by_output = {}
    for record in records:
        by_output.setdefault(record["output_path"], []).append(record)
    for group in by_output.values():
        if len(group) < 2:
            continue
        owner = max(
            group,
            key=lambda record: (
                record["finished_at"] or "",
                record["created_at"] or "",
                record["job_id"],
            ),
        )
        for record in group:
            if record is not owner:
                record["superseded_by"] = owner["job_id"]

    return records


def attach_posts(records, posts):
    by_asset = {}
    for record in records:
        if record["asset_location"] == "vault":
            by_asset.setdefault(record["asset"], []).append(record)
    by_basename = {}
    for asset in by_asset:
        by_basename.setdefault(posixpath.basename(asset), set()).add(asset)

    for post in posts:
        matched = set()
        for embed in post["embeds"]:
            targets = list(embed["candidates"])
            for candidate in embed["candidates"]:
                if "/" not in candidate:
                    targets.extend(sorted(by_basename.get(candidate, ())))
            for target in targets:
                if target in matched:
                    continue
                for record in by_asset.get(target, ()):
                    record["posts"].append(post["rel"])
                    record["post_embeds"].append(
                        {
                            "post": post["rel"],
                            "stem": post["stem"],
                            "status": post["status"],
                            "alt": embed["alt"],
                            "section": embed["section"] or "",
                            "excerpt": embed["excerpt"][:400],
                        }
                    )
                    matched.add(target)
                if target in matched:
                    break

    for record in records:
        record["posts"] = sorted(set(record["posts"]))
        record["post_embeds"].sort(key=lambda embed: embed["post"])
        if record["posts"]:
            first = record["post_embeds"][0]
            record["post_status"] = first["status"]


def record_relative_path(record) -> str:
    date = (record["created_at"] or "")[:10]
    month = date[:7]
    filename = f"{date}-{record['stem']}--{record['job_id']}.md"
    return posixpath.join(month, filename)


def render_record(record) -> str:
    lines = ["---"]
    lines.append(f'type: {_json("image-record")}')
    lines.append(f'job_id: {_json(record["job_id"])}')
    lines.append(f'engine: {_json(record["engine"])}')
    lines.append(f'prompt_type: {_json(record["prompt_type"])}')
    lines.append(f'width: {record["width"]}')
    lines.append(f'height: {record["height"]}')
    if record["generation"] is None:
        lines.append("generation: null")
    else:
        lines.append(f'generation: {_json(record["generation"])}')
    lines.append(f'created_at: {_json(record["created_at"])}')
    lines.append(f'finished_at: {_yaml_scalar(record["finished_at"])}')
    lines.append(f'asset: {_json(record["asset"])}')
    lines.append(f'asset_location: {_json(record["asset_location"])}')
    lines.append(f'asset_present: {_yaml_scalar(record["asset_present"])}')
    lines.append(f'superseded_by: {_yaml_scalar(record["superseded_by"])}')
    lines.append(f'posts: {_json(record["posts"])}')
    lines.append(f'post_status: {_yaml_scalar(record["post_status"])}')
    lines.append(f'verdict: {_json("unreviewed")}')
    lines.append(f'source: {_json("backfill")}')
    lines.append("---")
    lines.append("")
    lines.append(f'# {record["stem"]}')
    lines.append("")

    if record["asset_location"] == "vault" and not record["superseded_by"]:
        lines.append(f'![[{record["asset"]}]]')
        lines.append("")

    lines.append("## Why")
    lines.append("")
    if not record["post_embeds"]:
        lines.append("No post embeds this image.")
        lines.append("")
    else:
        for embed in record["post_embeds"]:
            lines.append(f'> {embed["alt"]}' if embed["alt"] else ">")
            lines.append("")
            lines.append(
                f'From [[{embed["stem"]}]], section "{embed["section"]}":'
            )
            lines.append("")
            lines.append(f'> {embed["excerpt"]}' if embed["excerpt"] else ">")
            lines.append("")

    lines.append("## Prompt")
    lines.append("")
    if record["prompt_type"] == "json" and record["parsed_prompt"] is not None:
        lines.append("```json")
        lines.append(
            json.dumps(record["parsed_prompt"], indent=2, ensure_ascii=False)
        )
        lines.append("```")
    else:
        lines.append("```")
        lines.append(record["prompt_value"].strip("\n"))
        lines.append("```")
    lines.append("")

    lines.append("## Verdicts")
    lines.append("")
    lines.append("| round | date | verdict | reason | issue |")
    lines.append("| --- | --- | --- | --- | --- |")
    lines.append("")
    lines.append("Back-filled from jobs.db; not reviewed yet.")
    lines.append("")
    return "\n".join(lines)


def _record_link(record) -> str:
    path = record_relative_path(record)
    label = posixpath.splitext(posixpath.basename(path))[0]
    return f"[[{path}\\|{label}]]"


def _post_link(post) -> str:
    return f"[[{post['rel']}\\|{post['stem']}]]"


def render_index(records, posts) -> str:
    ordered = sorted(records, key=record_relative_path)
    superseded = sum(1 for record in ordered if record["superseded_by"])
    max_only = sum(1 for record in ordered if record["asset_location"] == "max-only")
    with_post = sum(1 for record in ordered if record["posts"])
    without_post = len(ordered) - with_post

    lines = [
        "# Image library",
        "",
        "Generated by `studio/library_backfill.py` from `jobs.db`. Existing records "
        "are never overwritten; this index is regenerated on every run.",
        "",
        "## Totals",
        "",
        "| metric | count |",
        "| --- | --- |",
        f"| records | {len(ordered)} |",
        f"| superseded | {superseded} |",
        f"| max-only | {max_only} |",
        f"| with a post | {with_post} |",
        f"| without a post | {without_post} |",
        "",
        "## Posts",
        "",
    ]

    for post in sorted(posts, key=lambda item: item["rel"]):
        attached = sorted(
            (
                record
                for record in ordered
                if post["rel"] in record["posts"] and not record["superseded_by"]
            ),
            key=record_relative_path,
        )
        status = post["status"] if post["status"] is not None else "—"
        links = ", ".join(_record_link(record) for record in attached) or "—"
        lines.append(f'### {_post_link(post)}')
        lines.append("")
        lines.append("| post | status | records |")
        lines.append("| --- | --- | --- |")
        lines.append(f'| {_post_link(post)} | {status} | {links} |')
        lines.append("")

    unused = [
        record
        for record in ordered
        if not record["superseded_by"] and not record["posts"]
    ]
    lines.append("## Unused")
    lines.append("")
    if unused:
        lines.append("| record | asset |")
        lines.append("| --- | --- |")
        for record in unused:
            lines.append(f'| {_record_link(record)} | `{record["asset"]}` |')
        lines.append("")
    else:
        lines.append("None.")
        lines.append("")
    return "\n".join(lines)


def backfill(db: Path, vault: Path, max_vault_root: str, library_dir: Path, dry_run=False):
    records = build_records(db, vault, max_vault_root)
    posts = scan_posts(vault)
    attach_posts(records, posts)

    created = 0
    skipped = 0
    for record in records:
        target = library_dir / record_relative_path(record)
        if target.exists():
            skipped += 1
            continue
        created += 1
        if dry_run:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_record(record), encoding="utf-8", newline="\n")

    if not dry_run:
        library_dir.mkdir(parents=True, exist_ok=True)
        (library_dir / "index.md").write_text(
            render_index(records, posts), encoding="utf-8", newline="\n"
        )

    return {
        "created": created,
        "skipped": skipped,
        "superseded": sum(1 for record in records if record["superseded_by"]),
        "max_only": sum(
            1 for record in records if record["asset_location"] == "max-only"
        ),
        "with_post": sum(1 for record in records if record["posts"]),
    }


def _summary(counts) -> str:
    return (
        f"created {counts['created']}, skipped {counts['skipped']} (exist), "
        f"superseded {counts['superseded']}, max-only {counts['max_only']}, "
        f"with-post {counts['with_post']}"
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Back-fill the Obsidian image library from jobs.db."
    )
    parser.add_argument("--db", required=True, help="read-only jobs.db snapshot")
    parser.add_argument("--vault", default=DEFAULT_VAULT, help="Obsidian vault root")
    parser.add_argument(
        "--max-vault-root",
        default=DEFAULT_MAX_VAULT_ROOT,
        help="vault root as seen from the Max",
    )
    parser.add_argument(
        "--library-dir",
        default=None,
        help="where records and index.md are written (default: <vault>/"
        + LIBRARY_SUBDIR
        + ")",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="compute the summary, write nothing"
    )
    args = parser.parse_args(argv)

    db = Path(args.db).expanduser()
    if not db.is_file():
        parser.error(f"database not found: {db}")
    vault = Path(args.vault).expanduser()
    library_dir = (
        Path(args.library_dir).expanduser()
        if args.library_dir
        else vault / LIBRARY_SUBDIR
    )

    counts = backfill(
        db=db,
        vault=vault,
        max_vault_root=args.max_vault_root,
        library_dir=library_dir,
        dry_run=args.dry_run,
    )
    print(_summary(counts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
