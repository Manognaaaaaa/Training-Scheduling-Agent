import type { ReactNode } from 'react'
import type { FillBand } from '../api/sessions'

type Tone = 'slate' | 'green' | 'amber' | 'red' | 'blue' | 'violet' | 'indigo'

const TONES: Record<Tone, string> = {
  slate: 'bg-slate-100 text-slate-700',
  green: 'bg-emerald-100 text-emerald-800',
  amber: 'bg-amber-100 text-amber-800',
  red: 'bg-red-100 text-red-800',
  blue: 'bg-sky-100 text-sky-800',
  violet: 'bg-violet-100 text-violet-800',
  indigo: 'bg-indigo-100 text-indigo-800',
}

export function Badge({ tone = 'slate', children }: { tone?: Tone; children: ReactNode }) {
  return <span className={`inline-block whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ${TONES[tone]}`}>{children}</span>
}

const STATUS_TONE: Record<string, Tone> = {
  scheduled: 'blue',
  completed: 'green',
  cancelled: 'slate',
  booked: 'blue',
  attended: 'green',
  no_show: 'red',
}

/** Session or enrollment status. */
export function StatusBadge({ status }: { status: string }) {
  return <Badge tone={STATUS_TONE[status] ?? 'slate'}>{status.replace('_', ' ')}</Badge>
}

const SHIFT_TONE: Record<string, Tone> = { day: 'amber', night: 'indigo', rotating: 'violet' }

export function ShiftBadge({ shift }: { shift: string }) {
  return <Badge tone={SHIFT_TONE[shift] ?? 'slate'}>{shift}</Badge>
}

const BAND_TONE: Record<FillBand, Tone> = { low: 'red', medium: 'amber', high: 'green', cancelled: 'slate' }

/** Fill band with the percentage, e.g. "low 33%". */
export function FillBadge({ band, rate }: { band: FillBand; rate: number | null }) {
  return (
    <Badge tone={BAND_TONE[band]}>
      {band}
      {rate !== null && ` ${Math.round(rate * 100)}%`}
    </Badge>
  )
}

export function ActiveBadge({ active }: { active: boolean }) {
  return <Badge tone={active ? 'green' : 'slate'}>{active ? 'active' : 'inactive'}</Badge>
}
