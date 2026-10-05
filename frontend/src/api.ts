// Typed client for the FastAPI backend (see src/speech_analyser/api/main.py).

export type Word = { word: string; start: number; end: number; score?: number }

export type Baseline = {
  id: string
  speaker: string
  sex: 'M' | 'F'
  title: string
  year: number
  duration: number
  transcript: string
  license: string
  source_url: string
}

export type ClipFlaw = { type: string; label: string; severity: number | null; start: number; end: number }

export type Clip = {
  clip_id: string
  baseline_id: string
  kind: 'single' | 'mix' | 'self'
  level: number | null
  duration: number
  speaker?: string | null
  take?: string | null
  flaws: ClipFlaw[]
}

export type Evidence = { metric: string; participant: string; reference: string }

export type Flaw = {
  type: string
  label: string
  rubric: string
  start: number
  end: number
  word_span: [number, number]
  text: string
  severity: number
  deviation: number
  headline: string
  what: string
  evidence: Evidence[]
  math: string
  why: string
  tip: string
  measured: Record<string, number>
}

export type Deduction = { flaw: string; at: number | null; points: number }
export type Dimension = { label: string; score: number; band: string; deductions: Deduction[] }

export type Summary = {
  duration_s: number
  words: number
  speech_rate_wpm: number
  speech_rate_sps: number
  articulation_rate_sps: number
  pause_count: number
  pause_mean_s: number
  pause_ratio: number
  f0_median_hz: number
  pitch_sd_st: number
  pitch_range_st: number
  energy_range_db: number
  hnr_mean_db: number
  hf_mean_db: number
}

type Track = { f0_hz: (number | null)[]; f0_st: (number | null)[]; energy_db: (number | null)[]; hf_db: (number | null)[] }

export type Report = {
  score: { overall: number; band: string; dimensions: Record<string, Dimension> }
  flaws: Flaw[]
  globals: {
    tempo_ratio: number
    pitch_spread_ratio: number
    level_offset_db: number
    hf_offset_db: number
    matched_words: number
    participant_words: number
    baseline_words: number
  }
  summary: { participant: Summary; baseline: Summary }
  words: { participant: Word[]; baseline: Word[] }
  overlay: { t: number[]; participant: Track; baseline: Track }
  duration: number
  baseline_id: string | null
  participant_audio_url: string
  baseline_audio_url: string
  ground_truth: (ClipFlaw & { description?: string; rubric?: string })[] | null
}

export type EvalCell = {
  n: number
  recall: number | null
  iou: number | null
  onset_err_ms: number | null
  offset_err_ms: number | null
  severity_mae: number | null
}

export type Evaluation = {
  settings: { iou_threshold: number; oracle_alignment: boolean; baselines: string[] }
  overall: EvalCell
  by_type: Record<string, Record<string, EvalCell>>
  false_positives: { count: number; per_minute: number }
  score_vs_level_spearman: { mix: number | null; single: Record<string, number> }
}

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText
    try {
      detail = (await res.json()).detail ?? detail
    } catch {
      /* not JSON */
    }
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

export const api = {
  baselines: () => fetch('/api/baselines').then((r) => json<Baseline[]>(r)),
  clips: (baselineId: string) => fetch(`/api/clips?baseline_id=${baselineId}`).then((r) => json<Clip[]>(r)),
  analyzeClip: (clipId: string) => fetch(`/api/clips/${clipId}/analyze`, { method: 'POST' }).then((r) => json<Report>(r)),
  analyzeUpload: (form: FormData) => fetch('/api/analyze', { method: 'POST', body: form }).then((r) => json<Report>(r)),
  evaluation: () => fetch('/api/evaluation').then((r) => json<Evaluation>(r)),
}
