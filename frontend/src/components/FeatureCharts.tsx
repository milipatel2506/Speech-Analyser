import { LineChart } from 'echarts/charts'
import {
  AxisPointerComponent,
  DataZoomInsideComponent,
  GridComponent,
  MarkAreaComponent,
  MarkLineComponent,
  TitleComponent,
  TooltipComponent,
} from 'echarts/components'
import * as echarts from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { useEffect, useMemo, useRef, useState } from 'react'

echarts.use([
  LineChart,
  GridComponent,
  TitleComponent,
  TooltipComponent,
  AxisPointerComponent,
  DataZoomInsideComponent,
  MarkAreaComponent,
  MarkLineComponent,
  CanvasRenderer,
])
import type { Flaw, Report } from '../api'
import { usePlayer } from '../lib/player'
import { FLAW_NAMES, sev } from '../lib/severity'

// Three small multiples sharing one time axis (never a dual-axis chart). Each compares the
// participant ("You") with the reference delivery time-warped onto the participant's timeline.

const PANELS = [
  { key: 'f0_st', title: 'Pitch', unit: 'st', sub: 'semitones relative to each speaker’s median F0', related: ['monotone'], min: -12, max: 12 },
  { key: 'energy_db', title: 'Loudness', unit: 'dB', sub: 'RMS level relative to each speaker’s typical voiced level', related: ['volume_drop'], min: -40, max: 12 },
  { key: 'hf_db', title: 'Articulation', unit: 'dB', sub: '2–8 kHz vs 0–2 kHz spectral balance (consonant crispness)', related: ['mumble'], min: -40, max: 10 },
] as const

const PANEL_H = 118
const TOP = 34
const GAP = 58

function themeColors() {
  const s = getComputedStyle(document.documentElement)
  const v = (n: string) => s.getPropertyValue(n).trim()
  return { you: v('--series-you'), ref: v('--series-ref'), ink: v('--ink'), ink2: v('--ink-2'), muted: v('--muted'), grid: v('--grid'), axis: v('--axis'), surface: v('--surface') }
}

function useColorScheme() {
  const [scheme, setScheme] = useState(() => matchMedia('(prefers-color-scheme: dark)').matches)
  useEffect(() => {
    const mq = matchMedia('(prefers-color-scheme: dark)')
    const on = () => setScheme(mq.matches)
    mq.addEventListener('change', on)
    return () => mq.removeEventListener('change', on)
  }, [])
  return scheme
}

