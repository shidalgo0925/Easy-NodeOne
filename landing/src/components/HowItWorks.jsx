import { motion, useInView } from 'framer-motion'
import { useRef } from 'react'

const steps = ['Configuración inicial', 'Activación de módulos', 'Escalabilidad por organización']

export default function HowItWorks() {
  const ref = useRef(null)
  const inView = useInView(ref, { once: true, margin: '-80px' })

  return (
    <section className="px-4 py-12 md:py-16" ref={ref}>
      <div className="mx-auto max-w-6xl">
        <motion.h2
          className="text-center text-3xl font-bold text-gray-dark md:text-4xl"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
        >
          Cómo funciona EasyNodeOne
        </motion.h2>
        <div className="relative mt-8 flex flex-col items-stretch gap-6 md:flex-row md:items-start md:justify-between">
          {/* Horizontal line - visible on desktop */}
          <div className="absolute left-1/2 top-12 hidden h-0.5 w-2/3 -translate-x-1/2 overflow-hidden rounded md:block" aria-hidden>
            <motion.div
              className="h-full w-full bg-gradient-official"
              initial={{ scaleX: 0 }}
              animate={inView ? { scaleX: 1 } : { scaleX: 0 }}
              transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
              style={{ transformOrigin: 'left center' }}
            />
          </div>
          {steps.map((label, i) => (
            <motion.div
              key={label}
              className="relative z-10 flex flex-1 flex-col items-center"
              initial={{ opacity: 0, y: 24 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.5, delay: 0.2 + i * 0.15, ease: [0.22, 1, 0.36, 1] }}
            >
              <motion.div
                className="flex h-14 w-14 items-center justify-center rounded-full bg-gradient-official text-lg font-bold text-white shadow-soft"
                initial={{ scale: 0 }}
                animate={inView ? { scale: 1 } : { scale: 0 }}
                transition={{ duration: 0.4, delay: 0.35 + i * 0.15 }}
              >
                {i + 1}
              </motion.div>
              <p className="mt-4 text-center font-medium text-gray-dark">{label}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
