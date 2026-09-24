import { PAGINAS, paginasPara, type Pagina } from '../utils/paginas'

export type { Pagina }

// Navegación por estado y no con un router: meter react-router sería una
// dependencia nueva fuera de lo acordado en el spec. La contra: no hay
// enlaces directos a cada pantalla ni botón "atrás" del navegador.
export function Navegacion({
  actual,
  nivel,
  onCambiar,
}: {
  actual: Pagina
  nivel: number
  onCambiar: (pagina: Pagina) => void
}) {
  const visibles = paginasPara(nivel)
  return (
    <nav className="flex flex-col gap-1">
      {PAGINAS.filter((p) => visibles.includes(p.clave)).map(({ clave, texto }) => {
        const activa = clave === actual
        return (
          <button
            key={clave}
            type="button"
            onClick={() => onCambiar(clave)}
            aria-current={activa ? 'page' : undefined}
            className={`flex h-5 items-center rounded-control border-l-2 px-2 text-left transition-colors ${
              activa
                ? 'border-acento bg-lateral-activo font-semibold text-lateral-activo-texto'
                : 'border-transparent text-lateral-muted hover:bg-lateral-hover hover:text-lateral-texto'
            }`}
          >
            {texto}
          </button>
        )
      })}
    </nav>
  )
}
