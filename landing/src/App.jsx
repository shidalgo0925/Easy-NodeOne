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

export default function App() {
  return (
    <>
      <Header />
      <main>
        <Hero />
        <Problem />
        <Solution />
        <HowItWorks />
        <MultiTenant />
        <Security />
        <Plans />
        <CTA />
        <DemoForm />
      </main>
      <Footer />
    </>
  )
}
