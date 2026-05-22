const APP_URL = (import.meta.env.VITE_APP_URL || '').replace(/\/$/, '')

const navItems = [
  { label: 'Dashboard', active: true },
  { label: 'Miembros' },
  { label: 'Eventos' },
  { label: 'Pagos' },
  { label: 'Certificados' },
  { label: 'Académico' },
  { label: 'CRM' },
  { label: 'Marketing' },
]

const kpis = [
  { label: 'Miembros activos', value: '2.350', tone: 'text-emerald-400' },
  { label: 'Eventos', value: '18', tone: 'text-sky-400' },
  { label: 'Ingresos', value: '$24.780', tone: 'text-violet-300' },
  { label: 'Certificados', value: '1.320', tone: 'text-amber-300' },
]

function MiniSpark() {
  return (
    <svg className="h-8 w-full text-emerald-500/80" viewBox="0 0 80 24" preserveAspectRatio="none">
      <path
        d="M0 18 L12 14 L22 16 L34 8 L46 12 L58 6 L70 10 L80 4"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  )
}

function DashboardMock() {
  return (
    <div className="relative rounded-2xl border border-white/10 bg-slate-900/90 shadow-[0_24px_80px_-12px_rgba(0,0,0,0.65)] ring-1 ring-white/5">
      <div className="flex items-center justify-between gap-2 border-b border-white/10 px-3 py-2.5 md:px-4">
        <div className="flex min-w-0 items-center gap-2">
          <img src="/logos/logo-nodeone.png" alt="" className="h-8 w-auto shrink-0 opacity-95" width="120" height="32" />
          <span className="hidden truncate text-[10px] font-semibold uppercase tracking-wider text-slate-500 sm:inline">
            EN1
          </span>
        </div>
        <div className="hidden flex-1 justify-center sm:flex">
          <div className="flex h-8 w-full max-w-[200px] items-center rounded-lg border border-white/10 bg-slate-800/80 px-3 text-[11px] text-slate-500">
            Buscar…
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2 rounded-lg border border-white/10 bg-slate-800/80 px-2 py-1">
          <div className="h-6 w-6 rounded-full bg-gradient-to-br from-secondary to-cyan" />
          <span className="hidden text-xs font-medium text-slate-200 md:inline">Admin</span>
        </div>
      </div>
      <div className="flex min-h-[220px] md:min-h-[260px]">
        <aside className="hidden w-36 shrink-0 flex-col gap-0.5 border-r border-white/10 bg-slate-950/80 py-2 pl-2 pr-1 md:flex">
          {navItems.map((n) => (
            <div
              key={n.label}
              className={`rounded-md px-2 py-1.5 text-[11px] font-medium ${
                n.active ? 'bg-secondary/25 text-white' : 'text-slate-500 hover:bg-white/5'
              }`}
            >
              {n.label}
            </div>
          ))}
        </aside>
        <div className="flex flex-1 flex-col gap-3 p-3 md:p-4">
          <div className="grid grid-cols-2 gap-2 lg:grid-cols-4">
            {kpis.map((k) => (
              <div
                key={k.label}
                className="rounded-xl border border-white/10 bg-slate-800/50 p-2.5 shadow-inner md:p-3"
              >
                <p className="text-[10px] font-medium uppercase tracking-wide text-slate-500">{k.label}</p>
                <p className={`mt-1 text-lg font-bold tabular-nums text-white md:text-xl ${k.tone}`}>{k.value}</p>
                <MiniSpark />
              </div>
            ))}
          </div>
          <div className="grid flex-1 gap-2 md:grid-cols-2">
            <div className="rounded-xl border border-white/10 bg-slate-800/40 p-3">
              <p className="text-[11px] font-semibold text-slate-400">Actividad reciente</p>
              <ul className="mt-2 space-y-2">
                {[
                  { t: 'Nueva inscripción', sub: 'Programa IA · hace 12 min', dot: 'bg-sky-400' },
                  { t: 'Pago recibido', sub: 'Membresía Pro · hace 28 min', dot: 'bg-emerald-400' },
                  { t: 'Certificado emitido', sub: 'Evento Scrum · hace 1 h', dot: 'bg-amber-400' },
                ].map((row) => (
                  <li key={row.t} className="flex gap-2 text-[11px]">
                    <span className={`mt-1 h-2 w-2 shrink-0 rounded-full ${row.dot}`} />
                    <div>
                      <p className="font-medium text-slate-200">{row.t}</p>
                      <p className="text-slate-500">{row.sub}</p>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
            <div className="rounded-xl border border-white/10 bg-slate-800/40 p-3">
              <p className="text-[11px] font-semibold text-slate-400">Ingresos por mes</p>
              <div className="mt-3 flex h-[100px] items-end justify-between gap-1 px-1">
                {['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun'].map((m, i) => (
                  <div key={m} className="flex flex-1 flex-col items-center gap-1">
                    <div
                      className="w-full max-w-[28px] rounded-t bg-gradient-to-t from-secondary/30 to-cyan/80"
                      style={{ height: `${32 + i * 10}px` }}
                    />
                    <span className="text-[9px] text-slate-500">{m}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function HeroPlatform() {
  return (
    <section
      id="inicio"
      className="relative overflow-hidden bg-gradient-to-b from-slate-950 via-[#050a1f] to-black px-4 pb-16 pt-8 md:pb-24 md:pt-12"
    >
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_100%_60%_at_50%_-10%,rgba(37,99,235,0.22),transparent)]" />
      <div className="relative mx-auto grid max-w-6xl gap-10 lg:grid-cols-[1fr_1.05fr] lg:items-center lg:gap-12">
        <div>
          <div className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-3 py-1 text-[10px] font-bold uppercase tracking-[0.18em] text-slate-300">
            <img src="/logos/logo-nodeone.png" alt="EasyNodeOne" className="h-6 w-auto opacity-90" />
            <span>Plataforma modular</span>
          </div>
          <h1 className="mt-5 text-3xl font-bold leading-[1.12] tracking-tight text-white md:text-4xl lg:text-[2.65rem]">
            Centraliza miembros, eventos, pagos, certificados y operaciones en una sola{' '}
            <span className="bg-gradient-to-r from-sky-400 to-cyan-300 bg-clip-text text-transparent">
              plataforma modular
            </span>
            .
          </h1>
          <p className="mt-5 max-w-xl text-base leading-relaxed text-slate-400 md:text-lg">
            EN1 conecta membresías, eventos, cobros, certificación, CRM y marketing en un ecosistema multi-tenant
            pensado para instituciones, asociaciones y empresas que operan a escala.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <a
              href="/#contacto"
              className="inline-flex items-center justify-center rounded-xl bg-gradient-to-r from-secondary to-cyan px-5 py-3 text-sm font-bold text-white shadow-lg shadow-blue-500/25 transition hover:opacity-95"
            >
              Solicitar demo
            </a>
            <a
              href="/#ecosistema"
              className="inline-flex items-center justify-center rounded-xl border-2 border-white/25 bg-white/5 px-5 py-3 text-sm font-bold text-white backdrop-blur transition hover:bg-white/10"
            >
              Ver módulos
            </a>
            <a
              href="/#portal"
              className="inline-flex items-center justify-center rounded-xl border border-white/15 px-5 py-3 text-sm font-semibold text-slate-200 transition hover:border-white/30 hover:text-white"
            >
              Explorar plataforma
            </a>
            {APP_URL ? (
              <a
                href={`${APP_URL}/login`}
                className="inline-flex items-center justify-center rounded-xl px-3 py-3 text-sm font-medium text-slate-500 underline-offset-4 hover:text-slate-300"
              >
                Ir al login
              </a>
            ) : null}
          </div>
          <div className="mt-8 flex flex-wrap gap-4 text-xs font-semibold text-slate-500">
            {['Multi-tenant', 'Seguro', 'Escalable', 'API first'].map((x) => (
              <span key={x} className="flex items-center gap-1.5">
                <span className="h-1.5 w-1.5 rounded-full bg-cyan-400" />
                {x}
              </span>
            ))}
          </div>
        </div>
        <div className="relative">
          <div className="pointer-events-none absolute -inset-4 rounded-3xl bg-gradient-to-br from-secondary/20 to-cyan/10 blur-2xl" />
          <DashboardMock />
        </div>
      </div>
    </section>
  )
}
