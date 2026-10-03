import { apiFetch, json, qs, type ListParams, type Page } from './client'

export interface Driver {
  id: number
  employee_code: string
  name: string
  nationality: string
  shift: 'day' | 'night' | 'rotating'
  depot: string
  hire_date: string
  is_active: boolean
}

export interface DriverInput {
  name: string
  nationality: string
  shift: string
  depot: string
  hire_date: string
  employee_code?: string
  is_active?: boolean
}

export interface DriverBooking {
  enrollment_id: number
  session_id: number
  course_code: string
  course_name: string
  session_start: string
  session_status: string
  status: string
}

export interface DriverDetail extends Driver {
  history: DriverBooking[]
  upcoming: DriverBooking[]
}

export interface DriverOptions {
  nationalities: string[]
  shifts: string[]
  depots: string[]
}

export interface Unavailability {
  id: number
  driver_id: number
  start_time: string
  end_time: string
  reason: string
  cancelled_bookings: number
}

export interface DriverFilters extends ListParams {
  q?: string
  nationality?: string
  shift?: string
  depot?: string
  is_active?: string
}

export const listDrivers = (f: DriverFilters) => apiFetch<Page<Driver>>(`/drivers${qs({ ...f })}`)
export const getDriverOptions = () => apiFetch<DriverOptions>('/drivers/options')
export const getDriver = (id: number) => apiFetch<DriverDetail>(`/drivers/${id}`)
export const createDriver = (body: DriverInput) => apiFetch<Driver>('/drivers', json('POST', body))
export const updateDriver = (id: number, body: Partial<DriverInput>) =>
  apiFetch<Driver>(`/drivers/${id}`, json('PATCH', body))
export const deactivateDriver = (id: number) =>
  apiFetch<Driver & { cancelled_bookings: number }>(`/drivers/${id}`, json('DELETE'))
export const listUnavailability = (id: number) => apiFetch<Unavailability[]>(`/drivers/${id}/unavailability`)
export const addUnavailability = (id: number, body: { start_time: string; end_time: string; reason: string }) =>
  apiFetch<Unavailability>(`/drivers/${id}/unavailability`, json('POST', body))
export const removeUnavailability = (id: number, uid: number) =>
  apiFetch<void>(`/drivers/${id}/unavailability/${uid}`, json('DELETE'))
