export default function SecurityTrustBand() {
  return (
    <section id="seguridad" className="scroll-mt-24 border-t border-slate-200 bg-white px-4 py-14 md:py-16">
      <div className="mx-auto grid max-w-6xl gap-10 md:grid-cols-2 md:items-center">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 md:text-3xl">Seguro, escalable y auditable</h2>
          <p className="mt-3 text-slate-600">
            Arquitectura multi-tenant con separación de datos, backups y controles de acceso alineados a operación
            institucional.
          </p>
        </div>
        <ul className="space-y-3 text-sm font-medium text-slate-800">
          {[
            'Infraestructura en la nube',
            'Backups automáticos',
            'Cifrado en tránsito y en reposo (según despliegue)',
            'Roles y permisos granulares',
            'Auditoría y trazabilidad de acciones',
          ].map((t) => (
            <li key={t} className="flex items-start gap-3">
              <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-secondary/15 text-xs text-secondary">
                ✓
              </span>
              {t}
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}
