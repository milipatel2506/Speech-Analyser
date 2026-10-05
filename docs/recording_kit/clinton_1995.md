# Recording kit: Hillary Rodham Clinton, Remarks to the Fourth World Conference on Women (Beijing) (1995)

Record in a quiet room, phone or laptop mic ~20 cm from your mouth. Say your take name before you start, leave 1 s of silence, then read. Save as WAV/M4A/WebM; any format works.

## Take `good`: read naturally, as well as you can

> I have met new mothers in Indonesia who come together regularly in their village to discuss nutrition, family planning, and baby care. I have met working parents in Denmark who talk about the comfort they feel in knowing that their children can be cared for in safe and nurturing after-school centers. I have met women in South Africa who helped lead the struggle to end apartheid and are now helping to build a new democracy. I have met with the leading women of my own hemisphere who are working every day to promote literacy and better health care for children in their countries. I have met women in India and Bangladesh who are taking out small loans to buy milk cows or rickshaws or thread in order to create a livelihood for themselves and their families. I have met the doctors and nurses in Belarus and Ukraine who are trying to keep children alive in the aftermath of Chernobyl.

## Take `A`: natural, except at the marked spans

- **⟦FLAT⟧** Say this on one flat note, with no rise or fall in pitch, like reading a list.
- **⟦RUSH⟧** Speed through this part noticeably faster than the rest, without stopping.
- **⟦PAUSE⟧** Stop mid-phrase here for about 1–2 seconds, as if you lost your place.

> I have ⟦FLAT⟧ met new mothers in Indonesia who come together regularly in their village to discuss nutrition ⟦/FLAT⟧, family planning, and baby care. I have met working parents in Denmark who talk about the comfort they feel in knowing that their children can be cared for in safe and nurturing after-school centers. I have met women in South Africa who helped lead the struggle to end apartheid and are now helping to build a new democracy. I have met with the leading women of my own hemisphere who are working every day to promote literacy and better health care for children in their countries. I have met ⟦RUSH⟧ women in India and Bangladesh who are taking out small loans to buy ⟦/RUSH⟧ milk cows or rickshaws or thread in order to create a livelihood for themselves and their families. I have met the doctors and nurses in Belarus and Ukraine who are trying ⟦PAUSE⟧ to keep children alive in the aftermath of Chernobyl.

## Take `B`: natural, except at the marked spans

- **⟦QUIET⟧** Drop your volume sharply here, as if trailing off, then recover after.
- **⟦NO-PAUSE⟧** Do NOT pause at this boundary; run straight into the next words.
- **⟦MUMBLE⟧** Barely move your lips or jaw here; soften every consonant.
- **⟦DRAG⟧** Slow right down here: stretch the words and lose momentum.

> I have ⟦QUIET⟧ met new mothers in Indonesia who come together ⟦/QUIET⟧ regularly in their village to discuss nutrition, family planning, and baby care. I have met working parents in Denmark who talk about the comfort they feel in knowing that their children can be cared for in safe and nurturing after-school centers. I have met women in South Africa who helped lead the struggle to end apartheid and are now helping to build a new democracy. I have met with the leading women of my own hemisphere who are working every day to promote literacy and better health care for children in their countries ⟦NO-PAUSE⟧. I have met women in India and Bangladesh who are taking ⟦MUMBLE⟧ out small loans to buy milk cows or ⟦/MUMBLE⟧ rickshaws or thread in order to create a livelihood for themselves and their families. I have met the doctors and nurses in Belarus and Ukraine who are ⟦DRAG⟧ trying to keep children alive in the ⟦/DRAG⟧ aftermath of Chernobyl.

## Import

```bash
uv run python scripts/import_recording.py --baseline clinton_1995 --speaker <initials> --take good  path/to/good.wav
uv run python scripts/import_recording.py --baseline clinton_1995 --speaker <initials> --take A     path/to/A.wav
```
