import { apiFetch, qs } from './client'
import type { Reason, ShortfallType } from './tracking'

export interface AlertDetails {
  p_hit?: number
  low?: number
  high?: number
  projected?: number
  reasons?: Reason[]
  last_change?: 'opened' | 'escalated' | 'deescalated' | 'auto_resolved'
  last_change_at?: string
  previous_risk?: string | null
}

export interface Alert {
  id: number
  course_id: number
  course_code: string
  course_name: string
  created_at: string
  updated_at: string | null
  risk_level: string
  shortfall_type: ShortfallType | null
  projected_completions: number
  target_completions: number
  message: string | null
  status: 'open' | 'resolved' | 'dismissed'
  details: AlertDetails
}

export const listAlerts = (params: { status?: Alert['status']; course_id?: number; since?: string } = {}) =>
  apiFetch<Alert[]>(`/alerts${qs(params)}`)
