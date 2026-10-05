import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from 'react'

// One playhead shared by the waveform, the feature charts, the transcript and the flaw cards.

type Controls = {
  seek: (t: number) => void
  playRange: (a: number, b: number) => void
  toggle: () => void
  pause: () => void
}

type Player = Controls & {
  time: number
  playing: boolean
  setTime: (t: number) => void
  setPlaying: (p: boolean) => void
  register: (c: Controls | null) => void
  playReference: (url: string, a: number, b: number) => void
}

const Ctx = createContext<Player | null>(null)

export function PlayerProvider({ children }: { children: ReactNode }) {
  const [time, setTime] = useState(0)
  const [playing, setPlaying] = useState(false)
  const controls = useRef<Controls | null>(null)
  const refAudio = useRef<HTMLAudioElement | null>(null)

  const register = useCallback((c: Controls | null) => {
    controls.current = c
  }, [])

  const stopReference = useCallback(() => refAudio.current?.pause(), [])

  const playReference = useCallback((url: string, a: number, b: number) => {
    controls.current?.pause()
    let el = refAudio.current
    if (!el || !el.src.endsWith(url)) {
      el?.pause()
      el = new Audio(url)
      refAudio.current = el
    }
    const audio = el
    const stopAt = () => {
      if (audio.currentTime >= b) {
        audio.pause()
        audio.removeEventListener('timeupdate', stopAt)
      }
    }
    audio.addEventListener('timeupdate', stopAt)
    audio.currentTime = Math.max(0, a)
    void audio.play()
  }, [])

  // Stable callbacks: consumers (charts, waveform) must not re-initialise on every playhead tick.
  const seek = useCallback((t: number) => controls.current?.seek(t), [])
  const playRange = useCallback((a: number, b: number) => {
    stopReference()
    controls.current?.playRange(a, b)
  }, [])
  const toggle = useCallback(() => {
    stopReference()
    controls.current?.toggle()
  }, [])
  const pause = useCallback(() => controls.current?.pause(), [])

  const value = useMemo<Player>(
    () => ({ time, playing, setTime, setPlaying, register, playReference, seek, playRange, toggle, pause }),
    [time, playing, register, playReference, seek, playRange, toggle, pause],
  )
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function usePlayer() {
  const p = useContext(Ctx)
  if (!p) throw new Error('usePlayer outside PlayerProvider')
  return p
}
