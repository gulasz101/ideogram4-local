# SQLite queue maintenance recipes for ideogram4-local

One-off snippets for fixing stale queue state. Run from `~/git/ideogram4-local`.

## Mark a finished job as `done`

Use this when the worker produced the output file but exited before updating the database row.

```bash
cd ~/git/ideogram4-local
python3 - <<'PY'
import sqlite3, datetime
conn = sqlite3.connect('jobs.db')
cur = conn.cursor()
job_id = 'REPLACE_WITH_ACTUAL_JOB_ID'
cur.execute(
    "UPDATE jobs SET status='done', finished_at=? WHERE id=?",
    (datetime.datetime.now().isoformat(), job_id)
)
conn.commit()
print(f"Updated {job_id} to done")
conn.close()
PY
```

## Delete a test/accidental job

```bash
cd ~/git/ideogram4-local
python3 - <<'PY'
import sqlite3
conn = sqlite3.connect('jobs.db')
cur = conn.cursor()
job_id = 'REPLACE_WITH_ACTUAL_JOB_ID'
cur.execute("DELETE FROM jobs WHERE id=?", (job_id,))
conn.commit()
print(f"Deleted {job_id}")
conn.close()
PY
```

## List all jobs

```bash
cd ~/git/ideogram4-local
python3 - <<'PY'
import sqlite3, json
conn = sqlite3.connect('jobs.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("SELECT * FROM jobs ORDER BY created_at")
for row in cur.fetchall():
    print(json.dumps(dict(row), indent=2, default=str))
conn.close()
PY
```

## Reset the whole queue (dangerous — only when debugging)

```bash
cd ~/git/ideogram4-local
rm -f jobs.db .lock
```

This removes all job history. Do not do this if you care about the existing jobs.
