import { useEffect, useState } from 'react'
import { api, formatWhen, withSeconds } from '../api'
import { RESERVATION_STATUS, ROOM_TYPES, SPACE_STATUS } from '../labels'
import { Banner, Field, PageHeader, StatusPill } from '../components/ui/index.js'

const emptyForm = {
  space_id: '',
  requester_name: '',
  purpose: '',
  attendees: 10,
  starts_at: '2026-10-20T08:00',
  ends_at: '2026-10-20T10:00',
}

export default function Spaces() {
  const [spaces, setSpaces] = useState([])
  const [selected, setSelected] = useState(null)
  const [reservations, setReservations] = useState([])
  const [form, setForm] = useState(emptyForm)
  const [availability, setAvailability] = useState(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [loading, setLoading] = useState(false)

  async function load() {
    const [spaceRows, reservationRows] = await Promise.all([api('/spaces'), api('/reservations')])
    setSpaces(spaceRows)
    setReservations(reservationRows)
    setSelected((current) => current || spaceRows[0] || null)
  }

  useEffect(() => {
    load().catch((err) => setError(err.message))
  }, [])

  function update(event) {
    const { name, value } = event.target
    setForm((current) => ({ ...current, [name]: name === 'attendees' ? Number(value) : value }))
    if (name === 'space_id') {
      const space = spaces.find((item) => item.id === value)
      if (space) setSelected(space)
    }
  }

  async function createReservation(event) {
    event.preventDefault()
    setLoading(true)
    setError('')
    setNotice('')
    setAvailability(null)
    try {
      const created = await api('/reservations', {
        method: 'POST',
        body: JSON.stringify({
          ...form,
          space_id: form.space_id || selected?.id,
          starts_at: withSeconds(form.starts_at),
          ends_at: withSeconds(form.ends_at),
        }),
      })
      setNotice(`Reserva ${created.id} creada para ${created.space_name}.`)
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function checkAvailability() {
    const spaceId = form.space_id || selected?.id
    if (!spaceId) return
    setLoading(true)
    setError('')
    try {
      const params = new URLSearchParams({
        starts_at: withSeconds(form.starts_at),
        ends_at: withSeconds(form.ends_at),
      })
      setAvailability(await api(`/spaces/${spaceId}/availability?${params}`))
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function cancel(id) {
    setLoading(true)
    setError('')
    setNotice('')
    try {
      await api(`/reservations/${id}/cancel`, { method: 'PATCH' })
      setNotice('Reserva cancelada. El horario vuelve a estar libre.')
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <section>
      <PageHeader title="Reservas" />
      {error && <Banner kind="error">{error}</Banner>}
      {notice && <Banner kind="ok">{notice}</Banner>}
      {spaces.length === 0 && <Banner kind="warn">No hay salas. Regístrelas desde el Dashboard.</Banner>}
      <div className="grid-2">
        <div className="stack">
          {spaces.map((space) => (
            <button
              type="button"
              key={space.id}
              className={`space-card ${selected?.id === space.id ? 'selected' : ''}`}
              onClick={() => {
                setSelected(space)
                setForm((current) => ({ ...current, space_id: space.id }))
              }}
            >
              <div className="space-top">
                <strong>{space.name}</strong>
                <StatusPill status={space.status} label={SPACE_STATUS[space.status] || space.status} />
              </div>
              <p>Capacidad {space.capacity} · {space.computers_registered} computadores</p>
            </button>
          ))}
        </div>
        <div className="stack">
          {selected && (
            <article className="card">
              <h2>{selected.name}</h2>
              <p>
                {ROOM_TYPES[selected.room_type] || selected.room_type} · capacidad {selected.capacity}
              </p>
            </article>
          )}
          <form className="card" onSubmit={createReservation}>
            <h2>Nueva reserva</h2>
            <Field label="Espacio">
              <select name="space_id" value={form.space_id || selected?.id || ''} onChange={update}>
                {spaces.map((space) => (
                  <option key={space.id} value={space.id}>
                    {space.name}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Solicitante">
              <input name="requester_name" value={form.requester_name} onChange={update} required />
            </Field>
            <Field label="Motivo">
              <input name="purpose" value={form.purpose} onChange={update} required />
            </Field>
            <Field label="Asistentes">
              <input name="attendees" type="number" min="1" value={form.attendees} onChange={update} required />
            </Field>
            <div className="split">
              <Field label="Inicio">
                <input name="starts_at" type="datetime-local" value={form.starts_at} onChange={update} required />
              </Field>
              <Field label="Fin">
                <input name="ends_at" type="datetime-local" value={form.ends_at} onChange={update} required />
              </Field>
            </div>
            <div className="row-actions">
              <button type="submit" disabled={loading}>
                {loading ? 'Guardando…' : 'Crear reserva'}
              </button>
              <button type="button" className="secondary" onClick={checkAvailability} disabled={loading}>
                Consultar disponibilidad
              </button>
            </div>
            {availability && (
              <Banner kind={availability.available ? 'ok' : 'error'}>{availability.reason}</Banner>
            )}
          </form>
        </div>
      </div>
      <article className="card">
        <h2>Reservas</h2>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Espacio</th>
                <th>Solicitante</th>
                <th>Horario</th>
                <th>Asistentes</th>
                <th>Estado</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {reservations.map((item) => (
                <tr key={item.id}>
                  <td>{item.space_name}</td>
                  <td>
                    {item.requester_name}
                    <small>{item.purpose}</small>
                  </td>
                  <td>
                    {formatWhen(item.starts_at)} – {formatWhen(item.ends_at)}
                  </td>
                  <td>{item.attendees}</td>
                  <td>{RESERVATION_STATUS[item.status] || item.status}</td>
                  <td>
                    {item.status === 'active' && (
                      <button type="button" className="secondary" onClick={() => cancel(item.id)} disabled={loading}>
                        Cancelar
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {reservations.length === 0 && (
                <tr>
                  <td colSpan="6">No hay reservas.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </article>
    </section>
  )
}
