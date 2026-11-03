# nano banana — the Gemini web image engine (GUL-893)

Third engine on the Image Studio queue. Deployed 2026-11-04 on `main` (`14a6625`), engine id
`nanobanana`.

```
imagegen submit --engine nanobanana --prompt "<natural language>" --name <slug> [--json]
imagegen status <job-id>
imagegen fetch <job-id>          # → ~/image-studio/staging/<YYYY-MM-DD>/<slug>-<token>.png
```

## What it is

Gemini's own web image tool, reached through the `gemini-web2api-go` proxy on the Max
(`127.0.0.1:8083`, model `gemini-image`). The proxy drives a logged-in Gemini web session with a
Firefox cookie, so there is no Google API key and no per-image cost. The worker posts one chat
completion, the reply carries the picture inline as `data:image/jpeg;base64,…`, and the worker
decodes it to the job's output path.

## Measured

| | nanobanana | flux2-klein | ideogram4 |
|---|---|---|---|
| time | **12 s** (11.5–17 s seen) | ~173 s | ~21 min |
| size | 1376×768, seen 1584×672 | 1216×832 (`-W/-H`) | 1216×832 (`-W/-H`) |
| format | JPEG | PNG | PNG |
| prompt | natural language | natural language | canonical JSON |
| seed | none | integer | none |

Live job GUL-893 `bLnRpFS8X2g`: 1376×768 JPEG, 110,745 bytes, done in ~40 s wall clock including a
cold model turn; the engine call itself took 12 s when run directly.

## Rules

1. **One image a minute, 5-8 posts a wake.** Per-exit-IP rate limiting: a burst throttles the account
   for ~2 hours and takes the whole proxy down, not just this engine.
2. **The size is upstream's.** Do not promise a canvas size. Tell the post's layout what arrived.
3. **Prose instead of a picture = stale cookie or quota.** The `error` field carries the model's own
   words. Skip the post, report it, no retry loops.
4. **`unknown engine 'nanobanana'`** means the Max checkout is behind `main` — stop and say so, do not
   quietly fall back to Ideogram.
5. **The queue is shared and serialised.** A worker restart kills the running job ("killed by signal
   15"). If you need a restart, do it only on a queue with zero pending and zero running.

## Prompting

Write it like a brief, not like an Ideogram caption: subject, composition, palette, lighting, style
("flat-vector editorial illustration, dark navy background, amber accents, no text"). The web model
follows adjectives and mood well, and it does not need schema hygiene. Ask for no text/lettering and
overlay any title in the layout instead.
