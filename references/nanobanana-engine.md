# nano banana engine — the Gemini web image tool on the Image Studio queue

Third engine on the same SQLite queue and worker. It reaches Gemini's web image tool (nano banana)
through `gemini-web2api-go`, the cookie-driven Gemini proxy that already backs ZeroClaw. No Google
API key, no local weights, no GPU time.

## Wire format (verified against proxy v4.22.0, 2026-11-04)

```
POST http://127.0.0.1:8083/v1/chat/completions
Authorization: Bearer <proxy API key>
{"model": "gemini-image", "messages": [{"role": "user", "content": "<prompt>"}], "stream": false}
```

The reply is an ordinary chat completion whose `content` is markdown:

```
http://googleusercontent.com/image_generation_content/0_876  ![image](data:image/jpeg;base64,/9j/4AAQ…)
```

Take the `data:image/<type>;base64,` payload, base64-decode it, write the bytes to the job's output
path. The `http://googleusercontent.com/...` URL is session-scoped — **do not** try to fetch it.

Proxy `GET /` reports its version and model list; `gemini-image` must be in that list. The 4.22.0
build has **no** `/v1beta/models/{model}:generateContent` route (that landed in a later release), so
the OpenAI-compatible chat route is the one to use.

## Measured behaviour

| | nano banana | FLUX.2-klein | Ideogram 4 |
|---|---|---|---|
| Time per image | **11.5 s** | ~173 s | ~21 min |
| Output | 1376×768 JPEG | 1216×832 PNG | 1216×832 PNG |
| Prompt | natural language | natural language | canonical JSON |
| Size control | none (web tool decides) | `-W`/`-H` | `-W`/`-H` |
| Seed | none | integer | none |
| Needs | live Firefox cookie in the proxy | 15 GB weights + venv | 16 GB weights + sd.cpp |

## Operational rules

1. **The key lives in a 0600 file, not in the repo**: `~/.config/image-studio/gemini-web.key`
   (or `GEMINI_WEB_API_KEY` in the worker environment). `nanobanana_api_key()` reads env first, file
   second, and refuses with a clear message when both are missing.
2. **Check the proxy before blaming the engine.** `curl -s http://127.0.0.1:8083/` must return
   `{"status":"ok",…}`. A hung socket with the port still listening means the *container* is wedged:
   restart it (`docker start gemini-web2api` — it has `restart=no`). That trap cost a full session.
3. **Text instead of an image is the failure mode to recognise.** When the account is rate limited or
   the cookie is stale, the proxy answers 200 with prose. The worker turns that into
   `nano banana returned no image; the model said: <its words>` — read those words, they name the
   real cause (quota, sign-in, refusal).
4. **Rate limits are per exit IP, not per account.** Calm traffic (~1 image a minute) is fine;
   a bulk backlog run should pace itself rather than fire 150 prompts in one go.
5. **Sizes are not ours to choose.** Record the size that arrives (the log line does) and let the
   layout adapt; do not promise a 1216×832 header from this engine.

## Library record

A finished job stores `engine = "nanobanana"`, `seed = NULL`, and the output file is whatever
extension the upstream MIME type implies (`.jpg` for `image/jpeg`). The library back-fill reads the
engine column, so a nano banana image shows up labelled by its engine, not as an Ideogram render.
