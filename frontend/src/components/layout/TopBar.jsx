export default function TopBar({ online, open, onToggle }) {
  return (
    <header className="topbar">
      <div className="identity">
        <div className="brand-copy">
          <p className="wordmark">Campuslands</p>
          <strong>Campuslands Ops</strong>
          <span>Centro de operaciones del campus</span>
        </div>
      </div>
      <div className="top-actions">
        <p className={`connection ${online === null ? 'pending' : online ? 'online' : 'offline'}`}>
          <span className="dot" aria-hidden="true" />
          {online === null ? 'Comprobando backend' : online ? 'Backend conectado' : 'Backend sin conexión'}
        </p>
        <button type="button" className="menu-button" onClick={onToggle} aria-expanded={open}>
          {open ? 'Cerrar menú' : 'Menú'}
        </button>
      </div>
    </header>
  )
}
