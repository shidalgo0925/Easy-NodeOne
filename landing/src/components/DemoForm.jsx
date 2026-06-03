import { useState } from 'react'
import ProductFigure from './landing/ProductFigure'

const API_BASE = (import.meta.env.VITE_API_URL || import.meta.env.VITE_APP_URL || '').replace(/\/$/, '')
/** Solo para enlace externo (nueva pestaña). No iframe. Si está vacío, no se muestra el botón Calendly. */
const CALENDLY_EXTERNAL_URL = (import.meta.env.VITE_CALENDLY_URL || '').trim()
const WHATSAPP_URL = (import.meta.env.VITE_WHATSAPP_URL || 'https://wa.me/50761842170').trim()
const CONTACT_EMAIL = (import.meta.env.VITE_CONTACT_EMAIL || 'info@easynodeone.com').trim()

export default function DemoForm() {
  const [form, setForm] = useState({ name: '', company: '', phone: '', message: '' })
  const [sending, setSending] = useState(false)
  const [feedback, setFeedback] = useState('')
  const [success, setSuccess] = useState(false)

  async function onSubmit(e) {
    e.preventDefault()
    setFeedback('')
    setSuccess(false)

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
        setSuccess(true)
        setFeedback('Solicitud recibida. Nuestro equipo te contactará para coordinar la demo.')
      }
    } catch {
      setFeedback('Error de conexion. Intenta nuevamente.')
      setSuccess(false)
    } finally {
      setSending(false)
    }
  }

  return (
    <section id="contacto" className="bg-slate-50 px-4 py-12 md:py-16">
      <div className="mx-auto max-w-6xl">
        <h2 id="demo" className="text-center text-2xl font-bold text-gray-dark md:text-3xl">
          Solicitar demo
        </h2>
        <p className="mx-auto mt-3 max-w-2xl text-center text-gray-mid">
          Completá el formulario: el lead queda registrado en EN1 y te contactamos para coordinar la demo. Si querés
          ver algo “vivo” antes, esta es la misma experiencia de calendario y agenda que usan los equipos para{' '}
          <strong>eventos</strong> dentro de la plataforma.
        </p>

        <div className="mt-10 grid gap-10 lg:grid-cols-2 lg:items-start">
          <div className="order-2 lg:order-1">
            <ProductFigure
              className="mt-0"
              src="/images/product/gestion-eventos.png"
              alt="Vista de gestión de eventos en EN1 con calendario, lista de eventos y resumen del día."
              caption="Calendario y agenda de la operación de eventos en EN1. La coordinación de tu demo personal la hace nuestro equipo al recibir tu solicitud (o podés usar el enlace externo a Calendly si lo habilitamos)."
            />
          </div>

          <div className="order-1 mx-auto w-full max-w-xl lg:order-2 lg:mx-0 lg:max-w-none">
            <form onSubmit={onSubmit} className="space-y-4 rounded-2xl bg-white p-6 shadow-soft">
              <input
                type="text"
                placeholder="Nombre"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="w-full rounded-lg border border-gray-mid/30 px-4 py-2.5"
                autoComplete="name"
              />
              <input
                type="text"
                placeholder="Empresa"
                value={form.company}
                onChange={(e) => setForm({ ...form, company: e.target.value })}
                className="w-full rounded-lg border border-gray-mid/30 px-4 py-2.5"
                autoComplete="organization"
              />
              <input
                type="tel"
                placeholder="Teléfono"
                value={form.phone}
                onChange={(e) => setForm({ ...form, phone: e.target.value })}
                className="w-full rounded-lg border border-gray-mid/30 px-4 py-2.5"
                autoComplete="tel"
              />
              <textarea
                placeholder="Mensaje"
                rows={4}
                value={form.message}
                onChange={(e) => setForm({ ...form, message: e.target.value })}
                className="w-full rounded-lg border border-gray-mid/30 px-4 py-2.5"
              />
              <p className="text-xs text-gray-mid">
                Al enviar aceptás que te contactemos por correo o teléfono para la demo. Los datos se guardan en EN1
                (solicitud de demo).
              </p>
              <button
                type="submit"
                disabled={sending}
                className="w-full rounded-xl bg-gradient-official py-3.5 font-semibold text-white shadow-soft disabled:opacity-60"
              >
                {sending ? 'Enviando...' : 'Enviar solicitud'}
              </button>
              {feedback && (
                <p
                  className={`text-center text-sm ${success ? 'font-medium text-emerald-700' : 'text-gray-mid'}`}
                  role="status"
                >
                  {feedback}
                </p>
              )}

              <div className="border-t border-gray-light pt-4">
                <p className="text-center text-xs font-semibold uppercase tracking-wide text-gray-mid">
                  Otras formas de contacto
                </p>
                <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:justify-center">
                  <a
                    href={WHATSAPP_URL}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex justify-center rounded-xl border-2 border-secondary/30 px-4 py-2.5 text-center text-sm font-semibold text-secondary transition hover:bg-secondary/5"
                  >
                    WhatsApp
                  </a>
                  <a
                    href={`mailto:${CONTACT_EMAIL}?subject=${encodeURIComponent('Demo EasyNodeOne')}`}
                    className="inline-flex justify-center rounded-xl border-2 border-gray-mid/20 px-4 py-2.5 text-center text-sm font-semibold text-gray-dark transition hover:border-secondary/30 hover:text-secondary"
                  >
                    Correo: {CONTACT_EMAIL}
                  </a>
                  {CALENDLY_EXTERNAL_URL ? (
                    <a
                      href={CALENDLY_EXTERNAL_URL}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex justify-center rounded-xl border border-dashed border-gray-mid/40 px-4 py-2.5 text-center text-sm font-medium text-gray-mid transition hover:border-secondary hover:text-secondary"
                    >
                      Agendar en Calendly (externo)
                    </a>
                  ) : null}
                </div>
                {!CALENDLY_EXTERNAL_URL ? (
                  <p className="mt-2 text-center text-[11px] text-gray-mid">
                    Si preferís elegir horario vos mismo, podés usar Calendly desde el enlace que te enviemos por
                    correo.
                  </p>
                ) : null}
              </div>
            </form>
          </div>
        </div>
      </div>
    </section>
  )
}
