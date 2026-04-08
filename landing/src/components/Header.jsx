import { useState } from 'react'

// URL de la app (Flask). En producción: VITE_APP_URL=https://app.easynodeone.com
const APP_URL = import.meta.env.VITE_APP_URL || ''

export default function Header() {
  const [mobileOpen, setMobileOpen] = useState(false)
  const nav = [
    { label: 'Plataforma', href: '/#plataforma' },
    { label: 'Módulos', href: '/#modulos' },
    { label: 'Planes', href: '/#planes' },
    { label: 'Seguridad', href: '/#seguridad' },
    { label: 'Contacto', href: '/#contacto' },
  ]

  return (
    <header className="sticky top-0 z-50 border-b border-gray-light bg-white/95 backdrop-blur-sm">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2 px-4 py-2">
        <a href="/" className="flex items-center shrink-0">
          <img src="/logos/logo-nodeone.png" alt="EasyNodeOne" className="h-14 w-auto md:h-16" />
        </a>

        {/* Desktop: enlaces + CTAs */}
        <nav className="hidden items-center gap-5 md:flex md:gap-6">
          {nav.map((item) => (
            <a
              key={item.label}
              href={item.href}
              className="text-base font-bold text-gray-mid hover:text-secondary"
            >
              {item.label}
            </a>
          ))}
        </nav>

        <div className="flex items-center gap-3">
          {/* Registrarse: outline azul */}
          <a
            href={`${APP_URL}/register`}
            className="rounded-xl border-2 border-secondary px-4 py-2 text-sm font-semibold text-secondary transition hover:bg-secondary/5 md:px-5 md:py-2.5 md:text-base"
          >
            Registrarse
          </a>
          {/* Iniciar sesión: gradiente principal */}
          <a
            href={`${APP_URL}/login`}
            className="rounded-xl bg-gradient-to-br from-secondary to-cyan px-4 py-2 text-sm font-semibold text-white shadow-md transition hover:opacity-95 md:px-5 md:py-2.5 md:text-base"
          >
            Iniciar sesión
          </a>

          {/* Mobile: hamburguesa */}
          <button
            type="button"
            onClick={() => setMobileOpen((o) => !o)}
            className="inline-flex items-center justify-center rounded-lg p-2 text-gray-mid hover:bg-gray-light md:hidden"
            aria-label={mobileOpen ? 'Cerrar menú' : 'Abrir menú'}
            aria-expanded={mobileOpen}
          >
            <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              {mobileOpen ? (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              ) : (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              )}
            </svg>
          </button>
        </div>
      </div>

      {/* Mobile: menú colapsable */}
      {mobileOpen && (
        <div className="border-t border-gray-light bg-white px-4 py-4 md:hidden">
          <nav className="flex flex-col gap-4">
            {nav.map((item) => (
              <a
                key={item.label}
                href={item.href}
                onClick={() => setMobileOpen(false)}
                className="font-bold text-gray-mid hover:text-secondary"
              >
                {item.label}
              </a>
            ))}
          </nav>
        </div>
      )}
    </header>
  )
}
