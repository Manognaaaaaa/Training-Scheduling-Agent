import dayGridPlugin from '@fullcalendar/daygrid'
import type { DatesSetArg, EventContentArg, EventInput } from '@fullcalendar/core'
import interactionPlugin, { type DateClickArg } from '@fullcalendar/interaction'
import FullCalendar from '@fullcalendar/react'
import timeGridPlugin from '@fullcalendar/timegrid'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useMemo, useRef, useState } from 'react'
import { getCalendar, type CalendarEvent } from '../api/sessions'
import { getSimState } from '../api/sim'
import { inputClass } from '../components/FormModal'
import SessionDrawer from '../components/SessionDrawer'
import SessionFormModal from '../components/SessionFormModal'
import { useAllCourses, useAllTrainers } from '../hooks/useLookups'
import { toApiDateTime } from '../utils/datetime'

const LEGEND = [
  { band: 'low', label: 'Low (under 50%)', swatch: 'bg-red-300 border-red-500' },
  { band: 'medium', label: 'Medium (50 to 79%)', swatch: 'bg-amber-300 border-amber-500' },
  { band: 'high', label: 'High (80%+)', swatch: 'bg-emerald-300 border-emerald-600' },
  { band: 'cancelled', label: 'Cancelled', swatch: 'bg-slate-300 border-slate-500' },
]

function eventContent(arg: EventContentArg) {
  const e = arg.event.extendedProps as CalendarEvent
  const count = e.status === 'completed' ? e.attended : e.booked
  return (
    <div className="overflow-hidden px-1 text-xs leading-tight">
      <div className="font-semibold">{e.course_code} · {count}/{e.capacity}</div>
      <div className="truncate">{e.trainer_name}</div>
    </div>
  )
}

function CalendarView({ simNow }: { simNow: string }) {
  const calendarRef = useRef<FullCalendar>(null)
  const [range, setRange] = useState<{ start: string; end: string } | null>(null)
  const [courseId, setCourseId] = useState('')
  const [trainerId, setTrainerId] = useState('')
  const [showCancelled, setShowCancelled] = useState(false)
  const [openId, setOpenId] = useState<number | null>(null)
  const [newStart, setNewStart] = useState<Date | null>(null)
  const courses = useAllCourses().data?.items ?? []
  const trainers = useAllTrainers().data?.items ?? []

  const params = { start: range?.start ?? '', end: range?.end ?? '', course_id: courseId, trainer_id: trainerId, include_cancelled: showCancelled }
  const calendar = useQuery({
    queryKey: ['calendar', params],
    queryFn: () => getCalendar(params),
    enabled: range !== null,
    placeholderData: keepPreviousData,
  })

  const events = useMemo<EventInput[]>(
    () =>
      (calendar.data?.events ?? []).map((e) => ({
        id: String(e.id),
        start: e.start,
        end: e.end,
        classNames: [`fc-band-${e.fill_band}`, e.status === 'completed' ? 'fc-completed' : ''],
        extendedProps: e,
      })),
    [calendar.data],
  )

  function onDatesSet(arg: DatesSetArg) {
    const next = { start: toApiDateTime(arg.start), end: toApiDateTime(arg.end) }
    setRange((prev) => (prev && prev.start === next.start && prev.end === next.end ? prev : next))
  }

  function onDateClick(arg: DateClickArg) {
    if (arg.date <= new Date(simNow)) return // only future slots; the backend still has the final say
    const when = new Date(arg.date)
    if (arg.allDay) when.setHours(9, 0, 0, 0) // month view gives midnight: default to the first slot
    setNewStart(when)
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-3">
        <select className={`${inputClass} !w-52`} value={courseId} onChange={(e) => setCourseId(e.target.value)}>
          <option value="">All courses</option>
          {courses.map((c) => <option key={c.id} value={c.id}>{c.code} · {c.name}</option>)}
        </select>
        <select className={`${inputClass} !w-48`} value={trainerId} onChange={(e) => setTrainerId(e.target.value)}>
          <option value="">All trainers</option>
          {trainers.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
        </select>
        <label className="flex items-center gap-2 pb-2 text-sm">
          <input type="checkbox" checked={showCancelled} onChange={(e) => setShowCancelled(e.target.checked)} /> Show cancelled
        </label>
        <button className="ml-auto rounded-md border border-slate-300 bg-white px-4 py-2 text-sm hover:bg-slate-50" onClick={() => calendarRef.current?.getApi().gotoDate(new Date(simNow))}>
          Go to sim now
        </button>
      </div>

      <div className="flex flex-wrap items-center gap-x-5 gap-y-1 rounded-md bg-white px-4 py-2 text-xs text-slate-600 ring-1 ring-slate-200">
        {LEGEND.map((l) => (
          <span key={l.band} className="flex items-center gap-1.5"><span className={`inline-block h-3 w-3 rounded-sm border ${l.swatch}`} />{l.label}</span>
        ))}
        <span className="flex items-center gap-1.5"><span className="fc-completed inline-block h-3 w-3 rounded-sm border border-slate-400 bg-slate-200" />Striped = completed</span>
        <span className="text-slate-500">Fill rate: scheduled = booked / capacity, completed = attended / capacity.</span>
      </div>
      {calendar.isError && <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{calendar.error.message}</div>}

      <div className="rounded-lg border border-slate-200 bg-white p-3">
        <FullCalendar
          ref={calendarRef}
          plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin]}
          initialView="timeGridWeek"
          initialDate={simNow}
          now={simNow}
          nowIndicator
          timeZone="local"
          firstDay={0}
          slotMinTime="07:00:00"
          slotMaxTime="22:00:00"
          allDaySlot={false}
          height="auto"
          validRange={{ start: '2026-01-01', end: '2027-01-01' }}
          headerToolbar={{ left: 'prev,next', center: 'title', right: 'timeGridWeek,dayGridMonth' }}
          buttonText={{ timeGridWeek: 'Week', dayGridMonth: 'Month' }}
          slotLabelFormat={{ hour: '2-digit', minute: '2-digit', hour12: false }}
          eventTimeFormat={{ hour: '2-digit', minute: '2-digit', hour12: false }}
          events={events}
          eventContent={eventContent}
          eventClick={(arg) => setOpenId(Number(arg.event.id))}
          dateClick={onDateClick}
          datesSet={onDatesSet}
        />
      </div>

      {openId !== null && <SessionDrawer sessionId={openId} onClose={() => setOpenId(null)} />}
      {newStart && <SessionFormModal initialStart={newStart} onClose={() => setNewStart(null)} onSaved={(s) => setOpenId(s.id)} />}
    </div>
  )
}

export default function Calendar() {
  const sim = useQuery({ queryKey: ['sim', 'state'], queryFn: getSimState })
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Calendar</h1>
        <p className="mt-2 text-base text-slate-600">
          Training sessions coloured by fill rate. The now-line shows simulated time
          {sim.data && ` (${new Date(sim.data.current_time).toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' })})`}.
          Click a session to manage it, or an empty future slot to add one.
        </p>
      </div>
      {sim.isError && <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{sim.error.message}</div>}
      {sim.data ? <CalendarView simNow={sim.data.current_time} /> : !sim.isError && <p className="text-sm text-slate-500">Loading…</p>}
    </div>
  )
}
