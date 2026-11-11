#!/usr/bin/env python3
"""Queue for the Image Studio backlog review (GUL-27).

One card at a time: the "slot" is held by the one card that is open (or about
to open). `next` hands out the next card, re-render rounds before new posts.
All state lives in queue.json next to this script; every command takes a lock.

  backlog.py status                      table of every post that is not todo, plus the slot
  backlog.py next                        JSON: {"action": "create"|"wait"|"finished", ...}
  backlog.py opened <n> <GUL-id>         record the issue created for the slot's card
  backlog.py batch-opened <n> <GUL-id>    record the issue created for a batch card
  backlog.py fix-issue <n> <old> <new>   correct a mis-recorded issue id for a post
                                         (repair only: a wrong id was recorded)
  backlog.py reopen-card <n> <GUL-id> <round>
                                         re-register a batch card released by mistake
  backlog.py card-done <n> [--rendering] the card for post n is complete; frees the slot
  backlog.py ready <n> <round> <brief>   re-renders for post n are checked; queue round <round>
  backlog.py batch-open <count>          open up to <count> extra cards at once (Wojtek asked
                                         for more cards in flight); returns one entry per card
  backlog.py batch-open-ready <count>    open up to <count> queued re-render rounds as batch
                                         cards, without touching the live slot
  backlog.py note <n> <text>             append a note to post n
  backlog.py release                     free a stuck slot (repair only)
"""
import datetime
import fcntl
import json
import os
import sys

