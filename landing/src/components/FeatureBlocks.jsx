const blocks = [
  {
    title: 'Membresías y socios',
    items: ['Planes y renovaciones', 'Estados y segmentos', 'Portal del socio'],
  },
  {
    title: 'Eventos y formación',
    items: ['Inscripciones y cupos', 'Listas y check-in', 'Comunicación por cohorte'],
  },
  {
    title: 'Pagos y conciliación',
    items: ['Pasarelas', 'Aprobaciones y workflows', 'Activación automática'],
  },
  {
    title: 'Certificación',
    items: ['Plantillas', 'QR y verificación', 'Emisión masiva'],
  },
]

export default function FeatureBlocks() {
  return (
    <section id="features-detail" className="px-4 py-12 md:py-16">
      <div className="mx-auto max-w-6xl">
        <h2 className="text-center text-3xl font-bold text-gray-dark md:text-4xl">Funciones principales</h2>
        <p className="mx-auto mt-3 max-w-2xl text-center text-gray-mid">
          Vista resumida del núcleo operativo; el detalle por módulo está en la home y en tu instancia.
        </p>
        <div className="mt-8 grid gap-5 md:grid-cols-2">
          {blocks.map((block) => (
            <div key={block.title} className="rounded-2xl border border-gray-mid/15 bg-white p-6 shadow-soft">
              <h3 className="text-xl font-semibold text-gray-dark">{block.title}</h3>
              <ul className="mt-4 space-y-2 text-gray-mid">
                {block.items.map((item) => (
                  <li key={item}>- {item}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
