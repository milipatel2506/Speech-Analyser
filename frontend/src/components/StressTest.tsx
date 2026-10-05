import { useEffect, useState } from 'react'
import { api, type Evaluation } from '../api'
import { FLAW_NAMES } from '../lib/severity'

// Sequential single-hue ramp (blue) for recall: magnitude, not state.
const RAMP = ['#cde2fb', '#9ec5f4', '#6da7ec', '#3987e5', '#256abf', '#184f95']
const cellColor = (v: number) => RAMP[Math.min(RAMP.length - 1, Math.floor(v * (RAMP.length - 1) + 1e-9))]
const inkOn = (v: number) => (v >= 0.6 ? '#ffffff' : '#0b0b0b')

function Tile({ label, value, sub }: { label: string; value: string; sub: string }) {
  return (
    <div className="card p-4">
      <div className="text-xs text-ink-2">{label}</div>
      <div className="mt-1 text-3xl font-semibold tracking-tight">{value}</div>
      <div className="mt-0.5 text-xs text-muted">{sub}</div>
    </div>
  )
}

export function StressTest() {
  const [ev, setEv] = useState<Evaluation | null>(null)
  const [err, setErr] = useState('')
  useEffect(() => {
    api.evaluation().then(setEv).catch((e) => setErr(String(e.message ?? e)))
  }, [])

  if (err) return <div className="card p-6 text-sm text-ink-2">No evaluation results yet ({err}). Run <code>uv run python scripts/evaluate.py</code>.</div>
  if (!ev) return <div className="card p-6 text-sm text-muted">Loading evaluation…</div>
  const o = ev.overall
  const types = Object.keys(ev.by_type)

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        <Tile label="Detection recall" value={`${((o.recall ?? 0) * 100).toFixed(0)}%`} sub={`${o.n} injected flaws`} />
        <Tile label="Temporal IoU" value={(o.iou ?? 0).toFixed(2)} sub="matched regions vs truth" />
        <Tile label="Boundary error" value={`${(((o.onset_err_ms ?? 0) + (o.offset_err_ms ?? 0)) / 2).toFixed(0)} ms`} sub="mean |onset| and |offset|" />
        <Tile label="False positives" value={ev.false_positives.per_minute.toFixed(2)} sub="per minute of audio" />
        <Tile label="Score vs quality" value={`ρ = ${ev.score_vs_level_spearman.mix?.toFixed(2) ?? '–'}`} sub="Spearman, gradient L1→L5" />
      </div>

      <div className="card p-5">
        <div className="mb-1 text-sm font-medium">Recall by flaw type and injected severity</div>
        <p className="mb-4 text-xs text-muted">
          Full pipeline with independent forced re-alignment of every flawed clip; a detection counts when the type matches and temporal IoU ≥ {ev.settings.iou_threshold}. Baselines:{' '}
          {ev.settings.baselines.join(', ')}.
        </p>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] border-separate text-sm" style={{ borderSpacing: 2 }}>
            <thead>
              <tr className="text-xs text-muted">
                <th className="pb-1 text-left font-normal">Flaw</th>
                {[1, 2, 3, 4, 5].map((s) => (
                  <th key={s} className="pb-1 font-normal">
                    Severity {s}
                  </th>
                ))}
                <th className="pb-1 font-normal">IoU</th>
                <th className="pb-1 font-normal">Onset / offset err</th>
                <th className="pb-1 font-normal">Severity MAE</th>
              </tr>
            </thead>
            <tbody className="tnum">
              {types.map((t) => {
                const row = ev.by_type[t]
                const all = row.all
                return (
                  <tr key={t}>
                    <td className="pr-3 whitespace-nowrap text-ink-2">{FLAW_NAMES[t] ?? t}</td>
                    {[1, 2, 3, 4, 5].map((s) => {
                      const r = row[String(s)]?.recall
                      return (
                        <td key={s} className="h-9 rounded-[4px] text-center text-xs font-medium" style={r == null ? { background: 'var(--surface-2)' } : { background: cellColor(r), color: inkOn(r) }} title={`${row[String(s)]?.n ?? 0} clips`}>
                          {r == null ? '–' : `${Math.round(r * 100)}%`}
                        </td>
                      )
                    })}
                    <td className="text-center text-xs">{all.iou?.toFixed(2) ?? '–'}</td>
                    <td className="text-center text-xs">
                      {all.onset_err_ms?.toFixed(0) ?? '–'} / {all.offset_err_ms?.toFixed(0) ?? '–'} ms
                    </td>
                    <td className="text-center text-xs">{all.severity_mae?.toFixed(2) ?? '–'}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
        <div className="mt-4 flex items-center gap-2 text-xs text-muted">
          <span>0%</span>
          <div className="flex">
            {RAMP.map((c) => (
              <span key={c} className="h-2.5 w-8" style={{ background: c }} />
            ))}
          </div>
          <span>100% recall</span>
        </div>
      </div>
    </div>
  )
}
