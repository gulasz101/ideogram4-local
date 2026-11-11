# Vault asset paths at an approval close

Where an approved image lands in `tech_blog/assets/`, and what it is called. The record format, the `superseded_by` chain and the post-embed rules live in `library-records.md`; this file is only the path decision, which the other file states in one sentence and two documents disagree about.

## The two dates are not the same

| thing | date it carries | why |
| --- | --- | --- |
| asset folder `assets/<YYYY-MM-DD>/` | the day the close runs | the file enters the vault today |
| record filename `image-library/<YYYY-MM>/<YYYY-MM-DD>-...` | the job's `created_at` | the library indexes by render date |

So one close legitimately writes into two different dates, and a verdict that lands the next morning does not re-date the record. Take the record date from `imagegen status <job>`'s `created_at`, never from the approval day and never from the brief.

**A brief that names the post's own date folder is copying the slot's earlier record path, and the close-day rule still wins.** A July draft's re-review brief asked for `assets/2026-07-11/<item>.png` in both its bookkeeping block and its embed line, because the rejected image it replaces lives there; the day folder it belonged in was the one the close ran on, beside every other asset of the current batch. Follow the file's rule, then say the departure in the closing comment and in the queue note, because the brief and the vault now disagree and the next reader sees the brief first.

## The filename is the item id, as it stands

`assets/<day>/<item id>.png`.

**When the brief's item id already ends in its round suffix (`foo-r2`), do not apply a `<item id>-r<k>` formula on top of it.** The doubled name (`foo-r2-r2.png`) passes `verify-slot.py`, because the checker compares the asset's bytes, its presence and the embed — never the name against the item id — so the mistake is silent: the render ships under a name no brief, prompt file or record will ever name again, and the next reader finds a brief and a vault that disagree. One suffix, exactly as the item id reads.

## Free the path before you copy, and make the copy the check

- `ls` the day folder and `grep` the drafts for the path first; the folder is shared with every run closing a post, so a listing is a snapshot.
- Put the guard inside the copy: if the target exists with different bytes, refuse and pick a post-specific name (`dns-header-r2.png`, `post033-header-r2.png`); if it exists with the same bytes, the copy already happened and the pass converges.
- Hash the copy against the staging file and print both hashes. A retry under the same name defeats an exists-guard, so a refusal means a new name, not a second attempt.
- A backlog re-review that replaces a draft's own picture in place is the one case that copies over an existing file: preserve the old bytes as `<slug>.superseded-<old job id>.png` first, then overwrite.

## The embed edit is one line

Post-relative path plus a one-sentence alt text, and the alt text describes the shipped picture — verified on the render, not inherited from the brief or the card. Nothing else in the draft changes.
