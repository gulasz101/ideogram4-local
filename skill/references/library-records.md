# Library records

One record per rendered image, in the Obsidian vault. The format is the one `studio/library_backfill.py` `render_record()` writes, so back-filled and studio records sit in the same library and the same index.

## Where records live

```
~/wojtek.second.brain.obsidian.vault/3-resources/image-library/<YYYY-MM>/<YYYY-MM-DD>-<stem>--<job_id>.md
```

- `<YYYY-MM>` and `<YYYY-MM-DD>` come from the job's `created_at`.
- `<stem>` is the **fetched PNG stem**, i.e. the `label` slug plus the wrapper's 8-hex token: `<slug>-<token>`. `imagegen fetch` prints that path, so use its basename. `library_backfill.py`'s `record_relative_path()` builds the same filename and skips a job only if that exact path exists; using the label alone would make the next backfill write a duplicate `verdict: unreviewed` record.
- `<job_id>` is the job id `imagegen submit` printed.

Approved images live in the vault at `tech_blog/assets/<YYYY-MM-DD>/<slug>.png`, with the readable label slug (no token).

## Format

Use exactly the frontmatter keys and the three sections of `render_record()`: `## Why`, `## Prompt`, `## Verdicts`. The `# heading` is the record's `<stem>`, matching the filename. Studio records differ from back-filled ones only in these values:

| field | studio value |
| --- | --- |
| `source` | `"studio"` |
| `verdict` | the latest verdict (`approved` / `rejected` / `deferred`) |
| `asset` | the vault-relative PNG path once approved; `null` when rejected |
| `asset_location` | `"vault"` when approved; `"max-only"` when rejected |
| `asset_present` | `true` when approved; `false` when rejected |
| `posts` | the post(s) the request came from, vault-relative |

The remaining keys keep the back-fill meanings:

- `type: "image-record"`, `engine: "ideogram4"`, `prompt_type: "json"`.
- `width`, `height` as integers.
- `generation` is the prompt's wrapper-only `generation` block, or `null`.
- `created_at` and `finished_at` come from `imagegen status` — and from **that job's own** status line, read fresh. They are the renderer's timestamps, not yours to compose: a record whose `created_at` and `finished_at` are copied from a neighbouring job, taken from a prompt file's mtime, or inferred from a clock is wrong in a way nothing else in the record contradicts, so it survives review. When a record's dates and the renderer's `status` line disagree, the renderer wins and the record is patched. Compare the two before writing the record and again before closing the card.
- **`superseded_by` is `null` unless a later job replaced this image; a rejected render whose slot was later approved points at the approved job id (see **Multi-round slots**).**
- The **approved** record's `superseded_by` stays `null` — nothing replaced it — while **every** earlier record of the slot points at that one approved job id, the back-filled one included. Write the chain in one pass over all of the slot's records, not one record at a time, or the history ends in a dead end.
- `post_status` is the post's frontmatter `status` (for example `draft` or `published`), or `null`.
- `asset_location` values match the back-fill: `vault` or `max-only`.

## The vault is not a git repository

`~/wojtek.second.brain.obsidian.vault` is a symlink to `~/vault`, and neither path holds a `.git` directory. Record edits are therefore **not** committed — do not look for a repo, and do not try to commit. Report the changed record paths in the issue comment instead; that comment is the audit trail.

## The Verdicts table

Always keep the header exactly:

```markdown
| round | date | verdict | reason | issue |
| --- | --- | --- | --- | --- |
```

Append one row per round that resolves for this record:

```markdown
| 1 | 2026-10-21 | approved | Warm light and the forklift read as the migration story. | [GUL-42](/GUL/issues/GUL-42) |
```

Never rewrite an earlier row. The table is the verdict history; a later rejection does not erase an earlier approval.

## Approving or rejecting a back-filled record

A back-filled record (`source: "backfill"`, `verdict: "unreviewed"`) is an image that has been in the vault since before anyone reviewed it, so its verdict round changes the record and nothing else. Three edits, no more:

- `verdict:` becomes `"approved"` (or `"rejected"`; a defer is a rejection too, see below).
- Append one Verdicts row. Without a reason on the card use `Approved on review.` for an approval and `keep-as-is: <reason>` for a defer that keeps the image; never invent a reason he did not give.
- Delete the line `Back-filled from jobs.db; not reviewed yet.`

