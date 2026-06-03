import ProductFigure from './ProductFigure'

/** Referencia visual “plataforma modular” justo debajo del hero. */
export default function PlatformProductStrip() {
  return (
    <section className="border-b border-slate-200 bg-white px-4 py-12 md:py-16" aria-labelledby="product-strip-title">
      <div className="mx-auto max-w-6xl text-center">
        <h2 id="product-strip-title" className="text-xl font-bold tracking-tight text-slate-900 md:text-2xl">
          Plataforma modular en acción
        </h2>
        <p className="mx-auto mt-2 max-w-2xl text-sm text-slate-600 md:text-base">
          Vista referencial del ecosistema EN1 en escritorio y móvil: mismo producto, misma identidad operativa.
        </p>
        <ProductFigure
          priority
          className="mt-8"
          src="/images/product/plataforma-modular.png"
          alt="Interfaz EN1: resumen modular con métricas de miembros, eventos, ingresos y certificados en escritorio y móvil."
          caption="Referencia visual de producto — la instancia puede variar según módulos activos y marca del tenant."
        />
      </div>
    </section>
  )
}