HERE = os.environ.get("BACKLOG_DIR", os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(HERE, "queue.json")
LOCK = os.path.join(HERE, ".lock")


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load():
    with open(STATE) as f:
        return json.load(f)


def save(q):
    tmp = STATE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(q, f, indent=1)
    os.replace(tmp, STATE)


def post(q, n):
    for p in q["posts"]:
        if p["n"] == n:
            return p
    sys.exit(f"no post {n}")


def title(q, p, rnd):
    t = f"Backlog review {p['n']:03d}/{q['total']}"
    if rnd > 1:
        t += f", round {rnd}"
    return f"{t}: {p['title']}"


def cmd_next(q):
    s = q.get("slot")
    if s:
        return {"action": "wait", "reason": f"slot held by post {s['n']} round {s['round']}",
                "issue": s.get("issue"), "since": s["since"]}
    if q["ready"]:
        h = q["ready"].pop(0)
        p = post(q, h["n"])
        p["state"] = "card"
        q["slot"] = {"n": h["n"], "round": h["round"], "brief": h["brief"], "issue": None, "since": now()}
        return {"action": "create", "n": h["n"], "round": h["round"], "brief": h["brief"],
                "title": title(q, p, h["round"])}
    for p in q["posts"]:
        if p["state"] == "todo":
            p["state"] = "card"
            q["slot"] = {"n": p["n"], "round": 1, "brief": os.path.join(HERE, "briefs", p["brief"]),
                         "issue": None, "since": now()}
            return {"action": "create", "n": p["n"], "round": 1,
                    "brief": os.path.join(HERE, "briefs", p["brief"]), "title": title(q, p, 1)}
    if any(p["state"] in ("card", "rendering", "ready") for p in q["posts"]):
        return {"action": "wait", "reason": "re-renders still running"}
    return {"action": "finished"}


def cmd_batch_open(q, count):
    """Open up to `count` extra cards at once.

    The single-slot rule keeps one card in flight so the board stays readable.
    Wojtek asked for more cards in flight so there is work to do overnight, so
    this claims the next `count` todo posts as cards without touching the slot.
    A batch card is tracked in `q["batch"]` and released by `card-done`.
    """
    if count < 1:
        sys.exit("batch-open needs a count of at least 1")
    batch = q.setdefault("batch", [])
    taken = {b["n"] for b in batch}
    s = q.get("slot")
    if s:
        taken.add(s["n"])
    opened = []
    for p in q["posts"]:
        if len(opened) >= count:
            break
        if p["state"] != "todo" or p["n"] in taken:
            continue
        brief = os.path.join(HERE, "briefs", p["brief"])
        p["state"] = "card"
        entry = {"n": p["n"], "round": 1, "brief": brief, "issue": None, "since": now()}
        batch.append(entry)
        opened.append({"n": p["n"], "round": 1, "brief": brief, "title": title(q, p, 1)})
    return opened


def cmd_batch_open_ready(q, count):
    """Open up to `count` queued re-render rounds as batch cards.

    A re-render round waits in `q["ready"]` for the live slot. When Wojtek wants
    more than one card in flight, those rounds can go out as batch cards too,
    so a finished render does not sit idle while the slot is busy. The live
    slot is left alone; `card-done` releases a batch card the same way.
    """
    if count < 1:
        sys.exit("batch-open-ready needs a count of at least 1")
    batch = q.setdefault("batch", [])
    taken = {b["n"] for b in batch}
    s = q.get("slot")
    if s:
        taken.add(s["n"])
    opened = []
    for h in list(q["ready"]):
        if len(opened) >= count:
            break
        if h["n"] in taken:
            continue
        p = post(q, h["n"])
        p["state"] = "card"
        entry = {"n": h["n"], "round": h["round"], "brief": h["brief"], "issue": None, "since": now()}
        batch.append(entry)
        q["ready"].remove(h)
        opened.append({"n": h["n"], "round": h["round"], "brief": h["brief"], "title": title(q, p, h["round"])})
    return opened


def main(argv):
    if not argv:
        sys.exit(__doc__)
    cmd, args = argv[0], argv[1:]
    with open(LOCK, "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        q = load()
        out = None
        if cmd == "status":
            counts = {}
            for p in q["posts"]:
                counts[p["state"]] = counts.get(p["state"], 0) + 1
            print(json.dumps({"total": q["total"], "states": counts, "slot": q.get("slot"),
                              "ready": q["ready"]}, indent=1))
            for p in q["posts"]:
                if p["state"] != "todo":
                    print(f"{p['n']:03d} {p['state']:<9} {' '.join(p['issues']):<24} {p['post']}"
                          + (f"  [{'; '.join(p['notes'])}]" if p["notes"] else ""))
            return
        if cmd == "next":
            out = cmd_next(q)
        elif cmd == "batch-open":
            out = {"ok": True, "opened": cmd_batch_open(q, int(args[0]))}
        elif cmd == "batch-open-ready":
            out = {"ok": True, "opened": cmd_batch_open_ready(q, int(args[0]))}
        elif cmd == "batch-opened":
            n, ident = int(args[0]), args[1]
            batch = q.setdefault("batch", [])
            entry = next((b for b in batch if b["n"] == n), None)
            if not entry:
                sys.exit(f"post {n} is not a batch card: {batch}")
            entry["issue"] = ident
            post(q, n)["issues"].append(ident)
            out = {"ok": True, "entry": entry}
        elif cmd == "fix-issue":
            # repair: an issue id was recorded wrongly (it named an unrelated
            # issue, or an issue that does not exist). Replace it everywhere the
            # post's ids live, so the queue does not point at the wrong card.
            n, old, new = int(args[0]), args[1], args[2]
            p = post(q, n)
            if old not in p["issues"]:
                sys.exit(f"post {n} does not record {old}: {p['issues']}")
            p["issues"] = [new if i == old else i for i in p["issues"]]
            for b in q.setdefault("batch", []):
                if b["n"] == n and b.get("issue") == old:
                    b["issue"] = new
            s = q.get("slot")
            if s and s.get("n") == n and s.get("issue") == old:
                s["issue"] = new
            out = {"ok": True, "post": n, "issues": p["issues"]}
        elif cmd == "reopen-card":
            # repair: a batch card was released with card-done while its card
            # issue was still open and waiting for verdicts. Put the post back
            # to `card` and re-register the batch entry so the open card is
            # still tracked and the post is not counted as done.
            n, ident, rnd = int(args[0]), args[1], int(args[2])
            p = post(q, n)
            batch = q.setdefault("batch", [])
            entry = next((b for b in batch if b["n"] == n), None)
            if entry is None:
                brief = None
                for h in q.get("ready", []):
                    if h["n"] == n:
                        brief = h["brief"]
                        # drop the ready entry: the card is now a batch entry, and a
                        # ready round left behind is popped by `next` into a second
                        # card for the same round the moment the live slot frees
                        q["ready"].remove(h)
                        break
                if brief is None:
                    sys.exit(f"post {n} has no batch entry and no ready round to rebuild from")
                entry = {"n": n, "round": rnd, "brief": brief, "issue": ident, "since": now()}
                batch.append(entry)
            else:
                entry["issue"] = ident
                entry["round"] = rnd
            p["state"] = "card"
            if ident not in p["issues"]:
                p["issues"].append(ident)
            out = {"ok": True, "post": n, "state": p["state"], "entry": entry}
        elif cmd == "opened":
            n, ident = int(args[0]), args[1]
            s = q.get("slot")
            if not s or s["n"] != n:
                sys.exit(f"the slot is not held by post {n}: {s}")
            s["issue"] = ident
            post(q, n)["issues"].append(ident)
            out = {"ok": True, "slot": s}
        elif cmd == "card-done":
            n = int(args[0])
            s = q.get("slot")
            batch = q.setdefault("batch", [])
            entry = next((b for b in batch if b["n"] == n), None)
            if entry:
                # a batch card: release it and drop it from the batch list
                batch.remove(entry)
                post(q, n)["state"] = "rendering" if "--rendering" in args else "done"
                out = {"ok": True, "state": post(q, n)["state"], "batch": len(batch)}
            elif s and s["n"] == n:
                post(q, n)["state"] = "rendering" if "--rendering" in args else "done"
                q["slot"] = None
                out = {"ok": True, "state": post(q, n)["state"]}
            elif post(q, n)["state"] == "rendering":
                # the card already released the slot while its re-renders ran, and
                # those renders are now approved: close the post out
                post(q, n)["state"] = "rendering" if "--rendering" in args else "done"
                out = {"ok": True, "state": post(q, n)["state"], "closed_without_slot": True}
            else:
                sys.exit(f"the slot is not held by post {n}: {s}")
        elif cmd == "ready":
            n, rnd, brief = int(args[0]), int(args[1]), os.path.abspath(args[2])
            if not os.path.exists(brief):
                sys.exit(f"no such brief: {brief}")
            post(q, n)["state"] = "ready"
            q["ready"].append({"n": n, "round": rnd, "brief": brief, "since": now()})
            out = {"ok": True, "queued": len(q["ready"])}
        elif cmd == "note":
            post(q, int(args[0]))["notes"].append(" ".join(args[1:]))
            out = {"ok": True}
        elif cmd == "release":
            s = q.get("slot")
            if s and not s.get("issue"):
                # the card's issue was never created: give the work back to the queue
                p = post(q, s["n"])
                if s["round"] == 1:
                    p["state"] = "todo"
                else:
                    p["state"] = "ready"
                    q["ready"].insert(0, {"n": s["n"], "round": s["round"], "brief": s["brief"], "since": s["since"]})
            q["slot"] = None
            out = {"ok": True, "released": s}
        else:
            sys.exit(f"unknown command {cmd}\n{__doc__}")
        save(q)
        print(json.dumps(out))


if __name__ == "__main__":
    main(sys.argv[1:])
