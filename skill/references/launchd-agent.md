# LaunchAgent for ideogram4-local

Location: `~/Library/LaunchAgents/com.gulasz101.ideogram4-local.worker.plist`

Purpose:
- Start the Ideogram 4 worker at user login.
- Restart the worker if it crashes.
- Prevent crash loops via `ThrottleInterval`.

What it runs:

```
/opt/homebrew/bin/python3 /Users/wojciechgula/git/ideogram4-local/ideogram4_local.py worker --queue-timeout 86400
```

Environment variables set by the plist:

| Variable | Value |
|---|---|
| `IDEOGRAM4_MODELS_DIR` | `/Users/wojciechgula/sd.cpp-models` |
| `IDEOGRAM4_OUTPUT_DIR` | `/Users/wojciechgula/git/ideogram4-local/output` |
| `IDEOGRAM4_DB` | `/Users/wojciechgula/git/ideogram4-local/jobs.db` |
| `IDEOGRAM4_LOCK_FILE` | `/Users/wojciechgula/git/ideogram4-local/.lock` |

Logs go to `~/git/ideogram4-local/output/worker.log`.

Load:

```bash
launchctl unload ~/Library/LaunchAgents/com.gulasz101.ideogram4-local.worker.plist 2>/dev/null || true
launchctl load ~/Library/LaunchAgents/com.gulasz101.ideogram4-local.worker.plist
launchctl list | grep com.gulasz101.ideogram4-local.worker
```

Unload:

```bash
launchctl unload ~/Library/LaunchAgents/com.gulasz101.ideogram4-local.worker.plist
```

Restart:

```bash
launchctl unload ~/Library/LaunchAgents/com.gulasz101.ideogram4-local.worker.plist
launchctl load ~/Library/LaunchAgents/com.gulasz101.ideogram4-local.worker.plist
```

Migration note from manual worker:
If a manual `python3 ideogram4_local.py worker` is already running when you load the LaunchAgent, **do not load launchd while the generation is mid-sampling**. Let the current generation finish (the worker log will show `save result image`), then:

1. Kill the manual worker and any `sd-cli` child:
   ```bash
   pkill -f 'ideogram4_local.py worker'
   pkill -f 'sd-cli'
   ```
2. Remove the stale lock file:
   ```bash
   rm -f ~/git/ideogram4-local/.lock
   ```
3. Mark the just-finished job `done` in the SQLite queue (manual workers may exit before updating the DB):
   ```bash
   cd ~/git/ideogram4-local
   python3 - <<'PY'
   import sqlite3, datetime
   conn = sqlite3.connect('jobs.db')
   cur = conn.cursor()
   # replace with the actual running job id
   cur.execute("UPDATE jobs SET status='done', finished_at=? WHERE id='REPLACE_ME'",
               (datetime.datetime.now().isoformat(),))
   conn.commit()
   conn.close()
   PY
   ```
4. Then load the LaunchAgent.

This avoids two workers fighting over the lock and prevents stale `running` rows in `jobs.db`.

Key plist knobs:
- `KeepAlive.Crashed=true` — restart on crash.
- `RunAtLoad=true` — auto-start at login.
- `ThrottleInterval=30` — minimum 30 seconds between restarts.
- `ProcessType=Background` — polite background priority.
- Logs to `~/git/ideogram4-local/output/worker.log` (stdout and stderr merged).

Troubleshooting:
- If `launchctl load` fails silently on newer macOS, use `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.gulasz101.ideogram4-local.worker.plist` followed by `launchctl enable gui/$(id -u)/com.gulasz101.ideogram4-local.worker`. Verify with `launchctl list | grep com.gulasz101.ideogram4-local.worker`.
- If the worker is not listed but `pgrep` shows a process, it may be a leftover manual worker. Kill it and reload.
