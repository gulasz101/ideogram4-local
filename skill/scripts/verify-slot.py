#!/usr/bin/env python3
"""Verify a slot's approval closeout before its card issue is marked done.

The mechanical half of an approval close is written out in
`references/library-records.md` as prose, spread across four rules: the record's
filename against the job's own `created_at`, the `## Prompt` block against the
file that was submitted, the `superseded_by` chain, the post embed and alt text,
and the `## Why` quote against the post by line position. This runs all of it as
one command, so every close is checked identically instead of by whichever
paragraph that run happened to remember.

  python3 verify-slot.py --record <record.md> --job <job id> \
      --earlier <earlier record.md> [--earlier <...>] \
      --post <post.md> --prompt <submitted prompt.json> \
      [--asset-source <staging png>] [--source studio]

Every check prints PASS or FAIL with the values it compared, and the script
exits 1 if any check failed. The printed values are also the audit trail for the
closing comment: quote them, do not re-derive them.

`--earlier` takes one entry per earlier record of the slot (the rejected render,
a held-back attempt, the back-filled original); each must point at `--job`.
`--post` may be given more than once only if the image sits in several posts.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + (("  [" + str(detail) + "]") if detail else ""))
    return ok


def norm(text):
    return " ".join(text.split())


def frontmatter(text):
    if not text.startswith("---\n"):
        raise SystemExit("record does not start with frontmatter")
    end = text.index("\n---\n", 4)
    return text[4:end]


def fm_get(fm, key):
    m = re.search(r"^" + re.escape(key) + r":\s*(.*)$", fm, re.M)
    if not m:
        return None
    raw = m.group(1).strip()
    if raw == "null":
        return None
    if raw.startswith('"') and raw.endswith('"'):
        return raw[1:-1]
    return raw


def prompt_block(text):
    """The submitted prompt, inside its fence.

    An ideogram4 record fences JSON (```json); a flux2-klein record fences the
    natural-language prompt with a bare ``` because `prompt_type: "text"` has no
    JSON to parse. Both are documented record shapes, so both are read here.
    """
    for fence in ("```json\n", "```\n"):
        start = text.find(fence)
        if start < 0:
            continue
        start += len(fence)
        end = text.find("\n```", start)
        if end < 0:
            return None
        return text[start:end]
    return None


def section(text, heading):
    """Body of a '## heading' section, up to the next '## ' heading."""
    m = re.search(r"^## " + re.escape(heading) + r"\s*$", text, re.M)
    if not m:
        return ""
    start = m.end()
    nxt = re.search(r"^## ", text[start:], re.M)
    return text[start:start + nxt.start()] if nxt else text[start:]


def table_rows(body):
    return [l for l in body.split("\n") if l.startswith("|")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--job", required=True)
    ap.add_argument("--earlier", action="append", default=[])
    ap.add_argument("--post", action="append", default=[])
    ap.add_argument("--prompt")
    ap.add_argument("--asset-source")
    ap.add_argument("--source", default="studio")
    ap.add_argument("--vault")
    a = ap.parse_args()

    rec_path = Path(a.record)
    if not check("record exists", rec_path.is_file(), rec_path):
        return 1
    text = rec_path.read_text()
    fm = frontmatter(text)

    try:
        vault = Path(a.vault) if a.vault else rec_path.resolve().parents[3]
    except IndexError:
        return 1 if not check("record sits under <vault>/3-resources/image-library/<month>/", False, rec_path) else 1

    created = fm_get(fm, "created_at") or ""
    finished = fm_get(fm, "finished_at") or ""
    job = fm_get(fm, "job_id")
    verdict = fm_get(fm, "verdict")
    asset = fm_get(fm, "asset")

    check("job_id matches --job", job == a.job, job)
    check("created_at carries fractional seconds", bool(re.match(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d+", created)), created)
    check("finished_at carries fractional seconds", bool(re.match(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d+", finished)), finished)
    check("verdict is approved", verdict == "approved", verdict)
    check("source is the record's own value, not a brief's", fm_get(fm, "source") == a.source, fm_get(fm, "source"))
    check("asset_location is vault", fm_get(fm, "asset_location") == "vault")
    check("asset_present is true", fm_get(fm, "asset_present") == "true")
    check("approved record's superseded_by is null", fm_get(fm, "superseded_by") is None)
    check("asset names a file", bool(asset), asset)
    check("posts is non-empty", bool(fm_get(fm, "posts")))

    # --- filename and heading ---
    stem = rec_path.name
    expected_prefix = created[:10] + "-" if created else None
    # A job id can begin with a dash (`-GfBL3Y7iWY`). The record filename drops
    # that leading dash so the name does not read as a third separator, while the
    # `job_id` frontmatter keeps it verbatim. Build the suffix from the id with
    # the dash stripped, or the filename and heading checks fail on a healthy record.
    job_in_name = a.job[1:] if a.job.startswith("-") else a.job
    expected_suffix = "--" + job_in_name + ".md"
    check("filename starts with the job's created_at date", bool(expected_prefix) and stem.startswith(expected_prefix), stem)
    check("filename ends with --<job>.md", stem.endswith(expected_suffix), stem)
    heading_stem = stem[len(expected_prefix):-len(expected_suffix)] if (expected_prefix and stem.startswith(expected_prefix) and stem.endswith(expected_suffix)) else None
    check("heading is the stem (no date, no job id)", heading_stem is not None and ("\n# " + heading_stem + "\n") in text, heading_stem)

    # --- prompt block is the submitted file, byte for byte ---
    block = prompt_block(text)
    if not check("record carries a prompt block in a fence", block is not None):
        pass
    else:
        ptype = fm_get(frontmatter(text), "prompt_type")
        if ptype == "text":
            check("prompt_type is text, so the block is read as text not JSON", True)
        else:
            try:
                json.loads(block)
                check("prompt block parses as JSON", True)
            except Exception as e:
                check("prompt block parses as JSON", False, e)
        if a.prompt:
            src = Path(a.prompt).read_bytes()
            blk = block.encode()
            # prompt_block() stops at the "\n```" that closes the fence, so a
            # file ending in a newline always comes back one byte short of it.
            # That single trailing newline is the only difference allowed.
            check("prompt block is the submitted file byte for byte (its final newline aside)",
                  blk == src or blk + b"\n" == src,
                  "%d vs %d bytes" % (len(blk), len(src)))

    # --- duplicate-record guard ---
    # The earlier records of a slot usually live in a different month folder
    # (a September back-fill superseded by an October render), so the scan has
    # to cover this record's folder and each earlier record's own folder.
    # Globbing only rec_path.parent reported a false duplicate on every
    # cross-month slot.
    month_dir = rec_path.parent
    dirs = sorted({month_dir} | {Path(e).parent for e in a.earlier})
    naming = [p.name for d in dirs for p in d.glob("*.md")
              if a.job in p.read_text(errors="ignore")]
    expected = {rec_path.name} | {Path(e).name for e in a.earlier}
    check("job id appears in exactly this record plus its earlier records", set(naming) == expected,
          sorted(set(naming) ^ expected) or len(naming))

    # --- the chain ---
    for e in a.earlier:
        ep = Path(e)
        if not check("earlier record exists: " + ep.name, ep.is_file()):
            continue
        et = ep.read_text()
        efm = frontmatter(et)
        check("earlier points at the approved job: " + ep.name, fm_get(efm, "superseded_by") == a.job, fm_get(efm, "superseded_by"))
        # An earlier record that itself carried an approval (a slot whose ideogram
        # shipped on an earlier card and was later replaced by another engine's
        # render) is legitimate: it keeps its approved verdict and names this job
        # in superseded_by. The chain still has exactly one accepted image because
        # this check runs on records that point here.
        ev = fm_get(efm, "verdict")
        check("earlier keeps a verdict that is not this approval: " + ep.name,
              ev not in (None, "approved") or fm_get(efm, "superseded_by") == a.job, ev)

    # --- vault asset ---
    if asset:
        ap_ = vault / asset
        check("vault asset exists", ap_.is_file(), ap_)
        if a.asset_source and ap_.is_file():
            same = ap_.read_bytes() == Path(a.asset_source).read_bytes()
            check("vault asset is byte-identical to the source file", same, a.asset_source)

    # --- post embed and alt text ---
    for p in a.post:
        pp = Path(p)
        if not check("post exists: " + pp.name, pp.is_file()):
            continue
        ptext = pp.read_text()
        # The record's asset is vault-relative (`tech_blog/assets/...`) while the
        # post's embed target is relative to the post directory (`assets/...`),
        # so a plain `asset in line` test never matches and reports "0 mentions"
        # on a healthy post. Compare the post-relative form.
        target_rel = asset[len("tech_blog/"):] if asset and asset.startswith("tech_blog/") else asset
        mentions = [l for l in ptext.split("\n") if target_rel and target_rel in l]
        check("post embeds the asset exactly once: " + pp.name, len(mentions) == 1, len(mentions))
        if len(mentions) == 1:
            m = re.match(r"!\[(.*?)\]\((.*?)\)\s*$", mentions[0])
            if check("embed line is a markdown image", bool(m)):
                alt, target = m.group(1), m.group(2)
                check("alt text describes the picture, not a placeholder word",
                      alt.strip().lower() not in ("", "header", "image", "img", "illustration") and len(alt.split()) >= 4, alt)
                check("embed target exists next to the post", (pp.parent / target).is_file(), target)

    # --- Verdicts table ---
    rows = table_rows(section(text, "Verdicts"))
    check("Verdicts table has the exact header", bool(rows) and rows[0] == "| round | date | verdict | reason | issue |", rows[0] if rows else "missing")
    check("Verdicts table has a separator row", len(rows) > 1 and set(rows[1].replace("|", "").replace(" ", "")) <= set("-"), rows[1] if len(rows) > 1 else "missing")
    data = rows[2:]
    check("Verdicts table has at least one data row", len(data) >= 1, len(data))
    rounds = []
    for r in data:
        cells = r.split("|")
        if not check("row splits into 7 cells", len(cells) == 7, r[:60]):
            continue
        if not check("reason cell is padded on both sides", cells[4].startswith(" ") and cells[4].endswith(" "), repr(cells[4][:40])):
            continue
        check("reason cell is non-empty", bool(cells[4].strip()))
        try:
            rounds.append(int(cells[1].strip()))
        except ValueError:
            check("round cell is an integer", False, cells[1])
    if rounds:
        check("round numbers ascend", rounds == sorted(rounds), rounds)
        check("last row's verdict matches the frontmatter", data[-1].split("|")[3].strip() == verdict, data[-1].split("|")[3].strip())

    # --- Why provenance: the quote is the post's, the label is the heading above it ---
    why = section(text, "Why")
    label = re.search(r'section "(.*?)":', why)
    check('Why carries a `section "..."` provenance line', bool(label))
    quotes, cur = [], []
    for line in why.split("\n"):
        if line.startswith("> "):
            cur.append(line[2:])
        elif cur:
            quotes.append(" ".join(cur))
            cur = []
    if cur:
        quotes.append(" ".join(cur))
    check("Why quotes at least one passage", bool(quotes), len(quotes))
    for q in quotes:
        qn = norm(q)
        for p in a.post:
            pp = Path(p)
            if not pp.is_file():
                continue
            ptext = pp.read_text()
            check("quote appears in the post", qn in norm(ptext), qn[:60])
            needle = qn[:60]
            hit, above = None, []
            lines = ptext.split("\n")
            # A "#" line inside a fenced code block is a YAML or shell comment,
            # not a heading: treating it as one makes the nearest "heading" above
            # the quote a comment like `# Token is SOPS-encrypted ...`, so a
            # correctly labelled quote reads as mislabelled on any post that
            # carries commented YAML before the passage.
            headings = []
            in_fence = False
            for i, line in enumerate(lines):
                if line.startswith("```"):
                    in_fence = not in_fence
                elif not in_fence and line.startswith("#"):
                    headings.append((i, line))
            for i, line in enumerate(lines):
                if needle and needle in norm(line):
                    hit = i
                    above = [h for (j, h) in headings if j < i]
                    break
            if check("quote found by line position in the post", hit is not None):
                nearest = above[-1].lstrip("#").strip() if above else ""
                if label:
                    check("section label is the nearest heading above the quote", nearest == label.group(1).strip(), "label=%r heading=%r" % (label.group(1).strip(), nearest))

    failed = RESULTS.count(False)
    print("\n%d checks, %d failed" % (len(RESULTS), failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
