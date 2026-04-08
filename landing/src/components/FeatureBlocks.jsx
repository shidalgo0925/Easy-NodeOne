const blocks = [
  {
    title: 'Gestion de clientes',
    items: ['Lista de contactos', 'Historial de interacciones'],
  },
  {
    title: 'Bandeja de conversaciones',
    items: ['Chats organizados', 'Vista centralizada por equipo'],
  },
  {
    title: 'Seguimiento de ventas',
    items: ['Estado de leads', 'Pipeline simple'],
  },
  {
    title: 'Multiusuario',
    items: ['Varios agentes', 'Colaboracion por roles'],
  },
]

export default function FeatureBlocks() {
  return (
    <section id="features-detail" className="px-4 py-12 md:py-16">
      <div className="mx-auto max-w-6xl">
        <h2 className="text-center text-3xl font-bold text-gray-dark md:text-4xl">Funciones principales</h2>
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
