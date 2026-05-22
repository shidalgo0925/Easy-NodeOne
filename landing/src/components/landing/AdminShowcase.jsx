import ProductFigure from './ProductFigure'

export default function AdminShowcase() {
  return (
    <section id="admin" className="scroll-mt-24 bg-white px-4 py-16 md:py-24">
      <div className="mx-auto max-w-6xl">
        <h2 className="text-center text-3xl font-bold tracking-tight text-slate-900 md:text-4xl">Administración y control</h2>
        <p className="mx-auto mt-3 max-w-2xl text-center text-slate-600 md:text-lg">
          Panel operativo con métricas, colas de validación y trazabilidad de aprobaciones.
        </p>

        <div className="mt-12 grid gap-6 lg:grid-cols-3">
          <div className="rounded-2xl border border-slate-200 bg-slate-900 p-5 text-slate-100 shadow-xl lg:col-span-2">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-sm font-bold">Panel admin</span>
              <span className="rounded-full bg-emerald-500/20 px-2 py-0.5 text-[10px] font-bold text-emerald-300">
                EN VIVO
              </span>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-2 md:grid-cols-4">
              {[
                { k: 'Validaciones', v: '6' },
                { k: 'Pagos hoy', v: '14' },
                { k: 'Certs emitidos', v: '32' },
                { k: 'Inscripciones', v: '48' },
              ].map((x) => (
                <div key={x.k} className="rounded-xl border border-white/10 bg-white/5 p-3">
                  <p className="text-[10px] uppercase text-slate-400">{x.k}</p>
                  <p className="mt-1 text-2xl font-bold text-white">{x.v}</p>
                </div>
              ))}
            </div>
            <div className="mt-4 rounded-xl border border-white/10 bg-black/30 p-3">
              <p className="text-[11px] font-semibold text-slate-400">Cola de aprobaciones</p>
              <ul className="mt-2 space-y-2 text-xs">
                <li className="flex justify-between gap-2 border-b border-white/5 py-1.5">
                  <span>Pago membresía — Asoc. Contadores</span>
                  <span className="shrink-0 text-amber-300">pending_review</span>
                </li>
                <li className="flex justify-between gap-2 border-b border-white/5 py-1.5">
                  <span>Inscripción cohorte IA</span>
                  <span className="shrink-0 text-sky-300">awaiting_validation</span>
                </li>
                <li className="flex justify-between gap-2 py-1.5">
                  <span>Certificado masivo evento</span>
                  <span className="shrink-0 text-emerald-300">approved</span>
                </li>
              </ul>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
            <h3 className="text-sm font-bold text-slate-800">Seguridad operativa</h3>
            <ul className="mt-4 space-y-2.5 text-sm text-slate-700">
              {['Roles y permisos', 'Auditoría de cambios', 'Exportaciones controladas', '2FA-ready'].map((t) => (
                <li key={t} className="flex gap-2">
                  <span className="text-secondary">✓</span>
                  {t}
                </li>
              ))}
            </ul>
          </div>
        </div>

        <ProductFigure
          className="mt-8"
          src="/images/product/dashboard-admin.png"
          alt="Dashboard administrativo EN1 con KPIs, actividad reciente, ingresos por mes y gráficos de estado de pagos."
          caption="Referencia de panel administrativo y analítica — misma línea visual que el resto del sitio."
        />
      </div>
    </section>
  )
}
