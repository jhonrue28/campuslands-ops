import { NavLink } from 'react-router-dom'

export default function SideBar({ links, user, onLogout }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <p className="wordmark">Campuslands</p>
        <strong>Campuslands Ops</strong>
      </div>

      {user && (
        <div className="sidebar-user">
          <strong>{user.full_name}</strong>
          <span>{user.username} · {user.role}</span>
          <button type="button" className="secondary" onClick={onLogout}>
            Cerrar sesión
          </button>
        </div>
      )}

      <nav className="sidebar-nav" aria-label="Secciones principales">
        {links.map(([to, label]) => (
          <NavLink key={to} to={to} end={to === '/'}>
            {label}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
