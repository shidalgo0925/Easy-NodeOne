/**
 * Imagen de producto referencial (mockups de alta fidelidad).
 * Bordes suaves, sombra y lazy-load para no penalizar LCP en la parte superior.
 */
export default function ProductFigure({ src, alt, caption, priority = false, className = '' }) {
  return (
    <figure className={`mx-auto max-w-5xl ${className}`.trim()}>
      <div className="overflow-hidden rounded-2xl border border-slate-200/90 bg-white shadow-[0_20px_50px_-12px_rgba(15,23,42,0.18)] ring-1 ring-slate-900/5">
        <img
          src={src}
          alt={alt}
          width={1200}
          height={675}
          loading={priority ? 'eager' : 'lazy'}
          decoding="async"
          className="h-auto w-full object-cover object-top"
        />
      </div>
      {caption ? (
        <figcaption className="mt-3 text-center text-sm text-slate-500">{caption}</figcaption>
      ) : null}
    </figure>
  )
}
