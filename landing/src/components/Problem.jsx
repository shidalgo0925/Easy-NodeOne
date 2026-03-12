import { motion } from 'framer-motion'

const items = [
  { title: 'Gestión dispersa', num: '1' },
  { title: 'Integraciones complejas', num: '2' },
  { title: 'Procesos manuales', num: '3' },
]

export default function Problem() {
  return (
    <section id="plataforma" className="px-4 py-20 md:py-28">
      <div className="mx-auto max-w-6xl">
        <motion.h2
          className="text-center text-3xl font-bold text-gray-dark md:text-4xl"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-60px' }}
          transition={{ duration: 0.5 }}
        >
          Las organizaciones modernas enfrentan sistemas fragmentados.
        </motion.h2>
        <div className="mt-16 grid gap-8 md:grid-cols-3">
          {items.map(({ title, num }, i) => (
            <motion.div
              key={title}
              className="group rounded-2xl bg-white p-8 shadow-soft transition-all duration-300 hover:-translate-y-1 hover:shadow-card-hover hover:ring-2 hover:ring-secondary/10"
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-40px' }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
            >
              <motion.span
                className="inline-flex h-14 w-14 items-center justify-center rounded-xl bg-gradient-official text-2xl font-bold text-white shadow-soft"
                whileHover={{ scale: 1.05, rotate: 2 }}
                transition={{ duration: 0.3 }}
              >
                {num}
              </motion.span>
              <h3 className="mt-5 text-xl font-semibold text-gray-dark">{title}</h3>
            </motion.div>
          ))}
        </div>
        <motion.p
          className="mt-14 text-center text-lg text-gray-mid"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.3 }}
        >
          NodeOne unifica todo en una sola infraestructura modular.
        </motion.p>
      </div>
    </section>
  )
}
