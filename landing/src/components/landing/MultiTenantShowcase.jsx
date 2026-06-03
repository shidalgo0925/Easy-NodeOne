const ORGS = [
  { name: 'Instituto Tecnológico', host: 'instituto.en1', members: '1.200', status: 'Activo' },
  { name: 'Asociación de Contadores', host: 'contadores.en1', members: '850', status: 'Activo' },
  { name: 'Academia de Idiomas', host: 'idiomas.en1', members: '650', status: 'Activo' },
]

export default function MultiTenantShowcase() {
  return (
    <section id="multitenant" className="scroll-mt-24 bg-slate-50 px-4 py-16 md:py-24">
      <div className="mx-auto max-w-6xl">
        <div className="grid gap-10 lg:grid-cols-2 lg:items-center">
          <div>
            <h2 className="text-3xl font-bold tracking-tight text-slate-900 md:text-4xl">Multi-tenant por diseño</h2>
            <p className="mt-4 text-slate-600 md:text-lg">
              Cada organización con datos y configuración independientes. Módulos activables por tenant, mismos
              estándares de seguridad y una consola clara para operar varias marcas o unidades.
            </p>
            <ul className="mt-6 space-y-3 text-sm font-medium text-slate-700">
              {[
                'Múltiples organizaciones aisladas',
                'Módulos activables por instancia',
                'Branding y parámetros propios',
                'Escalamiento horizontal del servicio',
              ].map((t) => (
                <li key={t} className="flex gap-2">
                  <span className="mt-0.5 text-emerald-500">✓</span>
                  {t}
                </li>
              ))}
            </ul>
          </div>

          <div className="relative rounded-2xl border border-slate-200 bg-white p-4 shadow-card-hover md:p-5">
            <div className="mb-3 flex items-center justify-between">
              <span className="text-sm font-bold text-slate-800">Organizaciones</span>
              <span className="rounded-lg bg-secondary/10 px-2 py-1 text-[10px] font-bold uppercase text-secondary">
                SaaS
              </span>
            </div>
            <ul className="space-y-2">
              {ORGS.map((o) => (
                <li
                  key={o.name}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-100 bg-slate-50 px-3 py-2.5 text-xs md:text-sm"
                >
                  <div>
                    <p className="font-semibold text-slate-900">{o.name}</p>
                    <p className="text-slate-500">{o.host}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-bold text-emerald-800">
                      {o.status}
                    </span>
                    <span className="font-mono text-slate-600">{o.members} miemb.</span>
                  </div>
                </li>
              ))}
            </ul>
            <button
              type="button"
              className="mt-4 w-full rounded-xl bg-secondary py-2.5 text-sm font-bold text-white shadow-md transition hover:bg-blue-600"
            >
              + Nueva organización
            </button>

            <div className="pointer-events-none absolute -bottom-6 -right-6 h-28 w-28 rounded-full border-2 border-dashed border-sky-300/60" />
            <div className="pointer-events-none absolute -top-4 right-8 h-3 w-3 rounded-full bg-sky-400 shadow-[0_0_12px_rgba(56,189,248,0.8)]" />
          </div>
        </div>
      </div>
    </section>
  )
}
