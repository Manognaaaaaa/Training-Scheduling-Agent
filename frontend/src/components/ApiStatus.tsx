import { useEffect, useState } from 'react'
import { getHealth } from '../api/client'

const POLL_MS = 10_000

/** Sidebar badge: green when /health says ok, red otherwise. Rechecks every 10 s. */
export default function ApiStatus() {
  const [online, setOnline] = useState<boolean | null>(null)

  useEffect(() => {
    let cancelled = false

    async function check() {
      try {
        const health = await getHealth()
        if (!cancelled) setOnline(health.status === 'ok' && health.database === 'ok')
      } catch {
        if (!cancelled) setOnline(false)
      }
    }

    check()
    const timer = setInterval(check, POLL_MS)
    return () => {
      cancelled = true
      clearInterval(timer)
    }
  }, [])

  const label = online === null ? 'Checking API…' : online ? 'API connected' : 'API offline'
  const dot = online === null ? 'bg-slate-400' : online ? 'bg-green-500' : 'bg-red-500'
  const text = online === null ? 'text-slate-600' : online ? 'text-green-700' : 'text-red-700'

  return (
    <div className={`flex items-center gap-2 text-sm ${text}`}>
      <span className={`h-2.5 w-2.5 rounded-full ${dot}`} />
      {label}
    </div>
  )
}
