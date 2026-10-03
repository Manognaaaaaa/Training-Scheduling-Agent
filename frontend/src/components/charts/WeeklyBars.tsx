import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { WeekBar } from '../../api/tracking'
import { parseApi } from '../../utils/datetime'
import { SERIES, dayLabel, monthName } from '../../utils/tracking'
import ChartCard, { TooltipBox, type TipProps } from './ChartCard'

/** Completions per week (not cumulative). The week still in progress is drawn lighter. */
export default function WeeklyBars({ weeks }: { weeks: WeekBar[] }) {
  // One x tick per month: the first week bar whose month differs from the previous bar.
  const month = (i: number) => parseApi(weeks[i].week_start).getMonth()
  // The first bar is the week containing 1 Jan (it starts in December), so it gets no label of its own.
  const ticks = weeks.filter((_, i) => i > 0 && month(i) !== month(i - 1)).map((w) => w.week_start)
  return (
    <ChartCard
      title="Completions per week"
      note="Attended in each Sunday to Saturday week"
      table={{
        head: ['Week of', 'Attended', 'No-shows'],
        rows: weeks.map((w) => [dayLabel(parseApi(w.week_start).getTime()), w.attended, w.no_shows]),
      }}
    >
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={weeks} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
            <CartesianGrid stroke={SERIES.grid} vertical={false} />
            <XAxis
              dataKey="week_start" ticks={ticks} tickFormatter={(v: string) => monthName(parseApi(v).getTime())}
              tick={{ fontSize: 11, fill: SERIES.axis }} tickLine={false} interval={0}
            />
            <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: SERIES.axis }} tickLine={false} axisLine={false} width={32} />
            <Tooltip
              cursor={{ fill: '#f1f5f9' }}
              content={(props: TipProps) => {
                const w = props.active ? (props.payload?.[0]?.payload as WeekBar | undefined) : undefined
                if (!w) return null
                return (
                  <TooltipBox
                    title={`Week of ${dayLabel(parseApi(w.week_start).getTime())}${w.closed ? '' : ' (in progress)'}`}
                    rows={[['Attended', String(w.attended)], ['No-shows', String(w.no_shows)]]}
                  />
                )
              }}
            />
            <Bar dataKey="attended" isAnimationActive={false} radius={[2, 2, 0, 0]}>
              {weeks.map((w) => (
                <Cell key={w.week_start} fill={SERIES.actual} fillOpacity={w.closed ? 1 : 0.4} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </ChartCard>
  )
}
