import { NavLink, Outlet } from 'react-router-dom'
import ApiStatus from '../components/ApiStatus'

const links = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/master-data', label: 'Master Data' },
  { to: '/calendar', label: 'Calendar' },
  { to: '/alerts', label: 'Alerts' },
  { to: '/audit-log', label: 'Audit Log' },
  { to: '/fairness', label: 'Fairness' },
  { to: '/simulation', label: 'Simulation' },
]

export default function AppLayout() {
  return (
    <div className="flex min-h-screen bg-slate-50 text-slate-900">
      <aside className="flex w-60 shrink-0 flex-col border-r border-slate-200 bg-white">
        <div className="px-5 py-5 text-lg font-semibold">Training Optimiser</div>
        <nav className="flex-1 space-y-1 px-3">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              className={({ isActive }) =>
                `block rounded-md px-3 py-2 text-sm font-medium ${
                  isActive ? 'bg-slate-900 text-white' : 'text-slate-700 hover:bg-slate-100'
                }`
              }
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-slate-200 px-5 py-4">
          <ApiStatus />
        </div>
      </aside>
      <main className="flex-1 p-8">
        <Outlet />
      </main>
    </div>
  )
}
