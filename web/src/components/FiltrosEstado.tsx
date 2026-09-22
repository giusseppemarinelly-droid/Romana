import { ESTADOS } from '../utils/estados'
import type { ClaveEstado, FilaPesada } from '../utils/tablero'

export type Filtro = ClaveEstado | 'todas'

export function FiltrosEstado({
  filas,
  actual,
  onCambiar,
}: {
  filas: FilaPesada[]
  actual: Filtro
  onCambiar: (filtro: Filtro) => void
}) {
  const opciones: { clave: Filtro; etiqueta: string; cantidad: number }[] = [
    { clave: 'todas', etiqueta: 'Todas', cantidad: filas.length },
    ...ESTADOS.map((estado) => ({
      clave: estado.clave as Filtro,
      etiqueta: estado.etiqueta,
      cantidad: filas.filter((f) => f.estado === estado.clave).length,
    })),
  ]

  return (
    <div className="flex flex-wrap gap-1">
      {opciones.map(({ clave, etiqueta, cantidad }) => {
        const activo = clave === actual
        return (
          <button
            key={clave}
            type="button"
            onClick={() => onCambiar(clave)}
            aria-pressed={activo}
            className={`flex h-5 items-center gap-1 rounded-control border px-2 transition-colors ${
              activo
                ? 'border-acento bg-acento text-blanco hover:bg-acento-hover'
                : 'border-borde text-muted hover:bg-borde hover:text-texto'
            }`}
          >
            {etiqueta}
            <span className="font-semibold tabular-nums">{cantidad}</span>
          </button>
        )
      })}
    </div>
  )
}
