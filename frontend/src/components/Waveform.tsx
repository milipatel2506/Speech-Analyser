import { Pause, Play } from 'lucide-react'
import { useEffect, useRef } from 'react'
import WaveSurfer from 'wavesurfer.js'
import RegionsPlugin from 'wavesurfer.js/dist/plugins/regions.esm.js'
import type { Flaw } from '../api'
import { usePlayer } from '../lib/player'
import { FLAW_NAMES, fmtTime, sev } from '../lib/severity'

const cssVar = (name: string) => getComputedStyle(document.documentElement).getPropertyValue(name).trim()

function withAlpha(hex: string, alpha: number) {
  const n = parseInt(hex.slice(1), 16)
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${alpha})`
}

export function Waveform({ url, flaws, duration }: { url: string; flaws: Flaw[]; duration: number }) {
  const el = useRef<HTMLDivElement>(null)
  const { register, setTime, setPlaying, playing, toggle, time } = usePlayer()

  useEffect(() => {
    if (!el.current) return
    const regions = RegionsPlugin.create()
    const ws = WaveSurfer.create({
      container: el.current,
      url,
      height: 96,
      waveColor: cssVar('--axis') || '#c3c2b7',
      progressColor: cssVar('--series-you') || '#2a78d6',
      cursorColor: cssVar('--ink') || '#0b0b0b',
      cursorWidth: 1,
      barWidth: 2,
      barGap: 1,
      barRadius: 2,
      normalize: true,
      dragToSeek: true,
      plugins: [regions],
    } as ConstructorParameters<typeof WaveSurfer>[0])

    let stopAt: number | null = null
    ws.on('ready', () => {
      for (const f of flaws) {
        const s = sev(f.severity)
        const label = document.createElement('span')
        label.textContent = `${FLAW_NAMES[f.type] ?? f.type} · ${s.label}`
        label.style.cssText =
          'font: 600 10px system-ui; padding: 2px 5px; margin: 2px; border-radius: 4px; background: var(--surface); color: var(--ink); white-space: nowrap; box-shadow: 0 0 0 1px var(--border)'
        regions.addRegion({ start: f.start, end: Math.max(f.end, f.start + 0.05), color: withAlpha(s.hex, 0.22), drag: false, resize: false, content: label })
      }
    })
    ws.on('timeupdate', (t) => {
      setTime(t)
      if (stopAt !== null && t >= stopAt) {
        ws.pause()
        stopAt = null
      }
    })
    ws.on('play', () => setPlaying(true))
    ws.on('pause', () => setPlaying(false))
    ws.on('finish', () => setPlaying(false))
    regions.on('region-clicked', (r, e) => {
      e.stopPropagation()
      stopAt = r.end
      ws.setTime(r.start)
      void ws.play()
    })

    register({
      seek: (t) => ws.setTime(t),
      playRange: (a, b) => {
        stopAt = b
        ws.setTime(a)
        void ws.play()
      },
      toggle: () => void ws.playPause(),
      pause: () => ws.pause(),
    })
    return () => {
      register(null)
      ws.destroy()
    }
  }, [url, flaws, register, setTime, setPlaying])

  return (
    <div className="flex items-center gap-4">
      <button
        onClick={toggle}
        aria-label={playing ? 'Pause' : 'Play'}
        className="grid h-12 w-12 shrink-0 place-items-center rounded-full bg-accent text-white shadow-sm transition hover:brightness-110"
      >
        {playing ? <Pause size={20} fill="currentColor" /> : <Play size={20} fill="currentColor" className="ml-0.5" />}
      </button>
      <div className="min-w-0 flex-1">
        <div ref={el} className="w-full" />
        <div className="mt-1 flex justify-between text-xs text-muted tnum">
          <span>{fmtTime(time)}</span>
          <span>{fmtTime(duration)}</span>
        </div>
      </div>
    </div>
  )
}
