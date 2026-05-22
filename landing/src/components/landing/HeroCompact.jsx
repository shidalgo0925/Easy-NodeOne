import { HERO_COMPACT_TITLES } from './heroCompactTitles'

export default function HeroCompact({ page }) {
  const title = HERO_COMPACT_TITLES[page] || 'EasyNodeOne'

  return (
    <section className="relative overflow-hidden bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 px-4 py-14 md:py-16">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_80%_50%_at_50%_-20%,rgba(37,99,235,0.35),transparent)]" />
      <div className="relative mx-auto max-w-4xl text-center">
        <p className="text-xs font-bold uppercase tracking-[0.2em] text-cyan-300/90">EasyNodeOne · EN1</p>
        <h1 className="mt-3 text-3xl font-bold tracking-tight text-white md:text-4xl">{title}</h1>
        <p className="mx-auto mt-4 max-w-xl text-sm text-slate-300 md:text-base">
          Plataforma modular multi-tenant: miembros, eventos, pagos, certificados y más.
        </p>
      </div>
    </section>
  )
}
