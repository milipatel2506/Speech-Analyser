import { Database, FileAudio, Mic, Square, Upload } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { api, type Baseline, type Clip } from '../api'
import { FLAW_NAMES, fmtTime } from '../lib/severity'

type Props = {
  baselines: Baseline[]
  busy: boolean
  run: (label: string, job: () => Promise<import('../api').Report>) => void
}

const LEVEL_NAMES = ['', 'Near-perfect', 'Minor slips', 'Uneven', 'Poor', 'Botched']

function Tab({ on, onClick, icon, children }: { on: boolean; onClick: () => void; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className={`inline-flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition ${on ? 'bg-surface text-ink shadow-sm ring-1 ring-line' : 'text-ink-2 hover:text-ink'}`}
    >
      {icon}
      {children}
    </button>
  )
}

function SpeechPicker({ baselines, value, onChange }: { baselines: Baseline[]; value: string; onChange: (id: string) => void }) {
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-6">
      {baselines.map((b) => (
        <button
          key={b.id}
          onClick={() => onChange(b.id)}
          className={`rounded-xl border px-3 py-2.5 text-left transition ${value === b.id ? 'border-accent bg-accent-soft' : 'border-line hover:bg-surface-2'}`}
        >
          <div className="truncate text-sm font-medium">{b.speaker}</div>
          <div className="truncate text-xs text-muted">
            {b.year} · {b.duration.toFixed(0)} s
          </div>
        </button>
      ))}
    </div>
  )
}

