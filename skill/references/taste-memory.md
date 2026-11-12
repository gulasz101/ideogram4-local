# Taste memory

Wojtek's taste is a *model*, not a log: the verdicts he gave, what they were about, and the prompt traits behind them. Hindsight stores it; the library records mirror it in the vault.

## The three calls

| call | use | returns |
| --- | --- | --- |
| `hindsight_reflect` | "What is Wojtek's image taste for \<topic\>?" | a synthesised model across verdicts |
| `hindsight_recall` | a specific question about a verdict or a topic | observations, verbatim |
| `hindsight_retain` | a verdict, a rejection reason, a card's shared trait | the receipt `Memory queued for storage` |

`hindsight_retain` returns a **receipt, not an id**. The memory is queued, not yet indexed, so a recall right after it may not find it — that is normal, and it is not a reason to retain it twice. A deliverable that must *cite* a memory id therefore cannot get one from the retain call; get it from the REST API (below).

## The rules that hold

- **A timeout is a failed call, not an empty model.** Never read "no history" into a timeout, and never build a prompt on that inference. If reflect and recall both fail, the taste model for that topic is unavailable — say so on the issue, work from the library records, and retry later. Do not let it block a card. **A `hindsight_reflect` timeout on its own is not that case:** recall answers most of the time and carries the raw material, so send the recall, build the check from the records plus what it returns, and say on the card only that reflect timed out — a comment claiming the taste model was unavailable when recall answered misreports what the check rested on.
- **A recall that returns nothing on the first keyword is not proof there is no history.** The bank indexes on different phrasings, so an empty first keyword can be a phrasing miss. Try a second distinctive keyword before concluding the records are the only source.
- **The records beat the memory.** `hindsight_reflect` synthesises across verdicts and will assert a history the records contradict — it has described a round-1 rejection on a slot whose round-1 items were both approved. Check every claim against the record's `## Verdicts` table and the card's `result`, and follow the records where the two disagree. **It also invents dated verdicts:** a reflect answer carried a `2026-10-27 21:07` row saying a round-2 render of a slot had been *rejected for a grid deviation*, when that render had no verdict at all and its card was still `pending`. A verdict row is real only when `GET /interactions` `result.items[]` carries that item id with a `verdict`; the date printed on the row is not evidence, and a reflect answer that argues for a hold-back, a rebuild or a re-render on the strength of one is arguing from its own synthesis rather than from his eye.
- **It also reads a brief's defect prose back as his verdicts.** An answer for a post whose draft images had been held back at the self-check summarised the brief's *why those images were replaced* list as "all three were rejected for pasted-overlay defects", with a library rejection count behind it to make it look like history — while that post's card carried zero interactions, so it had judged nothing, and its own closing comment said nothing from the draft ever reached a card. **A card whose `GET /issues/<card>/interactions` returns no rows is a card that decided nothing**, and that one read settles the question before the answer is allowed to shape the close: a draft image held back at your self-check keeps `verdict: "unreviewed"` and its `Back-filled from jobs.db; not reviewed yet.` marker with only `superseded_by` moved, while a picture he actually judged gets the frontmatter verdict and the Verdicts row. Let the answer decide it and you write a decision in his name into records that read back later as his taste. **Even a claim that loosely matches what you see is not a verdict:** a reflect answer said "rejected for grey bars" while the record said "unreviewed" and your own check found a dark container and a split seam — the memory synthesised from the check notes, not from his eye, and the record's `unreviewed` stands.
- **A reflect answer can prescribe a prop the bar forbids.** A synthesised answer for an outage post asked for a small legible sign carrying a wrong-URL warning and called that wording mandatory, while the show bar and the brief both ban lettering outright in that picture. Read every prop and every style noun a reflect answer names against the show bar and the brief, drop the ones that would put lettering, a screen or a literal mark in the frame, and keep the half that describes the composition.
- **One verdict is one data point.** Two variants approved on one card does not mean he always approves both. A card's approvals are one observation about one post, not a rule about the series.
- **A caveat the card named in plain words and he approved over is neither a defect nor a licence.** The approval says that caveat did not sink that frame on that post. It does not make the shape safe in the next picture, and it does not turn the caveat into something the record should call a fault — keep its wording in `## Why` as a description of the file, and let a repeat be judged on its own card. Write this distinction into the closing comment, because the next round reads a card that carried caveats as a card that cleared them.
- **One memory per card for approvals, one per reject and per defer.** Retaining a memory per image multiplies one observation into three and reads as three independent data points later.
- **A reflect answer for a different series is a different series.** If it names a style the post's records do not use, it answered about another post's world. Match the series from the records' `## Prompt` blocks.
- **An approval with no reason is still an approval.** Write the row reason as "Approved on review.", and record in the retained memory that no reason was given. Never invent a reason he withheld.

## The REST fallback

`hindsight_recall` and `hindsight_reflect` go through a reranker that can time out. The bank's own REST API serves the same memories without it, and it is the only way to get a **memory id** — a queued receipt does not carry one, and a deliverable that must cite the memory holding a reject reason needs the id.

`scripts/hindsight-memory.py` wraps it:

```bash
# list and filter locally (the reranker-free path)
python3 scripts/hindsight-memory.py list "weird artifacts" 400

# fetch one memory by id
python3 scripts/hindsight-memory.py get <memory-id>

# curate a fact that misattributes a rule (see "Curating a wrong memory")
python3 scripts/hindsight-memory.py invalidate <id> --reason "contradicts card <card-id>"
python3 scripts/hindsight-memory.py edit <id> --text "corrected text"
```

The script reads the bank id and API url from `~/.hermes/profiles/matejko/hindsight/config.json` and the key from the profile `.env`, and never prints the key.

**The API surface** (base url and bank template come from the config file):

- `GET /v1/default/banks/{bank}/memories/list?limit=N&offset=0` — every memory with its `id`, `tags` and `text`. Filter the text locally. Add `state=invalidated` to read the curation archive, `type=world|experience|observation` to narrow by kind.
- `GET /v1/default/banks/{bank}/memories/{id}` — one memory, including its `source_memory_ids` and its `state`, `invalidation_reason` and `edited_at`.
- `POST /v1/default/banks/{bank}/memories/recall` — the ranked path; this is the one that times out.

**When the reranker times out, the ranked path returns `500` with `TEI rerank request failed`** while the list path still answers. That is the tell that the bank is reachable and only the ranking is down: go to `list` and filter, and do not conclude the bank is empty or broken.

**A `list` scan finds ids that `recall` never surfaces** — the list is not ranked, so a memory whose text shares no words with your query is still there. When you are looking for the memory holding a specific reason, search the list for a distinctive phrase from the reason itself. **The list route serves indexed memories only, so a memory you retained minutes ago is in neither path.** The list route is the fallback for the *ranker* being down, not for a memory being unindexed: a receipt of `Memory queued for storage` means the memory is queued, and searching the list for the reason's own words can come back empty while other memories from the same session sit there. Absence from both paths right after a retain is expected — do not re-retain it, and do not read it as a failed store.

Tags worth filtering on: `taste` (a taste observation), `verdict` (a verdict and its reason), `backlog` (from the backlog review). A memory carrying `taste` **and** `verdict` is the one that holds a rejection reason.

## Curating a wrong memory

Taste memories drift: a verdict gets summarised into a rule the user never stated, and the wrong rule then drives every later prompt. When a note misattributes something, fix it at the source, not only in the note you can see.

**Observations cannot be curated directly.** The bank refuses to edit or invalidate one:

```
Memory '<id>' is a observation; only world/experience facts can be curated. Observations are derived and regenerate from their sources.
```

That refusal is the design, not a fault: an observation is a consolidation of source facts, so the wrong statement usually lives in a source fact. **Curate the source fact and the observation goes with it** — invalidating or editing a source fact deletes the derived observations that cited it and re-queues the surviving sources for re-consolidation. The observation then reads as absent (`404`), which is the expected outcome: it was never a row that could be archived, so it cannot show up as "invalidated".

**To find the source facts of an observation**, read the observation and take its `source_memory_ids`; the ones carrying the wrong claim are the ones to curate. Curating one source fact can take several observations down with it, so list the ids you are about to change and expect collateral removals rather than treating them as a surprise.

**A curated fact is archived, not deleted.** `state: "invalidated"` with a `reason` moves the row into the curation archive and the reason is what makes the curation auditable later, so always pass one. `state: "valid"` restores it. Editing a fact's text re-embeds it and drops the observations built on it.

**Scan the whole bank before you claim a contradiction is gone.** Recall is ranked and truncated, so a fact that says the wrong thing can sit below the cut while the top hits look clean. List the bank and filter on the claim itself. Expect false positives — a rule's name and the user's name co-occur in unrelated notes about other posts — so confirm each hit is really an attribution before curating it.

**Re-consolidate after curating.** Trigger a consolidation pass and check the regenerated observation says the corrected thing; a bank that still holds the old sources will otherwise hand the old claim back on the next consolidation.

**The REST shapes** (the bank also serves the same operations as MCP tools over HTTP):

- `PATCH /v1/default/banks/{bank}/memories/{id}` with `{"state": "invalidated", "reason": "..."}` or `{"text": "..."}`.
- `POST /v1/default/banks/{bank}/consolidate` to re-derive observations.
- `GET /v1/default/banks/{bank}/memories/list?state=invalidated` for the curation archive.

`scripts/hindsight-memory.py` wraps the first and third: `invalidate <id> --reason "..."`, `edit <id> --text "..."`, `list --state invalidated`.

## What to retain

- **Per reject and per defer:** his reason, the post, the image, and the prompt traits it was about — the trait is what makes the memory useful next time, not the reason alone.
- **Per card, for its approvals:** what the approved images have in common, plus the honest limit that one card is one data point.
- **Quote him, then label the generalisation as yours.** "Matejko's hypothesis", never "Wojtek's rule" — a rule he never uttered is yours until he says it, and a note that credits it to him will come back from recall as his standing preference. Keep the quoted reason and the inferred trait in separate sentences so a later reader can tell which half came from him.
