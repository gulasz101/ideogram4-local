# Air wrapper: deployment and smoke test

Hermes runs on the Air, the Ideogram 4 worker stays on the M1 Max. `studio/imagegen.py` is the bridge: it submits jobs from the Air over the existing LAN SSH key, reports queue position and ETA, and fetches finished PNGs. This is the reference for when `imagegen` is missing, stale, or misconfigured.

## Install the wrapper on the Air

```bash
mkdir -p ~/.local/share
if [ -d ~/.local/share/ideogram4-local/.git ]; then
  git -C ~/.local/share/ideogram4-local pull --ff-only
else
  git clone git@github.com:gulasz101/ideogram4-local.git ~/.local/share/ideogram4-local
fi
ln -sf ~/.local/share/ideogram4-local/studio/imagegen.py ~/.local/bin/imagegen
which imagegen   # should resolve to the symlink into ~/.local/share/ideogram4-local
```

Do **not** point the symlink at `~/Projects/ideogram4-local`; that clone is the engineers' working copy and switches branches.

## Update the M1 Max worker checkout

```bash
ssh m1max 'git -C ~/git/ideogram4-local pull --ff-only'
ssh m1max 'git -C ~/git/ideogram4-local log --oneline -1'
ssh m1max 'launchctl list | grep ideogram4-local.worker'
```

Leave untracked files where they are and do not `git clean`. The worker must be loaded before submitting jobs from the Air.

## Run a live smoke test

```bash
JOB_ID=$(imagegen submit \
  --prompt-json ~/.local/share/ideogram4-local/templates/prompt-blog-gitops-header-single-pass.json \
  --name smoke-gul-21)
echo "Job ID: $JOB_ID"
imagegen status "$JOB_ID"
# ~21 minutes later
PNG=$(imagegen fetch "$JOB_ID")
echo "Fetched: $PNG"
ls -l "$PNG"
```

`fetch` prints the local path on stdout, under `~/image-studio/staging/<date>/`; the filename is `<slug>-<8 hex>.png`. Use that path for the size check and the upload rather than guessing a `<slug>.png` name. `fetch` takes `--dest <directory>` and nothing else: `--out <file>` is rejected with `unrecognized arguments`, because the wrapper always derives the filename from the job's slug and hex. Pass the date directory you want and capture the printed path.

**`status`'s `output_path` is a path on the Max, and on the Air it resolves into a local tree that does not hold the file.** `/Users/wojciechgula` is a symlink to `/Users/paperclip`, so `…/git/ideogram4-local/output/studio/<date>/<slug>.png` looks like a local path and `ls` or `cp` on it answers `No such file or directory` for a directory that plainly exists — which reads as a lost render. It is not lost; the render never left the Max. Do not open that path, do not search for the PNG on disk (a `find` for it is a denied wide search and a wasted call), and do not inspect the local `output/` directory, which stays empty because the worker writes on the Max. Run `imagegen fetch <job-id>` and take the path it prints.

## The queue is one FIFO, whatever the engine

Every engine shares a single worker queue, run one job at a time in creation order, so a fast nano banana job submitted after two ideogram jobs waits behind both of them. `queue_ahead` and `eta_minutes` on a pending job are a **static estimate frozen at submit**: they do not tick down, so a job that has not moved in 40 minutes looks identical to one that is about to run.

- **Read the real queue over SSH, not only `imagegen status`.** `ssh m1max "cd ~/git/ideogram4-local && python3 ideogram4_local.py list"` prints every recent job newest-first with `status`, `engine`, `started_at` and `finished_at`; the FIFO order is by `created_at` ascending, which is the reverse of the listing.
- **A render can run far past its nominal ETA.** An ideogram4 job at ~21 minutes normally can sit at `running` for 45+ minutes: `ssh m1max "tail -25 ~/git/ideogram4-local/output/worker.log"` shows the live sampling progress (`2/20 - 101.48s/it`), which tells a slow job from a hung one. A job on someone else's card is not yours to kill — report it, do not repair it.
- **A probe is a queued job, not an out-of-band ping.** A fifteen-word probe on a flaky engine joins the same FIFO as everything else, so behind two ideogram jobs it answers 45 minutes late and the hop that waits on it alone buys nothing. What to do with that wait is the probe policy in `references/nanobanana-engine.md`.

The wrapper prints only the job ID to stdout. A 1216×832 render takes about 21 minutes on the M1 Max; do not poll in the same run. Schedule a Paperclip issue monitor (`references/archive/review-loop.md`) and end the run, or resume on a later wake.

**A job ID can start with a dash, and then neither `status` nor `fetch` can take it.** The
IDs are random tokens, so one in about sixty begins with `-`; argparse reads it as an option
and both subcommands answer `error: the following arguments are required: job_id` — including
with a `--` separator, because the wrapper consumes that itself before the remote CLI sees
it. The job is fine, only the client cannot address it. Reach it over SSH instead:

```bash
ssh m1max "cd ~/git/ideogram4-local && python3 ideogram4_local.py status -- '-_ySI23odgo'"
scp m1max:/Users/wojciechgula/git/ideogram4-local/output/studio/<job date>/<slug>-<8 hex>.png \
    ~/image-studio/staging/<fetch date>/
```

The remote CLI does honour `--`, and its `status` JSON carries `output_path`, so the filename
to scp is known before the render finishes. Put that path in the handoff brief, because the
run that fetches it will hit the same wall.

## FLUX.2-klein fast drafts

`imagegen submit --engine flux2-klein` queues a fast draft: about 3 minutes per 1216×832
render. The prompt is natural language. `--prompt "…"` uploads a temporary `.txt` to
`<IMAGEGEN_REMOTE_DIR>/studio-incoming/` (and removes it locally afterwards);
`--prompt-file path` uploads that file. `--prompt-json` is rejected for FLUX, and
`--seed N` is optional — the remote CLI picks a random 32-bit seed when it is omitted.

```bash
JOB_ID=$(imagegen submit --engine flux2-klein \
  --prompt "a fox in a server room, warm monitor light" --json | jq -r '.job_id')
imagegen status "$JOB_ID"   # eta_minutes counts 3 per FLUX job, 21 per Ideogram job
```

`IMAGEGEN_FLUX_MIN_PER_JOB` (default `3`) is the per-FLUX-job ETA, alongside
`IMAGEGEN_MIN_PER_JOB` (default `21`) for Ideogram 4; a row with no `engine` counts as an
Ideogram job. The Ideogram argv is unchanged, so this wrapper still drives a Max whose
checkout predates phase 6; the FLUX path needs the phase-6 CLI and the
`~/.venvs/sou-flux` venv on the Max. The library record and the review loop are the same
for both engines (`references/library-records.md`).

## Pause the dead Mattermost watchdog (legacy)

After moving Hermes to the Air, the old `ideogram4-progress-watchdog` cron becomes a silent no-op because `jobs.db` lives on the Max. Pause it, do not delete it:

```bash
hermes -p andrzej cron pause 4641a45c3dbe
hermes -p andrzej cron list   # verify ideogram4-progress-watchdog shows [paused]
```

The Mattermost delivery path is retired; Matejko reviews in Paperclip.

## Acceptance criteria for Air wrapper rollout

- `which imagegen` resolves to the symlink into `~/.local/share/ideogram4-local`.
- The Max checkout is on the merged `main` commit.
- Smoke job ID, `status` output, and final `fetch` path are recorded in the issue comment.
- The fetched PNG is over 1 MB and attached to the issue.
- `hermes cron list` shows `ideogram4-progress-watchdog` paused.
