import { tiempoTranscurrido } from '../utils/tiempo'
import { Punto } from './Punto'

function textoActualizado(fecha: string) {
  const hace = tiempoTranscurrido(fecha)
  return hace === 'recién' ? 'Actualizado recién' : `Actualizado hace ${hace}`
}

/**
 * Conexión en vivo con el servidor central (el WebSocket), no con la
 * báscula: esa es local a la PC de la Romana y la web no la ve.
 * Nunca solo color: punto + texto. Si se cayó hay que decirlo, no dejar
 * datos viejos pasando por datos en vivo.
 */
export function EstadoConexion({
  conectado,
  actualizado,
}: {
  conectado: boolean
  actualizado: string | null
}) {
  return (
    <div role="status" className="flex flex-col gap-1">
      <div className="flex items-center gap-1">
        <Punto color={conectado ? 'bg-exito' : 'bg-error'} />
        <span className="font-semibold">
          {conectado ? 'Conectado al servidor' : 'Sin conexión al servidor'}
        </span>
      </div>
      <span className="text-lateral-muted">
        {actualizado ? textoActualizado(actualizado) : 'Esperando datos…'}
      </span>
    </div>
  )
}
