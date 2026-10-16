import { NavLink } from 'react-router-dom'

export default function NavBar({ links, open, onNavigate }) {
  return (
    <nav className={open ? 'nav open' : 'nav'}>
      {links.map(([to, label]) => (
        <NavLink key={to} to={to} end={to === '/'} onClick={onNavigate}>
          {label}
        </NavLink>
      ))}
    </nav>
  )
}
