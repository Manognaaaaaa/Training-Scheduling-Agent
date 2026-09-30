import { Route, Routes } from 'react-router-dom'
import AppLayout from './layouts/AppLayout'
import Alerts from './pages/Alerts'
import AuditLog from './pages/AuditLog'
import Calendar from './pages/Calendar'
import Dashboard from './pages/Dashboard'
import Fairness from './pages/Fairness'
import MasterData from './pages/MasterData'
import Simulation from './pages/Simulation'

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<Dashboard />} />
        <Route path="master-data" element={<MasterData />} />
        <Route path="calendar" element={<Calendar />} />
        <Route path="alerts" element={<Alerts />} />
        <Route path="audit-log" element={<AuditLog />} />
        <Route path="fairness" element={<Fairness />} />
        <Route path="simulation" element={<Simulation />} />
      </Route>
    </Routes>
  )
}
