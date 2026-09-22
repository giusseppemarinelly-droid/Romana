import type { Pesada } from '../types/pesada'
import { CAMPO_DE_REFERENCIA, estaDemorada, UMBRALES_DEMORA_MIN } from './demoras'

export interface DatosTablero {
  enPlanta: Pesada[]
  pendientesAprobacion: Pesada[]
  rechazadas: Pesada[]
  aprobadas: Pesada[]
  completadas: Pesada[]
}

export type ClaveEstado = keyof DatosTablero

export interface FilaPesada {
  pesada: Pesada
  estado: ClaveEstado
  /** Minutos esperando en ese estado; null en las completadas (ya no esperan) o si falta la fecha. */
  minutos: number | null
  demorada: boolean
}

/** El estado de cada fila viene del listado del que salió, no del campo
 *  `estado` de la pesada: las rechazadas, por ejemplo, se piden por el
 *  kardex y conviene que la fila diga de qué cola viene. */
const CLAVE_DE_DEMORA: Record<ClaveEstado, keyof typeof UMBRALES_DEMORA_MIN | null> = {
  enPlanta: 'enPlanta',
  pendientesAprobacion: 'esperandoCostos',
  rechazadas: 'rechazadas',
  aprobadas: 'aprobadas',
  completadas: null,
}

function minutosEsperando(pesada: Pesada, estado: ClaveEstado, ahora: Date): number | null {
  const claveDemora = CLAVE_DE_DEMORA[estado]
  if (!claveDemora) return null

  const desde = pesada[CAMPO_DE_REFERENCIA[claveDemora]] as string | null
  if (!desde) return null
  return (ahora.getTime() - new Date(desde).getTime()) / 60_000
}

/**
 * Convierte las cinco colas en una sola lista ordenada por urgencia: lo
 * que lleva más tiempo trabado primero, y las completadas al final (no
 * están esperando nada, se muestran como historial reciente).
 */
export function aplanarTablero(datos: DatosTablero, ahora: Date = new Date()): FilaPesada[] {
  const filas: FilaPesada[] = (Object.keys(datos) as ClaveEstado[]).flatMap((estado) =>
    datos[estado].map((pesada) => ({
      pesada,
      estado,
      minutos: minutosEsperando(pesada, estado, ahora),
      demorada: estaDemorada(pesada, CLAVE_DE_DEMORA[estado] ?? '', ahora),
    })),
  )

  const activas = filas.filter((f) => f.estado !== 'completadas')
  const completadas = filas.filter((f) => f.estado === 'completadas')

  // Sin fecha de referencia no se puede medir la espera: van al final de
  // las activas en vez de colarse arriba como si fueran urgentes.
  activas.sort((a, b) => (b.minutos ?? -1) - (a.minutos ?? -1))
  completadas.sort(
    (a, b) =>
      new Date(b.pesada.fecha_salida ?? 0).getTime() - new Date(a.pesada.fecha_salida ?? 0).getTime(),
  )

  return [...activas, ...completadas]
}
