# Recording kit: Kamala Harris, Concession Speech (2024)

Record in a quiet room, phone or laptop mic ~20 cm from your mouth. Start recording, stay silent for 1 second, read the text, stay silent for 1 second, stop. **Say nothing except the text**: no take name, no "okay". Forced alignment expects exactly these words, so extra speech shifts every timestamp. Any format works (M4A, WAV, MP3, WebM).

Save each take as `recordings/harris_<take>_<your initials>.<ext>` (e.g. `recordings/harris_A_mp.m4a`), then run `uv run python scripts/import_recordings.py`.

## Take `good`: read naturally, as well as you can

> Look, many of you know I started out as a prosecutor and throughout my career, I saw people at some of the worst times in their lives, people who had suffered great harm and great pain, and yet found within themselves the strength and the courage and the resolve to take the stand, to take a stand, to fight for justice, to fight for themselves, to fight for others. So let their courage be our inspiration. Let their determination be our charge.

## Take `A`: natural, except at the marked spans

- **⟦PAUSE⟧** Stop mid-phrase here for about 1–2 seconds, as if you lost your place.
- **⟦FLAT⟧** Say this on one flat note, with no rise or fall in pitch, like reading a list.
- **⟦RUSH⟧** Speed through this part noticeably faster than the rest, without stopping.

> Look, many of you know I started out as a prosecutor and throughout my career, I ⟦PAUSE⟧ saw people at some of the worst times in their lives, people who had suffered great harm and great pain, and yet found within themselves ⟦FLAT⟧ the strength and the courage and the resolve to take ⟦/FLAT⟧ the stand, to take a stand, to fight for justice, to fight for themselves, to fight for others. So ⟦RUSH⟧ let their courage be our inspiration. Let ⟦/RUSH⟧ their determination be our charge.

## Take `B`: natural, except at the marked spans

- **⟦MUMBLE⟧** Barely move your lips or jaw here; soften every consonant.
- **⟦DRAG⟧** Slow right down here: stretch the words and lose momentum.
- **⟦QUIET⟧** Drop your volume sharply here, as if trailing off, then recover after.
- **⟦NO-PAUSE⟧** Do NOT pause at this boundary; run straight into the next words.

> Look, many of you know I started out as a prosecutor and throughout ⟦MUMBLE⟧ my career, I saw people at ⟦/MUMBLE⟧ some of the worst times in their ⟦DRAG⟧ lives, people who had suffered great harm and great pain, and yet found within ⟦/DRAG⟧ themselves the strength and the courage ⟦QUIET⟧ and the resolve to take the stand, to take ⟦/QUIET⟧ a stand, to fight for justice, to fight for themselves ⟦NO-PAUSE⟧, to fight for others. So let their courage be our inspiration. Let their determination be our charge.

## Import

```bash
uv run python scripts/import_recordings.py          # every file in recordings/ named <speech>_<take>_<initials>.<ext>
uv run python scripts/import_recording.py --baseline harris_2024 --speaker <initials> --take A  path/to/file.m4a   # one file
```
