import type { Pesada } from '../types/pesada'
import { ESTADO_POR_CLAVE } from '../utils/estados'
import type { ClaveEstado, FilaPesada } from '../utils/tablero'
import { formatearMinutos, horaCorta } from '../utils/tiempo'
import { Punto } from './Punto'

function EtiquetaEstado({ estado }: { estado: ClaveEstado }) {
  const { etiqueta, punto } = ESTADO_POR_CLAVE[estado]
  return (
    <span className="flex items-center gap-1">
      <Punto color={punto} />
      {etiqueta}
    </span>
  )
}

const TH = 'px-2 text-left font-semibold text-muted'
const TD = 'px-2'

/**
 * Número de ticket como botón: abre el detalle. Es lo que hace la fila
 * accesible por teclado (Tab + Enter); el clic en cualquier otra parte de
 * la fila hace lo mismo, como atajo para el mouse.
 */
export function BotonTicket({ pesada, onAbrir }: { pesada: Pesada; onAbrir: (p: Pesada) => void }) {
  return (
    <button
      type="button"
      onClick={(e) => {
        // La fila también abre al hacer clic: sin esto se abriría dos veces.
        e.stopPropagation()
        onAbrir(pesada)
      }}
      aria-label={`Ver detalle del ticket ${pesada.numero_ticket}`}
      className="rounded-control font-semibold underline-offset-2 hover:underline"
    >
      {pesada.numero_ticket}
    </button>
  )
}

export function ListaPesadas({
  filas,
  onAbrir,
}: {
  filas: FilaPesada[]
  /** Si viene, cada fila abre el detalle de su pesada. */
  onAbrir?: (pesada: Pesada) => void
}) {
  if (filas.length === 0) {
    return (
      <p className="rounded-card border border-borde bg-card p-4 text-center text-muted">
        No hay pesadas para este filtro.
      </p>
    )
  }

  return (
    <div className="overflow-x-auto rounded-card border border-borde bg-card">
      <table className="w-full min-w-88 border-collapse">
        <thead>
          <tr className="h-6 border-b border-borde">
            <th className={TH}>Ticket</th>
            <th className={TH}>Vehículo</th>
            <th className={TH}>Producto / Empresa</th>
            <th className={TH}>Estado</th>
            <th className={`${TH} text-right`}>Espera</th>
          </tr>
        </thead>
        <tbody>
          {filas.map(({ pesada, estado, demorada, minutos }) => (
            <tr
              key={`${estado}-${pesada.id}`}
              onClick={onAbrir && (() => onAbrir(pesada))}
              className={`h-6 border-b border-borde transition-colors last:border-0 hover:bg-borde ${
                onAbrir ? 'cursor-pointer' : ''
              }`}
            >
              <td className={`${TD} font-semibold`}>
                {onAbrir ? <BotonTicket pesada={pesada} onAbrir={onAbrir} /> : pesada.numero_ticket}
                {pesada.es_manual && (
                  <span
                    className="ml-1 font-normal text-muted"
                    title="El peso se cargó a mano, no lo tomó la báscula"
                  >
                    manual
                  </span>
                )}
              </td>
              <td className={TD}>{pesada.vehiculo?.placa ?? '—'}</td>
              <td className={`${TD} text-muted`}>
                {pesada.producto?.nombre ??
                  pesada.empresa_cliente_proveedor ??
                  pesada.empresa_transportista ??
                  '—'}
              </td>
              <td className={TD}>
                <EtiquetaEstado estado={estado} />
              </td>
              <td className={`${TD} text-right tabular-nums`}>
                {/* `minutos` ya viene medido desde la fecha que corresponde
                    a cada estado (ver utils/tablero.ts). */}
                {estado === 'completadas' ? (
                  <span className="text-muted">{horaCorta(pesada.fecha_salida)}</span>
                ) : demorada ? (
                  // El punto rojo nunca va solo: la palabra dice lo mismo.
                  <span
                    className="inline-flex items-center gap-1 font-semibold"
                    title="Lleva más tiempo del esperado en este estado"
                  >
                    <Punto color="bg-error" />
                    Demorada · {formatearMinutos(minutos)}
                  </span>
                ) : (
                  <span className="text-muted">{formatearMinutos(minutos)}</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
