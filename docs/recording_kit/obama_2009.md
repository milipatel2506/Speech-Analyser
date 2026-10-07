# Recording kit: Barack Obama, Inaugural Address (2009)

Record in a quiet room, phone or laptop mic ~20 cm from your mouth. Start recording, stay silent for 1 second, read the text, stay silent for 1 second, stop. **Say nothing except the text**: no take name, no "okay". Forced alignment expects exactly these words, so extra speech shifts every timestamp. Any format works (M4A, WAV, MP3, WebM).

Save each take as `recordings/obama_<take>_<your initials>.<ext>` (e.g. `recordings/obama_A_mp.m4a`), then run `uv run python scripts/import_recordings.py`.

## Take `good`: read naturally, as well as you can

> In reaffirming the greatness of our nation, we understand that greatness is never a given. It must be earned. Our journey has never been one of shortcuts or settling for less. It has not been the path for the fainthearted, for those who prefer leisure over work or seek only the pleasures of riches and fame. Rather, it has been the risk-takers, the doers, the makers of things, some celebrated, but more often men and women obscure in their labor, who have carried us up the long, rugged path towards prosperity and freedom. For us, they packed up their few worldly possessions and traveled across oceans in search of a new life. For us, they toiled in sweatshops and settled the West, endured the lash of the whip, and plowed the hard earth. For us, they fought and died in places like Concord and Gettysburg, Normandy and Khe Sanh. Time and again, these men and women struggled and sacrificed and worked till their hands were raw so that we might live a better life.

## Take `A`: natural, except at the marked spans

- **⟦FLAT⟧** Say this on one flat note, with no rise or fall in pitch, like reading a list.
- **⟦PAUSE⟧** Stop mid-phrase here for about 1–2 seconds, as if you lost your place.
- **⟦RUSH⟧** Speed through this part noticeably faster than the rest, without stopping.

> In reaffirming the greatness of our nation, we understand that greatness is never a ⟦FLAT⟧ given. It must be earned. Our journey has never been one ⟦/FLAT⟧ of shortcuts or settling for less. It has not been the path for the fainthearted, for those who prefer leisure over work or seek only the pleasures of riches and fame. Rather, it has been the risk-takers, the doers, the makers of things, some ⟦PAUSE⟧ celebrated, but more often men and women obscure in their labor, who have carried us up the long, rugged path towards prosperity and freedom. For us, they packed up ⟦RUSH⟧ their few worldly possessions and traveled across oceans in search of a ⟦/RUSH⟧ new life. For us, they toiled in sweatshops and settled the West, endured the lash of the whip, and plowed the hard earth. For us, they fought and died in places like Concord and Gettysburg, Normandy and Khe Sanh. Time and again, these men and women struggled and sacrificed and worked till their hands were raw so that we might live a better life.

## Take `B`: natural, except at the marked spans

- **⟦NO-PAUSE⟧** Do NOT pause at this boundary; run straight into the next words.
- **⟦MUMBLE⟧** Barely move your lips or jaw here; soften every consonant.
- **⟦QUIET⟧** Drop your volume sharply here, as if trailing off, then recover after.
- **⟦DRAG⟧** Slow right down here: stretch the words and lose momentum.

> In reaffirming the greatness of our nation, we understand that greatness is never a given. It must be earned. Our journey has never been one of shortcuts or settling for less. It has not been the path for the fainthearted, for those who prefer leisure over work ⟦NO-PAUSE⟧ or seek only the pleasures of riches and fame. Rather, it has been the risk-takers, the doers, the makers of things, some celebrated, ⟦MUMBLE⟧ but more often men and women obscure in ⟦/MUMBLE⟧ their labor, who ⟦QUIET⟧ have carried us up the long ⟦/QUIET⟧, rugged path towards prosperity and freedom. For us, they packed up their few worldly possessions and traveled across oceans in search of a new life. For us, they ⟦DRAG⟧ toiled in sweatshops and settled the West, endured the ⟦/DRAG⟧ lash of the whip, and plowed the hard earth. For us, they fought and died in places like Concord and Gettysburg, Normandy and Khe Sanh. Time and again, these men and women struggled and sacrificed and worked till their hands were raw so that we might live a better life.

## Import

```bash
uv run python scripts/import_recordings.py          # every file in recordings/ named <speech>_<take>_<initials>.<ext>
uv run python scripts/import_recording.py --baseline obama_2009 --speaker <initials> --take A  path/to/file.m4a   # one file
```
