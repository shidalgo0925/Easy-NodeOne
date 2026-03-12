export default function Footer() {
  return (
    <footer className="bg-gray-dark px-4 pt-8 pb-6 text-gray-300">
      <div className="mx-auto max-w-6xl">
        <img src="/logos/logo-nodeone-dark.png" alt="Easy NodeOne" className="mb-8 h-[97px] w-auto opacity-90" />
      </div>
      <div className="mx-auto grid max-w-6xl gap-8 md:grid-cols-3">
        <div>
          <h4 className="font-semibold text-white">Producto</h4>
          <ul className="mt-3 space-y-2">
            <li><a href="#plataforma" className="hover:text-white">Plataforma</a></li>
            <li><a href="#modulos" className="hover:text-white">Módulos</a></li>
            <li><a href="#seguridad" className="hover:text-white">Seguridad</a></li>
          </ul>
        </div>
        <div>
          <h4 className="font-semibold text-white">Empresa</h4>
          <ul className="mt-3 space-y-2">
            <li>Easy Tech</li>
            <li><a href="#contacto" className="hover:text-white">Contacto</a></li>
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
      <div className="mx-auto mt-8 max-w-6xl border-t border-gray-mid/30 pt-8 text-center text-sm">
        Redes sociales
      </div>
    </footer>
  )
}
