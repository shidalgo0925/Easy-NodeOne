import { useEffect, useMemo } from 'react'
import Header from './components/Header'
import Hero from './components/Hero'
import Problem from './components/Problem'
import Solution from './components/Solution'
import HowItWorks from './components/HowItWorks'
import MultiTenant from './components/MultiTenant'
import Security from './components/Security'
import Plans from './components/Plans'
import CTA from './components/CTA'
import DemoForm from './components/DemoForm'
import Footer from './components/Footer'
import Benefits from './components/Benefits'
import TodayAndSoon from './components/TodayAndSoon'
import FeatureBlocks from './components/FeatureBlocks'
import WhatsAppFloat from './components/WhatsAppFloat'

const SEO_BY_PAGE = {
  home: {
    title: 'EasyNodeOne | Gestión de clientes y conversaciones',
    description:
      'Gestiona clientes, conversaciones y ventas desde una sola plataforma. Mejora tu atención y seguimiento comercial con EasyNodeOne.',
    path: '/',
  },
  features: {
    title: 'Funciones | EasyNodeOne',
    description:
      'Descubre las funciones de EasyNodeOne para gestionar clientes, conversaciones y seguimiento comercial.',
    path: '/features',
  },
  pricing: {
    title: 'Precios | EasyNodeOne',
    description: 'Planes claros para gestionar clientes, conversaciones y seguimiento comercial.',
    path: '/pricing',
  },
  contact: {
    title: 'Contacto | EasyNodeOne',
    description:
      'Solicita una demo de EasyNodeOne y recibe asesoría para implementar tu operación comercial.',
    path: '/contact',
  },
  useCases: {
    title: 'Casos de uso | EasyNodeOne',
    description:
      'Casos de uso por industria para aplicar EasyNodeOne en ventas, atención y seguimiento.',
    path: '/use-cases',
  },
  integrations: {
    title: 'Integraciones | EasyNodeOne',
    description:
      'Conoce las integraciones disponibles y próximas para conectar EasyNodeOne con tu operación.',
    path: '/integrations',
  },
}

function upsertMeta(attrName, attrValue, content) {
  let tag = document.head.querySelector(`meta[${attrName}="${attrValue}"]`)
  if (!tag) {
    tag = document.createElement('meta')
    tag.setAttribute(attrName, attrValue)
    document.head.appendChild(tag)
  }
  tag.setAttribute('content', content)
}

function upsertLink(rel, href) {
  let link = document.head.querySelector(`link[rel="${rel}"]`)
  if (!link) {
    link = document.createElement('link')
    link.setAttribute('rel', rel)
    document.head.appendChild(link)
  }
  link.setAttribute('href', href)
}

export default function App() {
  const page = useMemo(() => {
    const p = window.location.pathname.replace(/\/+$/, '') || '/'
    if (p === '/pricing') return 'pricing'
    if (p === '/contact') return 'contact'
    if (p === '/features') return 'features'
    if (p === '/use-cases') return 'useCases'
    if (p === '/integrations') return 'integrations'
    return 'home'
  }, [])

  useEffect(() => {
    const site = 'https://easynodeone.com'
    const seo = SEO_BY_PAGE[page]
    const canonicalUrl = `${site}${seo.path}`
    document.documentElement.lang = 'es'
    document.title = seo.title
    upsertMeta('name', 'description', seo.description)
    upsertMeta('property', 'og:type', 'website')
    upsertMeta('property', 'og:title', seo.title)
    upsertMeta('property', 'og:description', seo.description)
    upsertMeta('property', 'og:url', canonicalUrl)
    upsertMeta('property', 'og:image', `${site}/logos/logo-nodeone.png`)
    upsertMeta('name', 'twitter:card', 'summary_large_image')
    upsertMeta('name', 'twitter:title', seo.title)
    upsertMeta('name', 'twitter:description', seo.description)
    upsertMeta('name', 'twitter:image', `${site}/logos/logo-nodeone.png`)
    upsertLink('canonical', canonicalUrl)
  }, [page])

  return (
    <>
      <Header />
      <main>
        {page === 'home' && (
          <>
            <Hero />
            <Problem />
            <Benefits />
            <TodayAndSoon />
            <Solution />
            <HowItWorks />
            <MultiTenant />
            <Security />
            <Plans />
            <CTA />
            <DemoForm />
          </>
        )}
        {page === 'features' && (
          <>
            <Hero />
            <FeatureBlocks />
            <Solution />
            <Problem />
            <HowItWorks />
            <MultiTenant />
            <Security />
            <CTA />
          </>
        )}
        {page === 'pricing' && (
          <>
            <Hero />
            <Plans />
            <CTA />
            <DemoForm />
          </>
        )}
        {page === 'contact' && (
          <>
            <Hero />
            <DemoForm />
          </>
        )}
        {page === 'useCases' && (
          <>
            <Hero />
            <section className="px-4 py-12 md:py-16">
              <div className="mx-auto max-w-4xl rounded-2xl border border-gray-mid/15 bg-white p-6 shadow-soft">
                <h2 className="text-3xl font-bold text-gray-dark">Casos de uso</h2>
                <p className="mt-4 text-gray-mid">Pagina en preparacion. Incluira escenarios para ventas, atencion y seguimiento por industria.</p>
              </div>
            </section>
            <CTA />
          </>
        )}
        {page === 'integrations' && (
          <>
            <Hero />
            <section className="px-4 py-12 md:py-16">
              <div className="mx-auto max-w-4xl rounded-2xl border border-gray-mid/15 bg-white p-6 shadow-soft">
                <h2 className="text-3xl font-bold text-gray-dark">Integraciones</h2>
                <p className="mt-4 text-gray-mid">Pagina en preparacion. Mostrara integraciones disponibles y roadmap de conectores.</p>
              </div>
            </section>
            <CTA />
          </>
        )}
      </main>
      <Footer />
      <WhatsAppFloat />
    </>
  )
}
