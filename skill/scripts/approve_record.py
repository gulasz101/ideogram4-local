#!/usr/bin/env python3
"""Apply a verdict to a back-filled library record, in place.

A back-filled record carries the marker line "Back-filled from jobs.db; not
reviewed yet." and an empty Verdicts table:

    | round | date | verdict | reason | issue |
    | --- | --- | --- | --- | --- |
    <blank>
    Back-filled from jobs.db; not reviewed yet.

A verdict round changes exactly three things: the `verdict:` frontmatter
value, one row under the Verdicts header, and the removal of the marker.
Nothing else in the record moves.

This script makes those three edits in one pass and verifies the result, so a
half-applied edit (row added, marker left behind) cannot pass unnoticed.

Usage:
    approve_record.py <record.md> --approved --issue GUL-71
    approve_record.py <record.md> --approved --issue GUL-71 --reason "..."
    approve_record.py <record.md> --rejected --issue GUL-71 --reason "..."

Exit codes:
    0 = applied and verified
    1 = bad arguments, or the record did not have the expected shape
    2 = file not found
"""
import argparse
import re
import sys
from datetime import date
from pathlib import Path

MARKER = "Back-filled from jobs.db; not reviewed yet."
HEADER = "| round | date | verdict | reason | issue |"
SEPARATOR = "| --- | --- | --- | --- | --- |"


def issue_link(issue: str) -> str:
    prefix = issue.split("-")[0]
    return f"[{issue}](/{prefix}/issues/{issue})"


def cell(text: str) -> str:
    """Make text safe for one markdown table cell.

    A pipe inside a cell splits the row into two columns, and a newline
    inside a cell ends the row, so both have to go. Wojtek's reasons are free
    text and can contain either.
    """
    return text.replace("|", "/").replace("\n", " ").replace("\r", " ").strip()


def apply_verdict(path: Path, verdict: str, issue: str, reason: str, round_no: int) -> None:
    text = path.read_text()

    if MARKER not in text:
        sys.exit(f"error: {path} has no marker line; is it a back-filled record?")

    # 1. frontmatter verdict
    text, n = re.subn(
        r'^verdict: ".*"$', f'verdict: "{verdict}"', text, count=1, flags=re.M
    )
    if n != 1:
        sys.exit(f"error: {path} has no single `verdict:` frontmatter key")

    # 2. the row, placed directly under the table separator; the blank line
    #    and the marker that followed it are consumed.
    row = (
        f"| {round_no} | {date.today().isoformat()} | {verdict} "
        f"| {cell(reason)} | {issue_link(issue)} |"
    )
    lines = text.split("\n")
    out: list[str] = []
    row_written = False
    marker_removed = False
    for line in lines:
        if not row_written and line.strip() == SEPARATOR:
            out.append(line)
            out.append(row)
            row_written = True
            # consume the blank line and the marker that follow the separator
            continue
        if row_written and not marker_removed:
            if line.strip() == "" or line.strip() == MARKER:
                if line.strip() == MARKER:
                    marker_removed = True
                continue
            # first real content after the table: keep it
            marker_removed = True
            out.append(line)
            continue
        out.append(line)

    if not row_written:
        sys.exit(f"error: {path} has no Verdicts table separator")
    if not marker_removed:
        sys.exit(f"error: {path} marker line not found")

    text = "\n".join(out).rstrip("\n") + "\n"
    path.write_text(text)

    # 3. verify
    final = path.read_text()
    if MARKER in final:
        sys.exit("error: marker still present after edit")
    if f'verdict: "{verdict}"' not in final:
        sys.exit("error: frontmatter verdict did not take")
    if row not in final:
        sys.exit("error: verdict row missing after edit")
    if HEADER not in final:
        sys.exit("error: Verdicts header damaged")
    if "|" not in final.split(SEPARATOR)[-1].split("\n")[1]:
        sys.exit("error: no data row under the Verdicts header")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--approved", action="store_true")
    ap.add_argument("--rejected", action="store_true")
    ap.add_argument("--issue", required=True, help="e.g. GUL-71")
    ap.add_argument("--reason", default=None)
    ap.add_argument("--round", type=int, default=1)
    args = ap.parse_args()

    if args.approved == args.rejected:
        sys.exit("error: pass exactly one of --approved or --rejected")

    if args.approved:
        verdict = "approved"
        reason = args.reason or "Approved on review."
    else:
        if not args.reason:
            sys.exit("error: a rejection needs --reason")
        verdict = "rejected"
        reason = args.reason

    path = Path(args.record).expanduser()
    if not path.is_file():
        sys.exit(f"error: {path} not found")

    apply_verdict(path, verdict, args.issue, reason, args.round)
    print(f"ok: {path.name} -> {verdict} (round {args.round}, issue {args.issue})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
