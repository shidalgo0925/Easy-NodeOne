import ProductFigure from './ProductFigure'

const ROWS = [
  { sector: 'Institutos', uso: 'Diplomados, cohortes y certificación' },
  { sector: 'Asociaciones', uso: 'Membresías, renovaciones y beneficios' },
  { sector: 'Empresas', uso: 'Entrenamientos y desarrollo interno' },
  { sector: 'Eventos', uso: 'Registros, pagos y check-in' },
  { sector: 'Educación', uso: 'Programas académicos y trazabilidad' },
]

export default function UseCasesEN1() {
  return (
    <section id="casos" className="scroll-mt-24 bg-white px-4 py-16 md:py-24">
      <div className="mx-auto max-w-6xl">
        <h2 className="text-center text-3xl font-bold tracking-tight text-slate-900 md:text-4xl">
          Casos de uso por sector
        </h2>
        <p className="mx-auto mt-3 max-w-2xl text-center text-slate-600 md:text-lg">
          Misma plataforma, distintas operaciones: el núcleo EN1 se adapta a tu modelo.
        </p>

        <div className="mt-12 overflow-hidden rounded-2xl border border-slate-200 shadow-soft">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50">
                <th className="px-4 py-3 font-bold text-slate-800 md:px-6">Sector</th>
                <th className="px-4 py-3 font-bold text-slate-800 md:px-6">Uso típico en EN1</th>
              </tr>
            </thead>
            <tbody>
              {ROWS.map((r) => (
                <tr key={r.sector} className="border-b border-slate-100 last:border-0 hover:bg-slate-50/80">
                  <td className="px-4 py-4 font-semibold text-secondary md:px-6">{r.sector}</td>
                  <td className="px-4 py-4 text-slate-700 md:px-6">{r.uso}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="mt-8 grid gap-3 sm:grid-cols-2 md:grid-cols-5">
          {ROWS.map((r) => (
            <div
              key={r.sector}
              className="rounded-xl border border-slate-200 bg-slate-50/80 p-4 shadow-sm transition hover:border-secondary/30 hover:shadow-md"
            >
              <p className="text-xs font-bold uppercase tracking-wide text-secondary">{r.sector}</p>
              <p className="mt-2 text-xs text-slate-600">{r.uso}</p>
            </div>
          ))}
        </div>

        <ProductFigure
          className="mt-8"
          src="/images/product/soluciones-organizaciones.png"
          alt="Soluciones EN1 por tipo de organización: institutos, asociaciones, empresas, eventos, educación y sector público."
          caption="Vista referencial de soluciones por sector — sin fotos de stock en vivo; material de diseño de producto."
        />
      </div>
    </section>
  )
}
