import { motion } from 'framer-motion'

const plans = [
  { name: 'Basic', desc: 'Core + Members', id: 'basic', recommended: false },
  { name: 'Professional', desc: 'Services + Payments', id: 'pro', recommended: true },
  { name: 'Enterprise', desc: 'Communications + Integrations + Marca blanca', id: 'enterprise', recommended: false },
]

export default function Plans() {
  return (
    <section id="planes" className="px-4 py-20 md:py-28">
      <div className="mx-auto max-w-6xl">
        <motion.h2
          className="text-center text-3xl font-bold text-gray-dark md:text-4xl"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
        >
          Planes
        </motion.h2>
        <div className="mt-16 grid gap-8 md:grid-cols-3">
          {plans.map(({ name, desc, id, recommended }, i) => (
            <motion.div
              key={id}
              className={`relative rounded-2xl border bg-white p-8 shadow-soft transition-all duration-300 hover:-translate-y-1 hover:shadow-glow hover:shadow-secondary/15 ${
                recommended ? 'border-secondary/40 ring-2 ring-secondary/20' : 'border-gray-mid/20'
              }`}
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-40px' }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
              whileHover={{ scale: 1.02 }}
            >
              {recommended && (
                <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-gradient-official px-4 py-1 text-sm font-semibold text-white shadow-soft">
                  Recomendado
                </span>
              )}
              <h3 className="text-xl font-semibold text-gray-dark">{name}</h3>
              <p className="mt-3 text-gray-mid">{desc}</p>
              <motion.a
                href="#demo"
                className="mt-6 inline-block w-full rounded-xl bg-gradient-official py-3.5 text-center font-semibold text-white shadow-soft transition-shadow hover:shadow-glow"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                Solicitar información
              </motion.a>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
