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
- `created_at` and `finished_at` come from `imagegen status`.
- `superseded_by` is `null` unless a later job replaced this image.
- `post_status` is the post's frontmatter `status` (for example `draft` or `published`), or `null`.
- `asset_location` values match the back-fill: `vault` or `max-only`.

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

## Rejected renders

Write the record for a rejected render too, with `asset: null`, `asset_location: "max-only"`, `asset_present: false`, and the rejection reason in the table. The render may be deleted from staging; the record is what preserves why that prompt did not work.

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
