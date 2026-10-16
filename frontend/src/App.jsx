import { AuthProvider, useAuth } from './auth'
import AppShell from './components/layout/AppShell'
import Welcome from './pages/Welcome'

function Gate() {
  const { user, booting } = useAuth()
  if (booting) {
    return (
      <div className="welcome-screen">
        <div className="welcome-card">
          <p className="muted">Preparando el acceso…</p>
        </div>
      </div>
    )
  }
  if (!user) return <Welcome />
  return <AppShell />
}

export default function App() {
  return (
    <AuthProvider>
      <Gate />
    </AuthProvider>
  )
}
