import { apiFetch } from './client'

export type RiskLevel = 'high' | 'medium' | 'low' | 'achieved' | 'insufficient_data'
export type ShortfallType = 'capacity_gap' | 'attendance_gap' | 'pool_gap' | 'none'

export interface Reason {
  code: string
  message: string
  value: number
  benchmark: number
  impact: number
  group: string | null
  by: string | null
}

export interface CourseRow {
  course_id: number
  code: string
  name: string
  is_mandatory: boolean
  target: number
  attended: number
  target_pace: number
  pace_gap: number
  p_show: number
  p_fill: number
  remaining_sessions: number
  remaining_seats: number
  eligible_pool: number
  projected: number
  low: number
  high: number
  p_hit: number
  naive_projection: number
  linear_projection: number
  risk_level: RiskLevel
  shortfall_type: ShortfallType
  seats_needed: number
  weeks_observed: number
  reasons: Reason[]
  open_alert_id: number | null
}

export interface TrackingSummary {
  current_time: string
  percent_year_elapsed: number
  has_data: boolean
  total_attended: number
  total_target: number
  mandatory_compliance_pct: number
  risk_counts: Record<RiskLevel, number>
  open_alerts: number
}

export interface SeriesPoint {
  date: string
  target_pace: number
  actual: number | null
  forecast_mean: number | null
  forecast_low: number | null
  forecast_high: number | null
  is_now: boolean
}

export interface WeekBar {
  week_start: string
  attended: number
  no_shows: number
  closed: boolean
}

export interface Snapshot {
  as_of: string
  attended: number
  projected: number
  low: number
  high: number
  p_hit: number
  naive_projection: number
  risk_level: RiskLevel
}

export interface GroupRow {
  group: string
  active_drivers: number
  completed: number
  completion_pct: number
  no_show_rate: number | null
}

export interface CourseEvent {
  date: string
  kind: string
  label: string
}

export interface UpcomingSession {
  id: number
  start_time: string
  capacity: number
  booked: number
  fill_rate: number | null
  fill_band: 'low' | 'medium' | 'high' | 'cancelled'
}

export interface CourseDetail {
  course: CourseRow
  series: SeriesPoint[]
  weekly: WeekBar[]
  snapshots: Snapshot[]
  breakdown: { shift: GroupRow[]; nationality: GroupRow[] }
  events: CourseEvent[]
  upcoming_sessions: UpcomingSession[]
}

export interface RecomputeResult {
  as_of: string
  snapshots: number
  alerts_opened: number
  alerts_escalated: number
  alerts_deescalated: number
  alerts_resolved: number
}

export const getTrackingSummary = () => apiFetch<TrackingSummary>('/tracking/summary')
export const getTrackingCourses = () => apiFetch<CourseRow[]>('/tracking/courses')
export const getTrackingSeries = () => apiFetch<Record<string, SeriesPoint[]>>('/tracking/series')
export const getCourseDetail = (id: number) => apiFetch<CourseDetail>(`/tracking/courses/${id}`)
export const recomputeTracking = () => apiFetch<RecomputeResult>('/tracking/recompute', { method: 'POST' })
