import { AudioLines, FlaskConical, Loader2 } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { api, type Baseline, type Flaw, type Report } from './api'
import { FeatureCharts } from './components/FeatureCharts'
import { FlawList } from './components/FlawList'
import { GroundTruthStrip } from './components/GroundTruthStrip'
import { InputPanel } from './components/InputPanel'
import { ScoreSummary } from './components/ScoreSummary'
import { StressTest } from './components/StressTest'
import { Transcript } from './components/Transcript'
import { Waveform } from './components/Waveform'
import { PlayerProvider } from './lib/player'

const STAGES = ['Decoding & loudness normalisation', 'Forced alignment (wav2vec2 CTC)', 'Feature extraction (F0, RMS, FFT, HNR)', 'Contrastive comparison & scoring']

function Busy({ label, started }: { label: string; started: number }) {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), 250)
    return () => window.clearInterval(id)
  }, [])
  const secs = (now - started) / 1000
  const stage = Math.min(STAGES.length - 1, Math.floor(secs / 4))
  return (
    <div className="card flex items-center gap-4 p-5">
      <Loader2 className="animate-spin text-accent" size={22} />
      <div>
        <div className="text-sm font-medium">Analysing {label}…</div>
        <div className="text-xs text-muted tnum">
          {STAGES[stage]} · {secs.toFixed(0)} s
        </div>
      </div>
    </div>
  )
}

function Section({ title, sub, children, aside }: { title: string; sub?: string; children: React.ReactNode; aside?: React.ReactNode }) {
  return (
    <section className="card p-5">
      <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <h2 className="text-base font-semibold">{title}</h2>
          {sub && <p className="text-xs text-muted">{sub}</p>}
        </div>
        {aside}
      </div>
      {children}
    </section>
  )
}

function Results({ report }: { report: Report }) {
  const [focus, setFocus] = useState<Flaw | null>(null)
  return (
    <div className="space-y-5">
      <section className="card p-5">
        <ScoreSummary report={report} />
      </section>

      <Section title="Recording" sub="Shaded regions are detected flaws. Click a region to replay it.">
        <Waveform url={report.participant_audio_url} flaws={report.flaws} duration={report.duration} />
        {report.ground_truth && (
          <div className="mt-5 border-t border-line pt-4">
            <GroundTruthStrip truth={report.ground_truth} detected={report.flaws} duration={report.duration} />
          </div>
        )}
      </Section>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)]">
        <Section
          title="Acoustic overlay"
          sub="Your delivery vs the reference, aligned word-by-word onto your timeline"
          aside={
            focus && (
              <button onClick={() => setFocus(null)} className="rounded-lg border border-line px-2.5 py-1 text-xs hover:bg-surface-2">
                Show full clip
              </button>
            )
          }
        >
          <FeatureCharts report={report} focus={focus} />
        </Section>
        <div className="space-y-5">
          <Section title={`Flaw regions (${report.flaws.length})`} sub="Click a card to zoom the charts; expand for the measured evidence">
            <div className="max-h-[620px] overflow-y-auto pr-1">
              <FlawList report={report} focus={focus} setFocus={setFocus} />
            </div>
          </Section>
        </div>
      </div>

      <Section title="Transcript" sub="Forced-aligned words. Underlines mark flaw regions; click a word to jump there.">
        <Transcript report={report} />
      </Section>
    </div>
  )
}

export default function App() {
  const [view, setView] = useState<'analyse' | 'stress'>('analyse')
  const [baselines, setBaselines] = useState<Baseline[]>([])
  const [report, setReport] = useState<Report | null>(null)
  const [busy, setBusy] = useState<{ label: string; started: number } | null>(null)
  const [error, setError] = useState('')
  const resultsRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    api.baselines().then(setBaselines).catch((e) => setError(`Backend unreachable: ${e.message}`))
  }, [])

  const run = useCallback((label: string, job: () => Promise<Report>) => {
    setError('')
    setBusy({ label, started: Date.now() })
    job()
      .then((r) => {
        setReport(r)
        requestAnimationFrame(() => resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
      })
      .catch((e) => setError(e.message ?? String(e)))
      .finally(() => setBusy(null))
  }, [])

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 border-b border-line bg-[color:var(--page)]/85 backdrop-blur">
        <div className="mx-auto flex max-w-[1400px] items-center gap-6 px-4 py-3 sm:px-6">
          <div className="flex items-center gap-2.5">
            <img src="/favicon.svg" alt="" className="h-7 w-7" />
            <div>
              <div className="text-[15px] leading-tight font-semibold">Cadence</div>
              <div className="text-[11px] leading-tight text-muted">Contrastive speech delivery analysis</div>
            </div>
          </div>
          <nav className="ml-auto flex gap-1 text-sm">
            {(
              [
                ['analyse', 'Analyse', <AudioLines size={15} key="a" />],
                ['stress', 'Stress test', <FlaskConical size={15} key="s" />],
              ] as const
            ).map(([k, label, icon]) => (
              <button
                key={k}
                onClick={() => setView(k)}
                className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 font-medium transition ${view === k ? 'bg-accent-soft text-accent' : 'text-ink-2 hover:text-ink'}`}
              >
                {icon}
                {label}
              </button>
            ))}
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-[1400px] space-y-5 px-4 py-6 sm:px-6">
        {error && (
          <div className="card border-l-4 p-4 text-sm" style={{ borderLeftColor: 'var(--critical)' }}>
            {error}
          </div>
        )}
        {view === 'stress' ? (
          <StressTest />
        ) : (
          <PlayerProvider>
            {baselines.length > 0 && <InputPanel baselines={baselines} busy={!!busy} run={run} />}
            {busy && <Busy {...busy} />}
            <div ref={resultsRef} className="scroll-mt-20">
              {report && !busy && <Results key={report.participant_audio_url} report={report} />}
            </div>
          </PlayerProvider>
        )}
      </main>
    </div>
  )
}
