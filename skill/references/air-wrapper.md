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
imagegen fetch "$JOB_ID"
ls -l ~/image-studio/staging/*.png
```

The wrapper prints only the job ID to stdout. A 1216×832 render takes about 21 minutes on the M1 Max; do not poll in the same run. Schedule a Paperclip issue monitor (`references/review-loop.md`) and end the run, or resume on a later wake.

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
