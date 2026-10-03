import { useMutation, useQuery } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  getTrackingCourses, getTrackingSeries, getTrackingSummary, recomputeTracking, type CourseRow, type SeriesPoint,
} from '../api/tracking'
import { Badge, MandatoryBadge, RiskBadge } from '../components/Badge'
import ChartCard from '../components/charts/ChartCard'
import MiniChart from '../components/charts/MiniChart'
import { useToast } from '../components/Toast'
import { useRefresh } from '../hooks/useRefresh'
import { fmtDateTime } from '../utils/datetime'
import { SERIES, SHORTFALL_LABEL, fmtProb, fmtRange, pct } from '../utils/tracking'

const head = 'px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-slate-500'
const cell = 'px-3 py-2 text-sm align-top'

function Tile({ label, children, note }: { label: string; children: ReactNode; note?: ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold text-slate-900">{children}</div>
      {note && <div className="mt-1 text-xs text-slate-500">{note}</div>}
    </div>
  )
}

/** attended / target bar with a tick where the target pace is today. */
function ProgressBar({ course }: { course: CourseRow }) {
  const share = (n: number) => Math.min(100, (100 * n) / Math.max(1, course.target))
  return (
    <div className="w-40">
      <div className="relative h-2 rounded-full bg-slate-200" title={`Target pace today: ${Math.round(course.target_pace)}`}>
        <div className="h-2 rounded-full" style={{ width: `${share(course.attended)}%`, backgroundColor: SERIES.actual }} />
        <div className="absolute -top-1 h-4 w-0.5 bg-slate-700" style={{ left: `${share(course.target_pace)}%` }} />
      </div>
      <div className="mt-1 text-xs text-slate-600">
        {course.attended} / {course.target} <span className="text-slate-400">(tick = target pace)</span>
      </div>
    </div>
  )
}

