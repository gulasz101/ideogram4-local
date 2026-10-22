#!/usr/bin/env python3
"""Build a request_item_verdicts payload with the safe defaults baked in.

The card is frozen the moment it is posted, so the payload has to be right
before the POST: a missing resolverPolicy lets an agent resolve its own
image verdict, and one over-long description 400s the whole card.

Usage:
    build-verdict-card.py <spec.json> --out <payload.json>

The spec is a JSON object:
    issue_id         str   the issue uuid (goes into the idempotency key)
    round           int   1 for a post's first card
    title           str   card title
    summary         str   card summary
    prompt          str   the card's prompt line
    details_markdown str  legend + table, up to 20000 chars
    items           list  one per image, in brief order:
        id            str  the brief's item id
        label         str  the slug
        attachment_id str  the uploaded attachment id
        description   str  why + check note, 500 chars at most

Exits non-zero without writing anything when a description is too long or a
required field is missing, so a bad payload never reaches the board.
"""
import argparse
import json
import sys

MAX_DESCRIPTION = 500
MAX_DETAILS = 20000
VERDICTS = ["approve", "reject", "defer"]


def build(spec):
    for field in ("issue_id", "round", "title", "summary", "prompt",
                  "details_markdown", "items"):
        if field not in spec:
            raise SystemExit(f"spec is missing required field: {field}")

    details = spec["details_markdown"]
    if len(details) > MAX_DETAILS:
        raise SystemExit(
            f"details_markdown is {len(details)} chars, cap is {MAX_DETAILS}")

    items = []
    for index, item in enumerate(spec["items"]):
        for field in ("id", "label", "attachment_id", "description"):
            if field not in item:
                raise SystemExit(f"item {index} is missing field: {field}")
        description = item["description"]
        if len(description) > MAX_DESCRIPTION:
            raise SystemExit(
                f"item {item['id']} description is {len(description)} chars, "
                f"cap is {MAX_DESCRIPTION}")
        items.append({
            "id": item["id"],
            "label": item["label"],
            "description": description,
            "attachmentId": item["attachment_id"],
        })

    if not items:
        raise SystemExit("spec has no items; a card with no items is not a card")

    return {
        "kind": "request_item_verdicts",
        "resolverPolicy": "human_only",
        "title": spec["title"],
        "summary": spec["summary"],
        "continuationPolicy": "wake_assignee",
        "supersedeOnUserComment": True,
        "idempotencyKey": f"verdicts:{spec['issue_id']}:round-{spec['round']}",
        "payload": {
            "version": 1,
            "prompt": spec["prompt"],
            "detailsMarkdown": details,
            "items": items,
            "verdicts": VERDICTS,
            "requireReasonOn": ["reject"],
            "allowBulkApprove": True,
            "reasonLabel": "What should change?",
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("spec")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    with open(args.spec) as handle:
        spec = json.load(handle)

    payload = build(spec)
    with open(args.out, "w") as handle:
        json.dump(payload, handle, indent=2)

    for item in payload["payload"]["items"]:
        print(f"{item['label']} {len(item['description'])} chars "
              f"attach={item['attachmentId']}")
    print(f"idempotencyKey={payload['idempotencyKey']}")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
