import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api, formatWhen } from '../api'
import { RESOURCE_STATUS } from '../labels'
import { Banner, Field, PageHeader, StatusPill } from '../components/ui/index.js'

const STATUSES = ['available', 'maintenance', 'damaged', 'inactive', 'disabled']

export default function Computers() {
  const [searchParams] = useSearchParams()
  const [spaces, setSpaces] = useState([])
  const [spaceId, setSpaceId] = useState('')
  const [computers, setComputers] = useState([])
  const [selectedId, setSelectedId] = useState('')
  const [detail, setDetail] = useState(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [loading, setLoading] = useState(false)
  const [draft, setDraft] = useState({ name: '', asset_code: '', notes: '', hardware_notes: '' })
  const [peripheral, setPeripheral] = useState({ name: '', peripheral_type: 'monitor', asset_code: '', notes: '' })
  const [newComputer, setNewComputer] = useState({ name: '', asset_code: '' })
  const [damageNote, setDamageNote] = useState('')
  const [damageTarget, setDamageTarget] = useState('computer')

  async function loadSpaces(preferred) {
    const rows = await api('/spaces')
    setSpaces(rows)
    const fromQuery = searchParams.get('space')
    const next =
      preferred ||
      (fromQuery && rows.some((item) => item.id === fromQuery) ? fromQuery : null) ||
      spaceId ||
      rows.find((item) => item.room_type === 'AULA_PROGRAMACION')?.id ||
      rows[0]?.id ||
      ''
    setSpaceId(next)
    return next
  }

  async function loadComputers(nextSpaceId, preferredId) {
    if (!nextSpaceId) {
      setComputers([])
      setDetail(null)
      return
    }
    const rows = await api(`/spaces/${nextSpaceId}/computers`)
    setComputers(rows)
    const nextId = rows.some((item) => item.id === preferredId) ? preferredId : rows[0]?.id || ''
    setSelectedId(nextId)
    if (nextId) await loadDetail(nextId)
    else setDetail(null)
  }

  async function loadDetail(id) {
    const result = await api(`/computers/${id}`)
    setDetail(result)
    setDamageTarget('computer')
    setDraft({
      name: result.computer.name,
      asset_code: result.computer.asset_code,
      notes: result.computer.notes,
      hardware_notes: result.computer.hardware_notes,
    })
  }

  useEffect(() => {
    loadSpaces()
      .then((id) => loadComputers(id))
      .catch((err) => setError(err.message))
  }, [])

  async function refresh(nextSpaceId = spaceId, nextComputerId = selectedId) {
    await loadSpaces(nextSpaceId)
    await loadComputers(nextSpaceId, nextComputerId)
  }

  async function run(action, success) {
    setLoading(true)
    setError('')
    setNotice('')
    try {
      await action()
      setNotice(success)
      await refresh()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <section>
      <PageHeader title="Inventario" />
      {error && <Banner kind="error">{error}</Banner>}
      {notice && <Banner kind="ok">{notice}</Banner>}

      <article className="card">
        <Field label="Sala">
          <select
            value={spaceId}
            onChange={(event) => {
              const value = event.target.value
              setSpaceId(value)
              loadComputers(value).catch((err) => setError(err.message))
            }}
          >
            {spaces.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name} ({item.computers_registered})
              </option>
            ))}
          </select>
        </Field>
      </article>

      <div className="grid-2">
        <article className="card">
          <h2>Equipos</h2>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Equipo</th>
                  <th>Estado</th>
                </tr>
              </thead>
              <tbody>
                {computers.map((item) => (
                  <tr
                    key={item.id}
                    className={`click-row ${selectedId === item.id ? 'selected' : ''}`}
                    onClick={() => {
                      setSelectedId(item.id)
                      loadDetail(item.id).catch((err) => setError(err.message))
                    }}
                  >
                    <td>{item.asset_code || item.name}</td>
                    <td>
                      <StatusPill status={item.status} label={RESOURCE_STATUS[item.status] || item.status} />
                    </td>
                  </tr>
                ))}
                {computers.length === 0 && (
                  <tr>
                    <td colSpan="2">Sin equipos en esta sala.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </article>

        {detail && (
          <article className="card">
            <h2>{detail.computer.asset_code || detail.computer.name}</h2>
            <p>
              {detail.space_name || 'Sin sala'} · {RESOURCE_STATUS[detail.computer.status] || detail.computer.status}
            </p>

            <Field label="Estado">
              <select
                value={STATUSES.includes(detail.computer.status) ? detail.computer.status : 'maintenance'}
                onChange={(event) =>
                  run(
                    () =>
                      api(`/computers/${detail.computer.id}/status`, {
                        method: 'POST',
                        body: JSON.stringify({ status: event.target.value }),
                      }),
                    'Estado actualizado.',
                  )
                }
                disabled={loading}
              >
                {STATUSES.map((status) => (
                  <option key={status} value={status}>
                    {RESOURCE_STATUS[status]}
                  </option>
                ))}
              </select>
            </Field>

            <Field label="Sala">
              <select
                value={detail.computer.space_id || ''}
                onChange={(event) =>
                  run(
                    () =>
                      api(`/computers/${detail.computer.id}/location`, {
                        method: 'POST',
                        body: JSON.stringify({ space_id: event.target.value }),
                      }),
                    'Ubicación actualizada.',
                  )
                }
                disabled={loading}
              >
                {spaces.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
              </select>
            </Field>

            <form
              onSubmit={(event) => {
                event.preventDefault()
                run(
                  () =>
                    api(`/computers/${detail.computer.id}`, {
                      method: 'PATCH',
                      body: JSON.stringify(draft),
                    }),
                  'Datos guardados.',
                )
              }}
            >
              <Field label="Nombre">
                <input value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} />
              </Field>
              <Field label="Código">
                <input
                  value={draft.asset_code}
                  onChange={(event) => setDraft({ ...draft, asset_code: event.target.value })}
                />
              </Field>
              <Field label="Observaciones">
                <textarea value={draft.notes} onChange={(event) => setDraft({ ...draft, notes: event.target.value })} />
              </Field>
              <Field label="Hardware">
                <textarea
                  value={draft.hardware_notes}
                  onChange={(event) => setDraft({ ...draft, hardware_notes: event.target.value })}
                />
              </Field>
              <button type="submit" disabled={loading}>
                Guardar
              </button>
            </form>

            <form
              className="damage-form"
              onSubmit={(event) => {
                event.preventDefault()
                const peripheralItem =
                  damageTarget === 'computer' ? null : detail.peripherals.find((item) => item.id === damageTarget)
                const targetId = damageTarget === 'computer' ? detail.computer.id : peripheralItem?.id
                if (!targetId) return
                const label =
                  damageTarget === 'computer'
                    ? detail.computer.asset_code || detail.computer.name
                    : peripheralItem?.name || 'periférico'
                run(async () => {
                  await api(`/computers/${targetId}/status`, {
                    method: 'POST',
                    body: JSON.stringify({ status: 'damaged', note: damageNote }),
                  })
                  await api('/incidents', {
                    method: 'POST',
                    body: JSON.stringify({
                      title: `Daño en ${label}`,
                      description: damageNote,
                      category: 'tecnologia',
                      priority: 'media',
                      responsible_area: 'tecnologia',
                      recommendation: 'Diagnosticar y actualizar inventario.',
                      rationale: 'Reporte desde inventario.',
                      space_id: detail.computer.space_id,
                      resource_id: targetId,
                      source: 'manual',
                    }),
                  })
                  setDamageNote('')
                }, 'Daño registrado.')
              }}
            >
              <h2>Reportar daño</h2>
              <Field label="Equipo">
                <select value={damageTarget} onChange={(event) => setDamageTarget(event.target.value)}>
                  <option value="computer">{detail.computer.asset_code || detail.computer.name}</option>
                  {detail.peripherals.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.name}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Descripción">
                <textarea value={damageNote} onChange={(event) => setDamageNote(event.target.value)} required />
              </Field>
              <button type="submit" disabled={loading || !damageNote.trim()}>
                Registrar daño
              </button>
            </form>

            <h2>Periféricos</h2>
            <ul className="plain-list">
              {detail.peripherals.map((item) => (
                <li key={item.id}>
                  <span>
                    {item.name} · {item.peripheral_type} · {RESOURCE_STATUS[item.status] || item.status}
                  </span>
                </li>
              ))}
              {detail.peripherals.length === 0 && <li>Sin periféricos registrados.</li>}
            </ul>
            <form
              onSubmit={(event) => {
                event.preventDefault()
                run(async () => {
                  await api('/peripherals', {
                    method: 'POST',
                    body: JSON.stringify({
                      ...peripheral,
                      host_resource_id: detail.computer.id,
                      space_id: detail.computer.space_id,
                    }),
                  })
                  setPeripheral({ name: '', peripheral_type: 'monitor', asset_code: '', notes: '' })
                }, 'Periférico registrado.')
              }}
            >
              <Field label="Nombre">
                <input
                  value={peripheral.name}
                  onChange={(event) => setPeripheral({ ...peripheral, name: event.target.value })}
                  required
                />
              </Field>
              <Field label="Tipo">
                <select
                  value={peripheral.peripheral_type}
                  onChange={(event) => setPeripheral({ ...peripheral, peripheral_type: event.target.value })}
                >
                  <option value="monitor">Monitor</option>
                  <option value="teclado">Teclado</option>
                  <option value="raton">Ratón</option>
                  <option value="auriculares">Auriculares</option>
                  <option value="otro">Otro</option>
                </select>
              </Field>
              <Field label="Código">
                <input
                  value={peripheral.asset_code}
                  onChange={(event) => setPeripheral({ ...peripheral, asset_code: event.target.value })}
                />
              </Field>
              <button type="submit" disabled={loading}>
                Agregar periférico
              </button>
            </form>

            {detail.incidents.length > 0 && (
              <>
                <h2>Incidentes</h2>
                <ul className="plain-list">
                  {detail.incidents.map((item) => (
                    <li key={item.id}>
                      <span>
                        {item.title} · {item.status}
                      </span>
                    </li>
                  ))}
                </ul>
              </>
            )}

            {detail.events.length > 0 && (
              <>
                <h2>Historial</h2>
                <ul className="plain-list">
                  {detail.events.map((item) => (
                    <li key={item.id}>
                      <span>
                        {item.field}: {item.old_value || '—'} → {item.new_value || '—'}
                        <small>{formatWhen(item.created_at)}</small>
                      </span>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </article>
        )}
      </div>

      <form
        className="card"
        onSubmit={(event) => {
          event.preventDefault()
          run(async () => {
            const created = await api('/computers', {
              method: 'POST',
              body: JSON.stringify({
                name: newComputer.name,
                asset_code: newComputer.asset_code,
                space_id: spaceId,
                provisional: false,
              }),
            })
            setSelectedId(created.id)
            setNewComputer({ name: '', asset_code: '' })
          }, 'Computador registrado.')
        }}
      >
        <h2>Registrar computador</h2>
        <div className="split">
          <Field label="Nombre">
            <input
              value={newComputer.name}
              onChange={(event) => setNewComputer({ ...newComputer, name: event.target.value })}
              required
            />
          </Field>
          <Field label="Código">
            <input
              value={newComputer.asset_code}
              onChange={(event) => setNewComputer({ ...newComputer, asset_code: event.target.value })}
            />
          </Field>
        </div>
        <button type="submit" disabled={loading || !spaceId}>
          Registrar
        </button>
      </form>
    </section>
  )
}
