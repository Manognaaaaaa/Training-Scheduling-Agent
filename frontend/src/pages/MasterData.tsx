import { useSearchParams } from 'react-router-dom'
import CoursesTab from '../components/master/CoursesTab'
import DriversTab from '../components/master/DriversTab'
import SessionsTab from '../components/master/SessionsTab'
import TrainersTab from '../components/master/TrainersTab'

const TABS = [
  { id: 'drivers', label: 'Drivers', Component: DriversTab },
  { id: 'trainers', label: 'Trainers', Component: TrainersTab },
  { id: 'courses', label: 'Courses', Component: CoursesTab },
  { id: 'sessions', label: 'Sessions', Component: SessionsTab },
]

export default function MasterData() {
  const [params, setParams] = useSearchParams()
  const active = TABS.find((t) => t.id === params.get('tab')) ?? TABS[0] // the tab lives in the URL

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Master Data</h1>
        <p className="mt-2 text-base text-slate-600">Create, edit and retire drivers, trainers, courses and training sessions.</p>
      </div>
      <div className="flex gap-1 border-b border-slate-200">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setParams({ tab: t.id })}
            className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium ${
              t.id === active.id ? 'border-slate-900 text-slate-900' : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>
      <active.Component />
    </div>
  )
}
