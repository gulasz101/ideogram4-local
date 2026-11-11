#!/usr/bin/env python3
"""Ship approved renders into the vault: file, record, alt text, superseded old file.

Usage:
    python3 ship-approved-batch.py <spec.json> [--dry-run]

The spec is one JSON object. Every path in it is absolute; nothing is guessed from a slug or a
glob, because two posts of one batch share a slug prefix and a glob silently ships the wrong file.

{
  "issue": "GUL-894",
  "vault": "/Users/paperclip/vault",
  "staging": "/Users/paperclip/image-studio/staging/2026-11-04",
  "record_month": "2026-11",
  "record_date": "2026-11-04",
  "items": [
    {"post": "2026-08-17-the-missing-logs.md",   # vault-relative under tech_blog/
     "day": "2026-08-17",                          # asset folder
     "asset": "missing-logs-header.png",          # the filename the post ALREADY embeds
     "old_job": "FIkG4zPy3ug",                    # job behind the file being replaced; "" if new
     "stage": "096-missing-logs-header-ff91fbe4.png",
     "job": "OLe7oYRz9Uw",
     "engine": "nanobanana",
     "generation": {"model": "gemini-image", "seed": null},
     "created": "2026-11-04T05:36:52.511538",
     "finished": "2026-11-04T05:37:07.615185",
     "prompt": "/Users/paperclip/image-studio/prompts/096-header.txt",
     "alt": "one sentence describing the picture",
     "quote": "> the paragraph the image sits under",
     "why": "one or two sentences tying the picture to the section's beat",
     "embed": false,                              # OPTIONAL: the frame is approved but the post
                                                  # keeps one image per step. It still ships to
                                                  # the vault under its own `asset` name (house
                                                  # convention: `<slot>-flux.png`) with its own
                                                  # record, and the post's embed is left alone.
     "prompt_type": "json",                        # OPTIONAL: "json" for ideogram prompts, "text"
                                                  # for flux; defaults to "text".
     "post_status": "draft"}                      # OPTIONAL: the post's real status, so the new
                                                  # record does not claim `null`; defaults to draft.
  ]
}

Prints one line per verified step and a pixel-identity check per item at the end. Exits non-zero
when an embed is missing or appears twice, an alt does not land, or a shipped frame does not decode
to the staged pixels.
"""
import json
import os
import re
import shutil
import sys

from PIL import Image


def superseded_name(asset, old_job):
    stem, ext = os.path.splitext(asset)
    return f"{stem}.superseded-{old_job}{ext}"


def find_old_record(lib, job):
    for root, _, files in os.walk(lib):
        for f in files:
            if f.endswith(f"--{job}.md"):
                return os.path.join(root, f)
    return None


