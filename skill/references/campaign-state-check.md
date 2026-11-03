# Measuring the image backlog, and reading the number honestly

When the campaign has been running for days, the figure everyone quotes is the
one from its first sweep: how many PNGs in the vault failed a check. That number
is wrong in both directions by the time anyone acts on it — it counts images in
posts that already shipped and were repointed, and it cannot see an image that
is *missing*. Measure the drafts instead, and then read the result against the
cards that are open before repeating it.

## The procedure

`scripts/recheck-live-posts.py` walks it in about a minute, no model in the loop:

1. read `backlog/queue.json` and take every post whose `state` is not `done`;
2. open that post's draft and collect every `![alt](path)` embed;
3. resolve each path against the vault, recording the ones that do not exist;
4. run `check-grey-bars.py` and `check-palette-strip.py` on each distinct file;
5. write `backlog/audit/recheck-of-live-posts.md` and a `.jsonl` beside it.

Run it, quote its counts, and give the output path so the next reader can
re-run rather than trust. It is cheap enough to run at the end of any run that
is waiting on someone else.

## A folder walk cannot find a dead link

The sweep that walks `tech_blog/assets/` only ever sees files that are present,
so an embed pointing at a file that was renamed, never copied, or deleted is
invisible to it — and that is a published broken image, more visible to a reader
than a palette strip. Only a draft walk catches it. When the recheck reports
unresolved embeds, that is a **prose** defect owned by the post's author: there
is nothing to re-render, because the file does not exist. Hand it to the author
with the exact paths and the two possible answers (the picture was meant to be
there and needs rendering; the embed is stale and the line comes out) rather
than adding it to the render queue.

## Split the failing images by who owns them before reporting

A flagged image on a post that holds an open card is usually one of the slots
that card replaces — so it is work in progress, not a broken image on a card.
Do not assume either way: read the card's own items
(`GET /api/issues/<card>/interactions`, `payload.items[].id`) and compare them
with the draft's embeds. If the card carries every embed the draft has, the
flagged files disappear on approval and the honest report says so in one line.
If the card carries only some, name the slots it leaves behind — that is a real
finding, and its owner needs it before the card goes up.

The remainder — flagged images on posts with no card — is the campaign's
remaining work in one number. Report it as a count of posts and a count of
images, not as one figure, because the two answer different questions.

## Pitfalls

- **The queue's draft path key is `post`.** A script written against
  `draft`/`path`/`file` resolves nothing and reports zero live posts, which reads
  like a finished campaign.
- **Never quote the campaign's opening number as current.** It was computed on
  the whole vault on one day; the recheck is the current one and they will not
  agree.
- **`check-flat-bands.py` stays out of this count.** It fires on cel-shaded art,
  approved frames included, so including it turns a progress number into noise.
- **A card's approval only repoints the slots the card carries.** A post with
  four embeds and a three-slot card still ships one unrepaired image; that is
  the case worth naming in the closing comment, because nothing in the card's
  own checks will show it.
