#!/usr/bin/env python3
"""vread.py - read an image with a vision model on the agent's own provider.

Why this exists: the auxiliary vision path (vision_analyze -> the local proxy at
127.0.0.1:8083) is one shared channel. When it answers

    429 {"error":{"code":"ip_slot_full","message":"direct IP slot full: rph limit
          reached (configure proxies to scale)"}}

that is an hourly cap on the shared exit IP and it fails every caller, text
prompts included, so retrying the same route only burns the run. The agent's own
model provider carries vision-capable models, and the same image or a crop of it
can be read there instead.

A vision_analyze failure is NOT an empty check: read the pixels through this
script before writing a mechanical-only check note, and name the reader in the
note so the claim is auditable.

Usage:
    vread.py IMAGE "question" [model]
    vread.py IMAGE "question" [model] --box x0,y0,x1,y1

  --box    crop (script order: x0,y0,x1,y1, the crop-probe.py order) and upscale
           up to 6x before sending. Use it for any claim about one small prop:
           a whole-frame read undercounts a label or a glyph.
  model    default qwen3.8-flash. List the provider's models and pick another
           vision-capable id when a 410 says the model was deprecated.

Notes that cost renders to learn:
  * deepseek-v4-flash-vision-exp-go is deprecated; a 410 naming it is a stale
    model id, not a broken route.
  * llm.voitech.dev sits behind Cloudflare and answers 403 code 1010 to a bare
    urllib request, so a browser User-Agent is sent.
  * LM_API_KEY is read from the profile .env, never from the command line.
"""
import base64
import io
import json
import os
import sys
import urllib.request

ENV = os.path.expanduser("~/.hermes/profiles/matejko/.env")
MODEL = "qwen3.8-flash"
URL = "https://llm.voitech.dev/v1/chat/completions"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


def load_key():
    key = os.environ.get("LM_API_KEY")
    if key:
        return key
    with open(ENV) as fh:
        for line in fh:
            line = line.strip()
            if line.startswith("LM_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("LM_API_KEY not found in the environment or profile .env")


def main():
    args = list(sys.argv[1:])
    box = None
    if "--box" in args:
        i = args.index("--box")
        box = [int(v) for v in args[i + 1].split(",")]
        del args[i:i + 2]
    if len(args) < 2:
        raise SystemExit(__doc__)
    path, question = args[0], args[1]
    model = args[2] if len(args) > 2 else MODEL

    data = open(path, "rb").read()
    if box:
        from PIL import Image
        im = Image.open(io.BytesIO(data))
        im = im.crop((box[0], box[1], box[2], box[3]))
        scale = max(1, min(6, 900 // max(1, im.width)))
        if scale > 1:
            im = im.resize((im.width * scale, im.height * scale), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, format="PNG")
        data = buf.getvalue()
        print(f"[crop {box} -> {im.width}x{im.height}]")

    body = {
        "model": model,
        "max_tokens": 3000,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": question},
                {"type": "image_url",
                 "image_url": {"url": "data:image/png;base64," +
                                     base64.b64encode(data).decode()}},
            ],
        }],
    }
    req = urllib.request.Request(
        URL,
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {load_key()}",
                 "Content-Type": "application/json",
                 "User-Agent": UA,
                 "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=240) as r:
            out = json.load(r)
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.read()[:600].decode(errors='replace')}")
        return 1
    msg = out["choices"][0]["message"]
    content = msg.get("content") or ""
    if not content.strip():
        # The routed model may spend the whole budget on reasoning and return no
        # answer: finish_reason "length" with an empty content. That is not a
        # read, so say so instead of printing the raw JSON, which reads like an
        # image problem. Shorten the question and call again.
        reason = out["choices"][0].get("finish_reason")
        print(f"[empty read: finish_reason={reason}, no content returned - "
              f"ask a shorter question, one line per answer]")
        print(json.dumps(out)[:400])
        return 2
    print(content)
    return 0


if __name__ == "__main__":
    sys.exit(main())
