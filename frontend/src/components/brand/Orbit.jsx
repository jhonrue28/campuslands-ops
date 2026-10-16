import { useEffect, useRef, useState } from 'react'

const ASSETS = {
  ready: '/orbit/orbit-ready.png',
  tablet: '/orbit/orbit-tablet.png',
  hello: '/orbit/orbit-hello.png',
}

const MOTION = {
  float: 'orbit-float',
  bob: 'orbit-bob',
  tip: 'orbit-tip',
  sit: 'orbit-sit',
  none: '',
}

export default function Orbit({
  size = 'md',
  variant = 'hello',
  motion = 'float',
  caption,
  className = '',
  decorative = true,
  interactive = false,
  reactToPointer = false,
}) {
  const stageRef = useRef(null)
  const [tilt, setTilt] = useState({ x: 0, y: 0 })
  const [pulse, setPulse] = useState(false)
  const src = ASSETS[variant] || ASSETS.hello
  const motionClass = MOTION[motion] || MOTION.float

  useEffect(() => {
    if (!reactToPointer) return undefined
    function onMove(event) {
      const node = stageRef.current
      if (!node) return
      const rect = node.getBoundingClientRect()
      const px = (event.clientX - rect.left) / rect.width - 0.5
      const py = (event.clientY - rect.top) / rect.height - 0.5
      setTilt({
        x: Math.max(-10, Math.min(10, py * -14)),
        y: Math.max(-14, Math.min(14, px * 18)),
      })
    }
    function onLeave() {
      setTilt({ x: 0, y: 0 })
    }
    window.addEventListener('pointermove', onMove)
    window.addEventListener('pointerleave', onLeave)
    return () => {
      window.removeEventListener('pointermove', onMove)
      window.removeEventListener('pointerleave', onLeave)
    }
  }, [reactToPointer])

  function onActivate() {
    if (!interactive) return
    setPulse(true)
    window.setTimeout(() => setPulse(false), 520)
  }

  return (
    <figure
      className={`orbit-figure orbit-${size} ${motionClass} ${pulse ? 'orbit-pulse' : ''} ${className}`}
      onClick={onActivate}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault()
          onActivate()
        }
      }}
      role={interactive ? 'button' : undefined}
      tabIndex={interactive ? 0 : undefined}
    >
      <div
        ref={stageRef}
        className="orbit-stage"
        aria-hidden={decorative ? 'true' : undefined}
        style={
          reactToPointer
            ? {
                transform: `rotateX(${tilt.x}deg) rotateY(${tilt.y}deg)`,
              }
            : undefined
        }
      >
        <div className="orbit-glow" />
        <div className="orbit-platform" />
        <img
          src={src}
          alt={decorative ? '' : `Orbit (${variant}), mascota de Campuslands`}
          className="orbit-img"
          draggable="false"
        />
      </div>
      {caption ? <figcaption>{caption}</figcaption> : null}
    </figure>
  )
}

export const ORBIT_VARIANTS = Object.keys(ASSETS)
