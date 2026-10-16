import { useEffect, useState } from 'react'
import { api } from '../api'
import { PRIORITIES } from '../labels'
import { Banner, MetricCard, PageHeader } from '../components/ui/index.js'

export default function Dashboard() {
  const [data, setData] = useState(null)
  const [integrity, setIntegrity] = useState(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [loading, setLoading] = useState(false)

  async function load() {
    setError('')
    try {
      const [dashboard, matrix] = await Promise.all([api('/dashboard'), api('/integrity')])
      setData(dashboard)
      setIntegrity(matrix)
    } catch (err) {
      setError(err.message)
    }
  }

  useEffect(() => {
    load()
  }, [])

  async function loadOfficial() {
    setLoading(true)
    setNotice('')
    setError('')
    try {
      const result = await api('/catalog/official', { method: 'POST' })
      setNotice(`Catálogo: ${result.created_rooms} salas, ${result.created_computers} computadores.`)
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const cards = data
    ? [
        ['Salas', data.spaces_total],
        ['Reservas activas', data.active_reservations],
        ['Computadores', data.computers_total],
        ['Disponibles', data.computers_available],
        ['No operativos', data.computers_unavailable],
        ['Incidentes', data.open_incidents],
        ['Periféricos', data.peripherals_registered],
      ]
    : []

  return (
    <section>
      <PageHeader title="Dashboard" />
      {error && <Banner kind="error">{error}</Banner>}
      {notice && <Banner kind="ok">{notice}</Banner>}

      <article className="card">
        <div className="row-actions">
          <button type="button" onClick={loadOfficial} disabled={loading}>
            {loading ? 'Sincronizando…' : 'Registrar salas oficiales'}
          </button>
        </div>
      </article>

      <div className="stats">
        {cards.map(([label, value], index) => (
          <MetricCard key={label} label={label} value={value} delay={index * 45} />
        ))}
      </div>

      {data && (
        <div className="grid-2">
          <article className="card">
            <h2>Incidentes por prioridad</h2>
            <ul className="priority-list">
              {Object.entries(data.incidents_by_priority).map(([key, value]) => (
                <li key={key}>
                  <span>{PRIORITIES[key] || key}</span>
                  <b>{value}</b>
                </li>
              ))}
            </ul>
          </article>
          <article className="card">
            <h2>Integridad</h2>
            {integrity && (
              <p className={integrity.all_passed ? 'ok-text' : 'bad-text'}>
                {integrity.all_passed ? 'Datos consistentes.' : 'Hay inconsistencias.'}
              </p>
            )}
          </article>
        </div>
      )}
    </section>
  )
}
