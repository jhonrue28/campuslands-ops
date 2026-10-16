import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import Orbit from './Orbit'

const SCENE = {
  '/': {
    variant: 'hello',
    motion: 'float',
    line: 'Orbit te da la bienvenida al centro de operaciones.',
  },
  '/espacios': {
    variant: 'tablet',
    motion: 'tip',
    line: 'Orbit revisa salas y horarios contigo.',
  },
  '/computadores': {
    variant: 'tablet',
    motion: 'bob',
    line: 'Orbit consulta el inventario por aula.',
  },
  '/prestamos': {
    variant: 'ready',
    motion: 'bob',
    line: 'Orbit está listo para registrar préstamos.',
  },
  '/incidentes': {
    variant: 'tablet',
    motion: 'tip',
    line: 'Orbit analiza el reporte paso a paso.',
  },
  '/integridad': {
    variant: 'ready',
    motion: 'float',
    line: 'Orbit vigila la consistencia del sistema.',
  },
}

export default function OrbitGuide() {
  const { pathname } = useLocation()
  const scene = SCENE[pathname] || SCENE['/']
  const [visible, setVisible] = useState(false)
  const [open, setOpen] = useState(true)
  const [key, setKey] = useState(pathname)

  useEffect(() => {
    setKey(pathname)
    setVisible(false)
    const show = window.setTimeout(() => setVisible(true), 120)
    return () => window.clearTimeout(show)
  }, [pathname])

  useEffect(() => {
    const onScroll = () => {
      if (window.scrollY > 40) setOpen(true)
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <aside className={`orbit-guide ${visible ? 'is-visible' : ''} ${open ? 'is-open' : ''}`}>
      <button type="button" className="orbit-guide-toggle" onClick={() => setOpen((value) => !value)}>
        {open ? 'Ocultar Orbit' : 'Mostrar Orbit'}
      </button>
      {open && (
        <div className="orbit-guide-panel" key={key}>
          <Orbit size="sm" variant={scene.variant} motion={scene.motion} interactive reactToPointer />
          <p>{scene.line}</p>
        </div>
      )}
    </aside>
  )
}
