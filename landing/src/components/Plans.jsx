import { motion } from 'framer-motion'

/** Misma campaña: lista vs promo (Basic 35.95 → 29.50); mismo % en todos los planes */
const LIST_BASIC = 35.95
const PROMO_BASIC = 29.5
const PROMO_PERCENT = Math.round(((LIST_BASIC - PROMO_BASIC) / LIST_BASIC) * 100) // ≈18%

const promoFromList = (listUsd) =>
  `USD ${((listUsd * PROMO_BASIC) / LIST_BASIC).toFixed(2)} / mes`

const BASIC_PROMO = {
  originalLine: `USD ${LIST_BASIC.toFixed(2)} / mes`,
  currentLine: `USD ${PROMO_BASIC.toFixed(2)} / mes`,
  percentOff: PROMO_PERCENT,
}

const PRO_LIST = 79
const PRO_PROMO = {
  originalLine: `USD ${PRO_LIST} / mes`,
  currentLine: promoFromList(PRO_LIST),
  percentOff: PROMO_PERCENT,
}

/** Enterprise: tarifa referencial mensual (ajustable); mismo factor de descuento */
const ENTERPRISE_LIST = 149
const ENTERPRISE_PROMO = {
  originalLine: `USD ${ENTERPRISE_LIST} / mes`,
  currentLine: promoFromList(ENTERPRISE_LIST),
  percentOff: PROMO_PERCENT,
  enterpriseSubline:
    'Tarifa referencial; precio final personalizado según alcance y contrato.',
}

const plans = [
  {
    name: 'Basic',
    price: `USD ${PROMO_BASIC.toFixed(2)} / mes`,
    promo: BASIC_PROMO,
    desc: 'Gestión de clientes + bandeja + citas',
    id: 'basic',
    recommended: false,
    limits: [
      '1 usuario',
      'Gestión de clientes',
      'Bandeja centralizada',
      'Gestión de citas',
    ],
  },
  {
    name: 'Professional',
    price: PRO_PROMO.currentLine,
    promo: PRO_PROMO,
    desc: 'Multiusuario + seguimiento + reportes',
    id: 'pro',
    recommended: true,
    limits: ['Multiusuario', 'Seguimiento de ventas', 'Reportes operativos'],
  },
  {
    name: 'Enterprise',
    price: ENTERPRISE_PROMO.currentLine,
    promo: ENTERPRISE_PROMO,
    desc: 'Escala empresarial',
    id: 'enterprise',
    recommended: false,
    limits: [
      'Configuración a medida',
      'Integraciones avanzadas',
      'Soporte con SLA',
    ],
  },
]

export default function Plans() {
  return (
    <section id="planes" className="px-4 py-12 md:py-16">
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
        <div className="mt-8 grid gap-6 md:grid-cols-3">
          {plans.map(({ name, price, promo, desc, id, recommended, limits }, i) => {
            const enterpriseSubline = promo?.enterpriseSubline
            return (
            <motion.div
              key={id}
              className={`relative rounded-2xl border bg-white p-6 shadow-soft transition-all duration-300 hover:-translate-y-1 hover:shadow-glow hover:shadow-secondary/15 ${
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
              {promo && (
                <span
                  className={`absolute right-4 rounded-full bg-emerald-600 px-2.5 py-0.5 text-xs font-bold text-white shadow-sm md:right-6 ${
                    recommended ? 'top-10' : '-top-3'
                  }`}
                >
                  −{promo.percentOff}% por tiempo limitado
                </span>
              )}
              <h3 className="text-xl font-semibold text-gray-dark">{name}</h3>
              {promo ? (
                <div className="mt-2">
                  <p className="text-lg text-gray-mid line-through decoration-gray-mid/80">
                    {promo.originalLine}
                  </p>
                  <p className="mt-1 flex flex-wrap items-baseline gap-2">
                    <span className="text-2xl font-bold text-secondary">{promo.currentLine}</span>
                    <span className="rounded-md bg-emerald-50 px-2 py-0.5 text-sm font-semibold text-emerald-800">
                      Ahorra {promo.percentOff}%
                    </span>
                  </p>
                  {enterpriseSubline && (
                    <p className="mt-2 text-sm leading-snug text-gray-mid">{enterpriseSubline}</p>
                  )}
                </div>
              ) : (
                <p className="mt-2 text-2xl font-bold text-secondary">{price}</p>
              )}
              <p className="mt-3 text-gray-mid">{desc}</p>
              <ul className="mt-4 space-y-2 text-sm text-gray-mid">
                {limits.map((limit) => (
                  <li key={limit}>- {limit}</li>
                ))}
              </ul>
              <motion.a
                href="/contact#demo"
                className="mt-6 inline-block w-full rounded-xl bg-gradient-official py-3.5 text-center font-semibold text-white shadow-soft transition-shadow hover:shadow-glow"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                Solicitar información
              </motion.a>
            </motion.div>
            )
          })}
        </div>
        <p className="mt-4 text-center text-sm text-gray-mid">Funciones de automatizacion e IA se habilitan progresivamente segun plan de producto.</p>
      </div>
    </section>
  )
}
