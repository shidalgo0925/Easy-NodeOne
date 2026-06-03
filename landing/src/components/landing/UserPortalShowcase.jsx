const menu = ['Resumen', 'Membresías', 'Eventos', 'Certificados', 'Pagos', 'Perfil']

export default function UserPortalShowcase() {
  return (
    <section id="portal" className="scroll-mt-24 bg-slate-50 px-4 py-16 md:py-24">
      <div className="mx-auto max-w-6xl">
        <h2 className="text-center text-3xl font-bold tracking-tight text-slate-900 md:text-4xl">Portal del usuario</h2>
        <p className="mx-auto mt-3 max-w-2xl text-center text-slate-600 md:text-lg">
          Cada persona ve sus membresías, eventos, certificados y pagos en un solo panel coherente con la marca de
          tu organización.
        </p>

        <div className="mx-auto mt-12 max-w-4xl overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-card-hover">
          <div className="flex min-h-[280px] flex-col md:flex-row">
            <aside className="border-b border-slate-200 bg-slate-50 md:w-48 md:border-b-0 md:border-r">
              <p className="border-b border-slate-200 px-4 py-3 text-xs font-bold uppercase tracking-wide text-slate-500">
                Mi cuenta
              </p>
              <nav className="flex flex-row gap-1 overflow-x-auto p-2 md:flex-col">
                {menu.map((item) => (
                  <div
                    key={item}
                    className={`shrink-0 rounded-lg px-3 py-2 text-xs font-semibold md:text-sm ${
                      item === 'Certificados' ? 'bg-sky-100 text-sky-900' : 'text-slate-600 hover:bg-white'
                    }`}
                  >
                    {item}
                  </div>
                ))}
              </nav>
            </aside>
            <div className="flex-1 p-4 md:p-6">
              <p className="text-sm font-bold text-slate-800">Mis certificados</p>
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                {[
                  { t: 'Certificado de IA', e: 'Workshop IA', d: 'Emitido: 20/05/2026' },
                  { t: 'Certificado Scrum', e: 'Scrum Master', d: 'Emitido: 10/05/2026' },
                ].map((c) => (
                  <div
                    key={c.t}
                    className="flex gap-3 rounded-xl border border-slate-100 bg-slate-50/80 p-3 transition hover:border-secondary/25"
                  >
                    <div className="h-14 w-10 shrink-0 rounded border border-amber-200/80 bg-gradient-to-b from-amber-100 to-white" />
                    <div>
                      <p className="text-sm font-bold text-slate-900">{c.t}</p>
                      <p className="text-xs text-slate-600">{c.e}</p>
                      <p className="mt-1 text-[10px] font-medium text-slate-500">{c.d}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
