# Rendering a beat as physical state

When a section's idea is abstract — a config split, a limit nobody set, an alert that finally arrived, a repair that did not work — the frame has to show it as an object in a state. This file is the vocabulary that has passed review, plus the rules for choosing between the options.

Use it at step "rewrite the prompt" in `SKILL.md`: read the section, name the idea in one line, then pick an object and a state from here rather than inventing a new prop per slot.

## Rules

1. **Put the state on a surface the object owns.** Blued metal, a scorched bloom in brick, an even film of dust, a band worn pale. Never a mark drawn over the scene (tick, arrow, circled item), and never a repeated small mark — a row of notches is drawn as decoration, one notch in a place it cannot repeat is not.
2. **Show absence by what the surface has lost, not by a hole or a blank.** "Nothing has used this in days" reads from an even drift of dust with no footmark in it; a pale or white rectangle reads as a pasted panel.
3. **State the absence of control by naming what is not there.** "No governor, no linkage, nothing that could hold its speed" draws an ungoverned machine; a blurred rim alone reads as "fast", not as "uncontrolled".
4. **A pair that failed together is two objects of one family, both marked.** The repair that did nothing is the repaired part still bolted in place and furred with dust; the second failure is an identical object a pace away carrying the same state.
5. **"One of two carried the whole load" is a span.** Two identical planks on the same two supports: the walked one worn smooth and pale down the centre, the abandoned one broken through under undisturbed dust. A count of two, one state each, no caption needed.
6. **A signal that arrives is one continuous run ending in a clean part.** Pipe, rod, wire or rope from the source across the room to the far corner, joints sound, the far end clean metal while everything else is dull — and the dust it shed lying on the floor beneath the bracket is what proves it moved.
7. **A limit that was finally set is an object that stops.** A pawl dropped between the teeth, a clamp band on a pipe, a stop the lever meets. State the relation by body measure (a band the width of a thumb, on a pipe no wider than two fingers), never with a numeral.
8. **Nobody in the frame when the beat needs no hands.** A still life cannot double a figure, lose a hand or grow a leg. Put a person in only when an action is the beat, and then take the pose from `figure-and-prop-prompts.md`.
9. **Every frame keeps the register paragraph, a described object in each near corner, and the negative clause last.** The corners are what stops the model pasting something into an empty region.

## Table of beats to objects (all approved in review)

| beat | object and state |
| --- | --- |
| one failure returned, and it brought a second | the mended machine with its repair still bolted on and furred with dust, heat-scarred brick behind it, an identical machine a pace away stained the same way |
| one of two carried everything | two identical planks on the same trestles, one worn smooth down the centre, one broken through under dust with no footmark in it |
| a machine with nothing governing it | flywheel with no governor named in words, rim blurred with movement, bearings blued and smoking, soot band on the wall behind |
| work piling up with nothing trimming it | a chute pouring identical sacks until the pile reaches the joists and spills back over the belts, several split and empty |
| a pipeline that finally rings end to end | one continuous pipe run to a clean metal mouth in the far corner, lever lifted, the dust it shed lying on the flags below |
| a check before acting | a lens held over the lock it is checking; a probe that returns nothing at all |
| a limit set at last | a pawl dropped between the teeth; a flat clamp band on a narrow pipe |
| a supply split into two, one branch abandoned | one valve, a Y below it, one branch shut with a dry dusty bore, the other running out through a hole in the wall |

## Drafting to length

The register paragraph, the scene, the corners and the negative clause land at **320–340 words on the first draft**, and the approved band is **248–310**. Trim before staging: cut secondary shading and duplicated adjectives, keep the negative clause whole and last, and confirm with `wc -w`. A prompt over the band loses its tail — the negative clause — at the encoder, which is the part that keeps panels and lettering out.

## Audit the whole post, stage the whole post

The six-render cap is on **submissions**, not on prompt files. When a post has four slots and the cap carries three, audit and stage all four in the same pass and submit the first three in reading order; the fourth is then a batch submission with no audit behind it when its round comes. Say in the post's note which slots are staged and that the fourth waits for round 2.