export function FeatureCharts({ report, focus }: { report: Report; focus: Flaw | null }) {
  const el = useRef<HTMLDivElement>(null)
  const chart = useRef<echarts.ECharts | null>(null)
  const { time, seek } = usePlayer()
  const dark = useColorScheme()

  const option = useMemo(() => {
    const c = themeColors()
    const { t, participant, baseline } = report.overlay
    const pair = (arr: (number | null)[]) => t.map((x, i) => [x, arr[i]])
    const dur = report.duration
    const grids = PANELS.map((_, i) => ({ left: 52, right: 20, top: TOP + i * (PANEL_H + GAP), height: PANEL_H }))

    const areas = (related: readonly string[]) =>
      report.flaws.map((f) => {
        const s = sev(f.severity)
        const on = related.includes(f.type)
        return [
          {
            xAxis: f.start,
            itemStyle: { color: s.hex, opacity: on ? 0.22 : 0.08 },
            label: on ? { show: true, position: 'insideTop', formatter: FLAW_NAMES[f.type], color: c.ink2, fontSize: 10, fontWeight: 600 } : { show: false },
          },
          { xAxis: Math.max(f.end, f.start + 0.05) },
        ]
      })

    return {
      animation: false,
      backgroundColor: 'transparent',
      textStyle: { fontFamily: 'system-ui, -apple-system, Segoe UI, sans-serif' },
      axisPointer: { link: [{ xAxisIndex: 'all' }], lineStyle: { color: c.muted, width: 1 } },
      title: PANELS.map((p, i) => ({
        text: p.title,
        subtext: p.sub,
        left: 52,
        top: grids[i].top - 30,
        itemGap: 2,
        textStyle: { fontSize: 13, fontWeight: 600, color: c.ink },
        subtextStyle: { fontSize: 11, color: c.muted },
      })),
      grid: grids,
      tooltip: {
        trigger: 'axis',
        backgroundColor: c.surface,
        borderColor: c.axis,
        textStyle: { color: c.ink, fontSize: 12 },
        valueFormatter: (v: unknown) => (typeof v === 'number' ? v.toFixed(1) : '–'),
      },
      xAxis: PANELS.map((_, i) => ({
        type: 'value',
        gridIndex: i,
        min: 0,
        max: dur,
        axisLine: { lineStyle: { color: c.axis } },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { color: c.muted, fontSize: 11, formatter: (v: number) => `${Number.isInteger(v) ? v : v.toFixed(1)}s` },
      })),
      yAxis: PANELS.map((p, i) => ({
        type: 'value',
        gridIndex: i,
        min: p.min,
        max: p.max,
        splitNumber: 3,
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { lineStyle: { color: c.grid, width: 1 } },
        axisLabel: { color: c.muted, fontSize: 11, formatter: `{value}` },
        name: p.unit,
        nameTextStyle: { color: c.muted, fontSize: 11, align: 'right' },
      })),
      dataZoom: [{ type: 'inside', xAxisIndex: [0, 1, 2], filterMode: 'none' }],
      series: PANELS.flatMap((p, i) => [
        {
          name: 'Reference',
          type: 'line',
          xAxisIndex: i,
          yAxisIndex: i,
          data: pair(baseline[p.key]),
          showSymbol: false,
          connectNulls: false,
          lineStyle: { width: 1.5, color: c.ref },
          itemStyle: { color: c.ref },
          z: 2,
        },
        {
          id: `you${i}`,
          name: 'You',
          type: 'line',
          xAxisIndex: i,
          yAxisIndex: i,
          data: pair(participant[p.key]),
          showSymbol: false,
          connectNulls: false,
          lineStyle: { width: 2, color: c.you, cap: 'round', join: 'round' },
          itemStyle: { color: c.you },
          z: 3,
          markArea: { silent: true, data: areas(p.related) },
          markLine: { silent: true, symbol: 'none', animation: false, label: { show: false }, lineStyle: { color: c.ink, width: 1, type: 'solid' }, data: [{ xAxis: 0 }] },
        },
      ]),
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [report, dark])

  useEffect(() => {
    if (!el.current) return
    const ch = echarts.init(el.current, undefined, { renderer: 'canvas' })
    chart.current = ch
    const ro = new ResizeObserver(() => ch.resize())
    ro.observe(el.current)
    ch.getZr().on('click', (e) => {
      const pt = [e.offsetX, e.offsetY]
      for (let i = 0; i < PANELS.length; i++) {
        if (ch.containPixel({ gridIndex: i }, pt)) {
          const [x] = ch.convertFromPixel({ gridIndex: i }, pt) as number[]
          seek(Math.max(0, x))
          return
        }
      }
    })
    return () => {
      ro.disconnect()
      ch.dispose()
      chart.current = null
    }
  }, [seek])

  useEffect(() => {
    chart.current?.setOption(option as Parameters<echarts.ECharts["setOption"]>[0], true)
  }, [option])

  useEffect(() => {
    chart.current?.setOption({ series: PANELS.map((_, i) => ({ id: `you${i}`, markLine: { data: [{ xAxis: time }] } })) })
  }, [time])

  useEffect(() => {
    if (!chart.current) return
    if (focus) {
      const pad = Math.max(1.5, (focus.end - focus.start) * 0.6)
      chart.current.dispatchAction({ type: 'dataZoom', startValue: Math.max(0, focus.start - pad), endValue: Math.min(report.duration, focus.end + pad) })
    } else {
      chart.current.dispatchAction({ type: 'dataZoom', start: 0, end: 100 })
    }
  }, [focus, report.duration])

  return (
    <div>
      <div className="mb-1 flex items-center justify-end gap-5 text-xs text-ink-2">
        <span className="flex items-center gap-2">
          <span className="inline-block h-0.5 w-5 rounded" style={{ background: 'var(--series-you)' }} /> You
        </span>
        <span className="flex items-center gap-2">
          <span className="inline-block h-0.5 w-5 rounded" style={{ background: 'var(--series-ref)' }} /> Reference (time-aligned)
        </span>
      </div>
      <div ref={el} style={{ height: TOP + PANELS.length * (PANEL_H + GAP) - GAP + 30 }} className="w-full cursor-crosshair" />
      <p className="mt-1 text-xs text-muted">Scroll to zoom, click to jump the playhead. Shaded spans are detected flaws; the chart they belong to shows them darker.</p>
    </div>
  )
}
