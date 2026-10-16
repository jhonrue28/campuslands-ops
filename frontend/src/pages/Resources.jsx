import { useEffect, useState } from 'react'
import { api, formatWhen, withSeconds } from '../api'
import { LOAN_STATUS, RESOURCE_STATUS } from '../labels'
import { Banner, Field, PageHeader, StatusPill } from '../components/ui/index.js'
import Orbit from '../components/brand/Orbit'

export default function Resources() {
  const [resources, setResources] = useState([])
  const [loans, setLoans] = useState([])
  const [form, setForm] = useState({
    resource_id: '',
    borrower_name: '',
    borrower_contact: '',
    purpose: '',
    due_at: '2026-10-23T18:00',
  })
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [loading, setLoading] = useState(false)

  async function load() {
    const [resourceRows, loanRows] = await Promise.all([api('/resources'), api('/loans')])
    setResources(resourceRows)
    setLoans(loanRows)
    setForm((current) => ({
      ...current,
      resource_id: current.resource_id || resourceRows.find((item) => item.available)?.id || resourceRows[0]?.id || '',
    }))
  }

  useEffect(() => {
    load().catch((err) => setError(err.message))
  }, [])

  function update(event) {
    const { name, value } = event.target
    setForm((current) => ({ ...current, [name]: value }))
  }

  async function createLoan(event) {
    event.preventDefault()
    setLoading(true)
    setError('')
    setNotice('')
    try {
      const created = await api('/loans', {
        method: 'POST',
        body: JSON.stringify({
          ...form,
          due_at: form.due_at ? withSeconds(form.due_at) : null,
        }),
      })
      setNotice(`Préstamo ${created.id} registrado. El recurso quedó como prestado.`)
      setForm((current) => ({ ...current, borrower_name: '', borrower_contact: '', purpose: '' }))
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function returnLoan(id) {
    setLoading(true)
    setError('')
    setNotice('')
    try {
      await api(`/loans/${id}/return`, { method: 'POST' })
      setNotice('Devolución registrada.')
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const active = loans.filter((item) => item.status === 'active')
  const history = loans.filter((item) => item.status !== 'active')

  return (
    <section>
      <PageHeader eyebrow="Inventario" title="Préstamos" />
      {error && <Banner kind="error">{error}</Banner>}
      {notice && <Banner kind="ok">{notice}</Banner>}
      {resources.length === 0 && (
        <div className="card empty-orbit">
          <Orbit size="sm" variant="ready" motion="bob" caption="Orbit está listo cuando haya equipos" interactive />
          <Banner kind="warn">No hay equipos. Registre las salas oficiales desde el Dashboard.</Banner>
        </div>
      )}
      <article className="card">
        <h2>Inventario</h2>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Recurso</th>
                <th>Categoría</th>
                <th>Ubicación</th>
                <th>Serie</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              {resources.map((item) => (
                <tr key={item.id}>
                  <td>
                    {item.name}
                    {item.origin === 'synthetic' && <small>Dato sintético</small>}
                    {item.notes && <small>{item.notes}</small>}
                  </td>
                  <td>{item.category || '—'}</td>
                  <td>{item.location || '—'}</td>
                  <td>{item.serial_number || '—'}</td>
                  <td>
                    <StatusPill status={item.status} label={RESOURCE_STATUS[item.status] || item.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </article>
      <div className="grid-2">
        <form className="card" onSubmit={createLoan}>
          <h2>Registrar préstamo</h2>
          <Field label="Recurso">
            <select name="resource_id" value={form.resource_id} onChange={update} required>
              {resources.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name} · {RESOURCE_STATUS[item.status] || item.status}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Persona">
            <input name="borrower_name" value={form.borrower_name} onChange={update} required />
          </Field>
          <Field label="Contacto">
            <input name="borrower_contact" value={form.borrower_contact} onChange={update} />
          </Field>
          <Field label="Motivo">
            <input name="purpose" value={form.purpose} onChange={update} />
          </Field>
          <Field label="Fecha límite">
            <input name="due_at" type="datetime-local" value={form.due_at} onChange={update} />
          </Field>
          <button type="submit" disabled={loading}>
            {loading ? 'Guardando…' : 'Prestar'}
          </button>
        </form>
        <article className="card">
          <h2>Préstamos activos</h2>
          {active.length === 0 && <p className="muted">No hay préstamos activos.</p>}
          <ul className="plain-list">
            {active.map((item) => (
              <li key={item.id}>
                <div>
                  <strong>{item.resource_name}</strong>
                  <p>
                    {item.borrower_name} · desde {formatWhen(item.loaned_at)}
                  </p>
                  <p className="muted">Límite {formatWhen(item.due_at)}</p>
                </div>
                <button type="button" onClick={() => returnLoan(item.id)} disabled={loading}>
                  Registrar devolución
                </button>
              </li>
            ))}
          </ul>
        </article>
      </div>
      <article className="card">
        <h2>Historial</h2>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Recurso</th>
                <th>Persona</th>
                <th>Prestado</th>
                <th>Devuelto</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              {history.map((item) => (
                <tr key={item.id}>
                  <td>{item.resource_name}</td>
                  <td>{item.borrower_name}</td>
                  <td>{formatWhen(item.loaned_at)}</td>
                  <td>{formatWhen(item.returned_at)}</td>
                  <td>{LOAN_STATUS[item.status] || item.status}</td>
                </tr>
              ))}
              {history.length === 0 && (
                <tr>
                  <td colSpan="5">El historial está vacío.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </article>
    </section>
  )
}
