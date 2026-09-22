import type { Pesada } from '../types/pesada'

/**
 * A partir de cuándo una pesada lleva "demasiado" en cada estado. Son
 * valores de arranque, pensados para que el supervisor vea lo que se
 * está trabando; si en la planta resultan altos o bajos, se ajustan
 * acá (y si alguna vez hay que cambiarlos sin recompilar, el lugar
 * natural sería la tabla de Configuración, como la tolerancia de
 * aprobación).
 */
export const UMBRALES_DEMORA_MIN = {
  enPlanta: 4 * 60, // un camión esperando a ser cargado más de 4 h
  esperandoCostos: 60, // una pesada esperando decisión más de 1 h
  rechazadas: 30, // rechazada y todavía sin volver a pesar
  aprobadas: 30, // aprobada y todavía sin cerrar en Romana
} as const

export type ColumnaConDemora = keyof typeof UMBRALES_DEMORA_MIN

/** Fecha desde la que se cuenta la espera en cada columna. */
export const CAMPO_DE_REFERENCIA: Record<ColumnaConDemora, keyof Pesada> = {
  enPlanta: 'fecha_entrada',
  esperandoCostos: 'fecha_captura',
  rechazadas: 'fecha_captura',
  aprobadas: 'fecha_aprobacion',
}

export function estaDemorada(
  pesada: Pesada,
  columna: string,
  ahora: Date = new Date(),
): boolean {
  if (!(columna in UMBRALES_DEMORA_MIN)) return false

  const clave = columna as ColumnaConDemora
  const desde = pesada[CAMPO_DE_REFERENCIA[clave]] as string | null
  if (!desde) return false

  const minutos = (ahora.getTime() - new Date(desde).getTime()) / 60_000
  return minutos > UMBRALES_DEMORA_MIN[clave]
}
