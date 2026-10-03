import { apiFetch, json, qs, type ListParams, type Page } from './client'

export interface Trainer {
  id: number
  name: string
  max_sessions_per_week: number
  sessions_this_week: number
  warnings: string[]
}

export interface TrainerInput {
  name: string
  max_sessions_per_week: number
}

export const listTrainers = (f: ListParams & { q?: string }) => apiFetch<Page<Trainer>>(`/trainers${qs({ ...f })}`)
export const createTrainer = (body: TrainerInput) => apiFetch<Trainer>('/trainers', json('POST', body))
export const updateTrainer = (id: number, body: Partial<TrainerInput>) =>
  apiFetch<Trainer>(`/trainers/${id}`, json('PATCH', body))
export const deleteTrainer = (id: number) => apiFetch<void>(`/trainers/${id}`, json('DELETE'))
