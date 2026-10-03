import { apiFetch, json, qs, type ListParams, type Page } from './client'

export interface Course {
  id: number
  code: string
  name: string
  duration_hours: number
  default_capacity: number
  is_mandatory: boolean
  target_completions: number | null
}

export interface CourseInput {
  code: string
  name: string
  duration_hours: number
  default_capacity: number
  is_mandatory: boolean
  target_completions: number | null
}

export const listCourses = (f: ListParams & { q?: string }) => apiFetch<Page<Course>>(`/courses${qs({ ...f })}`)
export const createCourse = (body: CourseInput) => apiFetch<Course>('/courses', json('POST', body))
export const updateCourse = (id: number, body: Partial<CourseInput>) =>
  apiFetch<Course>(`/courses/${id}`, json('PATCH', body))
export const deleteCourse = (id: number) => apiFetch<void>(`/courses/${id}`, json('DELETE'))
