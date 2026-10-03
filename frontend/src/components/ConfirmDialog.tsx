import { useState, type ReactNode } from 'react'
import { ErrorBanner } from './FormModal'

interface Props {
  title: string
  /** Say what will happen, e.g. "This will cancel 3 upcoming bookings." */
  children: ReactNode
  confirmLabel: string
  onClose: () => void
  /** Throw to keep the dialog open and show the backend message (e.g. a 409). */
  onConfirm: () => Promise<void>
  danger?: boolean
}

export default function ConfirmDialog({ title, children, confirmLabel, onClose, onConfirm, danger = true }: Props) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function confirm() {
    setBusy(true)
    setError(null)
    try {
      await onConfirm()
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
      <div className="w-full max-w-md space-y-4 rounded-lg bg-white p-6 shadow-xl">
        <h2 className="text-lg font-semibold">{title}</h2>
        <div className="text-sm text-slate-600">{children}</div>
        <ErrorBanner message={error} />
        <div className="flex justify-end gap-2">
          <button className="rounded-md border border-slate-300 px-4 py-2 text-sm hover:bg-slate-50" onClick={onClose}>
            Keep
          </button>
          <button
            disabled={busy}
            onClick={confirm}
            className={`rounded-md px-4 py-2 text-sm font-medium text-white disabled:opacity-50 ${danger ? 'bg-red-600 hover:bg-red-700' : 'bg-slate-900 hover:bg-slate-700'}`}
          >
            {busy ? 'Working…' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
