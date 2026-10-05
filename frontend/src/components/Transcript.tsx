import type { Report } from '../api'
import { usePlayer } from '../lib/player'
import { sev } from '../lib/severity'

// Word-level transcript from forced alignment: the current word follows the playhead and words
// inside a flaw region are underlined in that flaw's severity colour. Click a word to seek.
export function Transcript({ report }: { report: Report }) {
  const { time, seek } = usePlayer()
  const words = report.words.participant
  const flawOf = (i: number) => report.flaws.find((f) => i >= f.word_span[0] && i <= f.word_span[1])

  return (
    <p className="text-[15px] leading-8">
      {words.map((w, i) => {
        const f = flawOf(i)
        const current = time >= w.start && time < (words[i + 1]?.start ?? w.end + 0.3)
        return (
          <span key={i}>
            <span
              onClick={() => seek(w.start)}
              title={`${w.start.toFixed(2)}–${w.end.toFixed(2)} s${f ? ` · ${f.label}` : ''}`}
              className={`cursor-pointer rounded px-0.5 transition-colors hover:bg-surface-2 ${current ? 'bg-accent-soft font-medium text-ink' : f ? 'text-ink' : 'text-ink-2'}`}
              style={f ? { textDecoration: 'underline', textDecorationColor: sev(f.severity).color, textDecorationThickness: 3, textUnderlineOffset: 5 } : undefined}
            >
              {w.word}
            </span>{' '}
          </span>
        )
      })}
    </p>
  )
}
