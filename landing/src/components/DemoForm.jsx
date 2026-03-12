export default function DemoForm() {
  return (
    <section id="demo" className="px-4 py-20 md:py-28">
      <div className="mx-auto max-w-xl">
        <h2 className="text-center text-2xl font-bold text-gray-dark md:text-3xl">Solicitar Demo</h2>
        <form className="mt-10 space-y-4 rounded-2xl bg-white p-8 shadow-soft">
          <input type="text" placeholder="Nombre" className="w-full rounded-lg border border-gray-mid/30 px-4 py-2.5" />
          <input type="text" placeholder="Organización" className="w-full rounded-lg border border-gray-mid/30 px-4 py-2.5" />
          <input type="email" placeholder="Email" className="w-full rounded-lg border border-gray-mid/30 px-4 py-2.5" />
          <input type="tel" placeholder="Teléfono" className="w-full rounded-lg border border-gray-mid/30 px-4 py-2.5" />
          <input type="text" placeholder="Tamaño organización" className="w-full rounded-lg border border-gray-mid/30 px-4 py-2.5" />
          <textarea placeholder="Mensaje" rows={3} className="w-full rounded-lg border border-gray-mid/30 px-4 py-2.5" />
          <button
            type="submit"
            className="w-full rounded-xl bg-gradient-official py-3.5 font-semibold text-white shadow-soft"
          >
            Enviar
          </button>
        </form>
      </div>
    </section>
  )
}
