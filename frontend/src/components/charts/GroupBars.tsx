import { Bar, BarChart, CartesianGrid, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { GroupRow } from '../../api/tracking'
import { SERIES } from '../../utils/tracking'
import ChartCard, { TooltipBox, type TipProps } from './ChartCard'

const SMALL_GROUP = 15 // groups with fewer active drivers are drawn lighter so they are not over-read

interface Row extends GroupRow {
  label: string
}

const noShow = (rate: number | null) => (rate === null ? '–' : `${Math.round(rate * 100)}%`)

/** Horizontal bars: completion % of each group, best first. Group size is in the label. */
export default function GroupBars({ title, rows }: { title: string; rows: GroupRow[] }) {
  const data: Row[] = [...rows]
    .sort((a, b) => b.completion_pct - a.completion_pct)
    .map((r) => ({ ...r, label: `${r.group} (n=${r.active_drivers})` }))
  return (
    <ChartCard
      title={title}
      note="Share of each group's active drivers who completed the course. Lighter bars = small groups (under 15 drivers)."
      table={{
        head: ['Group', 'Active drivers', 'Completed', 'Completion', 'No-show rate'],
        rows: data.map((r) => [r.group, r.active_drivers, r.completed, `${r.completion_pct.toFixed(1)}%`, noShow(r.no_show_rate)]),
      }}
    >
      <div style={{ height: Math.max(120, data.length * 30 + 30) }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ top: 0, right: 36, bottom: 0, left: 0 }}>
            <CartesianGrid stroke={SERIES.grid} horizontal={false} />
            <XAxis type="number" domain={[0, 100]} tickFormatter={(v: number) => `${v}%`} tick={{ fontSize: 11, fill: SERIES.axis }} tickLine={false} />
            <YAxis type="category" dataKey="label" width={130} tick={{ fontSize: 11, fill: SERIES.axis }} tickLine={false} axisLine={false} />
            <Tooltip
              cursor={{ fill: '#f1f5f9' }}
              content={(props: TipProps) => {
                const r = props.active ? (props.payload?.[0]?.payload as Row | undefined) : undefined
                if (!r) return null
                return (
                  <TooltipBox
                    title={r.group}
                    rows={[
                      ['Completion', `${r.completion_pct.toFixed(1)}%`],
                      ['Completed / active', `${r.completed} / ${r.active_drivers}`],
                      ['No-show rate', noShow(r.no_show_rate)],
                    ]}
                  />
                )
              }}
            />
            <Bar dataKey="completion_pct" isAnimationActive={false} radius={[0, 3, 3, 0]}>
              {data.map((r) => (
                <Cell key={r.group} fill={SERIES.actual} fillOpacity={r.active_drivers < SMALL_GROUP ? 0.4 : 1} />
              ))}
              <LabelList dataKey="completion_pct" position="right" formatter={(v: unknown) => `${Math.round(Number(v))}%`} style={{ fontSize: 11, fill: SERIES.axis }} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </ChartCard>
  )
}
