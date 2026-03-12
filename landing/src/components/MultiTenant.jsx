import { motion } from 'framer-motion'

const points = ['Multi-organización', 'Marca blanca', 'API-first', 'Infraestructura cloud-ready']

export default function MultiTenant() {
  return (
    <section className="relative overflow-hidden bg-gray-light/50 px-4 py-20 md:py-28">
      {/* Subtle grid pattern */}
      <div
        className="absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage: `linear-gradient(#2563EB 1px, transparent 1px), linear-gradient(90deg, #2563EB 1px, transparent 1px)`,
          backgroundSize: '32px 32px',
        }}
      />
      <div className="relative mx-auto max-w-6xl">
        <motion.h2
          className="text-center text-3xl font-bold text-gray-dark md:text-4xl"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
        >
          Diseñado para escalar.
        </motion.h2>
        <ul className="mt-12 flex flex-wrap justify-center gap-4">
          {points.map((p, i) => (
            <motion.li
              key={p}
              className="rounded-xl bg-white px-6 py-3 font-medium text-gray-dark shadow-soft"
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.08 }}
            >
              {p}
            </motion.li>
          ))}
        </ul>
        <motion.div
          className="mt-16 flex justify-center"
          initial={{ opacity: 0, scale: 0.95 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
        >
          <svg viewBox="0 0 280 160" className="h-40 w-full max-w-md md:h-48" aria-hidden>
            <defs>
              <linearGradient id="nodeGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#2563EB" />
                <stop offset="100%" stopColor="#06B6D4" />
              </linearGradient>
            </defs>
            {/* Connections */}
            <motion.line x1="140" y1="80" x2="50" y2="40" stroke="url(#nodeGrad)" strokeWidth="1.5" strokeOpacity="0.5"
              initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true }} transition={{ duration: 0.4 }} />
            <motion.line x1="140" y1="80" x2="230" y2="40" stroke="url(#nodeGrad)" strokeWidth="1.5" strokeOpacity="0.5"
              initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true }} transition={{ duration: 0.4, delay: 0.08 }} />
            <motion.line x1="140" y1="80" x2="50" y2="120" stroke="url(#nodeGrad)" strokeWidth="1.5" strokeOpacity="0.5"
              initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true }} transition={{ duration: 0.4, delay: 0.16 }} />
            <motion.line x1="140" y1="80" x2="230" y2="120" stroke="url(#nodeGrad)" strokeWidth="1.5" strokeOpacity="0.5"
              initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true }} transition={{ duration: 0.4, delay: 0.24 }} />
            {/* Outer nodes */}
            {[[50, 40], [230, 40], [50, 120], [230, 120]].map(([x, y], i) => (
              <motion.circle key={i} cx={x} cy={y} r="12" fill="white" stroke="url(#nodeGrad)" strokeWidth="2"
                initial={{ scale: 0 }} whileInView={{ scale: 1 }} viewport={{ once: true }} transition={{ delay: 0.2 + i * 0.08 }} />
            ))}
            {/* Core */}
            <motion.circle cx="140" cy="80" r="24" fill="url(#nodeGrad)"
              initial={{ scale: 0 }} whileInView={{ scale: 1 }} viewport={{ once: true }} transition={{ duration: 0.4 }} />
            <motion.circle cx="140" cy="80" r="8" fill="white" fillOpacity="0.9"
              initial={{ scale: 0 }} whileInView={{ scale: 1 }} viewport={{ once: true }} transition={{ delay: 0.2 }} />
          </svg>
        </motion.div>
      </div>
    </section>
  )
}
