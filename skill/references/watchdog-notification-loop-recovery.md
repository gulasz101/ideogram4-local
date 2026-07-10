# ideogram4-local watchdog notification-loop recovery

Session: 2026-07-05.

## Failure mode

The ideogram4-progress-watchdog cron posted the same finished image to the `ideogram4-local` Mattermost channel roughly every 5 minutes for ~50 posts.

## Root cause

Job IDs are generated as random/base64 strings and can start with a leading dash, e.g. `-MuwvZtmc74`.

`post_status.sh` checked whether a `done` job had already been announced with:

```bash
if ! echo "$NOTIFIED" | grep -qx "$job_id"; then
```

When `job_id` is `-MuwvZtmc74`, `grep` parses it as an option:

```
grep: invalid option -- 'M'
```

That error exits non-zero, so the `if ! ...` branch thinks the job has **not** been notified yet. It posts the image again and appends the same ID to the state file. Every cron tick repeats this, filling the channel and bloating `~/.ideogram4-local/.notified_done_jobs`.

## Fix

### 1. Pause the cron job

```bash
hermes cron pause ideogram4-progress-watchdog
# job_id 4641a45c3dbe
```

### 2. Make the grep call option-safe

In `post_status.sh` (checked out at `~/git/ideogram4-local`):

```diff
-    if ! echo "$NOTIFIED" | grep -qx "$job_id"; then
+    if ! echo "$NOTIFIED" | grep -qxF -- "$job_id"; then
```

- `-F` — force literal string matching.
- `--` — stop option parsing so IDs starting with `-` are treated as data.

### 3. Deduplicate the state file

```bash
sort -u ~/.ideogram4-local/.notified_done_jobs > /tmp/notified_clean.txt
mv /tmp/notified_clean.txt ~/.ideogram4-local/.notified_done_jobs
```

### 4. Verify, then resume

```bash
cd ~/git/ideogram4-local && bash post_status.sh
# expect no output when queue is idle and all done jobs are already announced

hermes cron resume ideogram4-progress-watchdog
```

## Validation

- Run `post_status.sh` twice after the fix; it should be silent and should not grow `.notified_done_jobs`.
- Check the target Mattermost channel: no duplicate image posts at the next 5-minute tick.

## General rule for watchdog scripts

When matching or passing externally-generated IDs in bash, always defend against leading dashes:

```bash
# Safe: treat remaining args as data
grep -qxF -- "$id" file
rm -f -- "$id"
cp -- "$src" "$dst"
```

Using `printf '%s\n' "$id" | grep -qxF` is also safe but `--` is the simpler fix.

## One-liner status check

```bash
printf "Total state entries: %d\n" "$(wc -l < ~/.ideogram4-local/.notified_done_jobs)"
printf "Unique state entries: %d\n" "$(sort -u ~/.ideogram4-local/.notified_done_jobs | wc -l)"
```

If the two numbers differ, the state file has duplicate notification records and should be rebuilt with `sort -u`.

## Reference

- `ideogram4-local/SKILL.md` Pitfall #7: Job IDs can start with a leading dash, which breaks naive `grep`.
- Tracking note: `homelab/tracking/2026-07-05-ideogram-watchdog-repost-loop.md`.
