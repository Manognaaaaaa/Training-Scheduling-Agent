import { useQuery } from '@tanstack/react-query'
import { listCourses } from '../api/courses'
import { listTrainers } from '../api/trainers'

/** All courses / trainers for dropdowns (there are only a handful). */
export function useAllCourses() {
  return useQuery({ queryKey: ['all-courses'], queryFn: () => listCourses({ page_size: 200, sort: 'code' }) })
}

export function useAllTrainers() {
  return useQuery({ queryKey: ['all-trainers'], queryFn: () => listTrainers({ page_size: 200, sort: 'name' }) })
}
