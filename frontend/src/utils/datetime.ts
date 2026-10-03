/**
 * The backend stores naive datetimes that mean Dubai local time. Never send `toISOString()`:
 * it converts to UTC and shifts every session by 4 hours. Always use `toApiDateTime`.
 */

const pad = (n: number) => String(n).padStart(2, '0')

/** Date -> 'YYYY-MM-DDTHH:mm:ss' in LOCAL time (no timezone suffix). */
export function toApiDateTime(date: Date): string {
  return (
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}` +
    `T${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
  )
}

/** 'YYYY-MM-DD' in local time. */
export function toDateOnly(date: Date): string {
  return toApiDateTime(date).slice(0, 10)
}

/** Value for an <input type="datetime-local"> ('YYYY-MM-DDTHH:mm'). */
export function toInputDateTime(date: Date): string {
  return toApiDateTime(date).slice(0, 16)
}

/** Parse an API datetime (naive, so the browser reads it as local time). */
export function parseApi(value: string): Date {
  return new Date(value)
}

/** Build a Date from a date input ('2026-03-01') and a time ('09:00'). */
export function combineDateTime(dateStr: string, timeStr: string): Date {
  const [y, m, d] = dateStr.split('-').map(Number)
  const [hh, mm] = timeStr.split(':').map(Number)
  return new Date(y, m - 1, d, hh, mm, 0)
}

export function fmtDateTime(value: string): string {
  return parseApi(value).toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' })
}

export function fmtDate(value: string): string {
  return parseApi(value).toLocaleDateString('en-GB', { dateStyle: 'medium' })
}

export function fmtTime(value: string): string {
  return parseApi(value).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })
}
