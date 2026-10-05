import type { ClipFlaw, Flaw } from '../api'
import { usePlayer } from '../lib/player'
import { FLAW_NAMES, fmtTime, sev } from '../lib/severity'

// Two lanes on one timeline: what was injected into the clip vs what the detector found.
export function GroundTruthStrip({ truth, detected, duration }: { truth: ClipFlaw[]; detected: Flaw[]; duration: number }) {
  const { time, seek } = usePlayer()
  const lane = (items: { type: string; severity: number | null; start: number; end: number }[]) =>
    items.map((f, i) => (
      <button
        key={i}
        onClick={() => seek(f.start)}
        title={`${FLAW_NAMES[f.type] ?? f.type} · ${sev(f.severity).label} · ${fmtTime(f.start)}–${fmtTime(f.end)}`}
        className="absolute top-1 bottom-1 flex items-center overflow-hidden rounded-[4px] px-1.5 text-[10px] font-semibold whitespace-nowrap text-ink"
        style={{
          left: `${(f.start / duration) * 100}%`,
          width: `max(6px, ${((f.end - f.start) / duration) * 100}%)`,
          background: `color-mix(in srgb, ${sev(f.severity).color} 35%, var(--surface))`,
        }}
      >
        {FLAW_NAMES[f.type] ?? f.type}
      </button>
    ))

  return (
    <div className="grid grid-cols-[120px_1fr] items-center gap-x-3 gap-y-1.5 text-xs">
      {[
        ['Injected (truth)', truth],
        ['Detected', detected],
      ].map(([label, items]) => (
        <div key={label as string} className="contents">
          <span className="text-ink-2">{label as string}</span>
          <div className="relative h-8 rounded-md bg-surface-2">
            {lane(items as ClipFlaw[])}
            <div className="pointer-events-none absolute top-0 bottom-0 w-px bg-ink" style={{ left: `${(time / duration) * 100}%` }} />
          </div>
        </div>
      ))}
    </div>
  )
}
