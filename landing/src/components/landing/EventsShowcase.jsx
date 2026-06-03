export default function EventsShowcase() {
  return (
    <section id="eventos" className="scroll-mt-24 bg-white px-4 py-12 md:py-16">
      <div className="mx-auto max-w-6xl">
        <div className="grid gap-8 lg:grid-cols-2 lg:items-center">
          <div>
            <h2 className="text-2xl font-bold text-slate-900 md:text-3xl">Eventos e inscripciones</h2>
            <p className="mt-3 text-slate-600">
              Cupos, listas, confirmación y cobro en el mismo flujo. Incluye vista de calendario y agenda del día en el
              panel de eventos.
            </p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="text-slate-500">
                  <th className="pb-2 font-semibold">Participante</th>
                  <th className="pb-2 font-semibold">Estado</th>
                  <th className="pb-2 font-semibold">Pago</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {[
                  ['María López', 'Confirmado', 'Pagado'],
                  ['Luis Prado', 'Lista de espera', 'Pendiente'],
                  ['Ana Torres', 'Confirmado', 'Pagado'],
                ].map(([a, b, c]) => (
                  <tr key={a}>
                    <td className="py-2 font-medium text-slate-800">{a}</td>
                    <td className="py-2 text-slate-600">{b}</td>
                    <td className="py-2">
                      <span
                        className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${
                          c === 'Pagado' ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-900'
                        }`}
                      >
                        {c}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>
  )
}
