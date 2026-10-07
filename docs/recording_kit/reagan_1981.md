# Recording kit: Ronald Reagan, First Inaugural Address (1981)

Record in a quiet room, phone or laptop mic ~20 cm from your mouth. Start recording, stay silent for 1 second, read the text, stay silent for 1 second, stop. **Say nothing except the text**: no take name, no "okay". Forced alignment expects exactly these words, so extra speech shifts every timestamp. Any format works (M4A, WAV, MP3, WebM).

Save each take as `recordings/reagan_<take>_<your initials>.<ext>` (e.g. `recordings/reagan_A_mp.m4a`), then run `uv run python scripts/import_recordings.py`.

## Take `good`: read naturally, as well as you can

> The business of our nation goes forward. These United States are confronted with an economic affliction of great proportions. We suffer from the longest and one of the worst sustained inflations in our national history. It distorts our economic decisions, penalizes thrift, and crushes the struggling young and the fixed-income elderly alike. It threatens to shatter the lives of millions of our people. Idle industries have cast workers into unemployment, human misery, and personal indignity. Those who do work are denied a fair return for their labor by a tax system which penalizes successful achievement and keeps us from maintaining full productivity. But great as our tax burden is, it has not kept pace with public spending. For decades, we have piled deficit upon deficit, mortgaging our future and our children's future for the temporary convenience of the present.

## Take `A`: natural, except at the marked spans

- **⟦PAUSE⟧** Stop mid-phrase here for about 1–2 seconds, as if you lost your place.
- **⟦FLAT⟧** Say this on one flat note, with no rise or fall in pitch, like reading a list.
- **⟦RUSH⟧** Speed through this part noticeably faster than the rest, without stopping.

> The business of our nation ⟦PAUSE⟧ goes forward. These United States are confronted with an economic affliction of great proportions. We suffer from the longest and one of the worst sustained inflations in our national history. It distorts our economic decisions, penalizes thrift, and crushes the struggling young and the fixed-income elderly alike. It threatens to shatter the lives ⟦FLAT⟧ of millions of our people. Idle industries have cast workers into unemployment, human misery ⟦/FLAT⟧, and personal indignity. Those who do work are denied ⟦RUSH⟧ a fair return for their labor by a tax system which ⟦/RUSH⟧ penalizes successful achievement and keeps us from maintaining full productivity. But great as our tax burden is, it has not kept pace with public spending. For decades, we have piled deficit upon deficit, mortgaging our future and our children's future for the temporary convenience of the present.

## Take `B`: natural, except at the marked spans

- **⟦NO-PAUSE⟧** Do NOT pause at this boundary; run straight into the next words.
- **⟦QUIET⟧** Drop your volume sharply here, as if trailing off, then recover after.
- **⟦DRAG⟧** Slow right down here: stretch the words and lose momentum.
- **⟦MUMBLE⟧** Barely move your lips or jaw here; soften every consonant.

> The business of our nation goes forward. These United States are confronted with an economic affliction of great proportions. We suffer from the longest and one of the worst sustained inflations in our national history. It distorts our economic decisions ⟦NO-PAUSE⟧, penalizes thrift, and crushes the struggling young and the fixed-income elderly ⟦QUIET⟧ alike. It threatens to shatter the ⟦/QUIET⟧ lives of millions of our ⟦DRAG⟧ people. Idle industries have cast workers into unemployment, human misery, and personal ⟦/DRAG⟧ indignity. Those who do work are denied a fair return for their labor by a tax system which penalizes successful achievement and keeps us from maintaining full productivity. But great as our tax burden is, it has not kept pace with public spending. For decades, we have piled deficit upon ⟦MUMBLE⟧ deficit, mortgaging our future and our children's future ⟦/MUMBLE⟧ for the temporary convenience of the present.

## Import

```bash
uv run python scripts/import_recordings.py          # every file in recordings/ named <speech>_<take>_<initials>.<ext>
uv run python scripts/import_recording.py --baseline reagan_1981 --speaker <initials> --take A  path/to/file.m4a   # one file
```
