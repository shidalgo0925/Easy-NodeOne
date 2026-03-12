import { motion } from 'framer-motion'

const modules = [
  { name: 'Core', desc: 'Usuarios, roles, permisos', icon: '◆' },
  { name: 'Members', desc: 'Gestión de miembros', icon: '◇' },
  { name: 'Services', desc: 'Citas y servicios', icon: '◎' },
  { name: 'Payments', desc: 'Stripe, PayPal, Yappy', icon: '◉' },
  { name: 'Communications', desc: 'Correo y WhatsApp', icon: '▣' },
  { name: 'Integrations', desc: 'APIs y Odoo', icon: '⬡' },
]

export default function Solution() {
  return (
    <section id="modulos" className="bg-gray-light/50 px-4 py-20 md:py-28">
      <div className="mx-auto max-w-6xl">
        <motion.h2
          className="text-center text-3xl font-bold text-gray-dark md:text-4xl"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-60px' }}
          transition={{ duration: 0.5 }}
        >
          Una plataforma modular, escalable y segura.
        </motion.h2>
        <div className="mt-16 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {modules.map(({ name, desc, icon }, i) => (
            <motion.div
              key={name}
              className="group relative overflow-hidden rounded-2xl border border-white bg-white p-8 shadow-soft transition-all duration-300 hover:-translate-y-1 hover:shadow-glow hover:shadow-secondary/10"
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-40px' }}
              transition={{ duration: 0.5, delay: i * 0.08 }}
            >
              <span className="absolute bottom-0 left-0 h-0.5 w-0 bg-gradient-official transition-all duration-300 group-hover:w-full" />
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-official text-xl text-white shadow-soft">
                {icon}
              </div>
              <h3 className="mt-5 text-lg font-semibold text-gray-dark">{name}</h3>
              <p className="mt-2 text-gray-mid">{desc}</p>
              <a href="#demo" className="mt-5 inline-block font-medium text-secondary transition-opacity hover:opacity-80">
                Ver más →
              </a>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
