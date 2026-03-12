import { motion } from 'framer-motion'

export default function CTA() {
  return (
    <section className="relative overflow-hidden bg-gradient-official px-4 py-24 text-white md:py-32">
      {/* Subtle glow */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_50%_at_50%_50%,rgba(255,255,255,0.08)_0%,transparent_70%)]" />
      <div className="absolute left-1/2 top-1/2 h-96 w-96 -translate-x-1/2 -translate-y-1/2 rounded-full bg-white/5 blur-3xl" />
      <div className="relative mx-auto max-w-3xl text-center">
        <motion.h2
          className="text-3xl font-bold md:text-4xl lg:text-5xl"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
        >
          Construye tu infraestructura digital con Easy NodeOne.
        </motion.h2>
        <motion.a
          href="#demo"
          className="mt-10 inline-block rounded-xl bg-white px-10 py-4 font-semibold text-secondary shadow-xl transition-colors hover:bg-gray-100 hover:text-primary"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.15 }}
          whileHover={{ scale: 1.03 }}
          whileTap={{ scale: 0.98 }}
        >
          Solicitar Demo
        </motion.a>
      </div>
    </section>
  )
}
