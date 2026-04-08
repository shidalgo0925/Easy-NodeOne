import { useState } from 'react'

const API_BASE = (import.meta.env.VITE_API_URL || import.meta.env.VITE_APP_URL || '').replace(/\/$/, '')
const CALENDLY_URL = import.meta.env.VITE_CALENDLY_URL || 'https://calendly.com/easynodeone26'

export default function DemoForm() {
  const [form, setForm] = useState({ name: '', company: '', phone: '', message: '' })
  const [sending, setSending] = useState(false)
  const [feedback, setFeedback] = useState('')

  async function onSubmit(e) {
    e.preventDefault()
    setFeedback('')

    if (!form.name || !form.company || !form.phone || !form.message) {
      setFeedback('Completa todos los campos.')
      return
    }

    const endpoint = API_BASE ? `${API_BASE}/api/public/demo-request` : '/api/public/demo-request'
    setSending(true)
    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...form, source: 'landing' }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok || !data.success) {
        setFeedback(data.error || 'No se pudo enviar tu solicitud.')
      } else {
        setForm({ name: '', company: '', phone: '', message: '' })
        setFeedback('Solicitud enviada. Te contactaremos pronto.')
      }
    } catch {
      setFeedback('Error de conexion. Intenta nuevamente.')
    } finally {
      setSending(false)
    }
  }

  return (
    <section id="contacto" className="px-4 py-12 md:py-16">
      <div className="mx-auto max-w-6xl">
        <h2 id="demo" className="text-center text-2xl font-bold text-gray-dark md:text-3xl">Solicitar Demo</h2>
        <p className="mt-3 text-center text-gray-mid">Dejanos tus datos o agenda directo en el calendario.</p>
        <div className="mt-8 grid gap-5 lg:grid-cols-2">
          <form onSubmit={onSubmit} className="space-y-4 rounded-2xl bg-white p-6 shadow-soft">
            <input
              type="text"
              placeholder="Nombre"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="w-full rounded-lg border border-gray-mid/30 px-4 py-2.5"
            />
            <input
              type="text"
              placeholder="Empresa"
              value={form.company}
              onChange={(e) => setForm({ ...form, company: e.target.value })}
              className="w-full rounded-lg border border-gray-mid/30 px-4 py-2.5"
            />
            <input
              type="tel"
              placeholder="Telefono"
              value={form.phone}
              onChange={(e) => setForm({ ...form, phone: e.target.value })}
              className="w-full rounded-lg border border-gray-mid/30 px-4 py-2.5"
            />
            <textarea
              placeholder="Mensaje"
              rows={3}
              value={form.message}
              onChange={(e) => setForm({ ...form, message: e.target.value })}
              className="w-full rounded-lg border border-gray-mid/30 px-4 py-2.5"
            />
            <p className="text-xs text-gray-mid">Al enviar aceptas que te contactemos por correo o telefono para la demo.</p>
            <button
              type="submit"
              disabled={sending}
              className="w-full rounded-xl bg-gradient-official py-3.5 font-semibold text-white shadow-soft disabled:opacity-60"
            >
              {sending ? 'Enviando...' : 'Enviar'}
            </button>
            {feedback && <p className="text-center text-sm text-gray-mid">{feedback}</p>}
            <a href="https://wa.me/50761842170" className="block text-center text-sm font-medium text-secondary hover:opacity-90">
              O escribenos por WhatsApp
            </a>
          </form>

          <div className="rounded-2xl bg-white p-3 shadow-soft">
            <iframe
              title="Calendario de demos"
              src={`${CALENDLY_URL}?hide_gdpr_banner=1`}
              className="h-[700px] w-full rounded-xl border border-gray-mid/20"
              loading="lazy"
            />
          </div>
        </div>
      </div>
    </section>
  )
}
