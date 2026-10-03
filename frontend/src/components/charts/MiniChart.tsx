import { CartesianGrid, ComposedChart, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { SeriesPoint } from '../../api/tracking'
import { parseApi } from '../../utils/datetime'
import { SERIES, dayLabel, monthName, monthTicks } from '../../utils/tracking'
import { TooltipBox, type TipProps } from './ChartCard'

interface Row {
  t: number
  actual: number | null
  pace: number
  forecast: number | null
}

/** Small multiple: y is "% of the course target" so every course shares one 0 to 120% scale. */
export default function MiniChart({ series, target }: { series: SeriesPoint[]; target: number }) {
  const share = (v: number | null) => (v === null || target === 0 ? null : (100 * v) / target)
  const data: Row[] = series.map((p) => ({
    t: parseApi(p.date).getTime(),
    actual: share(p.actual),
    pace: share(p.target_pace) ?? 0,
    forecast: share(p.forecast_mean),
  }))
  const ticks = monthTicks(data[0].t).filter((_, i) => i % 3 === 0) // Jan, Apr, Jul, Oct
  const pctText = (v: number | null) => (v === null ? '–' : `${Math.round(v)}%`)
  return (
    <div className="h-32">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 4, right: 6, bottom: 0, left: 0 }}>
          <CartesianGrid stroke={SERIES.grid} vertical={false} />
          <XAxis
            dataKey="t" type="number" scale="time" domain={[data[0].t, data[data.length - 1].t]} ticks={ticks}
            tickFormatter={monthName} tick={{ fontSize: 10, fill: SERIES.axis }} tickLine={false}
          />
          <YAxis domain={[0, 120]} ticks={[0, 50, 100]} tickFormatter={(v: number) => `${v}%`} tick={{ fontSize: 10, fill: SERIES.axis }} tickLine={false} axisLine={false} width={34} />
          <Tooltip
            cursor={{ stroke: SERIES.axis, strokeDasharray: '3 3' }}
            content={(props: TipProps) => {
              const row = props.active ? (props.payload?.[0]?.payload as Row | undefined) : undefined
              if (!row) return null
              const rows: [string, string][] = []
              if (row.actual !== null) rows.push(['Actual', pctText(row.actual)])
              rows.push(['Target pace', pctText(row.pace)])
              if (row.forecast !== null) rows.push(['Forecast', pctText(row.forecast)])
              return <TooltipBox title={dayLabel(row.t)} rows={rows} />
            }}
          />
          <ReferenceLine y={100} stroke={SERIES.target} strokeWidth={1} />
          <Line dataKey="pace" stroke={SERIES.pace} strokeWidth={1.25} strokeDasharray="5 3" dot={false} isAnimationActive={false} />
          <Line dataKey="forecast" stroke={SERIES.forecast} strokeWidth={1.75} strokeDasharray="2 3" strokeLinecap="round" dot={false} isAnimationActive={false} />
          <Line dataKey="actual" stroke={SERIES.actual} strokeWidth={2} dot={false} isAnimationActive={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
