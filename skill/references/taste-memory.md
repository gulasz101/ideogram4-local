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

- **A timeout is a failed call, not an empty model.** Never read "no history" into a timeout, and never build a prompt on that inference. If reflect and recall both fail, the taste model for that topic is unavailable — say so on the issue, work from the library records, and retry later. Do not let it block a card.
- **The records beat the memory.** `hindsight_reflect` synthesises across verdicts and will assert a history the records contradict — it has described a round-1 rejection on a slot whose round-1 items were both approved. Check every claim against the record's `## Verdicts` table and the card's `result`, and follow the records where the two disagree.
- **One verdict is one data point.** Two variants approved on one card does not mean he always approves both. A card's approvals are one observation about one post, not a rule about the series.
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
```

The script reads the bank id and API url from `~/.hermes/profiles/matejko/hindsight/config.json` and the key from the profile `.env`, and never prints the key.

**The API surface** (base url and bank template come from the config file):

- `GET /v1/default/banks/{bank}/memories/list?limit=N&offset=0` — every memory with its `id`, `tags` and `text`. Filter the text locally.
- `GET /v1/default/banks/{bank}/memories/{id}` — one memory.
- `POST /v1/default/banks/{bank}/memories/recall` — the ranked path; this is the one that times out.

**When the reranker times out, the ranked path returns `500` with `TEI rerank request failed`** while the list path still answers. That is the tell that the bank is reachable and only the ranking is down: go to `list` and filter, and do not conclude the bank is empty or broken.

**A `list` scan finds ids that `recall` never surfaces** — the list is not ranked, so a memory whose text shares no words with your query is still there. When you are looking for the memory holding a specific reason, search the list for a distinctive phrase from the reason itself.

Tags worth filtering on: `taste` (a taste observation), `verdict` (a verdict and its reason), `backlog` (from the backlog review). A memory carrying `taste` **and** `verdict` is the one that holds a rejection reason.

## What to retain

- **Per reject and per defer:** his reason, the post, the image, and the prompt traits it was about — the trait is what makes the memory useful next time, not the reason alone.
- **Per card, for its approvals:** what the approved images have in common, plus the honest limit that one card is one data point.
