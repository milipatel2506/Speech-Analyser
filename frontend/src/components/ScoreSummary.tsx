import type { Report } from '../api'
import { bandColor } from '../lib/severity'

const ORDER = ['pace', 'pausing', 'pitch_variety', 'energy', 'clarity']

function Stat({ label, you, ref, unit, hint }: { label: string; you: number; ref: number; unit: string; hint: string }) {
  const delta = ref ? (you - ref) / Math.abs(ref) : 0
  return (
    <div className="rounded-xl bg-surface-2 px-4 py-3" title={hint}>
      <div className="text-xs text-ink-2">{label}</div>
      <div className="mt-1 text-xl font-semibold">
        {you.toFixed(unit === 'wpm' || unit === '' ? 0 : 1)}
        <span className="ml-1 text-xs font-normal text-muted">{unit}</span>
      </div>
      <div className="text-xs text-muted tnum">
        ref {ref.toFixed(unit === 'wpm' || unit === '' ? 0 : 1)} · {delta >= 0 ? '+' : '−'}
        {Math.abs(delta * 100).toFixed(0)}%
      </div>
    </div>
  )
}

export function ScoreSummary({ report }: { report: Report }) {
  const { score, summary } = report
  const p = summary.participant
  const b = summary.baseline
  return (
    <div className="grid gap-6 lg:grid-cols-[220px_1fr_1fr]">
      <div className="flex flex-col justify-center">
        <div className="text-sm text-ink-2">Delivery score</div>
        <div className="flex items-baseline gap-2">
          <span className="text-6xl font-semibold tracking-tight">{score.overall.toFixed(0)}</span>
          <span className="text-lg text-muted">/ 100</span>
        </div>
        <div className="mt-1 inline-flex items-center gap-2 text-sm font-medium">
          <span className="h-2.5 w-2.5 rounded-full" style={{ background: bandColor(score.overall) }} />
          {score.band}
        </div>
        <div className="mt-2 text-xs text-muted">
          {report.flaws.length} flaw region{report.flaws.length === 1 ? '' : 's'} · {report.globals.matched_words}/{report.globals.participant_words} words aligned
        </div>
      </div>

      <div>
        <div className="mb-2 text-sm font-medium">Rubric</div>
        <div className="space-y-2.5">
          {ORDER.map((k) => {
            const d = score.dimensions[k]
            if (!d) return null
            const lost = d.deductions.reduce((a, x) => a + x.points, 0)
            return (
              <div key={k} title={d.deductions.map((x) => `−${x.points} ${x.flaw}`).join('\n') || 'No deductions'}>
                <div className="flex justify-between text-xs">
                  <span className="text-ink-2">{d.label}</span>
                  <span className="font-medium tnum">
                    {d.score.toFixed(0)}
                    {lost > 0 && <span className="ml-1.5 font-normal text-muted">−{lost.toFixed(0)}</span>}
                  </span>
                </div>
                <div className="mt-1 h-2 rounded-full bg-surface-2">
                  <div className="h-2 rounded-full transition-all" style={{ width: `${d.score}%`, background: bandColor(d.score) }} />
                </div>
              </div>
            )
          })}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <Stat label="Speech rate" you={p.speech_rate_wpm} ref={b.speech_rate_wpm} unit="wpm" hint="Words per minute including pauses" />
        <Stat label="Pitch variability" you={p.pitch_sd_st} ref={b.pitch_sd_st} unit="st" hint="Standard deviation of F0 in semitones (speaker-normalised)" />
        <Stat label="Pauses ≥ 250 ms" you={p.pause_count} ref={b.pause_count} unit="" hint="Number of silent gaps between words" />
        <Stat label="Loudness range" you={p.energy_range_db} ref={b.energy_range_db} unit="dB" hint="95th − 10th percentile of voiced level" />
      </div>
    </div>
  )
}
