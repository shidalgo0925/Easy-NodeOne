import ProductFigure from './ProductFigure'

const MODULES = [
  { id: 'memberships', label: 'Membresías', desc: 'Planes, renovaciones y estados de socio.', from: 'from-blue-500', to: 'to-blue-700' },
  { id: 'events', label: 'Eventos', desc: 'Inscripciones, cupos y check-in.', from: 'from-emerald-500', to: 'to-emerald-700' },
  { id: 'payments', label: 'Pagos', desc: 'Pasarelas, conciliación y aprobaciones.', from: 'from-violet-500', to: 'to-violet-700' },
  { id: 'certificates', label: 'Certificados', desc: 'Emisión, QR y verificación.', from: 'from-amber-500', to: 'to-orange-600' },
  { id: 'academic', label: 'Académico', desc: 'Programas, cohortes e inscripciones.', from: 'from-rose-500', to: 'to-rose-700' },
  { id: 'crm', label: 'CRM', desc: 'Pipeline y seguimiento comercial.', from: 'from-teal-500', to: 'to-teal-700' },
  { id: 'services', label: 'Servicios', desc: 'Catálogo y reservas.', from: 'from-pink-500', to: 'to-pink-700' },
  { id: 'marketing', label: 'Marketing', desc: 'Campañas y automatizaciones.', from: 'from-yellow-400', to: 'to-amber-600' },
]

export default function EcosystemEN1() {
  return (
    <section id="ecosistema" className="scroll-mt-24 bg-slate-50 px-4 py-16 md:py-24">
      <div className="mx-auto max-w-6xl">
        <div className="text-center">
          <h2 className="text-3xl font-bold tracking-tight text-slate-900 md:text-4xl">Ecosistema EN1</h2>
          <p className="mx-auto mt-3 max-w-2xl text-slate-600 md:text-lg">
            Módulos conectados en una sola base: activá solo lo que tu organización necesita.
          </p>
        </div>

        <div className="relative mt-14">
          <div
            className="pointer-events-none absolute left-[5%] right-[5%] top-0 hidden h-px border-t border-dashed border-slate-300 md:block"
            aria-hidden
          />
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {MODULES.map((m, i) => (
              <div key={m.id} className="relative flex flex-col items-center text-center">
                <div
                  className={`relative z-[1] mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br shadow-lg ${m.from} ${m.to} ring-4 ring-white`}
                >
                  <span className="text-lg font-black text-white/95">{m.label.slice(0, 1)}</span>
                  <span
                    className="absolute -top-1 left-1/2 hidden h-2 w-2 -translate-x-1/2 -translate-y-full rounded-full bg-secondary md:block"
                    aria-hidden
                  />
                </div>
                <h3 className="text-sm font-bold text-slate-900">{m.label}</h3>
                <p className="mt-1 text-xs leading-snug text-slate-600">{m.desc}</p>
                {i < MODULES.length - 1 && (
                  <div
                    className="absolute -right-2 top-7 hidden h-px w-4 border-t-2 border-dotted border-slate-300 lg:block"
                    aria-hidden
                  />
                )}
              </div>
            ))}
          </div>
        </div>

        <ProductFigure
          className="mt-8"
          src="/images/product/ecosistema-en1.png"
          alt="Mapa visual del ecosistema modular EN1: módulos conectados entre sí."
          caption="Referencia de ecosistema: miembros, eventos, pagos, certificados, académico, CRM, servicios, marketing, reportes y configuración."
        />
      </div>
    </section>
  )
}