**The row replaces the blank line the back-fill left under the header.** A back-filled table ends with the header, a separator, an empty line, then the marker; put the new row where that empty line was, so the marker is gone and the table has exactly one data row. Appending below the marker leaves the record still reading as unreviewed. After editing, grep the record for `Back-filled` (expect no match) and print the whole Verdicts table, not just the frontmatter, to confirm the shape.

**Use `scripts/approve_record.py` for every verdict, approval and rejection alike.** `approve_record.py <record.md> --approved --issue GUL-x` and `approve_record.py <record.md> --rejected --issue GUL-x --reason "..."` do the three edits in one pass and verify the result, so a half-applied edit (row added, marker left behind) cannot pass unnoticed. The script also sanitizes the reason for a table cell — a pipe inside a cell splits the row into two columns and a newline ends it, and Wojtek's reasons are free text that can contain either, so hand-copying a reason can silently break the table. Hand-editing the same three spots across 153 posts is where a half-applied edit creeps in, so prefer the script. Verify anyway by grepping the record for the marker and reading the whole Verdicts table, not just the frontmatter.

Leave `source: "backfill"`, `asset`, `asset_location`, `asset_present` and `superseded_by: null` exactly as they are: the file is already where the post points, so nothing was copied and nothing replaced it. **Do not edit the post and do not write a second record for the same job id** — `library_backfill.py` skips a job only on the exact `<stem>--<job_id>` filename, and a duplicate record splits the slot's history.

**`superseded_by` is set at approval time, not at rejection time.** A rejected back-filled record keeps `superseded_by: null` while the re-render is still in flight, because the field names the job that *replaced* this image and no replacement has been accepted yet. When the re-render is approved, set `superseded_by` to the approved job id in every earlier record of the slot, the back-filled one included. Pointing it at a render that was never approved makes the slot's history read as if the work were finished.

**A rejection does not set `superseded_by` — and neither does a render that is still in flight.** The temptation is to point a rejected record at the render that is now queued to replace it, so the history looks tidier. Do not: the field names an image that was *accepted*, and a render sitting in the queue has not been accepted by anyone. Leave it `null` until Wojtek approves, then set it in the same pass that writes the approved record.

## Rejected renders

Write the record for a rejected render too, with `asset: null`, `asset_location: "max-only"`, `asset_present: false`, and the rejection reason in the table. The render may be deleted from staging; the record is what preserves why that prompt did not work.

## Multi-round slots

A slot normally takes more than one round, and every render that reached a card gets its own record — rejected ones included. Write the records so the slot's history reads correctly from either of them:

- **The approved record carries the history of the slot.** Its Verdicts table has one row per round: the round-1 `rejected` row, with the reason prefixed by the rejected render's stem so the row names the image it is about, then the round-2 `approved` row.
- **Every earlier record of the slot points at the same approved job id.** When a slot takes three rounds, that is three earlier records — the back-filled one, the rejected render, and the silent attempt that never reached a card — and all of them get `superseded_by` set to the one job Wojtek approved. The chain is a pointer to the accepted image, not a link to the next render in line: a rejected render's `superseded_by` names the render that **replaced** it, and when that replacement is itself later replaced, the pointer moves again. So a render that was superseded by a *rejected* render still ends up pointing at the approved job, not at the render that briefly followed it. Write it in one pass over every record of the slot, or the slot's history points at a dead end.
- **The rejected record keeps its own single `rejected` row**, with `asset: null`, `asset_location: "max-only"`, `asset_present: false`, and `superseded_by` set to the job id of the render that replaced it.
- **The approved record keeps `superseded_by: null`** — nothing replaced it.

```markdown
| round | date | verdict | reason | issue |
| --- | --- | --- | --- | --- |
| 1 | 2026-10-21 | rejected | zeroclaw-claim-a-1a2b3c4d: the star placard reads as a prize, not as a claim about the model. | [GUL-34](/GUL/issues/GUL-34) |
| 2 | 2026-10-21 | approved | The cable from the robot to the dusty machine names the downgrade at a glance. | [GUL-34](/GUL/issues/GUL-34) |
```

