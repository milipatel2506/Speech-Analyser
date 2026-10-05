import { AlertTriangle, ChevronDown, Headphones, Play, Sigma, Target } from 'lucide-react'
import { useState } from 'react'
import type { Flaw, Report } from '../api'
import { usePlayer } from '../lib/player'
import { fmtTime, iou, sev } from '../lib/severity'

function SeverityBadge({ s }: { s: number }) {
  const v = sev(s)
  return (
    <span className="inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[11px] font-semibold" style={{ background: `color-mix(in srgb, ${v.color} 18%, transparent)`, color: 'var(--ink)' }}>
      <AlertTriangle size={12} style={{ color: v.color }} />
      {v.label} · {s}/5
    </span>
  )
}

function FlawCard({ flaw, report, active, onFocus }: { flaw: Flaw; report: Report; active: boolean; onFocus: () => void }) {
  const [open, setOpen] = useState(false)
  const { playRange, playReference } = usePlayer()
  const bw = report.words.baseline
  const [a, b] = flaw.word_span
  const refRange = bw[a] && bw[b] ? [bw[a].start - 0.15, bw[b].end + 0.15] : null
  const gt = report.ground_truth?.find((g) => g.type === flaw.type && iou(g, flaw) > 0)

  return (
    <div
      className={`card overflow-hidden transition ${active ? 'ring-2 ring-accent' : ''}`}
      onClick={onFocus}
    >
      <div className="flex">
        <div className="w-1 shrink-0" style={{ background: sev(flaw.severity).color }} />
        <div className="min-w-0 flex-1 p-4">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-semibold">{flaw.label}</span>
            <SeverityBadge s={flaw.severity} />
            <span className="text-xs text-muted tnum">
              {fmtTime(flaw.start)}–{fmtTime(flaw.end)}
            </span>
            {gt && (
              <span className="inline-flex items-center gap-1 rounded-md bg-surface-2 px-1.5 py-0.5 text-[11px] text-ink-2" title="Overlap with the injected ground-truth flaw">
                <Target size={12} /> matches ground truth · IoU {iou(gt, flaw).toFixed(2)}
              </span>
            )}
          </div>
          <p className="mt-2 text-sm leading-relaxed text-ink">{flaw.what}</p>

          <div className="mt-3 flex flex-wrap gap-2">
            <button onClick={() => playRange(flaw.start - 0.3, flaw.end + 0.3)} className="inline-flex items-center gap-1.5 rounded-lg bg-accent px-2.5 py-1.5 text-xs font-medium text-white hover:brightness-110">
              <Play size={13} fill="currentColor" /> Play yours
            </button>
            {refRange && (
              <button onClick={() => playReference(report.baseline_audio_url, refRange[0], refRange[1])} className="inline-flex items-center gap-1.5 rounded-lg border border-line px-2.5 py-1.5 text-xs font-medium hover:bg-surface-2">
                <Headphones size={13} /> Play reference
              </button>
            )}
            <button onClick={() => setOpen(!open)} className="ml-auto inline-flex items-center gap-1 rounded-lg px-2 py-1.5 text-xs text-ink-2 hover:bg-surface-2">
              Why this was flagged <ChevronDown size={14} className={`transition ${open ? 'rotate-180' : ''}`} />
            </button>
          </div>

          {open && (
            <div className="mt-4 space-y-4 border-t border-line pt-4 text-sm">
              <table className="w-full text-left text-xs">
                <thead className="text-muted">
                  <tr>
                    <th className="pb-1.5 font-normal">Measurement</th>
                    <th className="pb-1.5 font-normal">You</th>
                    <th className="pb-1.5 font-normal">Reference / tolerance</th>
                  </tr>
                </thead>
                <tbody className="tnum">
                  {flaw.evidence.map((e) => (
                    <tr key={e.metric} className="border-t border-line">
                      <td className="py-1.5 pr-3 text-ink-2">{e.metric}</td>
                      <td className="py-1.5 pr-3 font-medium">{e.participant}</td>
                      <td className="py-1.5">{e.reference}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="rounded-lg bg-surface-2 p-3">
                <div className="mb-1 flex items-center gap-1.5 text-xs font-medium text-ink-2">
                  <Sigma size={13} /> Mathematical rationale
                </div>
                <code className="block font-mono text-xs leading-relaxed break-words whitespace-pre-wrap">{flaw.math}</code>
              </div>
              <div>
                <div className="text-xs font-medium text-ink-2">Why it matters</div>
                <p className="mt-0.5 text-ink">{flaw.why}</p>
              </div>
              <div>
                <div className="text-xs font-medium text-ink-2">How to fix it</div>
                <p className="mt-0.5 text-ink">{flaw.tip}</p>
              </div>
              {gt?.description && (
                <div className="text-xs text-muted">
                  Ground truth: {gt.description} ({gt.severity == null ? 'performed' : `severity ${gt.severity}/5`}, {fmtTime(gt.start)}–{fmtTime(gt.end)})
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export function FlawList({ report, focus, setFocus }: { report: Report; focus: Flaw | null; setFocus: (f: Flaw | null) => void }) {
  if (!report.flaws.length) {
    return (
      <div className="card p-6 text-sm text-ink-2">
        No delivery flaws exceeded tolerance. Pace, pausing, pitch movement, loudness and articulation all track the reference.
      </div>
    )
  }
  return (
    <div className="space-y-3">
      {report.flaws.map((f, i) => (
        <FlawCard key={`${f.type}-${f.start}-${i}`} flaw={f} report={report} active={focus === f} onFocus={() => setFocus(f)} />
      ))}
    </div>
  )
}
