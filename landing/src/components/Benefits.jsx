const benefits = ['Responde mas rapido', 'No pierdas clientes', 'Organiza tu equipo']

export default function Benefits() {
  return (
    <section className="bg-gray-light/50 px-4 py-12 md:py-16">
      <div className="mx-auto max-w-6xl">
        <h2 className="text-center text-3xl font-bold text-gray-dark md:text-4xl">Beneficios para tu operacion diaria</h2>
        <div className="mt-8 grid gap-5 md:grid-cols-3">
          {benefits.map((item) => (
            <div key={item} className="rounded-2xl bg-white p-5 shadow-soft">
              <p className="text-lg font-semibold text-gray-dark">{item}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
