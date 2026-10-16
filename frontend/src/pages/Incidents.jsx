import { useEffect, useState } from 'react'
import { api, formatWhen } from '../api'
import { AREAS, CATEGORIES, INCIDENT_STATUS, PRIORITIES } from '../labels'
import { Banner, Field, PageHeader } from '../components/ui/index.js'

const emptyFilters = { category: '', priority: '', status: '' }

export default function Incidents() {
  const [spaces, setSpaces] = useState([])
  const [resources, setResources] = useState([])
  const [description, setDescription] = useState('')
  const [spaceId, setSpaceId] = useState('')
  const [resourceId, setResourceId] = useState('')
  const [analysis, setAnalysis] = useState(null)
  const [draft, setDraft] = useState(null)
  const [incidents, setIncidents] = useState([])
  const [filters, setFilters] = useState(emptyFilters)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [loading, setLoading] = useState(false)
  const [events, setEvents] = useState(null)

  async function loadIncidents(nextFilters = filters) {
    const params = new URLSearchParams()
    Object.entries(nextFilters).forEach(([key, value]) => {
      if (value) params.set(key, value)
    })
    const query = params.toString()
    setIncidents(await api(`/incidents${query ? `?${query}` : ''}`))
  }

  useEffect(() => {
    Promise.all([api('/spaces'), api('/resources'), api('/incidents')])
      .then(([spaceRows, resourceRows, incidentRows]) => {
        setSpaces(spaceRows)
        setResources(resourceRows)
        setIncidents(incidentRows)
      })
      .catch((err) => setError(err.message))
  }, [])

  async function analyze(event) {
    event.preventDefault()
    setLoading(true)
    setError('')
    setNotice('')
    setAnalysis(null)
    setDraft(null)
    try {
      const result = await api('/incidents/analyze', {
        method: 'POST',
        body: JSON.stringify({
          description,
          space_id: spaceId || null,
          resource_id: resourceId || null,
        }),
      })
      setAnalysis(result)
      setDraft({
        category: result.category,
        priority: result.priority,
        responsible_area: result.responsible_area,
        recommendation: result.recommendation,
        rationale: result.rationale,
      })
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function save() {
    if (!analysis || !draft) return
    setLoading(true)
    setError('')
    setNotice('')
    const corrected = ['category', 'priority', 'responsible_area', 'recommendation', 'rationale'].some(
      (key) => draft[key] !== analysis[key],
    )
    try {
      const saved = await api('/incidents', {
        method: 'POST',
        body: JSON.stringify({
          description,
          category: draft.category,
          priority: draft.priority,
          responsible_area: draft.responsible_area,
          recommendation: draft.recommendation,
          rationale: draft.rationale,
          source: analysis.source,
          priority_raised_by_policy: analysis.priority_raised_by_policy,
          corrected,
          space_id: spaceId || null,
          resource_id: resourceId || null,
        }),
      })
      setNotice(`Incidente ${saved.id} guardado.`)
      setDescription('')
      setAnalysis(null)
      setDraft(null)
      await loadIncidents()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function changeStatus(id, status) {
    setLoading(true)
    setError('')
    try {
      await api(`/incidents/${id}`, { method: 'PATCH', body: JSON.stringify({ status }) })
      setNotice('Estado actualizado.')
      await loadIncidents()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function showEvents(id) {
    setError('')
    try {
      setEvents(await api(`/incidents/${id}`))
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <section>
      <PageHeader title="Incidentes e IA" />
      {error && <Banner kind="error">{error}</Banner>}
      {notice && <Banner kind="ok">{notice}</Banner>}
      <div className="grid-2">
        <form className="card" onSubmit={analyze}>
          <h2>Analizar incidente</h2>
          <Field label="Descripción">
            <textarea value={description} onChange={(event) => setDescription(event.target.value)} minLength={8} required rows={6} />
          </Field>
          <Field label="Espacio relacionado">
            <select value={spaceId} onChange={(event) => setSpaceId(event.target.value)}>
              <option value="">Ninguno</option>
              {spaces.map((space) => (
                <option key={space.id} value={space.id}>
                  {space.name}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Recurso relacionado">
            <select value={resourceId} onChange={(event) => setResourceId(event.target.value)}>
              <option value="">Ninguno</option>
              {resources.map((resource) => (
                <option key={resource.id} value={resource.id}>
                  {resource.name}
                </option>
              ))}
            </select>
          </Field>
          <button type="submit" disabled={loading}>
            {loading ? 'Analizando…' : 'Analizar'}
          </button>
        </form>
        <article className="card">
          <h2>Resultado</h2>
          {analysis && draft && (
            <>
              <Banner kind={analysis.source === 'ai' ? 'ok' : 'warn'}>
                {analysis.source === 'ai' ? 'Clasificación con IA' : 'Clasificación por reglas'}
              </Banner>
              {analysis.priority_raised_by_policy && (
                <Banner kind="warn">La prioridad se elevó por la regla de seguridad del campus. El modelo no puede bajar un incidente crítico.</Banner>
              )}
              <Field label="Categoría">
                <select value={draft.category} onChange={(event) => setDraft({ ...draft, category: event.target.value })}>
                  {Object.entries(CATEGORIES).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Prioridad">
                <select value={draft.priority} onChange={(event) => setDraft({ ...draft, priority: event.target.value })}>
                  {Object.entries(PRIORITIES).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Área responsable">
                <select
                  value={draft.responsible_area}
                  onChange={(event) => setDraft({ ...draft, responsible_area: event.target.value })}
                >
                  {Object.entries(AREAS).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Recomendación">
                <textarea value={draft.recommendation} onChange={(event) => setDraft({ ...draft, recommendation: event.target.value })} rows={3} />
              </Field>
              <Field label="Por qué">
                <textarea value={draft.rationale} onChange={(event) => setDraft({ ...draft, rationale: event.target.value })} rows={3} />
              </Field>
              <button type="button" onClick={save} disabled={loading}>
                {loading ? 'Guardando…' : 'Confirmar y guardar'}
              </button>
            </>
          )}
        </article>
      </div>
      <article className="card">
        <h2>Incidentes registrados</h2>
        <div className="filters">
          <Field label="Categoría">
            <select
              value={filters.category}
              onChange={(event) => {
                const next = { ...filters, category: event.target.value }
                setFilters(next)
                loadIncidents(next).catch((err) => setError(err.message))
              }}
            >
              <option value="">Todas</option>
              {Object.entries(CATEGORIES).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Prioridad">
            <select
              value={filters.priority}
              onChange={(event) => {
                const next = { ...filters, priority: event.target.value }
                setFilters(next)
                loadIncidents(next).catch((err) => setError(err.message))
              }}
            >
              <option value="">Todas</option>
              {Object.entries(PRIORITIES).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Estado">
            <select
              value={filters.status}
              onChange={(event) => {
                const next = { ...filters, status: event.target.value }
                setFilters(next)
                loadIncidents(next).catch((err) => setError(err.message))
              }}
            >
              <option value="">Todos</option>
              {Object.entries(INCIDENT_STATUS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </Field>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Incidente</th>
                <th>Clasificación</th>
                <th>Origen</th>
                <th>Estado</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {incidents.map((item) => (
                <tr key={item.id}>
                  <td>
                    <strong>{item.title}</strong>
                    <small>{formatWhen(item.created_at)}</small>
                  </td>
                  <td>
                    {CATEGORIES[item.category] || item.category} · {PRIORITIES[item.priority] || item.priority}
                    <small>{AREAS[item.responsible_area] || item.responsible_area}</small>
                  </td>
                  <td>
                    {item.source === 'ai' ? 'IA' : item.source === 'rules_fallback' ? 'Respaldo por reglas' : 'Manual'}
                    {item.ref_core ? <small>{item.ref_core}</small> : null}
                  </td>
                  <td>
                    <select value={item.status} onChange={(event) => changeStatus(item.id, event.target.value)} disabled={loading}>
                      {Object.entries(INCIDENT_STATUS).map(([value, label]) => (
                        <option key={value} value={value}>
                          {label}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <button type="button" className="secondary" onClick={() => showEvents(item.id)}>
                      Historial
                    </button>
                  </td>
                </tr>
              ))}
              {incidents.length === 0 && (
                <tr>
                  <td colSpan="5">No hay incidentes con esos filtros.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        {events && (
          <div className="report">
            <strong>{events.title}</strong>
            <p>{events.description}</p>
            <ul>
              {events.events?.map((event) => (
                <li key={event.id}>
                  {event.field}: {event.old_value || '—'} → {event.new_value} · {formatWhen(event.created_at)}
                </li>
              ))}
            </ul>
          </div>
        )}
      </article>
    </section>
  )
}
