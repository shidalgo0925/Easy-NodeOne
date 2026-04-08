const today = ['Gestionar contactos', 'Ver historial de conversaciones', 'Dar seguimiento a leads']
const soon = ['Automatizacion', 'Integraciones avanzadas', 'IA']

export default function TodayAndSoon() {
  return (
    <section className="px-4 py-12 md:py-16">
      <div className="mx-auto grid max-w-6xl gap-6 md:grid-cols-2">
        <div className="rounded-2xl border border-gray-mid/15 bg-white p-6 shadow-soft">
          <h3 className="text-2xl font-bold text-gray-dark">Que puedes hacer hoy</h3>
          <ul className="mt-5 space-y-3 text-gray-mid">
            {today.map((item) => (
              <li key={item}>- {item}</li>
            ))}
          </ul>
        </div>
        <div className="rounded-2xl border border-secondary/20 bg-secondary/5 p-6">
          <h3 className="text-2xl font-bold text-gray-dark">Proximamente</h3>
          <ul className="mt-5 space-y-3 text-gray-mid">
            {soon.map((item) => (
              <li key={item}>- {item}</li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  )
}
