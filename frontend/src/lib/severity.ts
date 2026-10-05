// Severity is a *state*, so it uses the reserved status palette and always ships with an icon + label.

export const SEVERITY = {
  1: { label: 'Minor', color: 'var(--warning)', hex: '#fab219' },
  2: { label: 'Mild', color: 'var(--warning)', hex: '#fab219' },
  3: { label: 'Moderate', color: 'var(--serious)', hex: '#ec835a' },
  4: { label: 'Severe', color: 'var(--critical)', hex: '#d03b3b' },
  5: { label: 'Critical', color: 'var(--critical)', hex: '#d03b3b' },
} as const

export type Sev = keyof typeof SEVERITY

const PERFORMED = { label: 'Performed', color: 'var(--serious)', hex: '#ec835a' } as const

/** Severity style; null = a human-performed flaw whose physical size was not controlled. */
export const sev = (s: number | null) => (s == null ? PERFORMED : SEVERITY[Math.min(5, Math.max(1, Math.round(s))) as Sev])

export const FLAW_NAMES: Record<string, string> = {
  monotone: 'Monotone',
  rushing: 'Rushing',
  dragging: 'Dragging',
  long_pause: 'Awkward pause',
  pause_removal: 'Missing pause',
  volume_drop: 'Volume drop',
  mumble: 'Mumbling',
}

export const fmtTime = (t: number) => {
  const m = Math.floor(t / 60)
  const s = t - m * 60
  return `${m}:${s.toFixed(1).padStart(4, '0')}`
}

export const bandColor = (score: number) =>
  score >= 90 ? 'var(--good)' : score >= 75 ? 'var(--accent)' : score >= 60 ? 'var(--warning)' : score >= 40 ? 'var(--serious)' : 'var(--critical)'

export function iou(a: { start: number; end: number }, b: { start: number; end: number }) {
  const inter = Math.max(0, Math.min(a.end, b.end) - Math.max(a.start, b.start))
  const union = Math.max(a.end, b.end) - Math.min(a.start, b.start)
  return union > 0 ? inter / union : 0
}
