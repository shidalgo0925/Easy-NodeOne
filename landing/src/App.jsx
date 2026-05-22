import { useEffect, useMemo } from 'react'
import Header from './components/Header'
import Hero from './components/Hero'
import PlatformProductStrip from './components/landing/PlatformProductStrip'
import EcosystemEN1 from './components/landing/EcosystemEN1'
import UseCasesEN1 from './components/landing/UseCasesEN1'
import MultiTenantShowcase from './components/landing/MultiTenantShowcase'
import AutomationShowcase from './components/landing/AutomationShowcase'
import EventsShowcase from './components/landing/EventsShowcase'
import AcademicShowcase from './components/landing/AcademicShowcase'
import UserPortalShowcase from './components/landing/UserPortalShowcase'
import AdminShowcase from './components/landing/AdminShowcase'
import ApiDevShowcase from './components/landing/ApiDevShowcase'
import SecurityTrustBand from './components/landing/SecurityTrustBand'
import Plans from './components/Plans'
import DemoForm from './components/DemoForm'
import Footer from './components/Footer'
import FeatureBlocks from './components/FeatureBlocks'
import WhatsAppFloat from './components/WhatsAppFloat'

const SEO_BY_PAGE = {
  home: {
    title: 'EasyNodeOne | Plataforma modular multi-tenant',
    description:
      'EN1 centraliza miembros, eventos, pagos, certificados, CRM y marketing en un ecosistema SaaS para instituciones y asociaciones.',
    path: '/',
  },
  features: {
    title: 'Funciones | EasyNodeOne',
    description:
      'Módulos EN1: membresías, eventos, pagos, certificados, académico, CRM, servicios y marketing en una sola plataforma.',
    path: '/features',
  },
  pricing: {
    title: 'Precios | EasyNodeOne',
    description: 'Planes para equipos que operan membresías, eventos y formación con EN1.',
    path: '/pricing',
  },
  contact: {
    title: 'Contacto | EasyNodeOne',
    description: 'Solicita una demo de EasyNodeOne y alinea tu operación con el ecosistema EN1.',
    path: '/contact',
  },
  useCases: {
    title: 'Casos de uso | EasyNodeOne',
    description: 'Institutos, asociaciones, empresas, eventos y educación operando con EN1.',
    path: '/use-cases',
  },
  integrations: {
    title: 'Integraciones | EasyNodeOne',
    description: 'Integraciones, API y extensibilidad del stack EN1.',
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
            <Hero page="home" />
            <PlatformProductStrip />
            <EcosystemEN1 />
            <UseCasesEN1 />
            <MultiTenantShowcase />
            <AutomationShowcase />
            <EventsShowcase />
            <AcademicShowcase />
            <UserPortalShowcase />
            <AdminShowcase />
            <ApiDevShowcase />
            <SecurityTrustBand />
            <Plans />
            <DemoForm />
          </>
        )}
        {page === 'features' && (
          <>
            <Hero page="features" />
            <FeatureBlocks />
            <EcosystemEN1 />
            <ApiDevShowcase />
            <DemoForm />
          </>
        )}
        {page === 'pricing' && (
          <>
            <Hero page="pricing" />
            <Plans />
            <DemoForm />
          </>
        )}
        {page === 'contact' && (
          <>
            <Hero page="contact" />
            <DemoForm />
          </>
        )}
        {page === 'useCases' && (
          <>
            <Hero page="useCases" />
            <UseCasesEN1 />
            <DemoForm />
          </>
        )}
        {page === 'integrations' && (
          <>
            <Hero page="integrations" />
            <ApiDevShowcase />
            <DemoForm />
          </>
        )}
      </main>
      <Footer />
      <WhatsAppFloat />
    </>
  )
}
