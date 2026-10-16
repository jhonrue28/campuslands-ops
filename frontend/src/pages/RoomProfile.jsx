import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, formatWhen, withSeconds } from '../api'
import { hotspotById } from '../data/floorPlan'
import { RESERVATION_STATUS, ROOM_TYPES, SPACE_STATUS } from '../labels'
import { Banner, Field, PageHeader, StatusPill } from '../components/ui/index.js'

const emptyForm = {
  requester_name: '',
  purpose: '',
  attendees: 10,
  starts_at: '2026-10-20T08:00',
  ends_at: '2026-10-20T10:00',
}

function toLocalInput(value) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  const pad = (n) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

export default function RoomProfile() {
  const { spaceId } = useParams()
  const spot = hotspotById(spaceId)
  const [space, setSpace] = useState(null)
  const [reservations, setReservations] = useState([])
  const [form, setForm] = useState(emptyForm)
  const [editingId, setEditingId] = useState(null)
  const [editForm, setEditForm] = useState(emptyForm)
  const [availability, setAvailability] = useState(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [loading, setLoading] = useState(false)

  async function load() {
    const [spaceRow, reservationRows] = await Promise.all([
      api(`/spaces/${spaceId}`),
      api(`/reservations?space_id=${encodeURIComponent(spaceId)}`),
    ])
    setSpace(spaceRow)
    setReservations(reservationRows)
    setForm((current) => ({
      ...current,
      attendees: Math.min(current.attendees || 10, spaceRow.capacity || 10),
    }))
  }

  useEffect(() => {
    setError('')
    setNotice('')
    setEditingId(null)
    load().catch((err) => setError(err.message))
  }, [spaceId])

  function updateForm(setter) {
    return (event) => {
      const { name, value } = event.target
      setter((current) => ({ ...current, [name]: name === 'attendees' ? Number(value) : value }))
    }
  }

  async function run(action, success) {
    setLoading(true)
    setError('')
    setNotice('')
    try {
      await action()
      if (success) setNotice(success)
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function createReservation(event) {
    event.preventDefault()
    await run(async () => {
      const created = await api('/reservations', {
        method: 'POST',
        body: JSON.stringify({
          space_id: spaceId,
          requester_name: form.requester_name,
          purpose: form.purpose,
          attendees: form.attendees,
          starts_at: withSeconds(form.starts_at),
          ends_at: withSeconds(form.ends_at),
        }),
      })
      setForm({ ...emptyForm, attendees: Math.min(10, space?.capacity || 10) })
      setNotice(`Reserva ${created.id} creada.`)
    })
  }

  async function checkAvailability() {
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

  function startEdit(item) {
    setEditingId(item.id)
    setEditForm({
      requester_name: item.requester_name,
      purpose: item.purpose,
      attendees: item.attendees,
      starts_at: toLocalInput(item.starts_at),
      ends_at: toLocalInput(item.ends_at),
    })
  }

  async function saveEdit(event) {
    event.preventDefault()
    await run(async () => {
      await api(`/reservations/${editingId}`, {
        method: 'PATCH',
        body: JSON.stringify({
          requester_name: editForm.requester_name,
          purpose: editForm.purpose,
          attendees: editForm.attendees,
          starts_at: withSeconds(editForm.starts_at),
          ends_at: withSeconds(editForm.ends_at),
          status: 'active',
        }),
      })
      setEditingId(null)
    }, 'Reserva actualizada.')
  }

  const accent = spot?.color || '#38bdf8'
  const title = space?.name || spot?.name || spaceId

  return (
    <section className="scene-enter">
      <PageHeader title={title}>
        <Link className="button-link secondary-link" to="/">
          Volver al plano
        </Link>
      </PageHeader>
      {error && <Banner kind="error">{error}</Banner>}
      {notice && <Banner kind="ok">{notice}</Banner>}

      {space && (
        <article className="card room-hero" style={{ '--spot': accent }}>
          <div className="room-hero-top">
            <div>
              <h2 style={{ margin: 0, color: accent }}>{space.name}</h2>
              <p>{ROOM_TYPES[space.room_type] || space.room_type}</p>
            </div>
            <StatusPill status={space.status} label={SPACE_STATUS[space.status] || space.status} />
          </div>
          <p>
            Capacidad {space.capacity} · {space.computers_registered} computadores
          </p>
          <div className="row-actions">
            {space.status === 'available' ? (
              <button
                type="button"
                className="secondary"
                disabled={loading}
                onClick={() =>
                  run(
                    () =>
                      api(`/spaces/${spaceId}/status`, {
                        method: 'PATCH',
                        body: JSON.stringify({ status: 'disabled', note: 'Deshabilitado desde el perfil del salón' }),
                      }),
                    'Salón deshabilitado. No acepta nuevas reservas.',
                  )
                }
              >
                Deshabilitar salón
              </button>
            ) : (
              <button
                type="button"
                disabled={loading}
                onClick={() =>
                  run(
                    () =>
                      api(`/spaces/${spaceId}/status`, {
                        method: 'PATCH',
                        body: JSON.stringify({ status: 'available', note: 'Habilitado desde el perfil del salón' }),
                      }),
                    'Salón habilitado.',
                  )
                }
              >
                Habilitar salón
              </button>
            )}
            {space.status !== 'maintenance' && (
              <button
                type="button"
                className="secondary"
                disabled={loading}
                onClick={() =>
                  run(
                    () =>
                      api(`/spaces/${spaceId}/status`, {
                        method: 'PATCH',
                        body: JSON.stringify({ status: 'maintenance', note: 'En mantenimiento' }),
                      }),
                    'Salón en mantenimiento.',
                  )
                }
              >
                Marcar mantenimiento
              </button>
            )}
            <Link className="button-link secondary-link" to={`/computadores?space=${encodeURIComponent(spaceId)}`}>
              Ver inventario de la sala
            </Link>
          </div>
        </article>
      )}

      <div className="grid-2">
        <form className="card" onSubmit={createReservation}>
          <h2>Nueva reserva</h2>
          <Field label="Solicitante">
            <input name="requester_name" value={form.requester_name} onChange={updateForm(setForm)} required />
          </Field>
          <Field label="Motivo">
            <input name="purpose" value={form.purpose} onChange={updateForm(setForm)} required />
          </Field>
          <Field label="Asistentes">
            <input name="attendees" type="number" min="1" value={form.attendees} onChange={updateForm(setForm)} required />
          </Field>
          <div className="split">
            <Field label="Inicio">
              <input name="starts_at" type="datetime-local" value={form.starts_at} onChange={updateForm(setForm)} required />
            </Field>
            <Field label="Fin">
              <input name="ends_at" type="datetime-local" value={form.ends_at} onChange={updateForm(setForm)} required />
            </Field>
          </div>
          <div className="row-actions">
            <button type="submit" disabled={loading || space?.status !== 'available'}>
              {loading ? 'Guardando…' : 'Crear reserva'}
            </button>
            <button type="button" className="secondary" onClick={checkAvailability} disabled={loading}>
              Consultar disponibilidad
            </button>
          </div>
          {availability && <Banner kind={availability.available ? 'ok' : 'error'}>{availability.reason}</Banner>}
        </form>

        <article className="card">
          <h2>Reservas del salón</h2>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Solicitante</th>
                  <th>Horario</th>
                  <th>Estado</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {reservations.map((item) => (
                  <tr key={item.id}>
                    <td>
                      {item.requester_name}
                      <small>
                        {item.purpose} · {item.attendees} asistentes
                      </small>
                    </td>
                    <td>
                      {formatWhen(item.starts_at)} – {formatWhen(item.ends_at)}
                    </td>
                    <td>{RESERVATION_STATUS[item.status] || item.status}</td>
                    <td>
                      <div className="row-actions">
                        {item.status === 'active' && (
                          <>
                            <button type="button" className="secondary" disabled={loading} onClick={() => startEdit(item)}>
                              Editar
                            </button>
                            <button
                              type="button"
                              className="secondary"
                              disabled={loading}
                              onClick={() =>
                                run(
                                  () => api(`/reservations/${item.id}/cancel`, { method: 'PATCH' }),
                                  'Reserva cancelada.',
                                )
                              }
                            >
                              Cancelar
                            </button>
                          </>
                        )}
                        {item.status === 'cancelled' && (
                          <button
                            type="button"
                            className="secondary"
                            disabled={loading || space?.status !== 'available'}
                            onClick={() =>
                              run(
                                () =>
                                  api(`/reservations/${item.id}`, {
                                    method: 'PATCH',
                                    body: JSON.stringify({ status: 'active' }),
                                  }),
                                'Reserva reactivada.',
                              )
                            }
                          >
                            Reactivar
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
                {reservations.length === 0 && (
                  <tr>
                    <td colSpan="4">No hay reservas para este salón.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </article>
      </div>

      {editingId && (
        <form className="card" onSubmit={saveEdit}>
          <h2>Modificar reserva</h2>
          <Field label="Solicitante">
            <input name="requester_name" value={editForm.requester_name} onChange={updateForm(setEditForm)} required />
          </Field>
          <Field label="Motivo">
            <input name="purpose" value={editForm.purpose} onChange={updateForm(setEditForm)} required />
          </Field>
          <Field label="Asistentes">
            <input
              name="attendees"
              type="number"
              min="1"
              value={editForm.attendees}
              onChange={updateForm(setEditForm)}
              required
            />
          </Field>
          <div className="split">
            <Field label="Inicio">
              <input
                name="starts_at"
                type="datetime-local"
                value={editForm.starts_at}
                onChange={updateForm(setEditForm)}
                required
              />
            </Field>
            <Field label="Fin">
              <input
                name="ends_at"
                type="datetime-local"
                value={editForm.ends_at}
                onChange={updateForm(setEditForm)}
                required
              />
            </Field>
          </div>
          <div className="row-actions">
            <button type="submit" disabled={loading}>
              Guardar cambios
            </button>
            <button type="button" className="secondary" onClick={() => setEditingId(null)}>
              Cerrar
            </button>
          </div>
        </form>
      )}
    </section>
  )
}
