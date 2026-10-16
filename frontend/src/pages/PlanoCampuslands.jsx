import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { FLOOR_HOTSPOTS, FLOOR_PLAN_SRC } from '../data/floorPlan'
import { SPACE_STATUS } from '../labels'
import { Banner, PageHeader, StatusPill } from '../components/ui/index.js'

export default function PlanoCampuslands() {
  const navigate = useNavigate()
  const [spaces, setSpaces] = useState([])
  const [hovered, setHovered] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api('/spaces')
      .then(setSpaces)
      .catch((err) => setError(err.message))
  }, [])

  const byId = Object.fromEntries(spaces.map((item) => [item.id, item]))
  const active = hovered ? byId[hovered.id] : null

  return (
    <section className="plano-page scene-enter">
      <PageHeader title="Plano Campuslands" />
      {error && <Banner kind="error">{error}</Banner>}

      <div className="plano-layout">
        <div className="plano-canvas">
          <img src={FLOOR_PLAN_SRC} alt="Plano Campuslands — Torre Zenith" draggable={false} />
          {FLOOR_HOTSPOTS.map((spot) => {
            const space = byId[spot.id]
            const disabled = space && space.status !== 'available'
            return (
              <button
                key={spot.id}
                type="button"
                className={`plano-hotspot ${hovered?.id === spot.id ? 'is-hover' : ''} ${disabled ? 'is-disabled' : ''}`}
                style={{
                  left: `${spot.left}%`,
                  top: `${spot.top}%`,
                  width: `${spot.width}%`,
                  height: `${spot.height}%`,
                  '--spot': spot.color,
                }}
                aria-label={spot.name}
                onMouseEnter={() => setHovered(spot)}
                onMouseLeave={() => setHovered((current) => (current?.id === spot.id ? null : current))}
                onFocus={() => setHovered(spot)}
                onBlur={() => setHovered((current) => (current?.id === spot.id ? null : current))}
                onClick={() => navigate(`/salon/${spot.id}`)}
              >
                <span className="plano-tooltip">{spot.name}</span>
              </button>
            )
          })}
        </div>

        <aside className="plano-side">
          <article className="card plano-preview">
            {hovered ? (
              <>
                <h2 style={{ color: hovered.color }}>{hovered.name}</h2>
                {active && (
                  <>
                    <StatusPill status={active.status} label={SPACE_STATUS[active.status] || active.status} />
                    <p>
                      Capacidad {active.capacity}
                      {active.computers_registered > 0 ? ` · ${active.computers_registered} computadores` : ''}
                    </p>
                  </>
                )}
              </>
            ) : (
              <h2>Selecciona un salón</h2>
            )}
          </article>

          <ul className="plano-legend card">
            {FLOOR_HOTSPOTS.map((spot) => {
              const space = byId[spot.id]
              return (
                <li key={spot.id}>
                  <button type="button" className="legend-item" onClick={() => navigate(`/salon/${spot.id}`)}>
                    <span className="legend-swatch" style={{ background: spot.color }} />
                    <span>
                      <strong>{spot.name}</strong>
                      {space && <small>{SPACE_STATUS[space.status] || space.status}</small>}
                    </span>
                  </button>
                </li>
              )
            })}
          </ul>
        </aside>
      </div>
    </section>
  )
}