function DatasetExplorer({ baselines, busy, run }: Props) {
  const [sid, setSid] = useState(baselines[0]?.id ?? '')
  const [clips, setClips] = useState<Clip[]>([])
  const [active, setActive] = useState<string>('')

  useEffect(() => {
    if (sid) api.clips(sid).then(setClips).catch(() => setClips([]))
  }, [sid])

  const pick = (c: Clip) => {
    setActive(c.clip_id)
    run(`${c.clip_id}`, () => api.analyzeClip(c.clip_id))
  }
  const mix = clips.filter((c) => c.kind === 'mix').sort((a, b) => (a.level ?? 0) - (b.level ?? 0))
  const recorded = clips.filter((c) => c.kind === 'self')
  const types = [...new Set(clips.filter((c) => c.kind === 'single').map((c) => c.flaws[0]?.type))].filter(Boolean)
  const baseline = baselines.find((b) => b.id === sid)

  return (
    <div className="space-y-5">
      <SpeechPicker baselines={baselines} value={sid} onChange={setSid} />
      {baseline && (
        <p className="text-xs text-muted">
          {baseline.title} ({baseline.year}) · {baseline.license} ·{' '}
          <a href={baseline.source_url} target="_blank" rel="noreferrer" className="underline">
            source
          </a>
        </p>
      )}

      <div>
        <div className="mb-2 text-sm font-medium">Overall quality gradient</div>
        <div className="flex flex-wrap gap-2">
          {mix.map((c) => (
            <button
              key={c.clip_id}
              disabled={busy}
              onClick={() => pick(c)}
              title={c.flaws.map((f) => `${f.label} (sev ${f.severity}) ${fmtTime(f.start)}`).join('\n')}
              className={`rounded-lg border px-3 py-2 text-left text-sm transition disabled:opacity-50 ${active === c.clip_id ? 'border-accent bg-accent-soft' : 'border-line hover:bg-surface-2'}`}
            >
              <span className="font-semibold">L{c.level}</span> <span className="text-ink-2">{LEVEL_NAMES[c.level ?? 0]}</span>
              <div className="text-xs text-muted">
                {c.flaws.length} flaw{c.flaws.length === 1 ? '' : 's'}
              </div>
            </button>
          ))}
        </div>
      </div>

      {recorded.length > 0 && (
        <div>
          <div className="mb-2 text-sm font-medium">Self-recorded readings (different speakers)</div>
          <div className="flex flex-wrap gap-2">
            {recorded.map((c) => (
              <button
                key={c.clip_id}
                disabled={busy}
                onClick={() => pick(c)}
                className={`rounded-lg border px-3 py-2 text-left text-sm transition disabled:opacity-50 ${active === c.clip_id ? 'border-accent bg-accent-soft' : 'border-line hover:bg-surface-2'}`}
              >
                <span className="font-semibold">{c.speaker}</span> <span className="text-ink-2">take {c.take}</span>
                <div className="text-xs text-muted">{c.take === 'good' ? 'natural reading' : `${c.flaws.length} directed flaws`}</div>
              </button>
            ))}
          </div>
        </div>
      )}

      <div>
        <div className="mb-2 text-sm font-medium">Single-flaw severity ladders</div>
        <div className="overflow-x-auto">
          <table className="text-sm">
            <thead>
              <tr className="text-xs text-muted">
                <th className="pr-4 pb-1 text-left font-normal">Flaw</th>
                {[1, 2, 3, 4, 5].map((s) => (
                  <th key={s} className="px-1 pb-1 font-normal">
                    {s === 1 ? 'Subtle 1' : s === 5 ? '5 Egregious' : s}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {types.map((t) => (
                <tr key={t}>
                  <td className="py-0.5 pr-4 whitespace-nowrap text-ink-2">{FLAW_NAMES[t] ?? t}</td>
                  {[1, 2, 3, 4, 5].map((s) => {
                    const c = clips.find((x) => x.kind === 'single' && x.flaws[0]?.type === t && x.level === s)
                    return (
                      <td key={s} className="px-1 py-0.5 text-center">
                        {c && (
                          <button
                            disabled={busy}
                            onClick={() => pick(c)}
                            aria-label={`${FLAW_NAMES[t]} severity ${s}`}
                            className={`h-7 w-full min-w-10 rounded-md text-xs font-medium transition disabled:opacity-50 ${active === c.clip_id ? 'bg-accent text-white' : 'bg-surface-2 hover:bg-accent-soft'}`}
                          >
                            {s}
                          </button>
                        )}
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

function Recorder({ onBlob }: { onBlob: (b: Blob | null) => void }) {
  const [rec, setRec] = useState<MediaRecorder | null>(null)
  const [secs, setSecs] = useState(0)
  const [url, setUrl] = useState<string | null>(null)
  const timer = useRef<number | undefined>(undefined)

  const start = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false } })
    const mr = new MediaRecorder(stream)
    const chunks: Blob[] = []
    mr.ondataavailable = (e) => chunks.push(e.data)
    mr.onstop = () => {
      stream.getTracks().forEach((t) => t.stop())
      const blob = new Blob(chunks, { type: mr.mimeType })
      setUrl(URL.createObjectURL(blob))
      onBlob(blob)
    }
    mr.start()
    setRec(mr)
    setSecs(0)
    timer.current = window.setInterval(() => setSecs((s) => s + 1), 1000)
  }
  const stop = () => {
    rec?.stop()
    setRec(null)
    window.clearInterval(timer.current)
  }

  return (
    <div className="flex flex-wrap items-center gap-3">
      {rec ? (
        <button onClick={stop} className="inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-white" style={{ background: 'var(--critical)' }}>
          <Square size={14} fill="currentColor" /> Stop · {secs}s
        </button>
      ) : (
        <button onClick={start} className="inline-flex items-center gap-2 rounded-lg border border-line px-3 py-2 text-sm font-medium hover:bg-surface-2">
          <Mic size={15} /> Record
        </button>
      )}
      {url && !rec && <audio src={url} controls className="h-9" />}
    </div>
  )
}

function UploadForm({ baselines, busy, run }: Props) {
  const [sid, setSid] = useState(baselines[0]?.id ?? '')
  const [customRef, setCustomRef] = useState(false)
  const [refFile, setRefFile] = useState<File | null>(null)
  const [refText, setRefText] = useState('')
  const [audio, setAudio] = useState<Blob | null>(null)
  const [text, setText] = useState('')
  const baseline = baselines.find((b) => b.id === sid)

  const submit = () => {
    if (!audio) return
    const form = new FormData()
    form.append('audio', audio, audio instanceof File ? audio.name : 'recording.webm')
    if (customRef) {
      if (refFile) form.append('baseline_audio', refFile)
      form.append('baseline_transcript', refText)
    } else {
      form.append('baseline_id', sid)
    }
    if (text.trim()) form.append('transcript', text.trim())
    run('your delivery', () => api.analyzeUpload(form))
  }
  const ready = audio && (customRef ? refFile && refText.trim() : sid)

  return (
    <div className="space-y-5">
      <div>
        <div className="mb-2 flex items-center justify-between">
          <span className="text-sm font-medium">1 · Reference delivery</span>
          <label className="flex items-center gap-2 text-xs text-ink-2">
            <input type="checkbox" checked={customRef} onChange={(e) => setCustomRef(e.target.checked)} /> Upload my own reference
          </label>
        </div>
        {customRef ? (
          <div className="grid gap-2 sm:grid-cols-2">
            <label className="flex cursor-pointer items-center gap-2 rounded-lg border border-dashed border-line px-3 py-2 text-sm hover:bg-surface-2">
              <FileAudio size={15} /> {refFile ? refFile.name : 'Choose reference audio'}
              <input type="file" accept="audio/*,video/*" className="hidden" onChange={(e) => setRefFile(e.target.files?.[0] ?? null)} />
            </label>
            <textarea value={refText} onChange={(e) => setRefText(e.target.value)} placeholder="Reference transcript" rows={3} className="rounded-lg border border-line bg-surface px-3 py-2 text-sm" />
          </div>
        ) : (
          <>
            <SpeechPicker baselines={baselines} value={sid} onChange={setSid} />
            {baseline && (
              <div className="mt-3 rounded-xl bg-surface-2 p-3">
                <div className="mb-1 flex items-center justify-between gap-3">
                  <span className="text-xs text-ink-2">Read this aloud</span>
                  <audio src={`/api/baselines/${sid}/audio`} controls className="h-8" />
                </div>
                <p className="text-sm leading-relaxed">{baseline.transcript}</p>
              </div>
            )}
          </>
        )}
      </div>

      <div>
        <div className="mb-2 text-sm font-medium">2 · Your delivery</div>
        <div className="flex flex-wrap items-center gap-3">
          <Recorder onBlob={setAudio} />
          <span className="text-xs text-muted">or</span>
          <label className="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-line px-3 py-2 text-sm font-medium hover:bg-surface-2">
            <Upload size={15} /> {audio instanceof File ? audio.name : 'Upload audio'}
            <input type="file" accept="audio/*,video/*" className="hidden" onChange={(e) => setAudio(e.target.files?.[0] ?? null)} />
          </label>
        </div>
        <details className="mt-3 text-sm">
          <summary className="cursor-pointer text-xs text-ink-2">My transcript differs from the reference</summary>
          <textarea value={text} onChange={(e) => setText(e.target.value)} placeholder="Paste what you actually said (optional)" rows={3} className="mt-2 w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm" />
        </details>
      </div>

      <button
        disabled={!ready || busy}
        onClick={submit}
        className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white transition hover:brightness-110 disabled:opacity-40"
      >
        Analyse delivery
      </button>
    </div>
  )
}

export function InputPanel(props: Props) {
  const [tab, setTab] = useState<'dataset' | 'upload'>('dataset')
  return (
    <section className="card p-5">
      <div className="mb-5 inline-flex gap-1 rounded-xl bg-surface-2 p-1">
        <Tab on={tab === 'dataset'} onClick={() => setTab('dataset')} icon={<Database size={15} />}>
          Contrastive dataset
        </Tab>
        <Tab on={tab === 'upload'} onClick={() => setTab('upload')} icon={<Mic size={15} />}>
          Analyse your delivery
        </Tab>
      </div>
      {tab === 'dataset' ? <DatasetExplorer {...props} /> : <UploadForm {...props} />}
    </section>
  )
}
