import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import Orbit from './Orbit'

const SCENE = {
  '/': 'hello',
  '/espacios': 'tablet',
  '/computadores': 'tablet',
  '/prestamos': 'ready',
  '/incidentes': 'tablet',
  '/integridad': 'ready',
}

export default function OrbitBackdrop() {
  const { pathname } = useLocation()
  const variant = SCENE[pathname] || 'hello'
  const [tilt, setTilt] = useState({ x: 0, y: 0 })
  const [key, setKey] = useState(pathname)

  useEffect(() => {
    setKey(pathname)
  }, [pathname])

  useEffect(() => {
    function onMove(event) {
      const x = (event.clientX / window.innerWidth - 0.5) * 2
      const y = (event.clientY / window.innerHeight - 0.5) * 2
      setTilt({
        x: Math.max(-8, Math.min(8, y * -6)),
        y: Math.max(-10, Math.min(10, x * 10)),
      })
    }
    window.addEventListener('pointermove', onMove, { passive: true })
    return () => window.removeEventListener('pointermove', onMove)
  }, [])

  return (
    <div className="orbit-backdrop" aria-hidden="true">
      <div className="orbit-backdrop-glow" />
      <div
        className="orbit-backdrop-figure"
        key={key}
        style={{
          transform: `translate3d(${tilt.y * 1.2}%, ${tilt.x * 0.8}%, 0) rotateX(${tilt.x}deg) rotateY(${tilt.y}deg)`,
        }}
      >
        <Orbit size="lg" variant={variant} motion="float" />
      </div>
      <div className="orbit-backdrop-mist" />
    </div>
  )
}
