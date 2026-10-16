import { useEffect, useState } from 'react'
import { api } from '../api'
import { Banner, PageHeader } from '../components/ui/index.js'

export default function Integrity() {
  const [report, setReport] = useState(null)
  const [rooms, setRooms] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([api('/integrity'), api('/catalog/rooms')])
      .then(([matrix, summary]) => {
        setReport(matrix)
        setRooms(summary)
      })
      .catch((err) => setError(err.message))
  }, [])

  return (
    <section>
      <PageHeader title="Integridad" />
      {error && <Banner kind="error">{error}</Banner>}
      {report && (
        <article className="card">
          <h2>Comprobaciones</h2>
          <p className={report.all_passed ? 'ok-text' : 'bad-text'}>
            {report.all_passed ? 'Datos consistentes.' : 'Hay inconsistencias.'}
          </p>
          <ul className="check-list">
            {report.checks.map((check) => (
              <li key={check.name}>
                <span>
                  <span className={check.passed ? 'pill ok' : 'pill bad'}>{check.passed ? 'OK' : 'Fallo'}</span>{' '}
                  {check.detail}
                </span>
              </li>
            ))}
          </ul>
        </article>
      )}
      <article className="card">
        <h2>Inventario por sala</h2>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Sala</th>
                <th>Capacidad</th>
                <th>Esperados</th>
                <th>Registrados</th>
                <th>Disponibles</th>
                <th>Mantenimiento</th>
                <th>Dañados</th>
              </tr>
            </thead>
            <tbody>
              {rooms.map((room) => (
                <tr key={room.id}>
                  <td>{room.name}</td>
                  <td>{room.capacity}</td>
                  <td>{room.expected_computers}</td>
                  <td>{room.registered_computers}</td>
                  <td>{room.available}</td>
                  <td>{room.maintenance}</td>
                  <td>{room.damaged}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </article>
    </section>
  )
}
