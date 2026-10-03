import type { CourseRow, RiskLevel, ShortfallType } from '../api/tracking'

export const RISK_LABEL: Record<RiskLevel, string> = {
  high: 'High risk',
  medium: 'Medium risk',
  low: 'On track',
  achieved: 'Achieved',
  insufficient_data: 'Not enough data',
}

/** Icon + text, so risk is never shown by colour alone. */
export const RISK_ICON: Record<RiskLevel, string> = {
  high: '▲',
  medium: '◆',
  low: '●',
  achieved: '✓',
  insufficient_data: '…',
}

export const SHORTFALL_LABEL: Record<ShortfallType, string> = {
  capacity_gap: 'Capacity',
  attendance_gap: 'Attendance',
  pool_gap: 'Eligible pool',
  none: '–',
}

/** One plain sentence for the course header. */
export function shortfallSentence(course: CourseRow): string {
  switch (course.shortfall_type) {
    case 'capacity_gap':
      return "Capacity problem: even full sessions can't reach target. Adding sessions is the likely fix."
    case 'attendance_gap':
      return "Attendance problem: enough seats exist, but low fill or no-shows mean they won't convert. Filling empty seats or moving drivers to better slots is the likely fix."
    case 'pool_gap':
      return 'Eligible-pool problem: fewer drivers still need this course than the target requires. Reviewing the target is the likely fix, not scheduling.'
    default:
      if (course.risk_level === 'achieved') return 'Target reached.'
      if (course.risk_level === 'insufficient_data') return 'Not enough weeks of data yet to judge this course.'
      return 'On track: no shortfall expected at the current pace.'
  }
}

/** Series colours. Risk colours (red, amber, green, teal) are reserved for risk badges, never used here. */
export const SERIES = {
  actual: '#6d28d9',
  forecast: '#6d28d9',
  band: '#6d28d9',
  pace: '#94a3b8',
  target: '#475569',
  grid: '#e2e8f0',
  axis: '#64748b',
  event: '#0f172a',
}

export const pct = (value: number, digits = 0) => `${value.toFixed(digits)}%`

/** P(hit) as a percentage that never shows a misleading 0% or 100%. */
export function fmtProb(p: number): string {
  if (p < 0.01) return '<1%'
  if (p > 0.99) return '>99%'
  return `${Math.round(p * 100)}%`
}

export const fmtRange = (c: Pick<CourseRow, 'projected' | 'low' | 'high'>) =>
  `${Math.round(c.projected)} (${Math.round(c.low)} to ${Math.round(c.high)})`

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
export const monthName = (ms: number) => MONTHS[new Date(ms).getMonth()]

/** Millisecond timestamps of the 1st of every month of the year containing ``ms``. */
export function monthTicks(ms: number): number[] {
  const year = new Date(ms).getFullYear()
  return MONTHS.map((_, m) => new Date(year, m, 1).getTime())
}

/** 'Mar 14' for tooltips. */
export const dayLabel = (ms: number) => {
  const d = new Date(ms)
  return `${MONTHS[d.getMonth()]} ${d.getDate()}`
}
