import { motion } from 'framer-motion'

const ease = [0.22, 1, 0.36, 1]
const fadeSlide = { initial: { opacity: 0, y: 24 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.5, ease } }
const container = { initial: {}, animate: { transition: { staggerChildren: 0.1, delayChildren: 0.15 } } }

function NodeGrid() {
  const dots = [
    { x: 12, y: 20 }, { x: 88, y: 15 }, { x: 50, y: 45 }, { x: 25, y: 70 }, { x: 75, y: 65 },
    { x: 5, y: 50 }, { x: 95, y: 55 }, { x: 35, y: 25 }, { x: 65, y: 35 },
  ]
  return (
    <svg className="absolute inset-0 h-full w-full" aria-hidden>
      <defs>
        <linearGradient id="lineGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#2563EB" stopOpacity="0.4" />
          <stop offset="100%" stopColor="#06B6D4" stopOpacity="0.2" />
        </linearGradient>
      </defs>
      {dots.map((d, i) => (
        <motion.circle
          key={i}
          cx={`${d.x}%`}
          cy={`${d.y}%`}
          r="4"
          fill="url(#lineGrad)"
          initial={{ opacity: 0, scale: 0 }}
          animate={{ opacity: 0.6, scale: 1 }}
          transition={{ delay: 0.8 + i * 0.05, duration: 0.4 }}
        />
      ))}
      {[[0, 1], [1, 2], [2, 3], [2, 4], [0, 2], [1, 3], [3, 4], [5, 0], [6, 1], [7, 2], [8, 2]].slice(0, 8).map(([a, b], i) => (
        <motion.line
          key={`l-${i}`}
          x1={`${dots[a].x}%`}
          y1={`${dots[a].y}%`}
          x2={`${dots[b].x}%`}
          y2={`${dots[b].y}%`}
          stroke="url(#lineGrad)"
          strokeWidth="0.5"
          initial={{ opacity: 0 }}
          animate={{ opacity: 0.35 }}
          transition={{ delay: 1 + i * 0.03, duration: 0.5 }}
        />
      ))}
    </svg>
  )
}

export default function Hero() {
  return (
    <section className="relative overflow-hidden bg-gray-light/60 px-4 pt-16 pb-20 md:pt-24 md:pb-28">
      <div className="absolute inset-0 bg-gradient-radial" />
      <div className="relative mx-auto grid max-w-6xl gap-14 md:grid-cols-2 md:items-center">
        <motion.div className="relative" variants={container} initial="initial" animate="animate">
          <motion.h1
            className="text-4xl font-bold leading-tight text-gray-dark md:text-5xl lg:text-6xl"
            variants={fadeSlide}
          >
            Centraliza toda tu operación digital en un solo nodo.
          </motion.h1>
          <motion.p
            className="mt-6 text-lg text-gray-mid md:text-xl"
            variants={fadeSlide}
          >
            Plataforma modular: miembros, servicios, pagos e integraciones en un solo ecosistema.
          </motion.p>
          <motion.div className="mt-10 flex flex-wrap gap-4" variants={fadeSlide}>
            <motion.a
              href="#demo"
              className="relative rounded-xl bg-gradient-official px-6 py-3.5 font-semibold text-white shadow-lg shadow-secondary/30 transition-shadow duration-300 hover:shadow-glow"
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              Solicitar Demo
            </motion.a>
            <motion.a
              href="#plataforma"
              className="rounded-xl border-2 border-secondary bg-white px-6 py-3.5 font-medium text-secondary transition-colors hover:bg-secondary/5"
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              Ver Plataforma
            </motion.a>
          </motion.div>
        </motion.div>
        <motion.div
          className="relative flex justify-center"
          initial={{ opacity: 0, y: 32 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.3, ease: [0.22, 1, 0.36, 1] }}
        >
          <div className="relative h-72 w-full max-w-md md:h-80">
            <NodeGrid />
            <motion.div
              className="absolute inset-4 rounded-2xl bg-gradient-to-br from-secondary/15 to-cyan/20 shadow-soft md:inset-6"
              style={{ backdropFilter: 'blur(8px)' }}
              animate={{ y: [0, -8, 0] }}
              transition={{ duration: 5, repeat: Infinity, ease: 'easeInOut' }}
            />
            <motion.div
              className="absolute inset-8 rounded-xl border border-secondary/20 bg-white/80 shadow-card-hover md:inset-10"
              animate={{ y: [0, 6, 0] }}
              transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut', delay: 0.5 }}
            />
          </div>
        </motion.div>
      </div>
    </section>
  )
}
