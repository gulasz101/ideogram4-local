# Mattermost watchdog for ideogram4-local

How the ideogram4-local worker posts progress updates and finished-image attachments to a dedicated Mattermost channel.

## Why not Hermes `cron` delivery?

Two problems were discovered while wiring the watchdog:

1. **Hermes `hermes send`/`cron deliver: mattermost:` falls back to the user's home channel.**
   If the gateway has not yet learned about a new channel, sending to `mattermost:<channel-id>` silently resolves to the home channel.
2. **Cron responses containing `MEDIA:/path/to/file.png` do not reliably attach files to Mattermost.**
   The delivery pipeline raised errors/timeouts when a local file path was embedded.

The working solution is a small bash script in the repo that calls the Mattermost REST API directly with the bot token that the Hermes `andrzej` profile already has.

## Script

`post_status.sh` in `gulasz101/ideogram4-local`:
- Sources `~/.hermes/profiles/andrzej/.env` to read `MATTERMOST_TOKEN` and `MATTERMOST_URL`.
- Reads `jobs.db` to count `pending`/`running`/`done`/`failed` jobs.
- Tracks already-announced `done` jobs in `~/.ideogram4-local/.notified_done_jobs`.
- For each new `done` job, uploads the output PNG to Mattermost `/api/v4/files` (with `channel_id` as a form field) and then creates a post attaching the returned `file_ids`.
- When jobs are active, posts a plain progress update with worker/sd-cli process status and the latest worker log line.
- Does nothing when the queue is idle.

## Cron wiring

```bash
hermes cron create "every 5m" \
  --name ideogram4-progress-watchdog \
  --toolsets terminal \
  --deliver local
```

The prompt is just:

```bash
set -a
source "$HOME/.hermes/profiles/andrzej/.env"
set +a
export IDEOGRAM4_MODELS_DIR="${IDEOGRAM4_MODELS_DIR:-$HOME/sd.cpp-models}"
cd "$HOME/git/ideogram4-local"
bash post_status.sh
```

Setting `deliver: local` is important — the script itself handles Mattermost delivery; letting Hermes deliver the cron response to the chat just adds noise.

## Verifying the target channel

Before relying on a channel ID, confirm the bot account can reach it:

```bash
set -a
source "$HOME/.hermes/profiles/andrzej/.env"
set +a

# List channels the gateway currently knows
hermes --profile andrzej send --list mattermost

# Test post directly via API
curl -s -H "Authorization: Bearer $MATTERMOST_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"channel_id":"ygs1pwhzi7grurg9poui33oqja","message":"test"}' \
  "$MATTERMOST_URL/api/v4/posts"

# Test file upload (channel_id is required as form field)
curl -s -H "Authorization: Bearer $MATTERMOST_TOKEN" \
  -F "channel_id=ygs1pwhzi7grurg9poui33oqja" \
  -F "files=@/path/to/image.png" \
  "$MATTERMOST_URL/api/v4/files"
```

If the direct API test returns 201/200 but `hermes send --list` does not show the channel, the script approach is the right one.

## Key Mattermost API details

- **Post with file attachment:** `POST /api/v4/posts` with JSON body `{"channel_id":"...","message":"...","file_ids":["..."]}`.
- **File upload:** `POST /api/v4/files` with `multipart/form-data`. Must include `channel_id` field, not just the file, or you get a 400/403.

## Leading-dash job IDs and the grep `--` pitfall

On 2026-07-05 the watchdog reposted the same finished image roughly every 5 minutes. The culprit was job ID `-MuwvZtmc74`, which starts with a dash.

The original deduplication check was:

```bash
if ! echo "$NOTIFIED" | grep -qx "$job_id"; then
```

`grep` parsed `-MuwvZtmc74` as an option (`-M` is invalid), errored out, returned non-zero, and the `if ! ...` branch interpreted that as "not yet announced". Every tick appended the same ID to `~/.ideogram4-local/.notified_done_jobs` and reposted the image.

Fix: force literal matching and terminate option parsing:

```bash
if ! echo "$NOTIFIED" | grep -qxF -- "$job_id"; then
```

Recovery steps:
1. Pause the cron job first.
2. Apply the `--` fix in `post_status.sh`.
3. Clean the state file: `sort -u ~/.ideogram4-local/.notified_done_jobs > /tmp/clean && mv /tmp/clean ~/.ideogram4-local/.notified_done_jobs`.
4. Run the script manually and confirm it is silent.
5. Resume the cron job.

## Repo hygiene note

As of this session, `post_status.sh` is **not tracked** in `gulasz101/ideogram4-local` (`git ls-files` does not list it), and the repo contains several untracked prompt JSON files plus a stray `post_status.py`. For a rebuildable setup, either commit `post_status.sh` to the repo or move it to a known stable path outside the repo and update the cron prompt accordingly.

## Security

The script uses the existing bot token from the Hermes profile `.env`. No extra token file is created, and nothing is committed to the public repo.
