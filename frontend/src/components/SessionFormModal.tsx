import { useState } from 'react'
import { createSession, updateSession, type Session } from '../api/sessions'
import { useAllCourses, useAllTrainers } from '../hooks/useLookups'
import { useRefresh } from '../hooks/useRefresh'
import { combineDateTime, toApiDateTime, toDateOnly } from '../utils/datetime'
import FormModal, { Field, inputClass } from './FormModal'
import { useToast } from './Toast'

/** Sessions start on the hour at one of these times (same as the backend's SESSION_START_HOURS). */
const START_TIMES = ['09:00', '14:00', '18:00']

interface Props {
  /** Pass a session to edit it; leave out to create. */
  session?: Session
  /** Create mode: prefilled start, e.g. from a click on the calendar. */
  initialStart?: Date
  onClose: () => void
  onSaved?: (session: Session) => void
}

/** Create or edit a session. The backend decides whether the slot is allowed and its message is shown. */
export default function SessionFormModal({ session, initialStart, onClose, onSaved }: Props) {
  const courses = useAllCourses().data?.items ?? []
  const trainers = useAllTrainers().data?.items ?? []
  const refresh = useRefresh()
  const toast = useToast()
  const editing = session !== undefined

  const start = session ? new Date(session.start_time) : initialStart
  const [courseId, setCourseId] = useState(session ? String(session.course_id) : '')
  const [trainerId, setTrainerId] = useState(session ? String(session.trainer_id) : '')
  const [date, setDate] = useState(start ? toDateOnly(start) : '')
  const startTime = start ? `${String(start.getHours()).padStart(2, '0')}:00` : '09:00'
  const [time, setTime] = useState(START_TIMES.includes(startTime) ? startTime : '09:00')
  const [location, setLocation] = useState(session?.location ?? '')
  const [capacity, setCapacity] = useState(session ? String(session.capacity) : '')

  const defaultCapacity = courses.find((c) => String(c.id) === courseId)?.default_capacity

  async function save() {
    const startIso = date ? toApiDateTime(combineDateTime(date, time)) : ''
    let saved: Session
    if (editing) {
      saved = await updateSession(session.id, {
        trainer_id: Number(trainerId),
        start_time: startIso,
        location: location || undefined,
        capacity: capacity ? Number(capacity) : undefined,
      })
    } else {
      saved = await createSession({
        course_id: Number(courseId),
        trainer_id: Number(trainerId),
        start_time: startIso,
        location: location || undefined,
        capacity: capacity ? Number(capacity) : undefined,
      })
    }
    await refresh('sessions')
    toast.success(editing ? 'Session updated' : 'Session created')
    onSaved?.(saved)
    onClose()
  }

  return (
    <FormModal title={editing ? `Edit session ${session.course_code}` : 'Add session'} onClose={onClose} onSubmit={save}>
      <Field label="Course" name="course_id">
        <select className={inputClass} value={courseId} onChange={(e) => setCourseId(e.target.value)} disabled={editing} required>
          <option value="">Select a course…</option>
          {courses.map((c) => (
            <option key={c.id} value={c.id}>{c.code} · {c.name}</option>
          ))}
        </select>
      </Field>
      <Field label="Trainer" name="trainer_id">
        <select className={inputClass} value={trainerId} onChange={(e) => setTrainerId(e.target.value)} required>
          <option value="">Select a trainer…</option>
          {trainers.map((t) => (
            <option key={t.id} value={t.id}>{t.name}</option>
          ))}
        </select>
      </Field>
      <div className="grid grid-cols-2 gap-3">
        <Field label="Date" name="start_time">
          <input type="date" className={inputClass} value={date} onChange={(e) => setDate(e.target.value)} required />
        </Field>
        <Field label="Start time" name="start_time_hour">
          <select className={inputClass} value={time} onChange={(e) => setTime(e.target.value)}>
            {START_TIMES.map((t) => <option key={t}>{t}</option>)}
          </select>
        </Field>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <Field label="Location" name="location">
          <input className={inputClass} value={location} onChange={(e) => setLocation(e.target.value)} placeholder="Main Training Room" />
        </Field>
        <Field label="Capacity" name="capacity">
          <input
            type="number" className={inputClass} value={capacity} onChange={(e) => setCapacity(e.target.value)}
            placeholder={defaultCapacity ? `Default ${defaultCapacity}` : 'Course default'}
          />
        </Field>
      </div>
      <p className="text-xs text-slate-500">Sessions run Sunday to Thursday, in the future, with a trainer who is free and under their weekly limit.</p>
    </FormModal>
  )
}
