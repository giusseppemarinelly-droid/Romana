export type Pagina = 'tablero' | 'estadisticas' | 'costos'

const PAGINAS: { clave: Pagina; texto: string }[] = [
  { clave: 'tablero', texto: 'Pesajes en vivo' },
  { clave: 'estadisticas', texto: 'Estadísticas' },
  { clave: 'costos', texto: 'Costos' },
]

// Navegación por estado y no con un router: son tres pantallas y meter
// react-router sería una dependencia nueva fuera de lo acordado en el
// spec. La contra: no hay enlaces directos a cada pantalla ni botón
// "atrás" del navegador. Si aparecen más pantallas, conviene revisarlo.
export function Navegacion({
  actual,
  onCambiar,
}: {
  actual: Pagina
  onCambiar: (pagina: Pagina) => void
}) {
  return (
    <nav className="flex flex-col gap-1">
      {PAGINAS.map(({ clave, texto }) => {
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
