import { Navigate, Route, Routes } from 'react-router-dom'
import SpaceBackdrop from '../brand/SpaceBackdrop'
import SideBar from './SideBar'
import PlanoCampuslands from '../../pages/PlanoCampuslands'
import RoomProfile from '../../pages/RoomProfile'
import Dashboard from '../../pages/Dashboard'
import Spaces from '../../pages/Spaces'
import Computers from '../../pages/Computers'
import Incidents from '../../pages/Incidents'
import Integrity from '../../pages/Integrity'
import Users from '../../pages/Users'
import { useAuth } from '../../auth'

const LINKS = [
  ['/', 'Plano Campuslands'],
  ['/espacios', 'Reservas'],
  ['/computadores', 'Inventario'],
  ['/incidentes', 'Incidentes e IA'],
  ['/dashboard', 'Dashboard'],
  ['/integridad', 'Integridad'],
  ['/usuarios', 'Usuarios'],
]

export default function AppShell() {
  const { user, logout } = useAuth()

  return (
    <div className="shell">
      <SpaceBackdrop />
      <SideBar links={LINKS} user={user} onLogout={logout} />
      <main className="content content-wide">
        <Routes>
          <Route path="/" element={<PlanoCampuslands />} />
          <Route path="/plano" element={<Navigate to="/" replace />} />
          <Route path="/plano/:spaceId" element={<RoomProfile />} />
          <Route path="/salon/:spaceId" element={<RoomProfile />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/espacios" element={<Spaces />} />
          <Route path="/computadores" element={<Computers />} />
          <Route path="/recursos" element={<Navigate to="/computadores" replace />} />
          <Route path="/prestamos" element={<Navigate to="/computadores" replace />} />
          <Route path="/incidentes" element={<Incidents />} />
          <Route path="/integridad" element={<Integrity />} />
          <Route path="/usuarios" element={<Users />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  )
}
