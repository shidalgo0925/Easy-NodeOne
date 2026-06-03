import ProductFigure from './ProductFigure'

const STATUSES = [
  { code: 'pending_review', label: 'Pendiente de revisión', bg: 'bg-amber-100', text: 'text-amber-900' },
  { code: 'awaiting_validation', label: 'En validación', bg: 'bg-sky-100', text: 'text-sky-900' },
  { code: 'approved', label: 'Aprobado', bg: 'bg-emerald-500', text: 'text-white' },
  { code: 'active', label: 'Activo', bg: 'bg-emerald-100', text: 'text-emerald-900' },
]

function FakeQR() {
  const cells = Array.from({ length: 64 }, (_, i) => {
    const row = Math.floor(i / 8)
    const col = i % 8
    const on = (row + col) % 3 === 0 || (row * col) % 7 < 3
    return on
  })
  return (
    <div className="grid grid-cols-8 gap-px rounded-md bg-slate-900 p-1">
      {cells.map((on, i) => (
        <div key={i} className={`aspect-square ${on ? 'bg-white' : 'bg-slate-900'}`} />
      ))}
    </div>
  )
}

export default function AutomationShowcase() {
  return (
    <section id="automatizacion" className="scroll-mt-24 bg-white px-4 py-16 md:py-24">
      <div className="mx-auto max-w-6xl">
        <h2 className="text-center text-3xl font-bold tracking-tight text-slate-900 md:text-4xl">
          Automatiza operaciones críticas
        </h2>
        <p className="mx-auto mt-3 max-w-2xl text-center text-slate-600 md:text-lg">
          Pagos, activaciones, certificados, correos y workflows con estados visibles para tu equipo y tus usuarios.
        </p>

        <div className="mt-12 grid gap-6 lg:grid-cols-2">
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5 shadow-sm">
            <h3 className="text-sm font-bold uppercase tracking-wide text-slate-500">Pagos y estados</h3>
            <ul className="mt-4 space-y-2">
              {STATUSES.map((s) => (
                <li key={s.code} className="flex flex-wrap items-center gap-2 text-xs md:text-sm">
                  <code className={`rounded-md px-2 py-1 font-mono text-[10px] font-semibold ${s.bg} ${s.text}`}>{s.code}</code>
                  <span className="text-slate-600">{s.label}</span>
                </li>
              ))}
            </ul>
            <p className="mt-4 text-xs text-slate-500">
              Flujos con revisión administrativa, reglas por monto y activación automática al aprobar.
            </p>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5 shadow-sm">
            <h3 className="text-sm font-bold uppercase tracking-wide text-slate-500">Workflow de aprobación</h3>
            <div className="mt-4 flex flex-col items-stretch gap-2">
              <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-center text-xs font-medium text-slate-700">
                Pago registrado
              </div>
              <div className="text-center text-slate-400">↓</div>
              <div className="rounded-lg border border-sky-200 bg-sky-50 px-3 py-2 text-center text-xs">
                <span className="font-bold text-sky-900">En validación</span>
                <p className="text-[10px] text-sky-700">Revisión administrativa</p>
              </div>
              <div className="text-center text-slate-400">↓</div>
              <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-center text-xs">
                <span className="font-bold text-emerald-800">Aprobado → activación</span>
                <p className="text-[10px] text-emerald-700">Disparos de email y acceso a portal</p>
              </div>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm lg:col-span-2">
            <div className="grid gap-6 md:grid-cols-[1fr_auto] md:items-center">
              <div>
                <h3 className="text-sm font-bold uppercase tracking-wide text-slate-500">Certificados con verificación</h3>
                <p className="mt-2 max-w-md text-sm text-slate-600">
                  Plantillas institucionales, ID único y QR para validar emisión sin depender de PDFs sueltos.
                </p>
                <ul className="mt-4 flex flex-wrap gap-2 text-[11px] font-semibold text-slate-600">
                  {['Emails automáticos', 'Activaciones', 'Auditoría', 'Descarga segura'].map((x) => (
                    <li key={x} className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1">
                      {x}
                    </li>
                  ))}
                </ul>
              </div>
              <div className="mx-auto max-w-[200px] rounded-xl border border-slate-200 bg-gradient-to-b from-amber-50/80 to-white p-4 shadow-inner">
                <p className="text-center text-[9px] font-serif font-bold uppercase tracking-widest text-amber-900/80">
                  Certificado
                </p>
                <p className="mt-2 text-center text-lg font-bold text-slate-900">Ana Torres</p>
                <div className="mt-3 flex items-end justify-between gap-2">
                  <FakeQR />
                  <p className="text-[9px] font-mono text-slate-500">ID: CERT-2026-000123</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <ProductFigure
          className="mt-8"
          src="/images/product/automatizacion-workflows.png"
          alt="Constructor visual de workflows en EN1: disparadores, condiciones y acciones."
          caption="Automatización y workflows — referencia de producto para activaciones, correos y certificados."
        />
      </div>
    </section>
  )
}
