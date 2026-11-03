#!/usr/bin/env python3
"""Scan the backlog-review cards for stalls.

The queue's own state does not show a stall.  A stall is a card issue whose
board state no longer matches what has actually happened to it: a verdict card
Wojtek answered that nobody applied, a card parked in a state whose monitor can
never fire, a card with a queued render and no run left to collect it.  Each of
those holds a signed approval, a finished render, or both, and nothing in the
queue says so.

Usage:
    python3 scan-cards.py --runner-id <uuid> [--company-id <uuid>]
                           [--api http://127.0.0.1:3100/api]

Reads PAPERCLIP_API_KEY from the profile .env and never prints it.  A route it
cannot read is reported as unread, so a missing endpoint never looks like a
clean scan.
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

ENV = os.path.expanduser("~/.hermes/profiles/matejko/.env")
QUEUE = os.path.expanduser("~/image-studio/backlog/queue.json")
COMPANY = "0e2eb054-4cb6-4ea1-a2e7-2b1894285d8c"
# A status that means a run is still working the issue.
LIVE_STATES = {"queued", "running", "pending", "in_progress", "reconnecting",
               "starting"}
# A status whose monitor can fire.
MONITORABLE = ("in_progress", "in_review")


def read_key():
    try:
        with open(ENV) as fh:
            for line in fh:
                if line.startswith("PAPERCLIP_API_KEY="):
                    return line.split("=", 1)[1].strip()
    except OSError:
        pass
    sys.exit("PAPERCLIP_API_KEY not found in " + ENV)


def fetch(args, path):
    """GET a path, return parsed JSON, or None when it cannot be read."""
    cmd = ["curl", "-s", "-H", "Authorization: Bearer " + args.key,
           args.api + path]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True,
                             timeout=30).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    try:
        return json.loads(out)
    except ValueError:
        return None


def live_run_count(args, issue_id):
    """(count, readable) of the runs still working the issue."""
    runs = fetch(args, "/issues/%s/runs" % issue_id)
    if not isinstance(runs, list):
        return None, False
    live = [r for r in runs
            if str(r.get("status") or "").lower() in LIVE_STATES]
    return len(live), True


def last_verdict_card(interactions):
    """The most recent request_item_verdicts interaction, or None."""
    cards = [i for i in interactions if i.get("kind") == "request_item_verdicts"]
    if not cards:
        return None
    return sorted(cards, key=lambda i: i.get("createdAt") or "")[-1]


def batch_entries_without_issue():
    """Batch rounds claimed in queue.json that never got a card issue.

    batch-open claims the round first and the card issue is created afterwards.
    When that create fails, the round keeps its brief and its renders and holds
    no issue at all — so there is no card for the loop above to scan, and the
    finished renders wait with nothing in front of them.
    """
    try:
        with open(QUEUE) as fh:
            queue = json.load(fh)
    except (OSError, ValueError):
        return None
    return [e for e in (queue.get("batch") or []) if not e.get("issue")]


def minutes_since(stamp):
    if not stamp:
        return None
    try:
        when = datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
    except ValueError:
        return None
    return (datetime.now(timezone.utc) - when).total_seconds() / 60.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runner-id", required=True)
    ap.add_argument("--company-id", default=COMPANY)
    ap.add_argument("--api", default="http://127.0.0.1:3100/api")
    ap.add_argument("--older-than", type=float, default=30.0,
                    help="minutes before a card with no run counts as unpicked")
    args = ap.parse_args()
    args.key = read_key()

    cards = fetch(args, "/companies/%s/issues?parentId=%s"
                  % (args.company_id, args.runner_id))
    if cards is None:
        sys.exit("could not list the runner's cards")
    if isinstance(cards, dict):
        cards = cards.get("issues", [])

    flagged = 0
    seen = 0
    for card in sorted(cards, key=lambda c: c.get("identifier") or ""):
        if "Backlog review" not in (card.get("title") or ""):
            continue
        seen += 1
        issue_id = card["id"]
        issue = fetch(args, "/issues/%s" % issue_id) or {}
        interactions = fetch(args, "/issues/%s/interactions" % issue_id)
        if isinstance(interactions, dict):
            interactions = interactions.get("interactions", [])
        if not isinstance(interactions, list):
            interactions = []
        runs, runs_readable = live_run_count(args, issue_id)

        card_state = last_verdict_card(interactions)
        vstat = card_state.get("status") if card_state else "-"
        status = issue.get("status")
        flags = []

        # A card in the re-render state has its verdicts applied and a render
        # in flight, so the "answered but not applied" flag is a false positive
        # there.  The monitor is what proves the shape: a card that is
        # in_progress with a scheduled monitor is waiting for that render, and
        # the verdict rows were already written before the render went out.
        monitor_at = issue.get("monitorNextCheckAt")
        rerender_in_flight = (status == "in_progress" and bool(monitor_at))

        if status == "cancelled":
            # A cancelled card is retired, not stalled: its work moved to
            # another card on the same post.  Nothing can wake it, and the
            # post's other rows are what the queue tracks.
            print("%-9s %-12s verdicts=%-9s runs=%-3s retired (cancelled; check the post's other cards)"
                  % (card.get("identifier"), status, vstat, str(runs)))
            continue

        # A live run on an answered card is the run APPLYING those verdicts:
        # flagging it would report work in progress as work stranded.
        if (vstat == "answered" and status != "done" and not rerender_in_flight
                and not (runs_readable and runs)):
            flags.append("verdicts answered but not applied")
        if vstat == "pending" and status != "in_review":
            flags.append("pending card on a %s issue" % status)
        # A `todo` card whose run is already live is not a stall: that run is
        # the thing that opens the card, and a batch of fresh cards is normal
        # (Wojtek asked for 25 at once on GUL-230).  Only a todo card with no
        # live run at all is asleep.
        if status not in MONITORABLE and status != "done" and not (runs_readable and runs):
            flags.append("%s cannot fire a monitor" % status)
        # A card waiting on Wojtek is not waiting on a run: `in_review` with a
        # pending verdict card is the designed resting state of a review card.
        if (status in MONITORABLE and runs_readable and not runs
                and not rerender_in_flight and vstat != "pending"):
            flags.append("no live run on an open card")
        if vstat == "-" and status in ("todo", "backlog"):
            age = minutes_since(card.get("createdAt"))
            if runs_readable and not runs and age is not None and age > args.older_than:
                flags.append("card never picked up (%.0f min old)" % age)

        if flags:
            flagged += 1
        elif rerender_in_flight:
            flags.append("re-render in flight, monitor at %s" % monitor_at)
        run_field = str(runs) if runs_readable else "?"
        print("%-9s %-12s verdicts=%-9s runs=%-3s %s"
              % (card.get("identifier"), status, vstat, run_field,
                 "; ".join(flags) if flags else "ok"))

    print("\n%d flagged out of %d review cards" % (flagged, seen))
    if flagged:
        print("A flagged card is a candidate, not a verdict: read its thread "
              "and its interaction result before touching it.")

    orphans = batch_entries_without_issue()
    if orphans is None:
        print("\nqueue.json unreadable: batch entries with no card issue were "
              "NOT checked.")
    elif orphans:
        print("\n%d batch round(s) claimed with no card issue:" % len(orphans))
        for entry in orphans:
            print("  post %s round %s since %s | brief %s"
                  % (entry.get("n"), entry.get("round"), entry.get("since"),
                     entry.get("brief")))
        print("Create each card from its brief, then record it with "
              "backlog.py batch-opened <n> <GUL-id>.")
    else:
        print("\nbatch entries: every claimed round names its card issue")


if __name__ == "__main__":
    main()
