export default function Footer() {
  return (
    <footer className="bg-gray-dark px-4 pt-5 pb-4 text-gray-300">
      <div className="mx-auto max-w-6xl">
        <img src="/logos/logo-nodeone-dark.png" alt="EasyNodeOne" className="mb-5 h-[72px] w-auto opacity-90 md:h-[80px]" />
      </div>
      <div className="mx-auto grid max-w-6xl gap-5 md:grid-cols-3">
        <div>
          <h4 className="font-semibold text-white">Producto</h4>
          <ul className="mt-3 space-y-2">
            <li><a href="/features" className="hover:text-white">Plataforma</a></li>
            <li><a href="/pricing" className="hover:text-white">Planes</a></li>
            <li><a href="/use-cases" className="hover:text-white">Casos de uso</a></li>
            <li><a href="/integrations" className="hover:text-white">Integraciones</a></li>
            <li><a href="/features#seguridad" className="hover:text-white">Seguridad</a></li>
          </ul>
        </div>
        <div>
          <h4 className="font-semibold text-white">Empresa</h4>
          <ul className="mt-3 space-y-2">
            <li>Easy Tech</li>
            <li><a href="/contact#contacto" className="hover:text-white">Contacto</a></li>
          </ul>
        </div>
        <div>
          <h4 className="font-semibold text-white">Legal</h4>
          <ul className="mt-3 space-y-2">
            <li><a href="#" className="hover:text-white">Términos</a></li>
            <li><a href="#" className="hover:text-white">Privacidad</a></li>
          </ul>
        </div>
      </div>
      <div className="mx-auto mt-5 max-w-6xl border-t border-gray-mid/30 pt-5 text-center text-sm">
        Redes sociales
      </div>
    </footer>
  )
}
