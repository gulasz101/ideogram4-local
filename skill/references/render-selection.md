# Which render ships when both engines pass the bar

A re-render submits an `ideogram4` + `flux2-klein` pair. When **both** pass the show bar, the card still carries one render per slot, so one of them has to be chosen. The bar is only the floor; the prompt is the acceptance criterion.

- **Ship the render whose props match the prompt more closely** and which has no connector or pseudo-text defect, even a small one. A render that passes the show bar can still be the wrong picture for the slot if its figure, clothing or props drift from what the prompt asked for (a man in a white t-shirt and jeans where the prompt said a yellow sweater; a robot holding a cable over a doorframe where the prompt said a dome robot wired to a cube on a desk).
- **The same rule settles a tie between two clean renders:** the one that depicts the section's beat ships, and the other is named as the companion that lost.
- **Name the loser in two places** so the next round sees it: in the item's `description` (job id plus why it lost) and in the comment that links the attachments. The card is frozen once posted, so the comparison has to be written into the description before the POST.
- **Connector and pseudo-text defects win the tiebreak even when small.** A wire that ends in mid-air (a connector that appears as two separate gadgets that never connected) or pseudo-text in a corner is a hold-back regardless of how clean the rest of the frame is; the engine that avoided it ships.

This is the silent-re-render case inside one round: it does not consume a round, and the slot's item id stays the brief's id.
