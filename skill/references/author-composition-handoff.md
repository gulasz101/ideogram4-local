# Author composition hand-offs

When a picture keeps failing on the same clause, the fix belongs to the post's author, not to another reworded prompt. This file is the mechanics of that hand-off and of the run that picks the answer up.

## When it fires

- **Two renders rejected on the same clause**, or **two of your own self-check holds on the same clause**. A held-back render never reached the owner, so nothing in the card's history escalates it — but the second failure says the same thing a second rejection does: the composition is wrong, not the description.
- **Immediately**, without waiting for round 3, when the verdict itself names the concept ("does not fit the concept of the image", "makes no sense", "check it with the author"). The 3-round limit is a ceiling, not a schedule.
- **Not** when you are merely short of one idea and the owner is waiting — a card with the residual named is something he can judge in seconds, and a parked slot puts nothing in front of him.
- **The verdict reason names a collaborator** ("redo it together with florian", "check with the author"). That is not a composition blocker — it is a coordination request. Open a short courier issue to that agent carrying the revised prompts and what you need from them, and keep this card live and rendering; the re-render proceeds under the series rule in the meantime.

## A verdict reason that names a collaborator

The verdict is about one clause (unreadable text, wrong concept) and names who should settle it. The re-render still happens now, under the series rule that already covers that clause; the collaborator is asked to confirm or override, not to gate the render.

- **Open a courier issue, not a blocker.** Child of the card, assigned to the named agent, status `todo`. Body: the slot list, the job ids, the prompt file paths, the series rule you applied, and the one specific question they need to answer (e.g. "should any slot carry readable labels on comic-book bubbles, or is no text fine?"). Set `blockedByIssueIds` only if the render cannot proceed without their answer — a text clause can proceed without them.
- **Proceed with the re-render in this run.** Apply the series rule that the clause names (no readable lettering, no text of any kind on any surface) and drop the traits that caused the defect (`color_palette`, literal red-X/check marks, clipboard/label/screen surfaces). Do not wait for the collaborator's reply before submitting.
- **Name the courier issue in the closing comment** so the owner sees the hand-off recorded, and say plainly that the re-render went out without waiting.
- **When the answer lands**, it rides into the slot's next round if it changes anything; if it only confirms the no-text choice, note that in the next card's comment and move on. A confirmation is not a re-render.

## What to ask for

Ask for a **composition, not an idea**, and say so in those words. The answer that fixes a rendered artefact is nearly always geometric:

- camera height, angle and tilt, and what the frame crops on each side;
- where every element sits, and which one is the subject;
- how the join that keeps failing is physically drawn, with a test that can be checked on a crop;
- what fills each corner, since a bare region gets a pasted graphic;
- anything to keep out of the frame;
- one line of alt text for the draft.

The description carries the post path, the section, the owner's rejection reason verbatim, what the failed prompts described, and what the current prompt does — the author cannot read your card.

## The mechanics

0. **Check the author is awake before you hand anything off.** `GET /api/companies/{companyId}/agents` and read the target's `status`: an agent whose adapter sits in `error`, or that is otherwise not running, will not answer, and a hand-off to it leaves the slot with no render in flight and nobody scheduled to collect one — the failure looks exactly like a card waiting patiently. A hand-off is a waiting path only when the other side is live. When the author is unavailable, do not park the card on a blocker that cannot resolve: change what is in your own control (the pose, the occlusion, the prop), and say in the issue comment that the escalation was skipped, why, and what you spent instead — a deviation from an announced plan belongs on the record, because the owner reads the thread and has already been told what would happen next.
1. Open the hand-off as a **child of the card** and assign it to the post's author. Set the card's `blockedByIssueIds` to it: the blocker is the waiting path, and an `in_progress` card with no monitor and no pending interaction is what the board's recovery re-parks.
   - **Never block a card that already carries a live verdict card.** A pending `request_item_verdicts` on the issue means the owner is being asked to judge other items; blocking freezes that judgement behind a composition question about one slot. Escalate from the held slot's own card, or keep this card live and let the hand-off answer ride into the slot's next round.
2. **Do not arm a monitor while the card is blocked.** A monitor only fires on an `in_progress` or `in_review` issue, so a render queued under a blocked card never gets collected.
3. **When the answer lands, clear the block and arm the monitor in one PATCH:** `{"status":"in_progress","blockedByIssueIds":[],"executionPolicy":{"monitor":{"nextCheckAt":"<job ETA + 5, UTC>","scheduledBy":"assignee","notes":"..."}}}`. Read `monitorNextCheckAt` back non-null. Clearing the block in one call and arming in another leaves a window with no wake path.
4. **The post legitimately sits in `rendering` with an empty `ready` list** while the hand-off is open: nothing is rendering, and the queue's path to the next round is the blocker resolving. Say that in `backlog.py note <n>` — the hand-off issue, the blocker, no render in flight — and do not release the slot or open a placeholder card.
5. **An author can answer inside your own run.** Re-read the hand-off issue before ending: an already-`done` hand-off means its resolution wake has fired and the card will never be woken by it, so take the answer, write the prompt and submit the render in that same run.

## Turning the answer into a prompt

- Take his element table literally: his bbox order and his element order. Run `lint` for risk 0 and `check-bboxes.py` before submitting.
- **Verify the transcription, not just the file.** `check-bboxes.py` and `lint` only prove the prompt is internally consistent — a digit read wrong or a row skipped passes both, because the file you wrote never contradicts itself. After transcribing, extract the `[y1, x1, y2, x2]` arrays from the source table and from the prompt JSON and diff them; they must be identical, element for element, in order. A mismatch there is the exact shape that puts an element where nobody asked for it.
- **His boxes usually encode the fix.** A connector's box has to overlap both the source's box and the target's, and the figure's box has to stay off the connector's — the geometry is what stops the model parking the connector beside the target. Do not widen a figure's box "to give him room".
- If his prose and his boxes disagree (a range that is not inside the box it is said to end in), follow the boxes and note the discrepancy on the card.
- Credit him in the card's long note, so a later round knows where the composition came from.
- **His alt-text line ships as he wrote it.** The one line per slot he is asked for is the caption the embed gets on approval, not a starting point: he wrote it knowing what the section says, and a run that rewrites it from the finished render swaps his sentence for its own description of the same pixels. Carry it into the brief and the record so the approval run has it without re-reading the document — and when the render departs from his composition, the caption follows the file instead and the card names the departure, because a caption that describes a picture nobody made is worse than a paraphrase.
- **The answer usually arrives as an issue document, not as a comment.** A composition is long — camera, element table, per-slot pass/fail list, plan B — so the author writes it to the hand-off issue's `composition` document and closes the issue. Read it with `GET /api/issues/<handoff>/documents/composition` and take the body: the completion summary names the document, the document carries the text, and a run that only reads the comments finds the hand-off `done` with no instructions in the thread. Add the document key to the next round's brief so the slot's history names where the composition came from.
- **His pass/fail crop list is the self-check, so run it literally before the card.** He writes it as numbered items with a crop scale and an explicit fail condition ("2x, chin to mid-thigh: two continuous outlines meeting the belt once; fail on an outline that vanishes and returns, two belt lines, or a second set of legs"). Run those crops first and in his order, because he chose them from the defect that actually failed, and a frame that passes his list is a frame you can put up without guessing what he would see. Where his numbers and his boxes disagree, follow the boxes and say so on the card.
- Keep his answers to what the renderer needs — style, canvas size, the series' character, no lettering — rather than restating them as your own preferences.
