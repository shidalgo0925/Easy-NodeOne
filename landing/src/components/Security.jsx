import { motion } from 'framer-motion'

const items = [
  'Autenticación segura',
  'Control de roles',
  'Cifrado SSL',
  'Registro de actividad',
  'Arquitectura modular',
]

const icon = (
  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden>
    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
  </svg>
)

export default function Security() {
  return (
    <section id="seguridad" className="bg-[#0F172A] px-4 py-20 text-white md:py-28">
      <div className="mx-auto max-w-6xl">
        <motion.h2
          className="text-center text-3xl font-bold md:text-4xl"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
        >
          Seguridad de nivel empresarial.
        </motion.h2>
        <ul className="mt-16 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((item, i) => (
            <motion.li
              key={item}
              className="flex items-center gap-4 rounded-xl border border-white/10 bg-white/5 px-6 py-4 backdrop-blur-sm"
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-40px' }}
              transition={{ duration: 0.45, delay: i * 0.08 }}
            >
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-secondary/20 text-secondary">
                {icon}
              </span>
              <span className="text-gray-200">{item}</span>
            </motion.li>
          ))}
        </ul>
      </div>
    </section>
  )
}