function RiskTable({ courses }: { courses: CourseRow[] }) {
  const navigate = useNavigate()
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
      <table className="min-w-full divide-y divide-slate-200">
        <thead className="bg-slate-50">
          <tr>
            {['Course', 'Progress', 'Pace gap', 'Projected year-end (90% range)', 'P(hit target)', 'Risk', 'Shortfall', 'Main reason'].map((h) => (
              <th key={h} className={head}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {courses.map((c) => (
            <tr key={c.course_id} className="cursor-pointer hover:bg-slate-50" onClick={() => navigate(`/dashboard/courses/${c.course_id}`)}>
              <td className={cell}>
                <Link to={`/dashboard/courses/${c.course_id}`} className="font-medium text-slate-900 hover:underline" onClick={(e) => e.stopPropagation()}>
                  {c.name}
                </Link>
                <div className="mt-1 flex items-center gap-2">
                  <span className="text-xs text-slate-400">{c.code}</span>
                  <MandatoryBadge mandatory={c.is_mandatory} />
                </div>
              </td>
              <td className={cell}>
                <ProgressBar course={c} />
              </td>
              <td className={`${cell} whitespace-nowrap`}>{c.pace_gap > 0 ? '+' : ''}{Math.round(c.pace_gap)}</td>
              <td className={`${cell} whitespace-nowrap`}>{fmtRange(c)}</td>
              <td className={cell}>{fmtProb(c.p_hit)}</td>
              <td className={cell}>
                <RiskBadge level={c.risk_level} />
              </td>
              <td className={cell}>{SHORTFALL_LABEL[c.shortfall_type]}</td>
              <td className={`${cell} max-w-xs text-slate-600`}>{c.reasons[0]?.message ?? '–'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function SmallMultiples({ courses, series }: { courses: CourseRow[]; series: Record<string, SeriesPoint[]> }) {
  const navigate = useNavigate()
  return (
    <ChartCard
      title="Progress by course (% of target)"
      note="Every course on the same 0 to 120% scale. Solid = actual, dashed = target pace, dotted = forecast; the line at 100% is the target."
      table={{
        head: ['Course', 'Now (% of target)', 'Pace today (%)', 'Projected year-end (%)', 'Risk'],
        rows: courses.map((c) => [
          c.name, pct((100 * c.attended) / c.target), pct((100 * c.target_pace) / c.target), pct((100 * c.projected) / c.target), c.risk_level.replace('_', ' '),
        ]),
      }}
    >
      <div className="mb-3 flex flex-wrap gap-4 text-xs text-slate-600">
        <span><span className="inline-block h-0.5 w-6 align-middle" style={{ backgroundColor: SERIES.actual }} /> Actual</span>
        <span><span className="inline-block w-6 border-t-2 border-dashed align-middle" style={{ borderColor: SERIES.pace }} /> Target pace</span>
        <span><span className="inline-block w-6 border-t-2 border-dotted align-middle" style={{ borderColor: SERIES.forecast }} /> Forecast</span>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {courses.map((c) => (
          <div
            key={c.course_id}
            role="link"
            tabIndex={0}
            className="cursor-pointer rounded-lg border border-slate-200 p-3 hover:border-slate-400"
            onClick={() => navigate(`/dashboard/courses/${c.course_id}`)}
            onKeyDown={(e) => e.key === 'Enter' && navigate(`/dashboard/courses/${c.course_id}`)}
          >
            <div className="mb-1 flex items-start justify-between gap-2">
              <div className="text-sm font-medium text-slate-900">{c.name}</div>
              <RiskBadge level={c.risk_level} />
            </div>
            {series[c.course_id] ? <MiniChart series={series[c.course_id]} target={c.target} /> : <div className="h-32" />}
          </div>
        ))}
      </div>
    </ChartCard>
  )
}

export default function Dashboard() {
  const toast = useToast()
  const refresh = useRefresh()
  const summary = useQuery({ queryKey: ['tracking', 'summary'], queryFn: getTrackingSummary })
  const courses = useQuery({ queryKey: ['tracking', 'courses'], queryFn: getTrackingCourses })
  const series = useQuery({ queryKey: ['tracking', 'series'], queryFn: getTrackingSeries })

  const recompute = useMutation({
    mutationFn: recomputeTracking,
    onSuccess: async (r) => {
      toast.success(
        `Recomputed: ${r.alerts_opened} opened, ${r.alerts_escalated} escalated, ${r.alerts_deescalated} de-escalated, ${r.alerts_resolved} resolved`,
      )
      await refresh('sessions')
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const s = summary.data
  const error = summary.error ?? courses.error ?? series.error

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Dashboard</h1>
          <p className="mt-1 text-sm text-slate-600">Which courses will miss their 2026 target, by how much, and why.</p>
        </div>
        <button
          className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          disabled={recompute.isPending}
          onClick={() => recompute.mutate()}
          title="Re-run the forecasts and alert rules now (use after manual edits)"
        >
          {recompute.isPending ? 'Recomputing…' : 'Recompute'}
        </button>
      </div>

      {error && <div className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">{error.message}</div>}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <Tile label="Mandatory compliance" note="Progress toward the targets of mandatory courses">
          {s ? pct(s.mandatory_compliance_pct, 1) : '…'}
        </Tile>
        <Tile
          label="Completions vs target"
          note={s && `${s.percent_year_elapsed.toFixed(0)}% of the year elapsed`}
        >
          {s ? (
            <>
              {s.total_attended} <span className="text-base font-normal text-slate-500">/ {s.total_target}</span>
            </>
          ) : (
            '…'
          )}
        </Tile>
        <Tile label="Courses at risk" note="High and medium risk">
          {s ? (
            <span className="flex flex-col items-start gap-1 text-base">
              <span className="flex items-center gap-2"><RiskBadge level="high" /> {s.risk_counts.high}</span>
              <span className="flex items-center gap-2"><RiskBadge level="medium" /> {s.risk_counts.medium}</span>
            </span>
          ) : (
            '…'
          )}
        </Tile>
        <Tile label="Open alerts" note={<Link to="/alerts" className="underline">View alerts</Link>}>
          {s ? s.open_alerts : '…'}
        </Tile>
        <Tile label="Sim date">{s ? <span className="text-xl">{fmtDateTime(s.current_time)}</span> : '…'}</Tile>
      </div>

      {s && !s.has_data ? (
        <div className="rounded-lg border border-dashed border-slate-300 bg-white p-10 text-center">
          <div className="text-base font-medium text-slate-900">Not enough data yet</div>
          <p className="mt-1 text-sm text-slate-600">No session has been completed, so there is nothing to track or forecast from.</p>
          <Link to="/simulation" className="mt-4 inline-block rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700">
            Advance the simulation
          </Link>
        </div>
      ) : (
        <>
          <section>
            <h2 className="mb-2 flex items-center gap-2 text-lg font-semibold">
              Course risk <Badge>{courses.data?.length ?? 0} courses</Badge>
            </h2>
            {courses.data ? <RiskTable courses={courses.data} /> : <div className="text-sm text-slate-500">Loading…</div>}
          </section>
          {courses.data && series.data && <SmallMultiples courses={courses.data} series={series.data} />}
        </>
      )}
    </div>
  )
}
