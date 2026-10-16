import { useState } from 'react'
import Orbit from '../components/brand/Orbit'
import { Banner, Field } from '../components/ui/index.js'
import { useAuth } from '../auth'

export default function Welcome() {
  const { login } = useAuth()
  const [username, setUsername] = useState('mafe.cala')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [step, setStep] = useState('welcome')

  async function onSubmit(event) {
    event.preventDefault()
    setLoading(true)
    setError('')
    try {
      await login(username, password)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="welcome-screen">
      <div className="welcome-card scene-enter">
        <Orbit size="lg" variant="hello" motion="float" interactive decorative={false} />
        <p className="eyebrow">Campuslands Ops</p>
        <h1>Bienvenida</h1>

        {step === 'welcome' ? (
          <button type="button" onClick={() => setStep('login')}>
            Continuar al acceso
          </button>
        ) : (
          <form className="welcome-form" onSubmit={onSubmit}>
            {error && <Banner kind="error">{error}</Banner>}
            <Field label="Usuario">
              <input value={username} onChange={(event) => setUsername(event.target.value)} required autoFocus />
            </Field>
            <Field label="Contraseña">
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />
            </Field>
            <div className="row-actions">
              <button type="submit" disabled={loading}>
                {loading ? 'Entrando…' : 'Iniciar sesión'}
              </button>
              <button type="button" className="secondary" onClick={() => setStep('welcome')}>
                Volver
              </button>
            </div>
          </form>
        )}
      </div>
    </section>
  )
}
