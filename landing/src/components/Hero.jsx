import { useEffect, useRef } from 'react'

export default function Hero() {
  const sceneRef = useRef(null)
  const canvasRef = useRef(null)
  const tooltipRef = useRef(null)

  useEffect(() => {
    const canvas = canvasRef.current
    const scene = sceneRef.current
    const tooltip = tooltipRef.current
    if (!canvas || !scene || !tooltip) return

    const ctx = canvas.getContext('2d')
    const W = 520
    const H = 520
    canvas.width = W
    canvas.height = H
    const cx = W / 2
    const cy = H / 2

    const modules = [
      { name: 'Miembros', color: '#3b82f6', trail: 'rgba(59,130,246,', orbit: 160, speed: 0.007, tilt: 0.3, phase: 0 },
      { name: 'Pagos', color: '#10b981', trail: 'rgba(16,185,129,', orbit: 180, speed: 0.009, tilt: -0.5, phase: 1.05 },
      { name: 'Servicios', color: '#8b5cf6', trail: 'rgba(139,92,246,', orbit: 140, speed: 0.011, tilt: 0.7, phase: 2.1 },
      { name: 'Integraciones', color: '#f59e0b', trail: 'rgba(245,158,11,', orbit: 195, speed: 0.006, tilt: -0.2, phase: 3.14 },
      { name: 'Seguridad', color: '#ec4899', trail: 'rgba(236,72,153,', orbit: 165, speed: 0.013, tilt: 0.9, phase: 4.2 },
      { name: 'Reportes', color: '#06b6d4', trail: 'rgba(6,182,212,', orbit: 185, speed: 0.008, tilt: -0.8, phase: 5.25 },
    ]

    modules.forEach((m) => {
      m.angle = m.phase
      m.history = []
    })

    let mouseX = -999
    let mouseY = -999
    let frame = 0
    let rafId = 0
    let stars = []

    function onMouseMove(e) {
      const rect = scene.getBoundingClientRect()
      const scaleX = W / rect.width
      const scaleY = H / rect.height
      mouseX = (e.clientX - rect.left) * scaleX
      mouseY = (e.clientY - rect.top) * scaleY
    }

    function onMouseLeave() {
      mouseX = -999
      mouseY = -999
      tooltip.classList.remove('visible')
    }

    scene.addEventListener('mousemove', onMouseMove)
    scene.addEventListener('mouseleave', onMouseLeave)

    function getPos(m) {
      const rx = m.orbit
      const ry = m.orbit * 0.42
      const cosA = Math.cos(m.angle)
      const sinA = Math.sin(m.angle)
      const x0 = rx * cosA
      const y0 = ry * sinA
      const x = x0 * Math.cos(m.tilt) - y0 * Math.sin(m.tilt)
      const y = x0 * Math.sin(m.tilt) + y0 * Math.cos(m.tilt)
      return { x: cx + x, y: cy + y }
    }

    function drawOrbit(m) {
      const steps = 120
      ctx.beginPath()
      for (let i = 0; i <= steps; i += 1) {
        const a = (i / steps) * Math.PI * 2
        const x0 = m.orbit * Math.cos(a)
        const y0 = m.orbit * 0.42 * Math.sin(a)
        const x = x0 * Math.cos(m.tilt) - y0 * Math.sin(m.tilt)
        const y = x0 * Math.sin(m.tilt) + y0 * Math.cos(m.tilt)
        if (i === 0) ctx.moveTo(cx + x, cy + y)
        else ctx.lineTo(cx + x, cy + y)
      }
      ctx.closePath()
      ctx.strokeStyle = `${m.trail}0.12)`
      ctx.lineWidth = 0.8
      ctx.stroke()
    }

    function drawTrail(m) {
      if (m.history.length < 2) return
      for (let i = 1; i < m.history.length; i += 1) {
        const t = i / m.history.length
        ctx.beginPath()
        ctx.moveTo(m.history[i - 1].x, m.history[i - 1].y)
        ctx.lineTo(m.history[i].x, m.history[i].y)
        ctx.strokeStyle = `${m.trail}${t * 0.5})`
        ctx.lineWidth = t * 3
        ctx.lineCap = 'round'
        ctx.stroke()
      }
    }

    function drawNode(m) {
      const pos = getPos(m)
      const dist = Math.hypot(mouseX - pos.x, mouseY - pos.y)
      const isHovered = dist < 18
      const r = isHovered ? 10 : 7

      const distToCenter = Math.hypot(pos.x - cx, pos.y - cy)
      const alpha = Math.max(0, 1 - distToCenter / m.orbit) * 0.6 + 0.1
      ctx.beginPath()
      ctx.moveTo(cx, cy)
      ctx.lineTo(pos.x, pos.y)
      ctx.strokeStyle = `${m.trail}${alpha * 0.4})`
      ctx.lineWidth = 0.6
      ctx.setLineDash([4, 6])
      ctx.stroke()
      ctx.setLineDash([])

      const grd = ctx.createRadialGradient(pos.x, pos.y, 0, pos.x, pos.y, r * 3)
      grd.addColorStop(0, `${m.trail}0.4)`)
      grd.addColorStop(1, `${m.trail}0)`)
      ctx.beginPath()
      ctx.arc(pos.x, pos.y, r * 3, 0, Math.PI * 2)
      ctx.fillStyle = grd
      ctx.fill()

      ctx.beginPath()
      ctx.arc(pos.x, pos.y, r, 0, Math.PI * 2)
      ctx.fillStyle = m.color
      ctx.shadowBlur = isHovered ? 20 : 10
      ctx.shadowColor = m.color
      ctx.fill()
      ctx.shadowBlur = 0

      if (isHovered) {
        ctx.beginPath()
        ctx.arc(pos.x, pos.y, r + 4, 0, Math.PI * 2)
        ctx.strokeStyle = m.color
        ctx.lineWidth = 1.5
        ctx.globalAlpha = 0.5
        ctx.stroke()
        ctx.globalAlpha = 1
      }
      return { pos, isHovered }
    }

    function animate() {
      ctx.clearRect(0, 0, W, H)

      if (frame === 0) {
        stars = Array.from({ length: 80 }, () => ({
          x: Math.random() * W,
          y: Math.random() * H,
          r: Math.random() * 1.2,
          a: Math.random(),
        }))
      }

      stars.forEach((s) => {
        ctx.beginPath()
        ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(255,255,255,${s.a * 0.3})`
        ctx.fill()
      })

      modules.forEach(drawOrbit)

      let hoveredModule = null
      modules.forEach((m) => {
        m.angle += m.speed
        const pos = getPos(m)
        m.history.push({ x: pos.x, y: pos.y })
        if (m.history.length > 28) m.history.shift()
      })

      modules.forEach(drawTrail)
      modules.forEach((m) => {
        const { pos, isHovered } = drawNode(m)
        if (isHovered) hoveredModule = { name: m.name, color: m.color, x: pos.x, y: pos.y }
      })

      if (hoveredModule) {
        const rect = scene.getBoundingClientRect()
        const scaleX = rect.width / W
        const scaleY = rect.height / H
        tooltip.style.left = `${hoveredModule.x * scaleX}px`
        tooltip.style.top = `${hoveredModule.y * scaleY}px`
        tooltip.textContent = hoveredModule.name
        tooltip.style.borderColor = hoveredModule.color
        tooltip.classList.add('visible')
      } else {
        tooltip.classList.remove('visible')
      }

      frame += 1
      rafId = requestAnimationFrame(animate)
    }

    animate()

    return () => {
      cancelAnimationFrame(rafId)
      scene.removeEventListener('mousemove', onMouseMove)
      scene.removeEventListener('mouseleave', onMouseLeave)
    }
  }, [])

  return (
    <section className="hero-wrap">
      <div className="hero-grid">
        <div className="hero-copy">
          <h1 className="hero-title">Gestiona tus clientes y conversaciones desde un solo lugar.</h1>
          <p className="hero-sub">Organiza contactos, da seguimiento y mejora tu atencion sin perder oportunidades.</p>
          <div className="hero-actions">
            <a href="/#contacto" className="hero-btn-primary">Solicitar Demo</a>
            <a href="/#modulos" className="hero-btn-secondary">Ver módulos</a>
          </div>
        </div>

        <div className="hero-atom-panel">
          <div className="scene" id="scene" ref={sceneRef}>
            <canvas id="c" ref={canvasRef} />
            <div className="center-glow" />

            <div className="center-logo">
              <svg className="hex-bg" viewBox="0 0 96 96" fill="none" xmlns="http://www.w3.org/2000/svg">
                <defs>
                  <linearGradient id="hexgrad" x1="0" y1="0" x2="96" y2="96" gradientUnits="userSpaceOnUse">
                    <stop offset="0%" stopColor="#1d4ed8" />
                    <stop offset="100%" stopColor="#0ea5e9" />
                  </linearGradient>
                  <filter id="hexglow">
                    <feGaussianBlur stdDeviation="2" result="blur" />
                    <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
                  </filter>
                </defs>
                <polygon
                  points="48,4 86,26 86,70 48,92 10,70 10,26"
                  fill="url(#hexgrad)"
                  stroke="rgba(96,165,250,0.6)"
                  strokeWidth="1.5"
                  filter="url(#hexglow)"
                />
              </svg>
              <span className="n-letter">N</span>
            </div>

            <div className="tooltip" id="tooltip" ref={tooltipRef} />
          </div>
        </div>
      </div>

      <style>{`
        .hero-wrap {
          background: #f1f5f9;
          min-height: 0;
          padding: 12px 16px 28px;
        }
        .hero-grid {
          max-width: 1180px;
          margin: 0 auto;
          display: grid;
          gap: 16px;
          grid-template-columns: 1fr;
          align-items: center;
        }
        .hero-copy {
          background: #f1f5f9;
          padding: 8px 8px 8px 0;
        }
        .hero-title {
          font-size: clamp(34px, 4.4vw, 62px);
          line-height: 1.06;
          letter-spacing: -1.5px;
          color: #0f172a;
          margin-bottom: 12px;
          max-width: 680px;
        }
        .hero-sub {
          font-size: clamp(19px, 2.1vw, 30px);
          line-height: 1.38;
          color: #475569;
          max-width: 720px;
        }
        .hero-actions {
          margin-top: 20px;
          display: flex;
          gap: 12px;
          flex-wrap: wrap;
        }
        .hero-btn-primary, .hero-btn-secondary {
          border-radius: 12px;
          padding: 12px 24px;
          font-weight: 700;
          text-decoration: none;
          transition: 0.2s ease;
          display: inline-flex;
          align-items: center;
          justify-content: center;
        }
        .hero-btn-primary {
          color: #fff;
          background: linear-gradient(135deg, #2563eb 0%, #06b6d4 100%);
          box-shadow: 0 8px 20px rgba(37, 99, 235, 0.24);
        }
        .hero-btn-secondary {
          color: #2563eb;
          background: #fff;
          border: 2px solid #2563eb;
        }
        .hero-btn-primary:hover, .hero-btn-secondary:hover { transform: translateY(-1px); }
        .hero-atom-panel {
          background: #05091a;
          border-radius: 20px;
          display: flex;
          align-items: center;
          justify-content: center;
          min-height: 400px;
          overflow: hidden;
        }
        .scene {
          position: relative;
          width: 520px;
          height: 520px;
          max-width: 95%;
          max-height: 95%;
        }
        @media (min-width: 1024px) {
          .hero-grid {
            grid-template-columns: 1.02fr 0.98fr;
            gap: 22px;
          }
          .hero-wrap {
            padding-top: 8px;
          }
        }
        @media (max-width: 1023px) {
          .hero-title {
            font-size: clamp(36px, 8.2vw, 52px);
          }
          .hero-sub {
            font-size: clamp(19px, 5vw, 27px);
          }
          .hero-atom-panel {
            min-height: 320px;
          }
        }
        .scene {
          position: relative;
          width: 520px;
          height: 520px;
          max-width: 94vw;
          max-height: 62vh;
        }
        canvas {
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
        }
        .center-logo {
          position: absolute;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
          width: 96px;
          height: 96px;
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 10;
        }
        .hex-bg {
          position: absolute;
          width: 96px;
          height: 96px;
        }
        .n-letter {
          font-size: 42px;
          font-weight: 800;
          color: #fff;
          position: relative;
          z-index: 2;
          letter-spacing: -2px;
          text-shadow: 0 0 20px rgba(59,130,246,0.8);
          animation: pulse-n 3s ease-in-out infinite;
        }
        @keyframes pulse-n {
          0%, 100% { text-shadow: 0 0 20px rgba(59,130,246,0.8), 0 0 40px rgba(59,130,246,0.3); }
          50% { text-shadow: 0 0 30px rgba(59,130,246,1), 0 0 60px rgba(59,130,246,0.6), 0 0 80px rgba(96,165,250,0.4); }
        }
        .tooltip {
          position: absolute;
          background: rgba(255,255,255,0.1);
          backdrop-filter: blur(10px);
          border: 1px solid rgba(255,255,255,0.2);
          border-radius: 10px;
          padding: 6px 12px;
          font-size: 12px;
          font-weight: 600;
          color: #fff;
          white-space: nowrap;
          pointer-events: none;
          opacity: 0;
          transform: translate(-50%, -50%) scale(0.8);
          transition: opacity 0.3s, transform 0.3s;
          z-index: 20;
        }
        .tooltip.visible {
          opacity: 1;
          transform: translate(-50%, -140%) scale(1);
        }
        .center-glow {
          position: absolute;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
          width: 160px;
          height: 160px;
          border-radius: 50%;
          background: radial-gradient(circle, rgba(37,99,235,0.25) 0%, transparent 70%);
          animation: glow-pulse 3s ease-in-out infinite;
          z-index: 1;
        }
        @keyframes glow-pulse {
          0%, 100% { transform: translate(-50%,-50%) scale(1); opacity: 0.8; }
          50% { transform: translate(-50%,-50%) scale(1.2); opacity: 1; }
        }
      `}</style>
    </section>
  )
}
