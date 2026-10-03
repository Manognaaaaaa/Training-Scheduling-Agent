import { Area, CartesianGrid, ComposedChart, Legend, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { CourseEvent, Snapshot } from '../../api/tracking'
import { parseApi } from '../../utils/datetime'
import { SERIES, dayLabel, monthName, monthTicks } from '../../utils/tracking'
import ChartCard, { TooltipBox, type TipProps } from './ChartCard'

interface Row {
  t: number
  projected: number
  band: [number, number]
}

/** How the year-end projection moved week by week, so you can see the forecast react to events. */
export default function ForecastHistory({ snapshots, target, events }: { snapshots: Snapshot[]; target: number; events: CourseEvent[] }) {
  const data: Row[] = snapshots.map((s) => ({ t: parseApi(s.as_of).getTime(), projected: s.projected, band: [s.low, s.high] }))
  if (data.length === 0) {
    return (
      <ChartCard title="Forecast history" table={{ head: ['Week'], rows: [] }}>
        <p className="py-10 text-center text-sm text-slate-500">No weekly snapshots yet. Advance the simulation past a Saturday.</p>
      </ChartCard>
    )
  }
  const yMax = Math.ceil((Math.max(target, ...data.map((r) => r.band[1])) * 1.08) / 10) * 10
  const yMin = Math.floor((Math.min(target, ...data.map((r) => r.band[0])) * 0.9) / 10) * 10
  const ticks = monthTicks(data[0].t)
  return (
    <ChartCard
      title="Forecast history"
      note="Projected year-end completions as of each week-end, with the 90% range"
      table={{
        head: ['As of', 'Attended', 'Projected', 'Range low', 'Range high', 'P(hit)'],
        rows: snapshots.map((s) => [
          dayLabel(parseApi(s.as_of).getTime()), s.attended, Math.round(s.projected), Math.round(s.low), Math.round(s.high),
          `${Math.round(s.p_hit * 100)}%`,
        ]),
      }}
    >
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 16, right: 24, bottom: 0, left: 0 }}>
            <CartesianGrid stroke={SERIES.grid} vertical={false} />
            <XAxis
              dataKey="t" type="number" scale="time" domain={[ticks[0], ticks[11] + 30 * 86_400_000]} ticks={ticks}
              tickFormatter={monthName} tick={{ fontSize: 11, fill: SERIES.axis }} tickLine={false}
            />
            <YAxis domain={[yMin, yMax]} tick={{ fontSize: 11, fill: SERIES.axis }} tickLine={false} axisLine={false} width={40} />
            <Tooltip
              cursor={{ stroke: SERIES.axis, strokeDasharray: '3 3' }}
              content={(props: TipProps) => {
                const r = props.active ? (props.payload?.[0]?.payload as Row | undefined) : undefined
                if (!r) return null
                return (
                  <TooltipBox
                    title={dayLabel(r.t)}
                    rows={[['Projected', String(Math.round(r.projected))], ['90% range', `${Math.round(r.band[0])} to ${Math.round(r.band[1])}`]]}
                  />
                )
              }}
            />
            <Legend verticalAlign="top" height={28} iconType="plainline" wrapperStyle={{ fontSize: 12 }} />
            <Area dataKey="band" name="90% range" stroke="none" fill={SERIES.band} fillOpacity={0.15} isAnimationActive={false} legendType="square" />
            <Line dataKey="projected" name="Projected year-end" stroke={SERIES.actual} strokeWidth={2} dot={false} isAnimationActive={false} />
            <ReferenceLine y={target} stroke={SERIES.target} label={{ value: `Target ${target}`, position: 'insideTopLeft', fontSize: 11, fill: SERIES.target }} />
            {events.map((e, i) => (
              <ReferenceLine key={i} x={parseApi(e.date).getTime()} stroke={SERIES.event} strokeDasharray="2 3" strokeWidth={1} label={{ value: '◆', position: 'insideTop', fontSize: 10, fill: SERIES.event }} />
            ))}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </ChartCard>
  )
}
