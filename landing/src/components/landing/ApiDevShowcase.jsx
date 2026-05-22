const APP_URL = (import.meta.env.VITE_APP_URL || '').replace(/\/$/, '')

const logos = ['Stripe', 'PayPal', 'Mailchimp', 'Twilio', 'Zoom']

export default function ApiDevShowcase() {
  return (
    <section id="apis" className="scroll-mt-24 bg-slate-100 px-4 py-16 md:py-24">
      <div className="mx-auto max-w-6xl">
        <h2 className="text-center text-3xl font-bold tracking-tight text-slate-900 md:text-4xl">API, integraciones y extensión</h2>
        <p className="mx-auto mt-3 max-w-2xl text-center text-slate-600 md:text-lg">
          Conectá cobros, comunicaciones y reuniones. EN1 está pensado para crecer con webhooks y API REST coherente.
        </p>

        <div className="mt-12 grid gap-6 lg:grid-cols-3">
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="text-lg font-bold text-slate-900">Integraciones</h3>
            <p className="mt-2 text-sm text-slate-600">
              Pasarelas y herramientas de mensajería; el detalle técnico evoluciona por versión de instancia.
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              {logos.map((name) => (
                <span
                  key={name}
                  className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-bold text-slate-700"
                >
                  {name}
                </span>
              ))}
            </div>
            <a
              href="/integrations"
              className="mt-5 inline-block rounded-xl border-2 border-slate-300 px-4 py-2 text-sm font-semibold text-slate-800 transition hover:border-secondary hover:text-secondary"
            >
              Ver documentación
            </a>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5 text-slate-100 shadow-xl">
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold text-slate-300">Ejemplo de API</span>
              <span className="rounded bg-emerald-500/20 px-2 py-0.5 text-[10px] font-bold text-emerald-300">200 OK</span>
            </div>
            <pre className="mt-3 overflow-x-auto text-[11px] leading-relaxed">
              <code>
                <span className="text-sky-300">GET</span> <span className="text-slate-400">/api/v1/members</span>
                {'\n\n'}
                <span className="text-purple-300">{'{'}</span>
                {'\n'}
                {'  '}<span className="text-sky-300">&quot;data&quot;</span>
                <span className="text-slate-500">: [</span>
                {'\n'}
                {'    '}
                <span className="text-purple-300">{'{'}</span>
                {'\n'}
                {'      '}
                <span className="text-sky-300">&quot;id&quot;</span>
                <span className="text-slate-500">: </span>
                <span className="text-amber-300">1</span>
                <span className="text-slate-500">, </span>
                {'\n'}
                {'      '}
                <span className="text-sky-300">&quot;name&quot;</span>
                <span className="text-slate-500">: </span>
                <span className="text-emerald-300">&quot;Ana Torres&quot;</span>
                <span className="text-slate-500">, </span>
                {'\n'}
                {'      '}
                <span className="text-sky-300">&quot;status&quot;</span>
                <span className="text-slate-500">: </span>
                <span className="text-emerald-300">&quot;active&quot;</span>
                {'\n'}
                {'    '}
                <span className="text-purple-300">{'}'}</span>
                {'\n'}
                {'  '}
                <span className="text-slate-500">]</span>
                {'\n'}
                <span className="text-purple-300">{'}'}</span>
              </code>
            </pre>
          </div>

          <div className="flex flex-col justify-center rounded-2xl bg-gradient-to-br from-secondary via-blue-600 to-violet-700 p-6 text-white shadow-xl">
            <h3 className="text-xl font-bold">¿Listo para operar con EN1?</h3>
            <p className="mt-2 text-sm text-white/90">Agendá una demo técnica o comercial con el equipo.</p>
            <a
              href="/#contacto"
              className="mt-5 inline-flex justify-center rounded-xl bg-white/15 px-4 py-3 text-center text-sm font-bold text-white ring-1 ring-white/30 backdrop-blur transition hover:bg-white/25"
            >
              Solicitar demo
            </a>
            <p className="mt-4 text-center text-xs text-white/80">
              o escríbenos a{' '}
              <a href="mailto:info@easynodeone.com" className="font-semibold underline">
                info@easynodeone.com
              </a>
            </p>
            {APP_URL ? (
              <a href={`${APP_URL}/register`} className="mt-2 text-center text-xs text-white/70 underline">
                Crear cuenta en la instancia pública
              </a>
            ) : null}
          </div>
        </div>
      </div>
    </section>
  )
}