## Complete example

This is `3-resources/image-library/2026-10/2026-10-21-gitops-forklift-a-7f3a9c21--K3n8Qw7tY2c.md`:

```markdown
---
type: "image-record"
job_id: "K3n8Qw7tY2c"
engine: "ideogram4"
prompt_type: "json"
width: 1216
height: 832
generation: {"safety_bypass": true, "safety_bypass_mode": "single_pass"}
created_at: "2026-10-21T09:14:07"
finished_at: "2026-10-21T09:35:41"
asset: "tech_blog/assets/2026-10-21/gitops-forklift-a.png"
asset_location: "vault"
asset_present: true
superseded_by: null
posts: ["tech_blog/2026-10-15-my-homelab-agent-lied-about-its-own-model.md"]
post_status: "draft"
verdict: "approved"
source: "studio"
---

# gitops-forklift-a-7f3a9c21

![[tech_blog/assets/2026-10-21/gitops-forklift-a.png]]

## Why

The post argues that GitOps is the only durable way to run the homelab, so the header shows a forklift moving a server rack into a clean, ordered hall: the migration metaphor the opening paragraph uses. Wojtek's taste rules that applied: warm industrial light, one clear subject, no readable technical text in the image.

From [[2026-10-15-my-homelab-agent-lied-about-its-own-model]], section "Why GitOps is law":

> The cluster is not a pet. It is a loading dock: everything arrives through a manifest, and anything that did not arrive through a manifest is suspect.

## Prompt

```json
{
  "high_level_description": "A forklift lifts a server rack into a clean, ordered data hall, warm industrial light, one clear subject.",
  "style_description": {
    "aesthetics": "clean editorial tech photography",
    "lighting": "warm industrial side light with soft shadows",
    "medium": "photograph",
    "photo": "35mm, shallow depth of field, realistic",
    "color_palette": ["#D97A32", "#2B3A42", "#E8E2D6"]
  },
  "compositional_deconstruction": {
    "background": "A data hall that fills the entire frame edge to edge with no empty space, rows of racks receding to the top and bottom edges.",
    "elements": [
      {"type": "obj", "bbox": [0, 80, 1000, 620], "desc": "a yellow forklift lifting a black server rack, occupying the full height of the frame"},
      {"type": "obj", "bbox": [0, 0, 1000, 400], "desc": "rows of dark server racks with small amber status lights, reaching the top edge"},
      {"type": "obj", "bbox": [0, 620, 1000, 1000], "desc": "a polished concrete floor with painted safety lines, reaching the bottom edge"}
    ]
  },
  "generation": {"safety_bypass": true, "safety_bypass_mode": "single_pass"}
}
```

## Verdicts

| round | date | verdict | reason | issue |
| --- | --- | --- | --- | --- |
| 1 | 2026-10-21 | approved | Warm light and the forklift read as the migration story. | [GUL-42](/GUL/issues/GUL-42) |
```

## FLUX.2-klein record

A `flux2-klein` job is a natural-language draft. Its record has the same shape, with three differences: `engine` names the engine, `prompt_type` is `"text"`, and — because a text prompt carries no wrapper `generation` block — `generation` records what actually rendered: the model, the four distilled steps, and the job's seed.

```markdown
---
type: "image-record"
job_id: "K3n8Qw7tY2d"
engine: "flux2-klein"
prompt_type: "text"
width: 1216
height: 832
generation: {"model": "black-forest-labs/FLUX.2-klein-4B", "steps": 4, "seed": 1938475623}
created_at: "2026-10-21T10:02:11"
finished_at: "2026-10-21T10:04:03"
asset: "tech_blog/assets/2026-10-21/flux-fox.png"
asset_location: "vault"
asset_present: true
superseded_by: null
posts: ["tech_blog/2026-10-15-my-homelab-agent-lied-about-its-own-model.md"]
post_status: "draft"
verdict: "approved"
source: "studio"
---

# flux-fox-2b4c6d8e

![[tech_blog/assets/2026-10-21/flux-fox.png]]

## Why

…written exactly as for an Ideogram record…

## Prompt

```
a fox in a server room, warm monitor light
```
```

The `## Why` section and the Verdicts table are written exactly as for an Ideogram record.
