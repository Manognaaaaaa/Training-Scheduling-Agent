import { createContext, useContext, useState, type FormEvent, type ReactNode } from 'react'
import { ApiError } from '../api/client'

const FieldErrors = createContext<Record<string, string>>({})

/** Shared Tailwind classes for inputs inside forms. */
export const inputClass =
  'w-full rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500 disabled:bg-slate-100'

/** A labelled form field. `name` is the backend field name, used to show a 422 message under it. */
export function Field({ label, name, children }: { label: string; name: string; children: ReactNode }) {
  const errors = useContext(FieldErrors)
  return (
    <label className="block text-sm">
      <span className="mb-1 block font-medium text-slate-700">{label}</span>
      {children}
      {errors[name] && <span className="mt-1 block text-xs text-red-600">{errors[name]}</span>}
    </label>
  )
}

/** Red banner used for 409 / 422 messages from the backend. */
export function ErrorBanner({ message }: { message: string | null }) {
  if (!message) return null
  return <div role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{message}</div>
}

interface Props {
  title: string
  submitLabel?: string
  onClose: () => void
  /** Do the save. Throw (the api client does) to keep the modal open and show the message. */
  onSubmit: () => Promise<void>
  children: ReactNode
}

/** Modal form. A failed submit shows the backend `detail` in a banner and marks fields from 422 errors. */
export default function FormModal({ title, submitLabel = 'Save', onClose, onSubmit, children }: Props) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})

  async function submit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    setFieldErrors({})
    try {
      await onSubmit()
    } catch (err) {
      setError((err as Error).message)
      if (err instanceof ApiError) setFieldErrors(err.fieldErrors)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
      <form onSubmit={submit} className="max-h-full w-full max-w-lg space-y-4 overflow-y-auto rounded-lg bg-white p-6 shadow-xl">
        <h2 className="text-lg font-semibold">{title}</h2>
        <ErrorBanner message={error} />
        <FieldErrors.Provider value={fieldErrors}>
          <div className="space-y-3">{children}</div>
        </FieldErrors.Provider>
        <div className="flex justify-end gap-2 pt-2">
          <button type="button" className="rounded-md border border-slate-300 px-4 py-2 text-sm hover:bg-slate-50" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" disabled={busy} className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50">
            {busy ? 'Saving…' : submitLabel}
          </button>
        </div>
      </form>
    </div>
  )
}
