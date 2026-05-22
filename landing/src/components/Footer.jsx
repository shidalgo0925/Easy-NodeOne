export default function Footer() {
  return (
    <footer className="bg-gray-dark px-4 pt-8 pb-6 text-gray-300">
      <div className="mx-auto max-w-6xl">
        <img
          src="/logos/logo-nodeone-dark.png"
          alt="EasyNodeOne"
          className="mb-6 h-[72px] w-auto opacity-90 md:h-[80px]"
        />
      </div>
      <div className="mx-auto grid max-w-6xl gap-8 md:grid-cols-2 lg:grid-cols-4">
        <div>
          <h4 className="font-semibold text-white">Producto</h4>
          <ul className="mt-3 space-y-2 text-sm">
            <li>
              <a href="/#ecosistema" className="hover:text-white">
                Ecosistema EN1
              </a>
            </li>
            <li>
              <a href="/#casos" className="hover:text-white">
                Casos de uso
              </a>
            </li>
            <li>
              <a href="/#multitenant" className="hover:text-white">
                Multi-tenant
              </a>
            </li>
            <li>
              <a href="/pricing" className="hover:text-white">
                Planes
              </a>
            </li>
          </ul>
        </div>
        <div>
          <h4 className="font-semibold text-white">Desarrollo y operación</h4>
          <ul className="mt-3 space-y-2 text-sm">
            <li>
              <a href="/#apis" className="hover:text-white">
                API e integraciones
              </a>
            </li>
            <li>
              <a href="/integrations" className="hover:text-white">
                Documentación / roadmap
              </a>
            </li>
            <li>
              <a href="/#seguridad" className="hover:text-white">
                Arquitectura y seguridad
              </a>
            </li>
            <li>
              <a href="/#contacto" className="hover:text-white">
                Soporte y contacto
              </a>
            </li>
          </ul>
        </div>
        <div>
          <h4 className="font-semibold text-white">Empresa</h4>
          <ul className="mt-3 space-y-2 text-sm">
            <li>Easy Tech</li>
            <li>
              <a href="mailto:info@easynodeone.com" className="hover:text-white">
                info@easynodeone.com
              </a>
            </li>
          </ul>
        </div>
        <div>
          <h4 className="font-semibold text-white">Legal</h4>
          <ul className="mt-3 space-y-2 text-sm">
            <li>
              <a href="/#contacto" className="hover:text-white">
                Términos
              </a>
            </li>
            <li>
              <a href="/#contacto" className="hover:text-white">
                Privacidad
              </a>
            </li>
          </ul>
        </div>
      </div>
      <div className="mx-auto mt-8 max-w-6xl border-t border-gray-mid/30 pt-6 text-center text-xs text-slate-500">
        © {new Date().getFullYear()} EasyNodeOne · EN1
      </div>
    </footer>
  )
}
