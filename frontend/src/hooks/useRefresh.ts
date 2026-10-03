import { useQueryClient } from '@tanstack/react-query'

/**
 * Query keys that go stale after a change. A session change also moves trainer load, driver bookings and
 * the calendar, so the groups deliberately overlap: stale data is worse than one extra fetch.
 */
const GROUPS = {
  drivers: ['drivers', 'driver', 'driver-options', 'unavailability', 'eligible', 'enrollments', 'sessions', 'session', 'calendar', 'sim', 'tracking', 'alerts'],
  trainers: ['trainers', 'all-trainers', 'sessions', 'session', 'calendar', 'tracking', 'alerts'],
  courses: ['courses', 'all-courses', 'sessions', 'session', 'calendar', 'sim', 'tracking', 'alerts'],
  sessions: ['sessions', 'session', 'enrollments', 'eligible', 'calendar', 'trainers', 'driver', 'drivers', 'sim', 'tracking', 'alerts'],
} as const

export type RefreshGroup = keyof typeof GROUPS

/** Returns `refresh('sessions')`, which invalidates every query that could now be out of date. */
export function useRefresh() {
  const qc = useQueryClient()
  return (group: RefreshGroup) =>
    Promise.all(GROUPS[group].map((key) => qc.invalidateQueries({ queryKey: [key] })))
}
