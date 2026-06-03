export default function AcademicShowcase() {
  return (
    <section id="academico" className="scroll-mt-24 border-y border-slate-200 bg-slate-50 px-4 py-16 md:py-20">
      <div className="mx-auto max-w-6xl">
        <div className="grid gap-10 lg:grid-cols-2 lg:items-center">
          <div>
            <h2 className="text-2xl font-bold tracking-tight text-slate-900 md:text-3xl">Académico: programas y cohortes</h2>
            <p className="mt-3 text-slate-600">
              Estructura de oferta formativa, inscripciones por cohorte y seguimiento de participación — alineado con
              certificación y pagos en el mismo ciclo de vida.
            </p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-soft">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2">
              <span className="text-sm font-bold text-slate-800">Programa · Data & IA</span>
              <span className="rounded-md bg-violet-100 px-2 py-0.5 text-[10px] font-bold text-violet-800">2026-2</span>
            </div>
            <div className="mt-3 grid gap-2 text-xs">
              {[
                { c: 'Cohorte A', ins: '32/40', estado: 'En curso' },
                { c: 'Cohorte B', ins: '18/40', estado: 'Inscripciones' },
                { c: 'Cohorte C', ins: '0/35', estado: 'Borrador' },
              ].map((row) => (
                <div key={row.c} className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2">
                  <span className="font-semibold text-slate-800">{row.c}</span>
                  <span className="text-slate-500">{row.ins}</span>
                  <span className="rounded-full bg-slate-200 px-2 py-0.5 text-[10px] font-bold text-slate-700">
                    {row.estado}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