def ship(spec, item, dry):
    n = item["job"]
    day_dir = os.path.join(spec["vault"], "tech_blog/assets", item["day"])
    target = os.path.join(day_dir, item["asset"])
    stage = os.path.join(spec["staging"], item["stage"])
    lib = os.path.join(spec["vault"], "3-resources/image-library")

    # 1. keep the old bytes beside the new file, never delete them
    if item.get("old_job"):
        old_path = os.path.join(day_dir, superseded_name(item["asset"], item["old_job"]))
        if os.path.exists(target) and not os.path.exists(old_path):
            if not dry:
                shutil.move(target, old_path)
            print(f"{n} superseded -> {os.path.basename(old_path)}")
        elif os.path.exists(old_path):
            print(f"{n} old already at {os.path.basename(old_path)}")
        elif os.path.exists(target):
            raise SystemExit(f"{n}: {target} exists but no old_job was given")

    # 2. the approved frame becomes a real PNG at the path the post already embeds
    if not dry:
        with Image.open(stage) as im:
            im.save(target, "PNG", optimize=True)
    with Image.open(target if not dry else stage) as im:
        size, fmt = im.size, im.format
    print(f"{n} wrote {item['asset']} fmt={fmt} size={size} bytes={os.path.getsize(target if not dry else stage)}")

    # 3. the embed must exist exactly once, and the placeholder alt becomes a description.
    # An approved alternative that the post does not embed sets "embed": false and
    # skips this step: it ships to the vault beside the embedded frame as <slot>-flux.png
    # so the pair Wojtek approved is kept, without a second image in the post.
    post_path = os.path.join(spec["vault"], "tech_blog", item["post"])
    if item.get("embed", True):
        text = open(post_path, encoding="utf-8").read()
        embed = f"assets/{item['day']}/{item['asset']}"
        hits = len(re.findall(re.escape(embed), text))
        if hits != 1:
            raise SystemExit(f"{n}: embed {embed} appears {hits} times in {item['post']}")
        new_line = f"![{item['alt']}]({embed})"
        text2 = re.sub(r"!\[[^\]]*\]\(" + re.escape(embed) + r"\)", new_line, text)
        if text2 != text and not dry:
            open(post_path, "w", encoding="utf-8").write(text2)
            print(f"{n} alt rewritten")
        back = open(post_path, encoding="utf-8").read() if not dry else text2
        if new_line not in back:
            raise SystemExit(f"{n}: alt did not land in {item['post']}")
        if "tech_blog/tech_blog/" in back:
            raise SystemExit(f"{n}: doubled tech_blog path in {item['post']}")
    else:
        print(f"{n} approved alternative: not embedded, kept beside the post's frame")

    # 4. the old record must stop pointing at a file that now holds other bytes
    if item.get("old_job"):
        old_rec = find_old_record(lib, item["old_job"])
        if old_rec:
            r = open(old_rec, encoding="utf-8").read()
            r = r.replace(f'asset: "tech_blog/assets/{item["day"]}/{item["asset"]}"',
                          f'asset: "tech_blog/assets/{item["day"]}/{superseded_name(item["asset"], item["old_job"])}"')
            # the record's own embed must follow the moved file too, or it renders the
            # shipped picture inside a record that documents different bytes
            r = r.replace(f'![[tech_blog/assets/{item["day"]}/{item["asset"]}]]',
                          f'![[tech_blog/assets/{item["day"]}/{superseded_name(item["asset"], item["old_job"])}]]')
            r = re.sub(r"superseded_by: (null|\"[^\"]*\")", f'superseded_by: "{item["job"]}"', r, count=1)
            marker = f"Superseded by the `{item['job']}` render"
            if marker not in r:
                r = r.rstrip() + (f"\n\n**{marker}** on [{spec['issue']}](/GUL/issues/{spec['issue']}). "
                                  f"The post's embed now carries that render, and this job's own picture is kept beside it "
                                  f"as `tech_blog/assets/{item['day']}/{superseded_name(item['asset'], item['old_job'])}`.\n")
            if not dry:
                open(old_rec, "w", encoding="utf-8").write(r)
            print(f"{n} old record patched: {os.path.basename(old_rec)}")

    # 5. the new record, named off the fetched stem and the job id
    stem = os.path.splitext(item["stage"])[0]
    rec_dir = os.path.join(lib, spec["record_month"])
    rec_name = f"{spec['record_date']}-{stem}--{item['job']}.md"
    prompt_text = open(item["prompt"], encoding="utf-8").read().strip()
    gen = json.dumps(item.get("generation")) if item.get("generation") is not None else "null"
    front = (f'---\ntype: "image-record"\njob_id: "{item["job"]}"\nengine: "{item.get("engine", "nanobanana")}"\n'
             f'prompt_type: "{item.get("prompt_type", "text")}"\nwidth: {size[0]}\nheight: {size[1]}\ngeneration: {gen}\n'
             f'created_at: "{item["created"]}"\nfinished_at: "{item["finished"]}"\n'
             f'asset: "tech_blog/assets/{item["day"]}/{item["asset"]}"\nasset_location: "vault"\n'
             f'asset_present: true\nsuperseded_by: null\nposts: ["tech_blog/{item["post"]}"]\n'
             f'post_status: "{item.get("post_status", "draft")}"\nverdict: "approved"\nsource: "studio"\n---\n')
    body = (f"\n# {stem}\n\n![[tech_blog/assets/{item['day']}/{item['asset']}]]\n\n## Why\n\n{item['why']}\n\n"
            f"From [[{item['post'][:-3]}]]\n\n{item.get('quote', '')}\n\n## Prompt\n\n```\n{prompt_text}\n```\n\n"
            f"## Verdicts\n\n| round | date | verdict | reason | issue |\n| --- | --- | --- | --- | --- |\n"
            f'| {spec.get("round", 1)} | {spec["record_date"]} | approved | no reason given on the card | '
            f"[{spec['issue']}](/GUL/issues/{spec['issue']}) |\n")
    if not dry:
        os.makedirs(rec_dir, exist_ok=True)
        open(os.path.join(rec_dir, rec_name), "w", encoding="utf-8").write(front + body)
    print(f"{n} record {rec_name}")
    return target, stage


def main():
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    dry = "--dry-run" in sys.argv
    pairs = [ship(spec, item, dry) for item in spec["items"]]
    if dry:
        print("dry run: no file written")
        return
    try:
        import numpy as np
    except ImportError:
        print("numpy missing: pixel check skipped, compare by eye before closing")
        return
    for target, stage in pairs:
        a = np.asarray(Image.open(stage).convert("RGB")).astype(int)
        b = np.asarray(Image.open(target).convert("RGB")).astype(int)
        same = a.shape == b.shape and int(np.abs(a - b).max()) == 0
        print(f"pixels {os.path.basename(target)} maxdiff=0 {same}")
        if not same:
            raise SystemExit(f"{target} does not decode to {stage}")


if __name__ == "__main__":
    main()
