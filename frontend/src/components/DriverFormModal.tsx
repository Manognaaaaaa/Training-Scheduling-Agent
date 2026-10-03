import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { createDriver, getDriverOptions, updateDriver, type Driver } from '../api/drivers'
import { useRefresh } from '../hooks/useRefresh'
import FormModal, { Field, inputClass } from './FormModal'
import { useToast } from './Toast'

const SHIFTS = ['day', 'night', 'rotating']

export default function DriverFormModal({ driver, onClose }: { driver?: Driver; onClose: () => void }) {
  const options = useQuery({ queryKey: ['driver-options'], queryFn: getDriverOptions }).data
  const refresh = useRefresh()
  const toast = useToast()
  const [form, setForm] = useState({
    employee_code: driver?.employee_code ?? '',
    name: driver?.name ?? '',
    nationality: driver?.nationality ?? '',
    shift: driver?.shift ?? 'day',
    depot: driver?.depot ?? '',
    hire_date: driver?.hire_date ?? '',
  })
  const set = (key: keyof typeof form) => (e: { target: { value: string } }) => setForm({ ...form, [key]: e.target.value })

  async function save() {
    if (driver) {
      await updateDriver(driver.id, { ...form, employee_code: form.employee_code || undefined })
    } else {
      await createDriver({ ...form, employee_code: form.employee_code || undefined })
    }
    await refresh('drivers')
    toast.success(driver ? 'Driver updated' : 'Driver added')
    onClose()
  }

  return (
    <FormModal title={driver ? `Edit ${driver.name}` : 'Add driver'} onClose={onClose} onSubmit={save}>
      <Field label="Employee code" name="employee_code">
        <input className={inputClass} value={form.employee_code} onChange={set('employee_code')} placeholder="Leave empty for the next DRV-xxxx" />
      </Field>
      <Field label="Name" name="name">
        <input className={inputClass} value={form.name} onChange={set('name')} required />
      </Field>
      <div className="grid grid-cols-2 gap-3">
        <Field label="Nationality" name="nationality">
          <input className={inputClass} list="nationality-options" value={form.nationality} onChange={set('nationality')} required />
          <datalist id="nationality-options">{options?.nationalities.map((n) => <option key={n} value={n} />)}</datalist>
        </Field>
        <Field label="Shift" name="shift">
          <select className={inputClass} value={form.shift} onChange={set('shift')}>
            {SHIFTS.map((s) => <option key={s}>{s}</option>)}
          </select>
        </Field>
        <Field label="Depot" name="depot">
          <input className={inputClass} list="depot-options" value={form.depot} onChange={set('depot')} required />
          <datalist id="depot-options">{options?.depots.map((d) => <option key={d} value={d} />)}</datalist>
        </Field>
        <Field label="Hire date" name="hire_date">
          <input type="date" className={inputClass} value={form.hire_date} onChange={set('hire_date')} required />
        </Field>
      </div>
    </FormModal>
  )
}
