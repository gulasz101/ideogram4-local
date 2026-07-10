# Mattermost channel delivery for the Ideogram 4 watchdog

Date: 2026-07-01
Context: getting the Ideogram 4 watchdog cron to post finished images to the dedicated channel `ideogram4-local` (`ygs1pwhzi7grurg9poui33oqja`) instead of the default `homelab-2nd` channel.

## What did not work

1. **Cron `deliver: mattermost:ygs1pwhzi7grurg9poui33oqja`**
   - The cron reported `ok` but the message either did not arrive or landed in the home channel.
   - The Hermes gateway must already know the channel; a bare channel ID it has not synced is silently unreliable.

2. **`hermes send --to mattermost:ygs1pwhzi7grurg9poui33oqja`**
   - Failed with `Could not resolve 'ygs1pwhzi7grurg9poui33oqja' on mattermost`.
   - `hermes send --list mattermost` showed only channels the gateway had already learned.
   - Even after the gateway learned the channel, `hermes send` kept falling back to the home channel (`mrnhuzmr63fuzrbky893j4if6c`).

3. **`MEDIA:/path/to/image.png` in cron responses and `hermes send`**
   - Cron delivery with `MEDIA:` produced plugin timeouts or fell back to text-only.
   - `hermes send "MEDIA:/path"` raised `stat: path should be string, bytes, os.PathLike or integer, not tuple`.

## What worked

A bash script that calls the Mattermost REST API directly using the gateway's own `MATTERMOST_TOKEN` and `MATTERMOST_URL` from `~/.hermes/profiles/andrzej/.env`.

Key points:

- Source the andrzej profile `.env` so the script reuses the existing bot token:
  ```bash
  set -a
  source "$HOME/.hermes/profiles/andrzej/.env"
  set +a
  ```

- Text posts go to `/api/v4/posts`:
  ```bash
  curl -H "Authorization: Bearer $MATTERMOST_TOKEN" \
       -H "Content-Type: application/json" \
       -d '{"channel_id":"ygs1pwhzi7grurg9poui33oqja","message":"hello"}' \
       "$MATTERMOST_URL/api/v4/posts"
  ```

- File uploads **require `channel_id` as a multipart form field**, not just the file:
  ```bash
  curl -H "Authorization: Bearer $MATTERMOST_TOKEN" \
       -F "channel_id=ygs1pwhzi7grurg9poui33oqja" \
       -F "files=@/path/to/image.png" \
       "$MATTERMOST_URL/api/v4/files"
  ```

- The returned `file_infos[0].id` is then attached to the post:
  ```bash
  curl -H "Authorization: Bearer $MATTERMOST_TOKEN" \
       -H "Content-Type: application/json" \
       -d '{"channel_id":"ygs1pwhzi7grurg9poui33oqja","message":"done","file_ids":["FILE_ID"]}' \
       "$MATTERMOST_URL/api/v4/posts"
  ```

- Track already-announced jobs in `~/.ideogram4-local/.notified_done_jobs` so finished images are not reposted every cron tick.

## How to verify the channel is reachable

```bash
hermes --profile andrzej send --list mattermost | grep ygs1pwhzi7grurg9poui33oqja
```

If the channel is absent:
- Make sure the `@andrzej` bot user is a member of the channel (not just the human user).
- Post at least one message in the channel so the gateway learns it.
- Restart the gateway from outside a gateway session (e.g., via `launchctl` or a fresh shell).

If the channel is present but `hermes send` still falls back to the home channel, use the direct API script instead.

## Implementation in the repo

`~/git/ideogram4-local/post_status.sh` implements the above. It is invoked by the Hermes cron job `ideogram4-progress-watchdog` every 5 minutes with `deliver: local` (the script handles Mattermost delivery itself).
